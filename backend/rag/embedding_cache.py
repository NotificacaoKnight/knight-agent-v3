"""
Sistema de cache para embeddings - otimização de performance
"""
import os
import json
import hashlib
import pickle
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import numpy as np
from django.conf import settings
from django.core.cache import cache
import time

logger = logging.getLogger(__name__)

class EmbeddingCache:
    """
    Sistema de cache multicamada para embeddings:
    1. Cache em memória (Redis/Django Cache) - mais rápido
    2. Cache em disco (pickle) - persistente
    3. Fallback para geração nova
    """
    
    def __init__(self):
        # Diretório de cache
        self.cache_dir = Path(settings.BASE_DIR) / 'embedding_cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        # Configurações
        self.memory_cache_timeout = 3600  # 1 hora
        self.disk_cache_days = 30  # 30 dias
        self.max_memory_entries = 1000  # Limite de entradas na memória
        
        # Estatísticas
        self.stats = {
            'hits_memory': 0,
            'hits_disk': 0,
            'misses': 0,
            'saves': 0
        }
        
        logger.info(f"🗄️ EmbeddingCache inicializado: {self.cache_dir}")
    
    def _get_text_hash(self, text: str, model_name: str = "default") -> str:
        """
        Gera hash único para texto + modelo
        """
        content = f"{text}|{model_name}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def _get_cache_key(self, text_hash: str) -> str:
        """
        Gera chave para cache do Django/Redis
        """
        return f"embedding:{text_hash}"
    
    def _get_disk_path(self, text_hash: str) -> Path:
        """
        Gera caminho do arquivo em disco
        """
        # Organizar em subdiretórios para evitar muitos arquivos em uma pasta
        subdir = text_hash[:2]
        disk_dir = self.cache_dir / subdir
        disk_dir.mkdir(exist_ok=True)
        return disk_dir / f"{text_hash}.pkl"
    
    def get_embedding(
        self, 
        text: str, 
        model_name: str = "default"
    ) -> Optional[np.ndarray]:
        """
        Busca embedding no cache (memória -> disco -> None)
        """
        text_hash = self._get_text_hash(text, model_name)
        cache_key = self._get_cache_key(text_hash)
        
        # 1. Tentar cache em memória primeiro
        try:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                self.stats['hits_memory'] += 1
                logger.debug(f"🎯 Cache hit (memory): {text_hash}")
                return np.array(cached_data['embedding'])
        except Exception as e:
            logger.warning(f"Erro no cache de memória: {e}")
        
        # 2. Tentar cache em disco
        disk_path = self._get_disk_path(text_hash)
        if disk_path.exists():
            try:
                with open(disk_path, 'rb') as f:
                    cached_data = pickle.load(f)
                
                # Verificar se não está muito antigo
                cache_age_days = (time.time() - cached_data['timestamp']) / (24 * 3600)
                if cache_age_days <= self.disk_cache_days:
                    # Recarregar na memória para próximas buscas
                    try:
                        cache.set(
                            cache_key, 
                            cached_data, 
                            timeout=self.memory_cache_timeout
                        )
                    except Exception as e:
                        logger.warning(f"Erro ao salvar no cache de memória: {e}")
                    
                    self.stats['hits_disk'] += 1
                    logger.debug(f"💾 Cache hit (disk): {text_hash}")
                    return np.array(cached_data['embedding'])
                else:
                    # Cache muito antigo, remover
                    disk_path.unlink()
                    logger.debug(f"🗑️ Cache expirado removido: {text_hash}")
                    
            except Exception as e:
                logger.warning(f"Erro ao ler cache do disco: {e}")
                # Remover arquivo corrompido
                try:
                    disk_path.unlink()
                except:
                    pass
        
        # 3. Cache miss
        self.stats['misses'] += 1
        logger.debug(f"❌ Cache miss: {text_hash}")
        return None
    
    def save_embedding(
        self, 
        text: str, 
        embedding: np.ndarray, 
        model_name: str = "default",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Salva embedding no cache (memória + disco)
        """
        try:
            text_hash = self._get_text_hash(text, model_name)
            cache_key = self._get_cache_key(text_hash)
            
            # Preparar dados para cache
            # Converter embedding para lista se necessário
            if hasattr(embedding, 'tolist'):
                embedding_list = embedding.tolist()
            elif isinstance(embedding, list):
                embedding_list = embedding
            else:
                # Tentar converter para numpy e depois para lista
                import numpy as np
                embedding_list = np.array(embedding).tolist()
            
            cached_data = {
                'embedding': embedding_list,
                'text_hash': text_hash,
                'model_name': model_name,
                'timestamp': time.time(),
                'text_preview': text[:100] + '...' if len(text) > 100 else text,
                'metadata': metadata or {}
            }
            
            # 1. Salvar na memória
            try:
                cache.set(
                    cache_key, 
                    cached_data, 
                    timeout=self.memory_cache_timeout
                )
                logger.debug(f"💾 Salvo cache (memory): {text_hash}")
            except Exception as e:
                logger.warning(f"Erro ao salvar no cache de memória: {e}")
            
            # 2. Salvar no disco
            disk_path = self._get_disk_path(text_hash)
            try:
                with open(disk_path, 'wb') as f:
                    pickle.dump(cached_data, f)
                logger.debug(f"💿 Salvo cache (disk): {text_hash}")
            except Exception as e:
                logger.warning(f"Erro ao salvar cache no disco: {e}")
                return False
            
            self.stats['saves'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar embedding no cache: {e}")
            return False
    
    def get_multiple_embeddings(
        self, 
        texts: List[str], 
        model_name: str = "default"
    ) -> Tuple[List[Optional[np.ndarray]], List[str]]:
        """
        Busca múltiplos embeddings de uma vez
        Retorna: (embeddings_encontrados, textos_faltantes)
        """
        results = []
        missing_texts = []
        
        for text in texts:
            embedding = self.get_embedding(text, model_name)
            if embedding is not None:
                results.append(embedding)
            else:
                results.append(None)
                missing_texts.append(text)
        
        return results, missing_texts
    
    def save_multiple_embeddings(
        self, 
        text_embedding_pairs: List[Tuple[str, np.ndarray]], 
        model_name: str = "default"
    ) -> int:
        """
        Salva múltiplos embeddings de uma vez
        Retorna: número de embeddings salvos com sucesso
        """
        saved_count = 0
        
        for text, embedding in text_embedding_pairs:
            if self.save_embedding(text, embedding, model_name):
                saved_count += 1
        
        return saved_count
    
    def clear_cache(self, max_age_days: Optional[int] = None) -> Dict[str, int]:
        """
        Limpa cache antigo
        """
        cleared_stats = {'memory': 0, 'disk': 0}
        
        # Limpar cache de memória
        try:
            # Django cache não tem clear por padrão, mas podemos tentar
            if hasattr(cache, 'clear'):
                cache.clear()
                cleared_stats['memory'] = 1
        except Exception as e:
            logger.warning(f"Erro ao limpar cache de memória: {e}")
        
        # Limpar cache em disco
        max_age_seconds = (max_age_days or self.disk_cache_days) * 24 * 3600
        current_time = time.time()
        
        for cache_file in self.cache_dir.rglob("*.pkl"):
            try:
                # Verificar idade do arquivo
                file_age = current_time - cache_file.stat().st_mtime
                if file_age > max_age_seconds:
                    cache_file.unlink()
                    cleared_stats['disk'] += 1
            except Exception as e:
                logger.warning(f"Erro ao remover cache {cache_file}: {e}")
        
        logger.info(f"🧹 Cache limpo: {cleared_stats}")
        return cleared_stats
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Estatísticas do cache
        """
        # Calcular tamanho do cache em disco
        disk_size = 0
        disk_files = 0
        
        try:
            for cache_file in self.cache_dir.rglob("*.pkl"):
                disk_size += cache_file.stat().st_size
                disk_files += 1
        except Exception as e:
            logger.warning(f"Erro ao calcular estatísticas: {e}")
        
        # Hit rate
        total_requests = sum([
            self.stats['hits_memory'],
            self.stats['hits_disk'], 
            self.stats['misses']
        ])
        
        hit_rate = 0
        if total_requests > 0:
            hit_rate = (self.stats['hits_memory'] + self.stats['hits_disk']) / total_requests
        
        return {
            'hit_rate': f"{hit_rate:.2%}",
            'hits_memory': self.stats['hits_memory'],
            'hits_disk': self.stats['hits_disk'],
            'misses': self.stats['misses'],
            'saves': self.stats['saves'],
            'disk_files': disk_files,
            'disk_size_mb': f"{disk_size / (1024*1024):.2f}",
            'cache_dir': str(self.cache_dir)
        }

# Instância global do cache
embedding_cache = EmbeddingCache()