import uuid
import logging
import re
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from .models import User, UserSession
from .services import MicrosoftAuthService
from .serializers import UserSerializer
from .admin_config import is_admin_email
from .audit_logging import SecurityAuditLogger, get_client_ip

# Configure secure logging
logger = logging.getLogger(__name__)

# Secure domain validation pattern
VALID_DOMAIN_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@semcon\.com$', re.IGNORECASE)


@api_view(['GET'])
@permission_classes([AllowAny])
def microsoft_login(request):
    """Inicia processo de login Microsoft"""
    state = str(uuid.uuid4())
    request.session['auth_state'] = state
    
    auth_url = MicrosoftAuthService.get_auth_url(state)
    
    return Response({
        'auth_url': auth_url,
        'state': state
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def microsoft_callback(request):
    """Callback do Microsoft Azure AD"""
    code = request.data.get('code')
    state = request.data.get('state')
    
    if not code:
        return Response({'error': 'Código de autorização não fornecido'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Verificar state (CSRF protection) - pular para login via MSAL SPA
    if state != 'msal-spa-login' and state != request.session.get('auth_state'):
        return Response({'error': 'Estado inválido'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Trocar código por token
        token_result = MicrosoftAuthService.exchange_code_for_token(code, state)
        
        # Buscar informações do usuário
        user_info = MicrosoftAuthService.get_user_info(token_result['access_token'])
        
        # Extrair email do usuário
        user_email = user_info.get('mail', user_info.get('userPrincipalName', ''))
        
        # Verificar se deve ser admin
        should_be_admin = is_admin_email(user_email)
        
        # Criar ou atualizar usuário
        user, created = User.objects.get_or_create(
            microsoft_id=user_info['id'],
            defaults={
                'username': user_info.get('userPrincipalName', ''),
                'email': user_email,
                'first_name': user_info.get('givenName', ''),
                'last_name': user_info.get('surname', ''),
                'preferred_name': user_info.get('displayName', ''),
                'department': user_info.get('department', ''),
                'job_title': user_info.get('jobTitle', ''),
                'is_admin': should_be_admin,
            }
        )
        
        # Para usuários existentes, atualizar status de admin se necessário
        if not created and user.is_admin != should_be_admin:
            user.is_admin = should_be_admin
            user.save()
            print(f"✅ Status admin atualizado para {user.email}: {should_be_admin}")
        
        # Buscar e salvar foto do perfil (tanto para novos usuários quanto existentes)
        try:
            photo_content = MicrosoftAuthService.get_user_photo(token_result['access_token'])
            if photo_content:
                MicrosoftAuthService.save_user_photo(user, photo_content)
        except Exception as e:
            print(f"Erro ao processar foto do perfil: {str(e)}")
        
        # Invalidar sessões antigas do usuário
        UserSession.objects.filter(user=user, is_active=True).update(is_active=False)
        
        # Criar nova sessão
        session_token = str(uuid.uuid4())
        user_session = UserSession.objects.create(
            user=user,
            session_token=session_token,
            microsoft_token=token_result['access_token'],
            refresh_token=token_result.get('refresh_token'),
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Login do usuário no Django
        login(request, user)
        
        return Response({
            'user': UserSerializer(user).data,
            'session_token': session_token,
            'expires_at': user_session.expires_at
        })
        
    except Exception as e:
        return Response({'error': str(e)}, 
                       status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def microsoft_token_login(request):
    """Login usando access token do MSAL (SPA)"""
    access_token = request.data.get('access_token')
    
    if not access_token:
        return Response({'error': 'Access token não fornecido'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Obter dados para auditoria
        client_ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Buscar informações do usuário
        user_info = MicrosoftAuthService.get_user_info(access_token)
        
        # Extrair email do usuário
        user_email = user_info.get('mail', user_info.get('userPrincipalName', ''))
        
        # Verificar se deve ser admin
        should_be_admin = is_admin_email(user_email)
        
        # SEGURANÇA: Validação robusta de domínio corporativo
        if not user_email or not VALID_DOMAIN_PATTERN.match(user_email):
            SecurityAuditLogger.log_security_violation(
                'invalid_domain', client_ip, 
                f'Domain: {user_email.split("@")[-1] if "@" in user_email else "unknown"}'
            )
            SecurityAuditLogger.log_login_attempt(
                user_email, client_ip, user_agent, success=False, error_type='invalid_domain'
            )
            return Response({'error': 'Domínio não autorizado'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # SEGURANÇA: Validar tenant ID no token
        if not MicrosoftAuthService.validate_tenant(access_token):
            SecurityAuditLogger.log_security_violation(
                'invalid_tenant', client_ip, 'Token from unauthorized tenant'
            )
            SecurityAuditLogger.log_login_attempt(
                user_email, client_ip, user_agent, success=False, error_type='invalid_tenant'
            )
            return Response({'error': 'Token não pertence ao tenant autorizado'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # SEGURANÇA: Sanitizar e validar microsoft_id
        microsoft_id = str(user_info.get('id', '')).strip()
        if not microsoft_id or len(microsoft_id) > 255:
            logger.error(f"Microsoft ID inválido para usuário: {user_email[:20]}...")
            return Response({'error': 'Dados de autenticação inválidos'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # SEGURANÇA: Transação atomica para evitar race conditions
        with transaction.atomic():
            try:
                user = User.objects.select_for_update().get(microsoft_id=microsoft_id)
                created = False
            except User.DoesNotExist:
                # Verificar se email já existe (prevenir account takeover)
                if User.objects.filter(email=user_email).exists():
                    logger.error(f"Tentativa de criação com email existente: {user_email[:20]}...")
                    return Response({'error': 'Conflito de dados de usuário'}, 
                                   status=status.HTTP_409_CONFLICT)
                
                # Criar novo usuário apenas se não existir
                user = User.objects.create(
                    microsoft_id=microsoft_id,
                    username=user_info.get('userPrincipalName', '')[:150],  # Django limit
                    email=user_email,
                    first_name=user_info.get('givenName', '')[:30],  # Django limit
                    last_name=user_info.get('surname', '')[:150],   # Django limit
                    preferred_name=user_info.get('displayName', '')[:100],
                    department=user_info.get('department', '')[:100],
                    job_title=user_info.get('jobTitle', '')[:100],
                    is_admin=should_be_admin,
                )
                created = True
                logger.info(f"Novo usuário criado com ID: {user.id}")
            
            # Para usuários existentes, atualizar status de admin se necessário
            if not created and user.is_admin != should_be_admin:
                old_status = user.is_admin
                user.is_admin = should_be_admin
                user.save(update_fields=['is_admin'])
                SecurityAuditLogger.log_admin_privilege_change(
                    user.id, old_status, should_be_admin, 'system_auto'
                )
        
            # Buscar e salvar foto do perfil (tanto para novos usuários quanto existentes)
            try:
                photo_content = MicrosoftAuthService.get_user_photo(access_token)
                if photo_content:
                    MicrosoftAuthService.save_user_photo(user, photo_content)
            except Exception as e:
                logger.warning(f"Erro ao processar foto do perfil: {type(e).__name__}")
            
            # SEGURANÇA: Invalidar sessões antigas atomicamente
            UserSession.objects.filter(user=user, is_active=True).update(is_active=False)
            
            # Criar nova sessão
            session_token = str(uuid.uuid4())
            user_session = UserSession.objects.create(
                user=user,
                session_token=session_token,
                microsoft_token=access_token,  # TODO: Criptografar em produção
                expires_at=timezone.now() + timedelta(hours=1)
            )
            
            # Login do usuário no Django
            login(request, user)
            
            # Log de auditoria - login bem-sucedido
            SecurityAuditLogger.log_login_attempt(
                user_email, client_ip, user_agent, success=True
            )
            SecurityAuditLogger.log_session_created(
                user.id, session_token, client_ip
            )
            
            return Response({
                'user': UserSerializer(user).data,
                'session_token': session_token,
                'expires_at': user_session.expires_at
            })
            
    except ValidationError as e:
        SecurityAuditLogger.log_login_attempt(
            request.data.get('access_token', 'unknown')[:20], 
            get_client_ip(request), 
            request.META.get('HTTP_USER_AGENT', ''), 
            success=False, error_type='validation_error'
        )
        return Response({'error': 'Dados de autenticação inválidos'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        SecurityAuditLogger.log_login_attempt(
            request.data.get('access_token', 'unknown')[:20], 
            get_client_ip(request), 
            request.META.get('HTTP_USER_AGENT', ''), 
            success=False, error_type='internal_error'
        )
        logger.error(f"Erro interno no login: {type(e).__name__}: {str(e)}", exc_info=True)
        return Response({'error': 'Erro interno do servidor'}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
@permission_classes([AllowAny])  # Permitir logout mesmo sem autenticação
def logout(request):
    """Logout do usuário"""
    # Tentar obter o token do header
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        # Desativar sessão específica
        UserSession.objects.filter(session_token=token).update(is_active=False)
    
    # Se houver usuário autenticado, desativar todas as suas sessões
    if request.user.is_authenticated:
        UserSession.objects.filter(user=request.user).update(is_active=False)
    
    return Response({'message': 'Logout realizado com sucesso'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Buscar perfil do usuário atual"""
    return Response(UserSerializer(request.user).data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Atualizar perfil do usuário"""
    user = request.user
    
    # Campos permitidos para atualização
    allowed_fields = ['preferred_name', 'theme_preference', 'profile_picture']
    
    for field in allowed_fields:
        if field in request.data:
            setattr(user, field, request.data[field])
    
    user.save()
    
    return Response(UserSerializer(user).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_session(request):
    """Renovar sessão usando refresh token"""
    try:
        # Buscar sessão ativa
        session = UserSession.objects.get(
            user=request.user,
            is_active=True
        )
        
        if session.refresh_token:
            # Renovar token Microsoft
            token_result = MicrosoftAuthService.refresh_token(session.refresh_token)
            
            # Atualizar sessão
            session.microsoft_token = token_result['access_token']
            session.expires_at = timezone.now() + timedelta(hours=1)
            session.save()
            
            return Response({
                'session_token': session.session_token,
                'expires_at': session.expires_at
            })
        else:
            return Response({'error': 'Refresh token não disponível'}, 
                           status=status.HTTP_400_BAD_REQUEST)
            
    except UserSession.DoesNotExist:
        return Response({'error': 'Sessão não encontrada'}, 
                       status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, 
                       status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])  # Permitir verificação sem autenticação
def me(request):
    """Retorna informações do usuário atual"""
    if request.user.is_authenticated:
        return Response({
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'email': request.user.email,
                'preferred_name': request.user.preferred_name,
                'is_admin': getattr(request.user, 'is_admin', False)
            }
        })
    else:
        return Response({
            'authenticated': False,
            'user': None
        })