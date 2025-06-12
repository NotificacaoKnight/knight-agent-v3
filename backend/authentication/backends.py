import jwt
import requests
from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import User, UserSession
from .services import MicrosoftAuthService

class MicrosoftAuthBackend(BaseBackend):
    """Backend de autenticação para Microsoft Azure AD"""
    
    def authenticate(self, request, microsoft_token=None, **kwargs):
        if not microsoft_token:
            return None
            
        try:
            # Verificar e decodificar o token Microsoft
            user_info = MicrosoftAuthService.verify_token(microsoft_token)
            
            # Buscar ou criar usuário
            user, created = User.objects.get_or_create(
                microsoft_id=user_info['oid'],
                defaults={
                    'username': user_info.get('preferred_username', ''),
                    'email': user_info.get('email', ''),
                    'first_name': user_info.get('given_name', ''),
                    'last_name': user_info.get('family_name', ''),
                    'preferred_name': user_info.get('name', ''),
                    'department': user_info.get('department', ''),
                    'job_title': user_info.get('jobTitle', ''),
                }
            )
            
            return user
            
        except Exception as e:
            return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

class MicrosoftAuthAuthentication(BaseAuthentication):
    """Autenticação para DRF usando tokens Microsoft"""
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
            
        token = auth_header.split(' ')[1]
        
        try:
            # Verificar se é um token de sessão interno
            session = UserSession.objects.get(
                session_token=token,
                is_active=True
            )
            
            if session.is_expired():
                raise AuthenticationFailed('Token expirado')
                
            return (session.user, token)
            
        except UserSession.DoesNotExist:
            # Se não for token de sessão, tentar como token Microsoft
            try:
                user_info = MicrosoftAuthService.verify_token(token)
                user = User.objects.get(microsoft_id=user_info['oid'])
                return (user, token)
            except:
                raise AuthenticationFailed('Token inválido')
    
    def authenticate_header(self, request):
        return 'Bearer'