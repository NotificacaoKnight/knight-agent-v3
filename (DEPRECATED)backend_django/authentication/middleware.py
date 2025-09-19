from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from .models import UserSession

class TokenAuthenticationMiddleware(MiddlewareMixin):
    """Middleware para autenticação via token de sessão"""
    
    def process_request(self, request):
        # Pular se já houver usuário autenticado
        if hasattr(request, 'user') and request.user.is_authenticated:
            return
        
        # Buscar token no header Authorization
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            try:
                # Buscar sessão ativa
                session = UserSession.objects.select_related('user').get(
                    session_token=token,
                    is_active=True
                )
                
                # Verificar se não expirou
                if not session.is_expired():
                    request.user = session.user
                    request.session_token = token
                else:
                    # Desativar sessão expirada
                    session.is_active = False
                    session.save()
                    request.user = AnonymousUser()
            except UserSession.DoesNotExist:
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()