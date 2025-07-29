"""
PLANO DE REMEDIAÇÃO DE SEGURANÇA - CÓDIGO DE IMPLEMENTAÇÃO
Knight Agent - Sistema de Autenticação Azure AD
"""

# ==============================================================================
# 1. MODELS.PY - CRIPTOGRAFIA DE TOKENS
# ==============================================================================

"""
# authentication/models.py - SUBSTITUIR UserSession class
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from authentication.token_encryption import TokenEncryption
import logging

logger = logging.getLogger(__name__)

class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=255, unique=True, db_index=True)
    
    # Campos criptografados
    _microsoft_token = models.TextField(db_column='microsoft_token')
    _refresh_token = models.TextField(null=True, blank=True, db_column='refresh_token')
    
    # Metadados de segurança
    created_ip = models.GenericIPAddressField()
    created_user_agent = models.TextField()
    last_used_ip = models.GenericIPAddressField()
    last_used_at = models.DateTimeField(auto_now=True)
    
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Token binding
    device_fingerprint = models.CharField(max_length=64, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['session_token']),
        ]
    
    @property
    def microsoft_token(self):
        """Descriptografa token Microsoft"""
        try:
            return TokenEncryption.decrypt_token(self._microsoft_token) if self._microsoft_token else None
        except Exception as e:
            logger.error(f"Failed to decrypt microsoft token: {type(e).__name__}")
            return None
    
    @microsoft_token.setter
    def microsoft_token(self, value):
        """Criptografa token Microsoft"""
        if value:
            self._microsoft_token = TokenEncryption.encrypt_token(value)
        else:
            self._microsoft_token = None
    
    @property
    def refresh_token(self):
        """Descriptografa refresh token"""
        try:
            return TokenEncryption.decrypt_token(self._refresh_token) if self._refresh_token else None
        except Exception as e:
            logger.error(f"Failed to decrypt refresh token: {type(e).__name__}")
            return None
    
    @refresh_token.setter
    def refresh_token(self, value):
        """Criptografa refresh token"""
        if value:
            self._refresh_token = TokenEncryption.encrypt_token(value)
        else:
            self._refresh_token = None
    
    def is_expired(self):
        """Check if the session has expired"""
        return timezone.now() > self.expires_at
    
    def is_valid_for_ip(self, ip_address):
        """Verifica se sessão é válida para o IP"""
        # Implementar lógica de validação de IP
        # Por enquanto, sempre validar
        return True
    
    def rotate_token(self):
        """Rotaciona o token de sessão"""
        import secrets
        old_token = self.session_token
        self.session_token = secrets.token_urlsafe(32)
        self.save()
        return self.session_token
    
    def __str__(self):
        return f"{self.user.username} - {self.session_token[:10]}..."


# ==============================================================================
# 2. TOKEN_ENCRYPTION.PY - CRIPTOGRAFIA SEGURA
# ==============================================================================

"""
# authentication/token_encryption.py - SUBSTITUIR COMPLETAMENTE
"""
import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import logging

logger = logging.getLogger(__name__)

class TokenEncryption:
    """
    Sistema seguro de criptografia para tokens
    Usa chave separada do SECRET_KEY
    """
    
    _fernet = None
    _key_cache = {}
    
    @classmethod
    def _get_encryption_key(cls, key_version='v1'):
        """Gera chave de criptografia com versionamento"""
        if key_version in cls._key_cache:
            return cls._key_cache[key_version]
        
        # Obter segredo do ambiente (NÃO do SECRET_KEY)
        encryption_secret = os.environ.get('TOKEN_ENCRYPTION_SECRET')
        if not encryption_secret:
            raise ImproperlyConfigured(
                "TOKEN_ENCRYPTION_SECRET must be set in environment variables. "
                "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )
        
        # Validar tamanho mínimo
        if len(encryption_secret) < 32:
            raise ImproperlyConfigured("TOKEN_ENCRYPTION_SECRET must be at least 32 characters")
        
        # Salt único por versão
        salt = f'knight-token-{key_version}'.encode('utf-8')
        
        # Derivar chave usando PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,  # OWASP recommendation
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(encryption_secret.encode()))
        cls._key_cache[key_version] = key
        
        return key
    
    @classmethod
    def _get_fernet(cls):
        """Obter instância Fernet para criptografia"""
        if cls._fernet is None:
            try:
                key = cls._get_encryption_key()
                cls._fernet = Fernet(key)
            except Exception as e:
                logger.error(f"Failed to initialize encryption: {type(e).__name__}")
                raise
        
        return cls._fernet
    
    @classmethod
    def encrypt_token(cls, token):
        """
        Criptografar token com autenticação
        
        Args:
            token (str): Token a ser criptografado
            
        Returns:
            str: Token criptografado com versão
        """
        if not token or not isinstance(token, str):
            raise ValueError("Token must be a non-empty string")
        
        try:
            fernet = cls._get_fernet()
            
            # Adicionar timestamp para evitar replay attacks
            import time
            timestamp = int(time.time()).to_bytes(8, 'big')
            token_with_timestamp = timestamp + token.encode('utf-8')
            
            # Criptografar
            encrypted = fernet.encrypt(token_with_timestamp)
            
            # Adicionar versão para rotação de chaves
            versioned = b'v1:' + encrypted
            
            return base64.urlsafe_b64encode(versioned).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed: {type(e).__name__}")
            raise ValueError("Failed to encrypt token")
    
    @classmethod
    def decrypt_token(cls, encrypted_token):
        """
        Descriptografar token com validação
        
        Args:
            encrypted_token (str): Token criptografado
            
        Returns:
            str: Token descriptografado
        """
        if not encrypted_token or not isinstance(encrypted_token, str):
            raise ValueError("Encrypted token must be a non-empty string")
        
        try:
            # Decodificar base64
            versioned = base64.urlsafe_b64decode(encrypted_token.encode('utf-8'))
            
            # Extrair versão
            if not versioned.startswith(b'v1:'):
                raise ValueError("Unknown token version")
            
            encrypted = versioned[3:]  # Remove 'v1:'
            
            # Descriptografar
            fernet = cls._get_fernet()
            decrypted = fernet.decrypt(encrypted)
            
            # Validar timestamp (máximo 24 horas)
            import time
            timestamp = int.from_bytes(decrypted[:8], 'big')
            current_time = int(time.time())
            
            if current_time - timestamp > 86400:  # 24 horas
                raise ValueError("Token too old")
            
            # Retornar token sem timestamp
            return decrypted[8:].decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed: {type(e).__name__}")
            raise ValueError("Invalid or corrupted token")
    
    @classmethod
    def rotate_encryption_key(cls):
        """Rotação de chaves para o futuro"""
        # Implementar quando necessário
        pass


# ==============================================================================
# 3. SECURE_SERVICES.PY - VALIDAÇÃO SEGURA DE JWT
# ==============================================================================

"""
# authentication/secure_services.py - NOVA CLASSE
"""
import jwt
import requests
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.cache import cache
import hashlib

logger = logging.getLogger(__name__)

class SecureMicrosoftAuthService:
    """Serviço seguro para validação de tokens Microsoft"""
    
    # Cache de chaves públicas
    _public_keys_cache = {}
    _cache_expiry = None
    
    @classmethod
    def get_microsoft_public_keys(cls, force_refresh=False):
        """Obtém chaves públicas da Microsoft com cache"""
        now = datetime.now()
        
        # Verificar cache
        if not force_refresh and cls._cache_expiry and cls._cache_expiry > now:
            return cls._public_keys_cache
        
        try:
            # Buscar chaves
            keys_url = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/discovery/v2.0/keys"
            response = requests.get(keys_url, timeout=10)
            response.raise_for_status()
            
            keys_data = response.json()
            
            # Processar chaves
            cls._public_keys_cache = {}
            for key_data in keys_data['keys']:
                kid = key_data['kid']
                cls._public_keys_cache[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
            
            # Cache por 24 horas
            cls._cache_expiry = now + timedelta(hours=24)
            
            return cls._public_keys_cache
            
        except Exception as e:
            logger.error(f"Failed to fetch Microsoft public keys: {type(e).__name__}")
            if cls._public_keys_cache:  # Use cache antigo se disponível
                return cls._public_keys_cache
            raise ValidationError("Failed to fetch public keys")
    
    @classmethod
    def validate_token_secure(cls, access_token):
        """
        Validação completa e segura do token JWT
        
        Args:
            access_token: Token JWT da Microsoft
            
        Returns:
            dict: Payload validado do token
            
        Raises:
            ValidationError: Se o token for inválido
        """
        if not access_token:
            raise ValidationError("No token provided")
        
        try:
            # 1. Obter header sem verificar (para pegar kid)
            try:
                unverified_header = jwt.get_unverified_header(access_token)
            except jwt.InvalidTokenError:
                raise ValidationError("Malformed token")
            
            # 2. Validar algoritmo
            if unverified_header.get('alg') != 'RS256':
                raise ValidationError("Invalid algorithm")
            
            # 3. Obter chave pública
            kid = unverified_header.get('kid')
            if not kid:
                raise ValidationError("Missing key ID")
            
            public_keys = cls.get_microsoft_public_keys()
            public_key = public_keys.get(kid)
            
            if not public_key:
                # Tentar refresh e buscar novamente
                public_keys = cls.get_microsoft_public_keys(force_refresh=True)
                public_key = public_keys.get(kid)
                
                if not public_key:
                    raise ValidationError("Unknown signing key")
            
            # 4. Validar token com TODAS as verificações
            payload = jwt.decode(
                access_token,
                public_key,
                algorithms=['RS256'],
                audience=settings.AZURE_AD_CLIENT_ID,
                issuer=[
                    f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/v2.0",
                    f"https://sts.windows.net/{settings.AZURE_AD_TENANT_ID}/"
                ],
                options={
                    'verify_signature': True,
                    'verify_aud': True,
                    'verify_iss': True,
                    'verify_exp': True,
                    'verify_nbf': True,
                    'verify_iat': True,
                    'require_exp': True,
                    'require_iat': True,
                }
            )
            
            # 5. Validações adicionais de segurança
            
            # Verificar tenant
            if payload.get('tid') != settings.AZURE_AD_TENANT_ID:
                raise ValidationError("Invalid tenant")
            
            # Verificar que não é um token muito antigo
            iat = payload.get('iat', 0)
            current_time = datetime.now().timestamp()
            if current_time - iat > 3600:  # Token emitido há mais de 1 hora
                raise ValidationError("Token too old")
            
            # Verificar scopes mínimos
            scopes = payload.get('scp', '').split()
            required_scopes = ['User.Read']
            if not all(scope in scopes for scope in required_scopes):
                raise ValidationError("Insufficient scopes")
            
            # 6. Verificar blacklist (para tokens revogados)
            if cls.is_token_blacklisted(access_token):
                raise ValidationError("Token has been revoked")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise ValidationError("Token has expired")
        except jwt.InvalidAudienceError:
            raise ValidationError("Invalid audience")
        except jwt.InvalidIssuerError:
            raise ValidationError("Invalid issuer")
        except jwt.InvalidTokenError as e:
            logger.error(f"JWT validation error: {str(e)}")
            raise ValidationError("Invalid token")
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error validating token: {type(e).__name__}")
            raise ValidationError("Token validation failed")
    
    @classmethod
    def is_token_blacklisted(cls, token):
        """Verifica se token está na blacklist"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return cache.get(f"blacklist:token:{token_hash}") is not None
    
    @classmethod
    def blacklist_token(cls, token, duration=86400):
        """Adiciona token à blacklist"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        cache.set(f"blacklist:token:{token_hash}", True, duration)


# ==============================================================================
# 4. ENHANCED_RATE_LIMITING.PY
# ==============================================================================

"""
# authentication/enhanced_rate_limiting.py - SUBSTITUIR rate_limiting.py
"""
import time
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EnhancedAuthRateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting avançado com detecção de ataques
    """
    
    # Configurações mais restritivas
    RATE_LIMITS = {
        '/api/auth/microsoft/token/': {
            'requests': 3,
            'window': 300,  # 5 minutos
            'lockout_time': 900,  # 15 minutos
            'progressive_lockout': True
        },
        '/api/auth/microsoft/callback/': {
            'requests': 5,
            'window': 300,
            'lockout_time': 600,
            'progressive_lockout': True
        },
        '/api/auth/microsoft/login/': {
            'requests': 10,
            'window': 300,
            'lockout_time': 600,
            'progressive_lockout': False
        },
        '/api/auth/logout/': {
            'requests': 10,
            'window': 60,
            'lockout_time': 300,
            'progressive_lockout': False
        }
    }
    
    # Detecção de padrões suspeitos
    SUSPICIOUS_PATTERNS = {
        'rapid_fire': {'threshold': 5, 'window': 10},  # 5 requests em 10 segundos
        'distributed': {'threshold': 10, 'window': 60},  # 10 IPs diferentes em 1 minuto
        'credential_stuffing': {'threshold': 20, 'window': 300}  # 20 logins falhados em 5 min
    }
    
    def process_request(self, request):
        """Processar request com rate limiting avançado"""
        path = request.path
        
        # Verificar se é endpoint protegido
        if not any(path.startswith(p) for p in self.RATE_LIMITS):
            return None
        
        # Obter configuração
        config = next((self.RATE_LIMITS[p] for p in self.RATE_LIMITS if path.startswith(p)), None)
        if not config:
            return None
        
        # Obter IP do cliente
        client_ip = self.get_client_ip(request)
        if not client_ip:
            return self.block_request("Unable to determine client IP")
        
        # Verificar IP na blacklist
        if self.is_ip_blacklisted(client_ip):
            return self.block_request("IP temporarily blocked", 403)
        
        # Verificar lockout
        lockout_key = f"auth:lockout:{client_ip}:{path}"
        lockout_data = cache.get(lockout_key)
        
        if lockout_data:
            remaining_time = lockout_data['expires'] - datetime.now().timestamp()
            if remaining_time > 0:
                return self.block_request(
                    f"Too many attempts. Try again in {int(remaining_time)} seconds",
                    429,
                    {'retry_after': int(remaining_time)}
                )
        
        # Verificar rate limit
        rate_key = f"auth:rate:{client_ip}:{path}"
        current_requests = cache.get(rate_key, [])
        
        # Filtrar requests antigos
        now = datetime.now()
        cutoff = now - timedelta(seconds=config['window'])
        recent_requests = [req for req in current_requests if req > cutoff.timestamp()]
        
        # Verificar limite
        if len(recent_requests) >= config['requests']:
            # Aplicar lockout
            lockout_multiplier = 1
            
            if config.get('progressive_lockout'):
                # Aumentar tempo de lockout progressivamente
                lockout_count = cache.get(f"auth:lockout:count:{client_ip}", 0) + 1
                cache.set(f"auth:lockout:count:{client_ip}", lockout_count, 86400)
                lockout_multiplier = min(lockout_count, 5)  # Máximo 5x
            
            lockout_duration = config['lockout_time'] * lockout_multiplier
            cache.set(lockout_key, {
                'expires': (now + timedelta(seconds=lockout_duration)).timestamp(),
                'attempts': len(recent_requests)
            }, lockout_duration)
            
            # Log para auditoria
            logger.warning(
                f"Rate limit exceeded for IP {client_ip} on {path}. "
                f"Lockout: {lockout_duration}s (multiplier: {lockout_multiplier})"
            )
            
            # Verificar padrões suspeitos
            self.check_attack_patterns(client_ip, path)
            
            return self.block_request(
                f"Too many attempts. Try again in {lockout_duration} seconds",
                429,
                {'retry_after': lockout_duration}
            )
        
        # Adicionar request atual
        recent_requests.append(now.timestamp())
        cache.set(rate_key, recent_requests, config['window'])
        
        # Detecção de rapid fire
        if len(recent_requests) >= self.SUSPICIOUS_PATTERNS['rapid_fire']['threshold']:
            time_span = recent_requests[-1] - recent_requests[0]
            if time_span <= self.SUSPICIOUS_PATTERNS['rapid_fire']['window']:
                logger.warning(f"Rapid fire detected from IP {client_ip}")
                self.flag_suspicious_ip(client_ip, 'rapid_fire')
        
        return None
    
    def get_client_ip(self, request):
        """Obter IP real considerando proxies confiáveis"""
        # Lista de headers em ordem de prioridade
        ip_headers = [
            'HTTP_CF_CONNECTING_IP',  # Cloudflare
            'HTTP_X_REAL_IP',         # Nginx
            'HTTP_X_FORWARDED_FOR',   # Padrão
            'REMOTE_ADDR'             # Fallback
        ]
        
        for header in ip_headers:
            ip = request.META.get(header)
            if ip:
                # Pegar primeiro IP se houver cadeia
                ip = ip.split(',')[0].strip()
                if self.is_valid_ip(ip) and not self.is_private_ip(ip):
                    return ip
        
        # Fallback para REMOTE_ADDR mesmo se for privado
        return request.META.get('REMOTE_ADDR')
    
    def is_valid_ip(self, ip):
        """Validar formato de IP"""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def is_private_ip(self, ip):
        """Verificar se é IP privado"""
        import ipaddress
        try:
            return ipaddress.ip_address(ip).is_private
        except ValueError:
            return False
    
    def is_ip_blacklisted(self, ip):
        """Verificar se IP está na blacklist"""
        return cache.get(f"auth:blacklist:ip:{ip}") is not None
    
    def blacklist_ip(self, ip, duration=3600):
        """Adicionar IP à blacklist"""
        cache.set(f"auth:blacklist:ip:{ip}", True, duration)
        logger.warning(f"IP {ip} added to blacklist for {duration} seconds")
    
    def flag_suspicious_ip(self, ip, reason):
        """Marcar IP como suspeito"""
        key = f"auth:suspicious:{ip}"
        data = cache.get(key, {'count': 0, 'reasons': []})
        data['count'] += 1
        data['reasons'].append({
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        
        cache.set(key, data, 86400)  # 24 horas
        
        # Auto-blacklist se muito suspeito
        if data['count'] >= 5:
            self.blacklist_ip(ip, 7200)  # 2 horas
    
    def check_attack_patterns(self, ip, path):
        """Detectar padrões de ataque"""
        # Implementar detecção de:
        # - Credential stuffing
        # - Distributed attacks
        # - Password spraying
        pass
    
    def block_request(self, message, status_code=429, extra_data=None):
        """Bloquear request com resposta padronizada"""
        response_data = {
            'error': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if extra_data:
            response_data.update(extra_data)
        
        return JsonResponse(response_data, status=status_code)


# ==============================================================================
# 5. SECURE_VIEWS.PY - VIEWS SEGURAS
# ==============================================================================

"""
# authentication/secure_views.py - CORREÇÕES PARA views.py
"""

# Adicionar no início de views.py:
import secrets
import hashlib
from django.views.decorators.csrf import csrf_protect
from authentication.secure_services import SecureMicrosoftAuthService
from authentication.monitoring import SecurityMonitor

# Função para gerar tokens seguros
def generate_secure_session_token():
    """Gera token de sessão criptograficamente seguro"""
    return secrets.token_urlsafe(32)

# Função para tratamento seguro de erros
def handle_auth_error(e, request=None, user_email=None):
    """Tratamento seguro de erros sem expor informações"""
    import uuid
    error_id = str(uuid.uuid4())
    
    # Log interno detalhado
    logger.error(
        f"Auth error {error_id}: {type(e).__name__}: {str(e)}",
        exc_info=True,
        extra={
            'error_id': error_id,
            'user_email': user_email[:20] + '...' if user_email else 'unknown',
            'ip': get_client_ip(request) if request else 'unknown'
        }
    )
    
    # Mapeamento de erros genéricos
    error_messages = {
        ValidationError: "Authentication failed",
        jwt.ExpiredSignatureError: "Session expired",
        jwt.InvalidTokenError: "Invalid credentials",
    }
    
    # Mensagem genérica
    message = error_messages.get(type(e), "Authentication error")
    
    # Se for erro crítico, alertar equipe
    if not isinstance(e, (ValidationError, jwt.ExpiredSignatureError)):
        alert_security_team(error_id, e, request)
    
    return Response({
        'error': message,
        'error_id': error_id,
        'support': 'Contact support with error ID if issue persists'
    }, status=status.HTTP_401_UNAUTHORIZED)

# Substituir a função microsoft_token_login por esta versão segura:
@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt  # Manter por enquanto para compatibilidade
def microsoft_token_login_secure(request):
    """Login seguro usando access token do MSAL"""
    access_token = request.data.get('access_token')
    
    if not access_token:
        SecurityAuditLogger.log_login_attempt(
            'unknown', get_client_ip(request), 
            request.META.get('HTTP_USER_AGENT', ''),
            success=False, error_type='missing_token'
        )
        return Response({'error': 'Authentication required'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Dados para auditoria
        client_ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Validar token com serviço seguro
        try:
            token_payload = SecureMicrosoftAuthService.validate_token_secure(access_token)
        except ValidationError as e:
            SecurityAuditLogger.log_security_violation(
                'invalid_token', client_ip, str(e)
            )
            SecurityAuditLogger.log_login_attempt(
                'unknown', client_ip, user_agent,
                success=False, error_type='invalid_token'
            )
            return handle_auth_error(e, request)
        
        # Extrair informações do token validado
        user_email = token_payload.get('preferred_username', token_payload.get('email', ''))
        microsoft_id = token_payload.get('oid', token_payload.get('sub', ''))
        
        # Validação de domínio corporativo
        if not user_email or not user_email.endswith('@semcon.com'):
            SecurityAuditLogger.log_security_violation(
                'invalid_domain', client_ip,
                f'Domain: {user_email.split("@")[-1] if "@" in user_email else "unknown"}'
            )
            return Response({'error': 'Unauthorized domain'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # Verificar se deve ser admin
        should_be_admin = is_admin_email(user_email)
        
        # Buscar informações completas do usuário
        try:
            user_info = MicrosoftAuthService.get_user_info(access_token)
        except Exception as e:
            logger.error(f"Failed to get user info: {type(e).__name__}")
            return handle_auth_error(e, request, user_email)
        
        # Transação atômica para operações de usuário
        with transaction.atomic():
            try:
                user = User.objects.select_for_update().get(microsoft_id=microsoft_id)
                created = False
                
                # Verificar mudanças suspeitas
                if user.email != user_email:
                    SecurityAuditLogger.log_security_violation(
                        'email_change_attempt', client_ip,
                        f'From {user.email} to {user_email}'
                    )
                    return Response({'error': 'Account verification required'}, 
                                   status=status.HTTP_403_FORBIDDEN)
                
            except User.DoesNotExist:
                # Verificar se email já existe
                if User.objects.filter(email=user_email).exists():
                    SecurityAuditLogger.log_security_violation(
                        'duplicate_email', client_ip, user_email
                    )
                    return Response({'error': 'Account conflict'}, 
                                   status=status.HTTP_409_CONFLICT)
                
                # Criar novo usuário com validação
                user = User.objects.create(
                    microsoft_id=microsoft_id,
                    username=user_info.get('userPrincipalName', '')[:150],
                    email=user_email,
                    first_name=user_info.get('givenName', '')[:30],
                    last_name=user_info.get('surname', '')[:150],
                    preferred_name=user_info.get('displayName', '')[:100],
                    department=user_info.get('department', '')[:100],
                    job_title=user_info.get('jobTitle', '')[:100],
                    is_admin=should_be_admin,
                )
                created = True
            
            # Atualizar privilégios se necessário
            if not created and user.is_admin != should_be_admin:
                old_status = user.is_admin
                user.is_admin = should_be_admin
                user.save(update_fields=['is_admin', 'updated_at'])
                SecurityAuditLogger.log_admin_privilege_change(
                    user.id, old_status, should_be_admin, 'system_auto'
                )
            
            # Verificar atividade suspeita
            if not SecurityMonitor.check_suspicious_activity(user, request):
                return Response({'error': 'Security verification required'}, 
                               status=status.HTTP_403_FORBIDDEN)
            
            # Buscar foto (não crítico)
            try:
                photo_content = MicrosoftAuthService.get_user_photo(access_token)
                if photo_content:
                    MicrosoftAuthService.save_user_photo(user, photo_content)
            except Exception:
                pass  # Não falhar login por causa da foto
            
            # Invalidar sessões antigas
            old_sessions = UserSession.objects.filter(user=user, is_active=True)
            old_sessions.update(is_active=False)
            
            # Criar nova sessão segura
            session_token = generate_secure_session_token()
            device_fingerprint = hashlib.sha256(
                f"{user_agent}{client_ip}".encode()
            ).hexdigest()[:64]
            
            user_session = UserSession.objects.create(
                user=user,
                session_token=session_token,
                microsoft_token=access_token,  # Será criptografado pelo setter
                expires_at=timezone.now() + timedelta(minutes=settings.SESSION_LIFETIME_MINUTES),
                created_ip=client_ip,
                created_user_agent=user_agent[:500],
                last_used_ip=client_ip,
                device_fingerprint=device_fingerprint
            )
            
            # Login do usuário
            login(request, user)
            
            # Logs de sucesso
            SecurityAuditLogger.log_login_attempt(
                user_email, client_ip, user_agent, success=True
            )
            SecurityAuditLogger.log_session_created(
                user.id, session_token, client_ip
            )
            
            # Resposta segura
            return Response({
                'user': UserSerializer(user).data,
                'session_token': session_token,
                'expires_at': user_session.expires_at,
                'security': {
                    'mfa_required': False,  # Implementar no futuro
                    'password_change_required': False
                }
            })
            
    except Exception as e:
        # Garantir que sempre logamos tentativas falhadas
        SecurityAuditLogger.log_login_attempt(
            request.data.get('access_token', 'unknown')[:20],
            get_client_ip(request),
            request.META.get('HTTP_USER_AGENT', ''),
            success=False, error_type='internal_error'
        )
        return handle_auth_error(e, request)


# ==============================================================================
# 6. SETTINGS_SECURE.PY - CONFIGURAÇÕES DE SEGURANÇA
# ==============================================================================

"""
# Adicionar ao knight_backend/settings.py
"""

# === SECURITY SETTINGS ===

# HTTPS and Security Headers
SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS Settings
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookie Security
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_NAME = 'knightsession'
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'

CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_NAME = 'knightcsrf'

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Content Security Policy (usando django-csp)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "https://login.microsoftonline.com")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # Para admin
CSP_FONT_SRC = ("'self'",)
CSP_IMG_SRC = ("'self'", "data:", "https://graph.microsoft.com")
CSP_CONNECT_SRC = (
    "'self'", 
    "https://login.microsoftonline.com", 
    "https://graph.microsoft.com"
)
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)

# Permissions Policy
PERMISSIONS_POLICY = {
    "accelerometer": [],
    "camera": [],
    "geolocation": [],
    "microphone": [],
    "usb": [],
}

# Session Configuration
SESSION_LIFETIME_MINUTES = 15  # Reduzido de 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# Password Validation (para admin Django)
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Cache Configuration (para sessions e rate limiting)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        }
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    },
    'rate_limit': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/3'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Security Middleware Order (IMPORTANTE!)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',  # Primeiro!
    'corsheaders.middleware.CorsMiddleware',
    'authentication.enhanced_rate_limiting.EnhancedAuthRateLimitMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # Reabilitar!
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'authentication.middleware.TokenAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'csp.middleware.CSPMiddleware',  # Content Security Policy
]

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'security': {
            'format': '{asctime} SECURITY {levelname}: {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'security',
        },
        'auth_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'authentication.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'security_audit': {
            'handlers': ['security_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'authentication': {
            'handlers': ['auth_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Security alerts
ADMINS = [
    ('Security Team', 'security@company.com'),
]
MANAGERS = ADMINS

# Token Encryption (MUST be set in environment!)
if not os.environ.get('TOKEN_ENCRYPTION_SECRET'):
    raise ImproperlyConfigured(
        "TOKEN_ENCRYPTION_SECRET must be set! "
        "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
    )


# ==============================================================================
# 7. MONITORING.PY - SISTEMA DE MONITORAMENTO
# ==============================================================================

"""
# authentication/monitoring.py - NOVO ARQUIVO
"""
import json
import requests
from datetime import datetime, timedelta
from django.core.mail import mail_admins
from django.conf import settings
from django.core.cache import cache
from authentication.models import UserSession
from authentication.audit_logging import SecurityAuditLogger, get_client_ip
import logging

logger = logging.getLogger(__name__)

class SecurityMonitor:
    """Sistema de monitoramento de segurança em tempo real"""
    
    # Limiares de detecção
    ANOMALY_THRESHOLDS = {
        'multiple_ips': 3,          # IPs diferentes em 1 hora
        'multiple_countries': 2,     # Países diferentes em 24 horas
        'failed_attempts': 5,        # Tentativas falhadas em 30 min
        'concurrent_sessions': 5,    # Sessões simultâneas
        'rapid_logins': 3,          # Logins em 5 minutos
    }
    
    @classmethod
    def check_suspicious_activity(cls, user, request):
        """Verifica atividade suspeita do usuário"""
        client_ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        anomalies = []
        
        # 1. Verificar múltiplos IPs
        recent_ips = cls.get_recent_ips(user, hours=1)
        if len(set(recent_ips)) > cls.ANOMALY_THRESHOLDS['multiple_ips']:
            anomalies.append({
                'type': 'multiple_ips',
                'severity': 'high',
                'details': f"{len(set(recent_ips))} different IPs in last hour"
            })
        
        # 2. Verificar geolocalização
        location_anomaly = cls.check_location_anomaly(user, client_ip)
        if location_anomaly:
            anomalies.append(location_anomaly)
        
        # 3. Verificar user agent suspeito
        if cls.is_suspicious_user_agent(user_agent):
            anomalies.append({
                'type': 'suspicious_agent',
                'severity': 'medium',
                'details': 'Automated tool or bot detected'
            })
        
        # 4. Verificar horário incomum
        if cls.is_unusual_login_time(user):
            anomalies.append({
                'type': 'unusual_time',
                'severity': 'low',
                'details': 'Login outside normal hours'
            })
        
        # 5. Verificar sessões concorrentes
        active_sessions = UserSession.objects.filter(
            user=user, is_active=True
        ).count()
        if active_sessions > cls.ANOMALY_THRESHOLDS['concurrent_sessions']:
            anomalies.append({
                'type': 'many_sessions',
                'severity': 'high',
                'details': f"{active_sessions} active sessions"
            })
        
        # 6. Verificar logins rápidos
        rapid_logins = cls.check_rapid_logins(user)
        if rapid_logins:
            anomalies.append(rapid_logins)
        
        # Avaliar risco total
        risk_score = cls.calculate_risk_score(anomalies)
        
        # Tomar ação baseada no risco
        if risk_score >= 80:  # Risco crítico
            cls.alert_security_team(user, anomalies, request, 'CRITICAL')
            cls.invalidate_all_sessions(user)
            return False
        elif risk_score >= 60:  # Risco alto
            cls.alert_security_team(user, anomalies, request, 'HIGH')
            cls.require_mfa(user)  # Implementar MFA
            return True
        elif risk_score >= 40:  # Risco médio
            cls.alert_security_team(user, anomalies, request, 'MEDIUM')
            return True
        
        return True
    
    @classmethod
    def get_recent_ips(cls, user, hours=24):
        """Obtém IPs recentes do usuário"""
        cache_key = f"user:ips:{user.id}"
        ips = cache.get(cache_key, [])
        
        # Adicionar de sessões ativas
        sessions = UserSession.objects.filter(
            user=user,
            created_at__gte=datetime.now() - timedelta(hours=hours)
        ).values_list('created_ip', flat=True)
        
        ips.extend(sessions)
        return list(set(ips))
    
    @classmethod
    def check_location_anomaly(cls, user, current_ip):
        """Verifica anomalia de localização"""
        try:
            # Obter localização atual
            current_location = cls.get_ip_location(current_ip)
            if not current_location:
                return None
            
            # Obter localizações anteriores
            cache_key = f"user:locations:{user.id}"
            previous_locations = cache.get(cache_key, [])
            
            # Verificar mudança de país
            countries = set([loc['country'] for loc in previous_locations])
            countries.add(current_location['country'])
            
            if len(countries) > cls.ANOMALY_THRESHOLDS['multiple_countries']:
                return {
                    'type': 'location_anomaly',
                    'severity': 'critical',
                    'details': f"Login from {len(countries)} different countries"
                }
            
            # Verificar velocidade impossível (mais de 1000km em 1 hora)
            for prev_loc in previous_locations[-5:]:  # Últimas 5 localizações
                time_diff = (datetime.now() - prev_loc['timestamp']).total_seconds() / 3600
                distance = cls.calculate_distance(
                    current_location['lat'], current_location['lon'],
                    prev_loc['lat'], prev_loc['lon']
                )
                
                if time_diff > 0 and distance / time_diff > 1000:  # km/h
                    return {
                        'type': 'impossible_travel',
                        'severity': 'critical',
                        'details': f"Travel speed {int(distance/time_diff)} km/h"
                    }
            
            # Salvar localização atual
            previous_locations.append({
                'country': current_location['country'],
                'city': current_location.get('city'),
                'lat': current_location['lat'],
                'lon': current_location['lon'],
                'timestamp': datetime.now()
            })
            
            # Manter apenas últimas 20 localizações
            cache.set(cache_key, previous_locations[-20:], 86400 * 7)  # 7 dias
            
        except Exception as e:
            logger.error(f"Location check failed: {type(e).__name__}")
        
        return None
    
    @classmethod
    def get_ip_location(cls, ip):
        """Obtém localização do IP (implementar com serviço de GeoIP)"""
        # Cache primeiro
        cache_key = f"ip:location:{ip}"
        location = cache.get(cache_key)
        if location:
            return location
        
        try:
            # Usar serviço de GeoIP (exemplo com ipapi.co)
            response = requests.get(
                f"https://ipapi.co/{ip}/json/",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                location = {
                    'country': data.get('country_name'),
                    'country_code': data.get('country'),
                    'city': data.get('city'),
                    'lat': data.get('latitude'),
                    'lon': data.get('longitude'),
                }
                
                # Cache por 24 horas
                cache.set(cache_key, location, 86400)
                return location
        except Exception as e:
            logger.error(f"GeoIP lookup failed: {type(e).__name__}")
        
        return None
    
    @classmethod
    def calculate_distance(cls, lat1, lon1, lat2, lon2):
        """Calcula distância entre coordenadas em km"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Raio da Terra em km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    @classmethod
    def is_suspicious_user_agent(cls, user_agent):
        """Detecta user agents suspeitos"""
        if not user_agent:
            return True
        
        suspicious_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
            'python-requests', 'postman', 'insomnia', 'httpie'
        ]
        
        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in suspicious_patterns)
    
    @classmethod
    def is_unusual_login_time(cls, user):
        """Verifica se login é em horário incomum"""
        current_hour = datetime.now().hour
        
        # Definir horário normal (6h - 22h no fuso do usuário)
        # Simplificado - implementar com timezone do usuário
        return current_hour < 6 or current_hour > 22
    
    @classmethod
    def check_rapid_logins(cls, user):
        """Verifica logins muito rápidos"""
        cache_key = f"user:login:times:{user.id}"
        login_times = cache.get(cache_key, [])
        
        now = datetime.now()
        login_times.append(now)
        
        # Manter apenas últimas 24 horas
        cutoff = now - timedelta(hours=24)
        login_times = [t for t in login_times if t > cutoff]
        
        # Verificar logins nos últimos 5 minutos
        recent_cutoff = now - timedelta(minutes=5)
        recent_logins = [t for t in login_times if t > recent_cutoff]
        
        if len(recent_logins) >= cls.ANOMALY_THRESHOLDS['rapid_logins']:
            return {
                'type': 'rapid_logins',
                'severity': 'medium',
                'details': f"{len(recent_logins)} logins in 5 minutes"
            }
        
        cache.set(cache_key, login_times, 86400)
        return None
    
    @classmethod
    def calculate_risk_score(cls, anomalies):
        """Calcula score de risco baseado nas anomalias"""
        severity_scores = {
            'critical': 40,
            'high': 25,
            'medium': 15,
            'low': 5
        }
        
        total_score = 0
        for anomaly in anomalies:
            total_score += severity_scores.get(anomaly['severity'], 0)
        
        return min(total_score, 100)  # Máximo 100
    
    @classmethod
    def alert_security_team(cls, user, anomalies, request, severity='HIGH'):
        """Alerta equipe de segurança sobre atividade suspeita"""
        alert_data = {
            'severity': severity,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.get_full_name()
            },
            'anomalies': anomalies,
            'request_info': {
                'ip': get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'path': request.path,
                'method': request.method
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Log
        logger.warning(f"SECURITY ALERT [{severity}]: {json.dumps(alert_data)}")
        SecurityAuditLogger.log_security_violation(
            'suspicious_activity', 
            get_client_ip(request),
            json.dumps(anomalies)
        )
        
        # Email para admins
        if severity in ['CRITICAL', 'HIGH']:
            try:
                mail_admins(
                    f'[{severity}] Security Alert - {user.email}',
                    json.dumps(alert_data, indent=2),
                    fail_silently=False
                )
            except Exception as e:
                logger.error(f"Failed to send security email: {type(e).__name__}")
        
        # Webhook (se configurado)
        if hasattr(settings, 'SECURITY_WEBHOOK_URL'):
            try:
                requests.post(
                    settings.SECURITY_WEBHOOK_URL,
                    json=alert_data,
                    timeout=5
                )
            except Exception as e:
                logger.error(f"Failed to send webhook: {type(e).__name__}")
    
    @classmethod
    def invalidate_all_sessions(cls, user):
        """Invalida todas as sessões do usuário"""
        UserSession.objects.filter(user=user, is_active=True).update(
            is_active=False
        )
        logger.warning(f"All sessions invalidated for user {user.id}")
    
    @classmethod
    def require_mfa(cls, user):
        """Marca usuário como necessitando MFA (implementar)"""
        cache.set(f"user:require_mfa:{user.id}", True, 3600)


# ==============================================================================
# 8. MIGRATION PARA CRIPTOGRAFAR TOKENS EXISTENTES
# ==============================================================================

"""
# authentication/migrations/xxxx_encrypt_existing_tokens.py
"""
from django.db import migrations
from authentication.token_encryption import TokenEncryption

def encrypt_existing_tokens(apps, schema_editor):
    """Criptografa tokens existentes no banco"""
    UserSession = apps.get_model('authentication', 'UserSession')
    
    for session in UserSession.objects.all():
        try:
            # Verificar se já está criptografado
            if session.microsoft_token and not TokenEncryption.is_encrypted(session.microsoft_token):
                session._microsoft_token = TokenEncryption.encrypt_token(session.microsoft_token)
            
            if session.refresh_token and not TokenEncryption.is_encrypted(session.refresh_token):
                session._refresh_token = TokenEncryption.encrypt_token(session.refresh_token)
            
            session.save()
        except Exception as e:
            print(f"Failed to encrypt session {session.id}: {e}")

def decrypt_tokens_rollback(apps, schema_editor):
    """Rollback - descriptografa tokens"""
    # Implementar se necessário
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('authentication', 'latest_migration'),
    ]

    operations = [
        migrations.RunPython(encrypt_existing_tokens, decrypt_tokens_rollback),
    ]


# ==============================================================================
# 9. SCRIPTS DE DEPLOYMENT SEGURO
# ==============================================================================

"""
# scripts/secure_deployment_checklist.sh
"""
#!/bin/bash

echo "=== KNIGHT AGENT SECURITY DEPLOYMENT CHECKLIST ==="
echo ""

# 1. Verificar variáveis de ambiente
echo "1. Checking environment variables..."
required_vars=(
    "SECRET_KEY"
    "TOKEN_ENCRYPTION_SECRET"
    "AZURE_AD_CLIENT_ID"
    "AZURE_AD_CLIENT_SECRET"
    "AZURE_AD_TENANT_ID"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ ERROR: $var is not set!"
        exit 1
    else
        echo "✅ $var is set"
    fi
done

# 2. Verificar configurações de segurança
echo ""
echo "2. Checking security settings..."
python manage.py check --deploy

# 3. Verificar HTTPS
echo ""
echo "3. Checking HTTPS configuration..."
if [ "$DEBUG" == "True" ]; then
    echo "⚠️  WARNING: DEBUG is True - ensure HTTPS in production!"
else
    echo "✅ DEBUG is False"
fi

# 4. Verificar permissões de arquivos
echo ""
echo "4. Checking file permissions..."
find . -type f -name "*.log" -exec chmod 640 {} \;
find . -type d -name "logs" -exec chmod 750 {} \;
echo "✅ Log file permissions set"

# 5. Criar diretórios necessários
echo ""
echo "5. Creating required directories..."
mkdir -p logs media/profile_pics
chmod 750 logs
chmod 755 media/profile_pics
echo "✅ Directories created"

# 6. Executar migrations
echo ""
echo "6. Running migrations..."
python manage.py migrate

# 7. Coletar static files
echo ""
echo "7. Collecting static files..."
python manage.py collectstatic --noinput

# 8. Verificar Redis
echo ""
echo "8. Checking Redis connection..."
python -c "from django.core.cache import cache; cache.set('test', 'ok'); print('✅ Redis OK' if cache.get('test') == 'ok' else '❌ Redis FAILED')"

# 9. Gerar token de criptografia se não existir
echo ""
echo "9. Checking encryption token..."
if [ -z "$TOKEN_ENCRYPTION_SECRET" ]; then
    echo "Generating new encryption token..."
    export TOKEN_ENCRYPTION_SECRET=$(python -c 'import secrets; print(secrets.token_urlsafe(64))')
    echo "⚠️  SAVE THIS TOKEN: $TOKEN_ENCRYPTION_SECRET"
fi

echo ""
echo "=== DEPLOYMENT CHECKLIST COMPLETE ==="
echo ""
echo "⚠️  IMPORTANT REMINDERS:"
echo "- Enable HTTPS in production"
echo "- Configure firewall rules"
echo "- Set up monitoring and alerting"
echo "- Review and apply security patches regularly"
echo "- Implement MFA for all users"
echo "- Configure backup strategy"
echo ""


# ==============================================================================
# 10. TESTES DE SEGURANÇA
# ==============================================================================

"""
# authentication/tests/test_security.py
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from authentication.token_encryption import TokenEncryption
from authentication.secure_services import SecureMicrosoftAuthService
import jwt
from unittest.mock import patch, MagicMock

User = get_user_model()

class TestTokenEncryption(TestCase):
    """Testes para criptografia de tokens"""
    
    def test_encrypt_decrypt_token(self):
        """Testa criptografia e descriptografia"""
        original_token = "test_token_12345"
        
        encrypted = TokenEncryption.encrypt_token(original_token)
        self.assertNotEqual(encrypted, original_token)
        self.assertIn('v1:', base64.urlsafe_b64decode(encrypted).decode()[:3])
        
        decrypted = TokenEncryption.decrypt_token(encrypted)
        self.assertEqual(decrypted, original_token)
    
    def test_invalid_token_decrypt(self):
        """Testa descriptografia de token inválido"""
        with self.assertRaises(ValueError):
            TokenEncryption.decrypt_token("invalid_token")
    
    def test_empty_token_handling(self):
        """Testa tratamento de tokens vazios"""
        with self.assertRaises(ValueError):
            TokenEncryption.encrypt_token("")
        
        with self.assertRaises(ValueError):
            TokenEncryption.decrypt_token("")

class TestSecureAuthentication(TestCase):
    """Testes para autenticação segura"""
    
    def setUp(self):
        self.client = Client()
    
    @patch('authentication.secure_services.SecureMicrosoftAuthService.validate_token_secure')
    def test_invalid_domain_rejection(self, mock_validate):
        """Testa rejeição de domínio inválido"""
        mock_validate.return_value = {
            'preferred_username': 'user@invalid.com',
            'oid': '12345'
        }
        
        response = self.client.post('/api/auth/microsoft/token/', {
            'access_token': 'fake_token'
        })
        
        self.assertEqual(response.status_code, 403)
        self.assertIn('Unauthorized domain', response.json()['error'])
    
    def test_rate_limiting(self):
        """Testa rate limiting"""
        # Fazer múltiplas requisições
        for i in range(4):
            response = self.client.post('/api/auth/microsoft/token/', {
                'access_token': f'token_{i}'
            })
        
        # Próxima deve ser bloqueada
        response = self.client.post('/api/auth/microsoft/token/', {
            'access_token': 'token_blocked'
        })
        
        self.assertEqual(response.status_code, 429)
        self.assertIn('Too many attempts', response.json()['error'])
    
    def test_sql_injection_prevention(self):
        """Testa prevenção de SQL injection"""
        malicious_token = "'; DROP TABLE authentication_user; --"
        
        response = self.client.post('/api/auth/microsoft/token/', {
            'access_token': malicious_token
        })
        
        # Deve falhar na validação, não no SQL
        self.assertIn(response.status_code, [400, 401])
        
        # Verificar que tabela ainda existe
        self.assertTrue(User.objects.count() >= 0)

class TestJWTValidation(TestCase):
    """Testes para validação de JWT"""
    
    @patch('requests.get')
    def test_expired_token_rejection(self, mock_get):
        """Testa rejeição de token expirado"""
        # Mock das chaves públicas
        mock_get.return_value.json.return_value = {
            'keys': [{'kid': 'test_kid', 'kty': 'RSA', 'n': '...', 'e': 'AQAB'}]
        }
        
        # Token expirado
        expired_token = jwt.encode({
            'exp': 0,  # Expirado em 1970
            'aud': 'test_client_id'
        }, 'secret', algorithm='HS256')
        
        with self.assertRaises(ValidationError) as cm:
            SecureMicrosoftAuthService.validate_token_secure(expired_token)
        
        self.assertIn('expired', str(cm.exception).lower())


# ==============================================================================
print("Código de remediação pronto para implementação!")
print("IMPORTANTE: Revisar e testar cuidadosamente antes de aplicar em produção")
print("Gerar TOKEN_ENCRYPTION_SECRET com: python -c 'import secrets; print(secrets.token_urlsafe(64))'")