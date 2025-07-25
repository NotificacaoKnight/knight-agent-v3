"""
Vector Store customizado para Agno com persistência usando FAISS
"""
import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import faiss
import pickle
from pathlib import Path
try:
    from agno.storage.base import VectorDb
except ImportError:
    # Fallback se a classe base não existir
    class VectorDb:
        """Interface base para Vector Database"""
        pass
import logging

logger = logging.getLogger(__name__)


class FaissVectorStore(VectorDb):
    """
    Vector store baseado em FAISS para uso com Agno
    Implementa a interface VectorDb do Agno com persistência local
    """
    
    def __init__(self, index_path: str = None, dimension: int = 1024):
        """
        Inicializa o FAISS vector store
        
        Args:
            index_path: Caminho para salvar/carregar o índice
            dimension: Dimensão dos embeddings
        """
        self.dimension = dimension
        self.index_path = index_path or "/tmp/agno_faiss_index"
        self.metadata_path = f"{self.index_path}_metadata.pkl"
        
        # Criar diretório se não existir
        Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Inicializar ou carregar índice
        self._init_index()
        
        # Metadados dos documentos
        self.documents: List[Dict[str, Any]] = []
        self._load_metadata()
        
        logger.info(f"FaissVectorStore inicializado com {len(self.documents)} documentos")
    
    def _init_index(self):
        """Inicializa ou carrega o índice FAISS"""
        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
                logger.info(f"Índice FAISS carregado de {self.index_path}")
            except Exception as e:
                logger.warning(f"Erro ao carregar índice: {e}. Criando novo...")
                self.index = faiss.IndexFlatL2(self.dimension)
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
            logger.info("Novo índice FAISS criado")
    
    def _load_metadata(self):
        """Carrega metadados salvos"""
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, 'rb') as f:
                    self.documents = pickle.load(f)
                logger.info(f"Metadados carregados: {len(self.documents)} documentos")
            except Exception as e:
                logger.warning(f"Erro ao carregar metadados: {e}")
                self.documents = []
        else:
            self.documents = []
    
    def _save_index(self):
        """Salva o índice e metadados"""
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.documents, f)
            logger.info(f"Índice e metadados salvos em {self.index_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar índice: {e}")
    
    def add(self, embeddings: np.ndarray, documents: List[Dict[str, Any]]) -> None:
        """
        Adiciona embeddings e documentos ao índice
        
        Args:
            embeddings: Array numpy com embeddings (n_docs x dimension)
            documents: Lista de documentos com metadados
        """
        if len(embeddings) != len(documents):
            raise ValueError("Número de embeddings deve ser igual ao número de documentos")
        
        # Adicionar ao índice FAISS
        self.index.add(embeddings.astype(np.float32))
        
        # Adicionar metadados
        self.documents.extend(documents)
        
        # Salvar automaticamente
        self._save_index()
        
        logger.info(f"Adicionados {len(documents)} documentos ao índice")
    
    def search(self, query_embedding: np.ndarray, k: int = 5, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Busca documentos similares
        
        Args:
            query_embedding: Embedding da query
            k: Número de resultados
            filters: Filtros opcionais
            
        Returns:
            Lista de documentos com scores
        """
        if self.index.ntotal == 0:
            logger.warning("Índice vazio, nenhum resultado retornado")
            return []
        
        # Buscar no FAISS
        distances, indices = self.index.search(
            query_embedding.reshape(1, -1).astype(np.float32), 
            min(k, self.index.ntotal)
        )
        
        results = []
        for i, (idx, dist) in enumerate(zip(indices[0], distances[0])):
            if idx >= 0 and idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc['score'] = float(1 / (1 + dist))  # Converter distância em score
                doc['distance'] = float(dist)
                
                # Aplicar filtros se fornecidos
                if filters:
                    match = all(
                        doc.get('metadata', {}).get(key) == value 
                        for key, value in filters.items()
                    )
                    if not match:
                        continue
                
                results.append(doc)
        
        return results[:k]
    
    def delete(self, document_ids: List[str]) -> None:
        """
        Remove documentos do índice (não implementado no FAISS básico)
        Para simplificar, vamos apenas marcar como deletado nos metadados
        """
        for doc_id in document_ids:
            for doc in self.documents:
                if doc.get('id') == doc_id or doc.get('metadata', {}).get('document_id') == doc_id:
                    doc['deleted'] = True
        
        self._save_index()
        logger.info(f"Marcados {len(document_ids)} documentos como deletados")
    
    def clear(self) -> None:
        """Limpa todo o índice"""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []
        self._save_index()
        logger.info("Índice limpo")
    
    def count(self) -> int:
        """Retorna número de documentos no índice"""
        return sum(1 for doc in self.documents if not doc.get('deleted', False))
    
    # Métodos compatíveis com Agno VectorDb
    def insert(self, documents: List[Dict[str, Any]]) -> None:
        """Compatibilidade com Agno - inserir documentos"""
        # Extrair embeddings se disponíveis
        embeddings = []
        for doc in documents:
            if 'embedding' in doc:
                embeddings.append(doc['embedding'])
            else:
                # Gerar embedding vazio se não fornecido
                embeddings.append(np.zeros(self.dimension))
        
        if embeddings:
            self.add(np.array(embeddings), documents)
    
    def query(self, embedding: np.ndarray, top_k: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Compatibilidade com Agno - buscar documentos"""
        return self.search(embedding, k=top_k, filters=kwargs.get('filters'))