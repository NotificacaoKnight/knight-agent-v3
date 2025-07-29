from rest_framework.permissions import BasePermission

class IsKnightAdmin(BasePermission):
    """
    Permissão customizada para verificar se o usuário é admin do Knight
    Verifica o campo 'is_admin' em vez do 'is_staff' padrão do Django
    """
    
    def has_permission(self, request, view):
        """
        Verifica se o usuário está autenticado e tem is_admin=True
        """
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'is_admin', False)
        )

class IsKnightAdminOrReadOnly(BasePermission):
    """
    Permissão que permite leitura para todos usuários autenticados,
    mas escrita/edição apenas para admins
    """
    
    def has_permission(self, request, view):
        # Leitura permitida para usuários autenticados
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return bool(request.user and request.user.is_authenticated)
        
        # Escrita apenas para admins
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'is_admin', False)
        )