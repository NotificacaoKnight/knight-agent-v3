"""
Configuração de administradores automáticos
Lista de emails que devem ter privilégios de administrador automaticamente
"""

# Lista de emails que devem ser administradores automaticamente
ADMIN_EMAILS = [
    'felipe.nascimento@semcon.com',
    'paulo.pereira@semcon.com'
    # Adicione outros emails de administradores aqui
]

# Domínios que podem ter administradores (opcional)
ADMIN_DOMAINS = [
    'semcon.com',
    # Adicione outros domínios se necessário
]

def is_admin_email(email: str) -> bool:
    """
    Verifica se um email deve ter privilégios de administrador
    
    Args:
        email: Email do usuário
        
    Returns:
        True se o email deve ser admin, False caso contrário
    """
    if not email:
        return False
    
    email = email.lower().strip()
    
    # Verificar se email está na lista específica
    if email in [admin_email.lower() for admin_email in ADMIN_EMAILS]:
        return True
    
    # Opcional: verificar se é do domínio admin (descomente se desejar)
    # for domain in ADMIN_DOMAINS:
    #     if email.endswith(f'@{domain}'):
    #         return True
    
    return False

def get_admin_emails():
    """Retorna lista de emails de administradores"""
    return ADMIN_EMAILS.copy()

def add_admin_email(email: str):
    """
    Adiciona email à lista de administradores (para uso programático)
    Nota: Para mudanças permanentes, edite diretamente ADMIN_EMAILS
    """
    global ADMIN_EMAILS
    if email and email not in ADMIN_EMAILS:
        ADMIN_EMAILS.append(email)