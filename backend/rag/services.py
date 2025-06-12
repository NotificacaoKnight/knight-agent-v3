import os
import json
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import tiktoken

from django.conf import settings
from django.core.cache import cache

from documents.models import Document, DocumentChunk
from .models import VectorStore, SearchQuery, SearchResult

class EmbeddingService:
    """Serviço para gerar embeddings otimizado para português"""
    
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Carrega modelo de embedding com cache"""
        cache_key = f"embedding_model_{self.model_name}"
        self.model = cache.get(cache_key)
        
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
            # Cache por 1 hora
            cache.set(cache_key, self.model, 3600)
    
    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """Gera embeddings para lista de textos"""
        if not texts:
            return np.array([])
        
        # Normalizar textos
        normalized_texts = [self._preprocess_text(text) for text in texts]
        
        # Gerar embeddings
        embeddings = self.model.encode(
            normalized_texts,
            batch_size=32,
            show_progress_bar=len(texts) > 100,
            convert_to_numpy=True,
            normalize_embeddings=True  # Importante para busca por similaridade
        )
        
        return embeddings
    
    def encode_single_text(self, text: str) -> np.ndarray:
        """Gera embedding para um único texto"""
        return self.encode_texts([text])[0]
    
    def _preprocess_text(self, text: str) -> str:
        """Pré-processa texto para melhor qualidade dos embeddings"""
        # Remover quebras de linha excessivas
        text = text.replace('\n\n\n', '\n\n')
        text = text.replace('\r\n', '\n')
        
        # Limitar tamanho (modelos têm limite de tokens)
        if len(text) > 8000:  # Aproximadamente 2000 tokens
            text = text[:8000]
        
        return text.strip()
    
    def get_dimension(self) -> int:
        """Retorna dimensão dos embeddings do modelo atual"""
        if self.model is None:
            self._load_model()
        return self.model.get_sentence_embedding_dimension()
    
    def generate_embeddings_for_document(self, document: Document):
        """Gera embeddings para todos os chunks de um documento"""
        chunks = document.chunks.all().order_by('chunk_index')
        
        if not chunks:
            return
        
        # Extrair textos dos chunks
        texts = [chunk.content for chunk in chunks]
        
        # Gerar embeddings
        embeddings = self.encode_texts(texts)
        
        # Salvar embeddings nos chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()
            chunk.save(update_fields=['embedding'])

class ChunkingService:
    """Serviço para divisão de documentos em chunks otimizado para português"""
    
    def __init__(self):
        self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    def create_chunks(
        self, 
        text: str, 
        chunk_size: int = 700, 
        overlap: int = 100,
        preserve_structure: bool = True
    ) -> List[Dict[str, Any]]:
        """Cria chunks de texto com sobreposição"""
        
        if not text.strip():
            return []
        
        # Dividir por estrutura se preservar estrutura estiver ativo
        if preserve_structure:
            return self._chunk_by_structure(text, chunk_size, overlap)
        else:
            return self._chunk_by_size(text, chunk_size, overlap)
    
    def _chunk_by_structure(self, text: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """Divide texto preservando estrutura (cabeçalhos, parágrafos)"""
        chunks = []
        
        # Dividir por seções (cabeçalhos markdown)
        sections = self._split_by_headers(text)
        
        current_chunk = ""
        current_size = 0
        chunk_index = 0
        
        for section in sections:
            section_tokens = self._count_tokens(section['content'])
            
            # Se a seção cabe no chunk atual
            if current_size + section_tokens <= chunk_size:
                current_chunk += section['content'] + "\n\n"
                current_size += section_tokens
            else:
                # Salvar chunk atual se não estiver vazio
                if current_chunk.strip():
                    chunks.append({
                        'content': current_chunk.strip(),
                        'chunk_index': chunk_index,
                        'start': len(current_chunk) - len(current_chunk.lstrip()),
                        'end': len(current_chunk),
                        'section_title': section.get('title', ''),
                        'tokens': current_size
                    })
                    chunk_index += 1
                
                # Se a seção é muito grande, dividir por parágrafos
                if section_tokens > chunk_size:
                    section_chunks = self._chunk_large_section(
                        section['content'], 
                        chunk_size, 
                        overlap,
                        chunk_index
                    )
                    chunks.extend(section_chunks)
                    chunk_index += len(section_chunks)
                    current_chunk = ""
                    current_size = 0
                else:
                    # Iniciar novo chunk com esta seção
                    current_chunk = section['content'] + "\n\n"
                    current_size = section_tokens
        
        # Adicionar último chunk se não estiver vazio
        if current_chunk.strip():
            chunks.append({
                'content': current_chunk.strip(),
                'chunk_index': chunk_index,
                'start': 0,
                'end': len(current_chunk),
                'tokens': current_size
            })
        
        return chunks
    
    def _chunk_by_size(self, text: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """Divide texto por tamanho fixo com sobreposição"""
        chunks = []
        tokens = self.tokenizer.encode(text)
        
        start = 0
        chunk_index = 0
        
        while start < len(tokens):
            # Definir fim do chunk
            end = min(start + chunk_size, len(tokens))
            
            # Extrair tokens do chunk
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunks.append({
                'content': chunk_text,
                'chunk_index': chunk_index,
                'start': start,
                'end': end,
                'tokens': len(chunk_tokens)
            })
            
            # Próximo chunk com sobreposição
            start = end - overlap
            chunk_index += 1
            
            # Evitar chunks muito pequenos no final
            if len(tokens) - start < overlap:
                break
        
        return chunks
    
    def _split_by_headers(self, text: str) -> List[Dict[str, str]]:
        """Divide texto por cabeçalhos markdown"""
        lines = text.split('\n')
        sections = []
        current_section = []
        current_title = ""
        
        for line in lines:
            if line.strip().startswith('#'):
                # Salvar seção anterior
                if current_section:
                    sections.append({
                        'title': current_title,
                        'content': '\n'.join(current_section)
                    })
                
                # Iniciar nova seção
                current_title = line.strip()
                current_section = [line]
            else:
                current_section.append(line)
        
        # Adicionar última seção
        if current_section:
            sections.append({
                'title': current_title,
                'content': '\n'.join(current_section)
            })
        
        return sections
    
    def _chunk_large_section(
        self, 
        text: str, 
        chunk_size: int, 
        overlap: int, 
        start_index: int
    ) -> List[Dict[str, Any]]:
        """Divide seção grande em chunks menores"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        current_size = 0
        chunk_index = start_index
        
        for paragraph in paragraphs:
            paragraph_tokens = self._count_tokens(paragraph)
            
            if current_size + paragraph_tokens <= chunk_size:
                current_chunk += paragraph + "\n\n"
                current_size += paragraph_tokens
            else:
                # Salvar chunk atual
                if current_chunk.strip():
                    chunks.append({
                        'content': current_chunk.strip(),
                        'chunk_index': chunk_index,
                        'tokens': current_size
                    })
                    chunk_index += 1
                
                # Iniciar novo chunk
                current_chunk = paragraph + "\n\n"
                current_size = paragraph_tokens
        
        # Adicionar último chunk
        if current_chunk.strip():
            chunks.append({
                'content': current_chunk.strip(),
                'chunk_index': chunk_index,
                'tokens': current_size
            })
        
        return chunks
    
    def _count_tokens(self, text: str) -> int:
        """Conta tokens no texto"""
        return len(self.tokenizer.encode(text))

class VectorSearchService:
    """Serviço de busca vetorial usando FAISS"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = None
        self.document_chunks = {}
        self._load_vector_store()
    
    def _load_vector_store(self):
        """Carrega ou cria vector store"""
        try:
            vector_store_config = VectorStore.objects.filter(is_active=True).first()
            
            if vector_store_config and os.path.exists(vector_store_config.index_path):
                # Carregar índice existente
                self.vector_store = faiss.read_index(vector_store_config.index_path)
                self._load_chunk_mapping()
            else:
                # Criar novo índice
                self._create_new_index()
                
        except Exception as e:
            print(f"Erro ao carregar vector store: {e}")
            self._create_new_index()
    
    def _create_new_index(self):
        """Cria novo índice FAISS"""
        dimension = self.embedding_service.get_dimension()
        
        # Usar HNSW para melhor performance em buscas
        self.vector_store = faiss.IndexHNSWFlat(dimension, 32)
        self.vector_store.hnsw.efConstruction = 200
        self.vector_store.hnsw.efSearch = 50
        
        self.document_chunks = {}
    
    def _load_chunk_mapping(self):
        """Carrega mapeamento de chunks"""
        cache_key = "vector_store_chunk_mapping"
        self.document_chunks = cache.get(cache_key, {})
        
        if not self.document_chunks:
            # Recriar mapeamento do banco
            chunks = DocumentChunk.objects.filter(
                embedding__isnull=False
            ).select_related('document')
            
            for i, chunk in enumerate(chunks):
                self.document_chunks[i] = {
                    'document_id': chunk.document.id,
                    'chunk_id': chunk.id,
                    'chunk_index': chunk.chunk_index,
                    'content': chunk.content
                }
            
            # Cache por 1 hora
            cache.set(cache_key, self.document_chunks, 3600)
    
    def add_document_embeddings(self, document: Document):
        """Adiciona embeddings de um documento ao índice"""
        chunks = document.chunks.filter(embedding__isnull=False)
        
        if not chunks:
            return
        
        # Converter embeddings para numpy array
        embeddings = []
        for chunk in chunks:
            embeddings.append(np.array(chunk.embedding))
        
        embeddings_array = np.vstack(embeddings)
        
        # Adicionar ao índice
        start_idx = self.vector_store.ntotal
        self.vector_store.add(embeddings_array)
        
        # Atualizar mapeamento de chunks
        for i, chunk in enumerate(chunks):
            self.document_chunks[start_idx + i] = {
                'document_id': chunk.document.id,
                'chunk_id': chunk.id,
                'chunk_index': chunk.chunk_index,
                'content': chunk.content
            }
        
        # Salvar índice atualizado
        self._save_vector_store()
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Busca semântica por similaridade"""
        if not query.strip() or self.vector_store.ntotal == 0:
            return []
        
        # Gerar embedding da query
        query_embedding = self.embedding_service.encode_single_text(query)
        query_vector = query_embedding.reshape(1, -1)
        
        # Buscar no índice
        scores, indices = self.vector_store.search(query_vector, k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx in self.document_chunks:
                chunk_info = self.document_chunks[idx]
                results.append({
                    'document_id': chunk_info['document_id'],
                    'chunk_id': chunk_info['chunk_id'],
                    'chunk_index': chunk_info['chunk_index'],
                    'content': chunk_info['content'],
                    'score': float(score),
                    'search_type': 'semantic'
                })
        
        return results
    
    def _save_vector_store(self):
        """Salva índice FAISS em disco"""
        try:
            index_path = os.path.join(settings.VECTOR_STORE_PATH, 'faiss_index.bin')
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            
            faiss.write_index(self.vector_store, index_path)
            
            # Atualizar configuração
            vector_store_config, created = VectorStore.objects.get_or_create(
                name='default',
                defaults={
                    'embedding_model': settings.EMBEDDING_MODEL,
                    'dimension': self.embedding_service.get_dimension(),
                    'index_path': index_path,
                    'vectors_count': self.vector_store.ntotal
                }
            )
            
            if not created:
                vector_store_config.vectors_count = self.vector_store.ntotal
                vector_store_config.save()
            
            # Atualizar cache
            cache.set("vector_store_chunk_mapping", self.document_chunks, 3600)
            
        except Exception as e:
            print(f"Erro ao salvar vector store: {e}")

class BM25SearchService:
    """Serviço de busca BM25 (keyword-based)"""
    
    def __init__(self):
        self.bm25_index = None
        self.document_chunks = []
        self._load_bm25_index()
    
    def _load_bm25_index(self):
        """Carrega ou cria índice BM25"""
        cache_key = "bm25_index"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            self.bm25_index = cached_data['index']
            self.document_chunks = cached_data['chunks']
        else:
            self._create_bm25_index()
    
    def _create_bm25_index(self):
        """Cria índice BM25 com todos os chunks"""
        chunks = DocumentChunk.objects.select_related('document').all()
        
        self.document_chunks = []
        corpus = []
        
        for chunk in chunks:
            self.document_chunks.append({
                'document_id': chunk.document.id,
                'chunk_id': chunk.id,
                'chunk_index': chunk.chunk_index,
                'content': chunk.content
            })
            
            # Tokenizar para BM25 (português)
            tokens = self._tokenize_portuguese(chunk.content)
            corpus.append(tokens)
        
        if corpus:
            self.bm25_index = BM25Okapi(corpus)
        
        # Cache por 1 hora
        cache.set("bm25_index", {
            'index': self.bm25_index,
            'chunks': self.document_chunks
        }, 3600)
    
    def _tokenize_portuguese(self, text: str) -> List[str]:
        """Tokenização otimizada para português"""
        import re
        
        # Converter para minúsculas
        text = text.lower()
        
        # Remover pontuação e caracteres especiais
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Dividir em tokens
        tokens = text.split()
        
        # Filtrar tokens muito curtos (stopwords básicas)
        stop_words = {
            'a', 'ao', 'aos', 'as', 'da', 'das', 'de', 'do', 'dos', 'e', 'em', 'na', 'nas', 'no', 'nos',
            'o', 'os', 'ou', 'para', 'por', 'que', 'se', 'um', 'uma', 'mas', 'como', 'com', 'é', 'são',
            'foi', 'ser', 'ter', 'sua', 'seu', 'seus', 'suas', 'ele', 'ela', 'eles', 'elas', 'isso', 'isto'
        }
        
        tokens = [token for token in tokens if token not in stop_words and len(token) > 2]
        
        return tokens
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Busca BM25"""
        if not query.strip() or not self.bm25_index:
            return []
        
        # Tokenizar query
        query_tokens = self._tokenize_portuguese(query)
        
        if not query_tokens:
            return []
        
        # Buscar
        scores = self.bm25_index.get_scores(query_tokens)
        
        # Ordenar por score
        top_indices = np.argsort(scores)[::-1][:k]
        
        results = []
        for idx in top_indices:
            if idx < len(self.document_chunks) and scores[idx] > 0:
                chunk_info = self.document_chunks[idx]
                results.append({
                    'document_id': chunk_info['document_id'],
                    'chunk_id': chunk_info['chunk_id'],
                    'chunk_index': chunk_info['chunk_index'],
                    'content': chunk_info['content'],
                    'score': float(scores[idx]),
                    'search_type': 'bm25'
                })
        
        return results
    
    def update_index(self):
        """Atualiza índice BM25"""
        self._create_bm25_index()

class HybridSearchService:
    """Serviço de busca híbrida combinando busca semântica e BM25"""
    
    def __init__(self):
        self.vector_search = VectorSearchService()
        self.bm25_search = BM25SearchService()
        self.semantic_weight = settings.SEMANTIC_WEIGHT
        self.bm25_weight = settings.BM25_WEIGHT
    
    def search(
        self, 
        query: str, 
        k: int = 5,
        semantic_weight: Optional[float] = None,
        bm25_weight: Optional[float] = None,
        user: Any = None
    ) -> Tuple[List[Dict[str, Any]], SearchQuery]:
        """Busca híbrida com log da query"""
        
        start_time = time.time()
        
        # Usar pesos padrão se não especificados
        if semantic_weight is None:
            semantic_weight = self.semantic_weight
        if bm25_weight is None:
            bm25_weight = self.bm25_weight
        
        # Normalizar pesos
        total_weight = semantic_weight + bm25_weight
        semantic_weight = semantic_weight / total_weight
        bm25_weight = bm25_weight / total_weight
        
        # Buscar com ambos os métodos
        embedding_start = time.time()
        semantic_results = self.vector_search.search(query, k * 2)  # Buscar mais para combinar
        embedding_duration = int((time.time() - embedding_start) * 1000)
        
        bm25_results = self.bm25_search.search(query, k * 2)
        
        # Combinar resultados
        combined_results = self._combine_results(
            semantic_results, 
            bm25_results, 
            semantic_weight, 
            bm25_weight
        )
        
        # Limitar ao número solicitado
        top_results = combined_results[:k]
        
        search_duration = int((time.time() - start_time) * 1000)
        
        # Log da query
        search_query = SearchQuery.objects.create(
            user=user,
            query_text=query,
            search_type='hybrid',
            semantic_weight=semantic_weight,
            bm25_weight=bm25_weight,
            top_k=k,
            results_count=len(top_results),
            results=[
                {
                    'document_id': result['document_id'],
                    'chunk_id': result['chunk_id'],
                    'combined_score': result['combined_score'],
                    'semantic_score': result.get('semantic_score'),
                    'bm25_score': result.get('bm25_score')
                }
                for result in top_results
            ],
            search_duration_ms=search_duration,
            embedding_duration_ms=embedding_duration
        )
        
        return top_results, search_query
    
    def _combine_results(
        self, 
        semantic_results: List[Dict], 
        bm25_results: List[Dict],
        semantic_weight: float,
        bm25_weight: float
    ) -> List[Dict[str, Any]]:
        """Combina resultados dos dois métodos de busca"""
        
        # Criar dicionário para combinar por chunk_id
        combined = {}
        
        # Normalizar scores semânticos (0-1)
        if semantic_results:
            max_semantic_score = max(result['score'] for result in semantic_results)
            min_semantic_score = min(result['score'] for result in semantic_results)
            score_range = max_semantic_score - min_semantic_score
            
            for result in semantic_results:
                chunk_id = result['chunk_id']
                normalized_score = (result['score'] - min_semantic_score) / score_range if score_range > 0 else 0
                
                combined[chunk_id] = {
                    **result,
                    'semantic_score': normalized_score,
                    'bm25_score': 0.0
                }
        
        # Normalizar scores BM25 (0-1)
        if bm25_results:
            max_bm25_score = max(result['score'] for result in bm25_results)
            min_bm25_score = min(result['score'] for result in bm25_results)
            score_range = max_bm25_score - min_bm25_score
            
            for result in bm25_results:
                chunk_id = result['chunk_id']
                normalized_score = (result['score'] - min_bm25_score) / score_range if score_range > 0 else 0
                
                if chunk_id in combined:
                    combined[chunk_id]['bm25_score'] = normalized_score
                else:
                    combined[chunk_id] = {
                        **result,
                        'semantic_score': 0.0,
                        'bm25_score': normalized_score
                    }
        
        # Calcular score combinado
        for chunk_id, result in combined.items():
            result['combined_score'] = (
                result['semantic_score'] * semantic_weight +
                result['bm25_score'] * bm25_weight
            )
        
        # Ordenar por score combinado
        sorted_results = sorted(
            combined.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )
        
        return sorted_results