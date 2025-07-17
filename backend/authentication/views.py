import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from .models import User, UserSession
from .services import MicrosoftAuthService
from .serializers import UserSerializer


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
        
        # Criar ou atualizar usuário
        user, created = User.objects.get_or_create(
            microsoft_id=user_info['id'],
            defaults={
                'username': user_info.get('userPrincipalName', ''),
                'email': user_info.get('mail', user_info.get('userPrincipalName', '')),
                'first_name': user_info.get('givenName', ''),
                'last_name': user_info.get('surname', ''),
                'preferred_name': user_info.get('displayName', ''),
                'department': user_info.get('department', ''),
                'job_title': user_info.get('jobTitle', ''),
            }
        )
        
        # Buscar e salvar foto do perfil (tanto para novos usuários quanto existentes)
        try:
            photo_content = MicrosoftAuthService.get_user_photo(token_result['access_token'])
            if photo_content:
                MicrosoftAuthService.save_user_photo(user, photo_content)
        except Exception as e:
            print(f"Erro ao processar foto do perfil: {str(e)}")
        
        # Criar sessão
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
        # Buscar informações do usuário
        user_info = MicrosoftAuthService.get_user_info(access_token)
        
        # Criar ou atualizar usuário
        user, created = User.objects.get_or_create(
            microsoft_id=user_info['id'],
            defaults={
                'username': user_info.get('userPrincipalName', ''),
                'email': user_info.get('mail', user_info.get('userPrincipalName', '')),
                'first_name': user_info.get('givenName', ''),
                'last_name': user_info.get('surname', ''),
                'preferred_name': user_info.get('displayName', ''),
                'department': user_info.get('department', ''),
                'job_title': user_info.get('jobTitle', ''),
            }
        )
        
        # Buscar e salvar foto do perfil (tanto para novos usuários quanto existentes)
        try:
            photo_content = MicrosoftAuthService.get_user_photo(access_token)
            if photo_content:
                MicrosoftAuthService.save_user_photo(user, photo_content)
        except Exception as e:
            print(f"Erro ao processar foto do perfil: {str(e)}")
        
        # Criar sessão
        session_token = str(uuid.uuid4())
        user_session = UserSession.objects.create(
            user=user,
            session_token=session_token,
            microsoft_token=access_token,
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