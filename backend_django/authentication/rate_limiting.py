"""
Rate limiting middleware for authentication endpoints
Previne ataques de força bruta no sistema de autenticação
"""
import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status

logger = logging.getLogger(__name__)

class AuthenticationRateLimitMiddleware(MiddlewareMixin):
    """
    Middleware para rate limiting em endpoints de autenticação
    """
    
    # Configurações de rate limiting por endpoint
    RATE_LIMITS = {
        '/api/auth/microsoft/token/': {'requests': 5, 'window': 300},  # 5 req por 5 min
        '/api/auth/microsoft/callback/': {'requests': 10, 'window': 300},  # 10 req por 5 min
        '/api/auth/microsoft/login/': {'requests': 20, 'window': 300},  # 20 req por 5 min
    }
    
    def process_request(self, request):
        """Verificar rate limiting para endpoints de autenticação"""
        
        # Verificar se é um endpoint protegido
        path = request.path
        if path not in self.RATE_LIMITS:
            return None
        
        # Obter IP do cliente (considerando proxies)
        client_ip = self.get_client_ip(request)
        if not client_ip:
            return None
        
        # Configuração do rate limit para este endpoint
        config = self.RATE_LIMITS[path]
        max_requests = config['requests']
        window_seconds = config['window']
        
        # Chave única para cache
        cache_key = f"rate_limit:{client_ip}:{path}"
        
        # Obter dados do cache
        current_requests = cache.get(cache_key, [])
        
        # Filtrar requests dentro da janela de tempo
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=window_seconds)
        
        # Manter apenas requests recentes
        recent_requests = [
            req_time for req_time in current_requests 
            if req_time > cutoff_time
        ]
        
        # Verificar se excedeu o limite
        if len(recent_requests) >= max_requests:
            logger.warning(
                f"Rate limit excedido para IP {client_ip} no endpoint {path}. "
                f"Tentativas: {len(recent_requests)}/{max_requests}"
            )
            
            return JsonResponse({
                'error': 'Muitas tentativas de login. Tente novamente em alguns minutos.',
                'retry_after': window_seconds
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Adicionar request atual
        recent_requests.append(now)
        
        # Salvar no cache
        cache.set(cache_key, recent_requests, window_seconds)
        
        return None
    
    def get_client_ip(self, request):
        """Obter IP real do cliente considerando proxies"""
        # Headers comuns de proxy
        ip_headers = [
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_CF_CONNECTING_IP',  # Cloudflare
            'REMOTE_ADDR'
        ]
        
        for header in ip_headers:
            ip = request.META.get(header)
            if ip:
                # Pegar primeiro IP se houver múltiplos (cadeia de proxies)
                ip = ip.split(',')[0].strip()
                if self.is_valid_ip(ip):
                    return ip
        
        return None
    
    def is_valid_ip(self, ip):
        """Validar se é um IP válido"""
        import socket
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False