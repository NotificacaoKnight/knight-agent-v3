"""
Sistema de auditoria segura para eventos de autenticação
Registra eventos críticos sem expor informações sensíveis
"""
import logging
import hashlib
from datetime import datetime
from django.conf import settings
from django.utils import timezone

# Logger específico para auditoria
audit_logger = logging.getLogger('security_audit')

class SecurityAuditLogger:
    """
    Logger de auditoria de segurança com anonimização de dados sensíveis
    """
    
    @staticmethod
    def hash_sensitive_data(data, salt=None):
        """Hash de dados sensíveis para logs"""
        if not data:
            return "null"
        
        if salt is None:
            salt = settings.SECRET_KEY[:16]
        
        return hashlib.sha256(f"{data}{salt}".encode()).hexdigest()[:12]
    
    @staticmethod
    def log_login_attempt(email, ip_address, user_agent, success=False, error_type=None):
        """Log de tentativa de login"""
        hashed_email = SecurityAuditLogger.hash_sensitive_data(email)
        hashed_ip = SecurityAuditLogger.hash_sensitive_data(ip_address)
        
        event_data = {
            'event': 'login_attempt',
            'email_hash': hashed_email,
            'ip_hash': hashed_ip,
            'user_agent': user_agent[:100] if user_agent else None,
            'success': success,
            'error_type': error_type,
            'timestamp': timezone.now().isoformat()
        }
        
        if success:
            audit_logger.info(f"LOGIN_SUCCESS: {event_data}")
        else:
            audit_logger.warning(f"LOGIN_FAILED: {event_data}")
    
    @staticmethod
    def log_admin_privilege_change(user_id, old_status, new_status, changed_by=None):
        """Log de mudança de privilégios de admin"""
        event_data = {
            'event': 'admin_privilege_change',
            'user_id': user_id,
            'old_admin_status': old_status,
            'new_admin_status': new_status,
            'changed_by': changed_by,
            'timestamp': timezone.now().isoformat()
        }
        
        audit_logger.warning(f"ADMIN_PRIVILEGE_CHANGE: {event_data}")
    
    @staticmethod
    def log_session_created(user_id, session_token_hash, ip_address):
        """Log de criação de sessão"""
        hashed_ip = SecurityAuditLogger.hash_sensitive_data(ip_address)
        hashed_token = SecurityAuditLogger.hash_sensitive_data(session_token_hash)
        
        event_data = {
            'event': 'session_created',
            'user_id': user_id,
            'session_hash': hashed_token,
            'ip_hash': hashed_ip,
            'timestamp': timezone.now().isoformat()
        }
        
        audit_logger.info(f"SESSION_CREATED: {event_data}")
    
    @staticmethod
    def log_security_violation(violation_type, ip_address, details=None):
        """Log de violação de segurança"""
        hashed_ip = SecurityAuditLogger.hash_sensitive_data(ip_address)
        
        event_data = {
            'event': 'security_violation',
            'violation_type': violation_type,
            'ip_hash': hashed_ip,
            'details': details,
            'timestamp': timezone.now().isoformat()
        }
        
        audit_logger.error(f"SECURITY_VIOLATION: {event_data}")
    
    @staticmethod
    def log_token_validation_failure(token_hash, reason, ip_address):
        """Log de falha na validação de token"""
        hashed_ip = SecurityAuditLogger.hash_sensitive_data(ip_address)
        hashed_token = SecurityAuditLogger.hash_sensitive_data(token_hash)
        
        event_data = {
            'event': 'token_validation_failure',
            'token_hash': hashed_token,
            'reason': reason,
            'ip_hash': hashed_ip,
            'timestamp': timezone.now().isoformat()
        }
        
        audit_logger.warning(f"TOKEN_VALIDATION_FAILURE: {event_data}")

def get_client_ip(request):
    """Utility para obter IP do cliente"""
    ip_headers = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_REAL_IP',
        'HTTP_CF_CONNECTING_IP',
        'REMOTE_ADDR'
    ]
    
    for header in ip_headers:
        ip = request.META.get(header)
        if ip:
            return ip.split(',')[0].strip()
    
    return 'unknown'