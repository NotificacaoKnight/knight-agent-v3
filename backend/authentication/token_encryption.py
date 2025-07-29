"""
Sistema de criptografia para tokens sensíveis
Criptografa tokens Microsoft antes de armazenar no banco de dados
"""
import base64
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import logging

logger = logging.getLogger(__name__)

class TokenEncryption:
    """
    Classe para criptografar/descriptografar tokens sensíveis
    """
    
    _fernet = None
    
    @classmethod
    def _get_encryption_key(cls):
        """Gera chave de criptografia a partir do SECRET_KEY"""
        if not hasattr(settings, 'SECRET_KEY') or not settings.SECRET_KEY:
            raise ImproperlyConfigured("SECRET_KEY não configurado")
        
        # Usar SECRET_KEY para gerar chave consistente
        key_material = settings.SECRET_KEY.encode('utf-8')
        key_hash = hashlib.sha256(key_material).digest()
        key_b64 = base64.urlsafe_b64encode(key_hash)
        
        return key_b64
    
    @classmethod
    def _get_fernet(cls):
        """Obter instância Fernet para criptografia"""
        if cls._fernet is None:
            try:
                key = cls._get_encryption_key()
                cls._fernet = Fernet(key)
            except Exception as e:
                logger.error(f"Erro ao inicializar criptografia: {type(e).__name__}")
                raise
        
        return cls._fernet
    
    @classmethod
    def encrypt_token(cls, token):
        """
        Criptografar token
        
        Args:
            token (str): Token a ser criptografado
            
        Returns:
            str: Token criptografado em base64
            
        Raises:
            ValueError: Se token for inválido
        """
        if not token or not isinstance(token, str):
            raise ValueError("Token deve ser uma string não vazia")
        
        try:
            fernet = cls._get_fernet()
            encrypted_token = fernet.encrypt(token.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_token).decode('utf-8')
        except Exception as e:
            logger.error(f"Erro ao criptografar token: {type(e).__name__}")
            raise ValueError("Erro na criptografia do token")
    
    @classmethod
    def decrypt_token(cls, encrypted_token):
        """
        Descriptografar token
        
        Args:
            encrypted_token (str): Token criptografado
            
        Returns:
            str: Token descriptografado
            
        Raises:
            ValueError: Se token for inválido ou corrupto
        """
        if not encrypted_token or not isinstance(encrypted_token, str):
            raise ValueError("Token criptografado deve ser uma string não vazia")
        
        try:
            fernet = cls._get_fernet()
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode('utf-8'))
            decrypted_token = fernet.decrypt(encrypted_bytes)
            return decrypted_token.decode('utf-8')
        except Exception as e:
            logger.error(f"Erro ao descriptografar token: {type(e).__name__}")
            raise ValueError("Token corrompido ou inválido")
    
    @classmethod
    def is_encrypted(cls, token):
        """
        Verificar se um token está criptografado
        
        Args:
            token (str): Token a verificar
            
        Returns:
            bool: True se estiver criptografado
        """
        if not token:
            return False
        
        try:
            # Tentar descriptografar para verificar se é válido
            cls.decrypt_token(token)
            return True
        except (ValueError, Exception):
            return False

# Funções utilitárias para compatibilidade com código existente
def encrypt_microsoft_token(token):
    """Criptografar token Microsoft"""
    return TokenEncryption.encrypt_token(token)

def decrypt_microsoft_token(encrypted_token):
    """Descriptografar token Microsoft"""
    return TokenEncryption.decrypt_token(encrypted_token)

def should_encrypt_tokens():
    """Verificar se deve criptografar tokens (produção)"""
    return not getattr(settings, 'DEBUG', True)