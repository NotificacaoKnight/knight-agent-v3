"""
Connection Pooling para otimização de performance HTTP
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class HTTPConnectionPool:
    """
    Gerenciador de connection pooling para requisições HTTP
    """
    
    def __init__(self):
        self.sessions: Dict[str, requests.Session] = {}
        
        # Configurações padrão de pooling
        self.pool_connections = 10  # Conexões por host
        self.pool_maxsize = 100     # Total de conexões no pool
        self.max_retries = 3        # Tentativas em caso de erro
        self.timeout = 30           # Timeout padrão em segundos
        
        # Configuração de retry
        self.retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        
        logger.info(f"🔌 HTTPConnectionPool inicializado (connections={self.pool_connections}, maxsize={self.pool_maxsize})")
    
    def get_session(self, base_url: str, headers: Optional[Dict[str, str]] = None) -> requests.Session:
        """
        Obtém ou cria uma sessão para um base_url específico
        """
        # Usar base_url como chave para reutilizar sessões
        session_key = base_url
        
        if session_key not in self.sessions:
            logger.info(f"🆕 Criando nova sessão para: {base_url}")
            
            # Criar nova sessão
            session = requests.Session()
            
            # Configurar adapter com pooling
            adapter = HTTPAdapter(
                pool_connections=self.pool_connections,
                pool_maxsize=self.pool_maxsize,
                max_retries=self.retry_strategy
            )
            
            # Montar adapter para HTTP e HTTPS
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # Headers padrão
            session.headers.update({
                'User-Agent': 'Knight-Agent/1.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Connection': 'keep-alive',  # Importante para connection pooling
            })
            
            # Headers customizados se fornecidos
            if headers:
                session.headers.update(headers)
            
            self.sessions[session_key] = session
        else:
            logger.debug(f"♻️ Reutilizando sessão existente para: {base_url}")
            session = self.sessions[session_key]
            
            # Atualizar headers se fornecidos
            if headers:
                session.headers.update(headers)
        
        return session
    
    def request(
        self, 
        method: str,
        url: str,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> requests.Response:
        """
        Faz uma requisição usando pooling
        """
        # Extrair base_url se não fornecido
        if not base_url:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Obter sessão com pooling
        session = self.get_session(base_url, headers)
        
        # Usar timeout padrão se não especificado
        if timeout is None:
            timeout = self.timeout
        
        # Fazer requisição
        logger.debug(f"🌐 {method} {url} (pooled connection)")
        
        try:
            response = session.request(
                method=method,
                url=url,
                timeout=timeout,
                **kwargs
            )
            
            logger.debug(f"✅ Response: {response.status_code} ({response.elapsed.total_seconds():.2f}s)")
            return response
            
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout após {timeout}s: {url}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🔌 Erro de conexão: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Erro na requisição: {e}")
            raise
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Atalho para requisição POST"""
        return self.request("POST", url, **kwargs)
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Atalho para requisição GET"""
        return self.request("GET", url, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas das conexões
        """
        stats = {
            'active_sessions': len(self.sessions),
            'sessions': {}
        }
        
        for base_url, session in self.sessions.items():
            # Tentar obter estatísticas do adapter
            try:
                for prefix, adapter in session.adapters.items():
                    if hasattr(adapter, 'poolmanager') and adapter.poolmanager:
                        pool_stats = {
                            'num_connections': adapter.poolmanager.num_connections,
                            'num_requests': adapter.poolmanager.num_requests,
                        }
                        stats['sessions'][base_url] = pool_stats
            except:
                stats['sessions'][base_url] = {'status': 'active'}
        
        return stats
    
    def close_all(self):
        """
        Fecha todas as sessões
        """
        logger.info(f"🔒 Fechando {len(self.sessions)} sessões...")
        
        for base_url, session in self.sessions.items():
            try:
                session.close()
                logger.debug(f"✅ Sessão fechada: {base_url}")
            except Exception as e:
                logger.warning(f"❌ Erro ao fechar sessão {base_url}: {e}")
        
        self.sessions.clear()
        logger.info("🔒 Todas as sessões fechadas")

# Instância global do pool
http_pool = HTTPConnectionPool()