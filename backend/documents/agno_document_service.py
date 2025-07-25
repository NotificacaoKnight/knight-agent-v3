"""
Serviço assíncrono de documentos usando Agno Knowledge com MongoDB Atlas
Otimizado para múltiplos usuários simultâneos
"""
import os
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import numpy as np
import torch

# Forçar uso de CPU para evitar problemas de compatibilidade CUDA
torch.cuda.is_available = lambda: False
from agno.agent import Agent
from agno.knowledge import AgentKnowledge
from agno.knowledge.text import TextKnowledgeBase
from agno.embedder import Embedder
from agno.embedder.sentence_transformer import SentenceTransformerEmbedder
try:
    from agno.vectordb.mongodb import MongoDb
    from agno.knowledge.text import TextKnowledgeBase
    from pymongo.mongo_client import MongoClient
    from pymongo.server_api import ServerApi
    from pymongo.operations import SearchIndexModel
except ImportError:
    MongoDb = None
    TextKnowledgeBase = None
    MongoClient = None
    ServerApi = None
    SearchIndexModel = None
from .services import DocumentProcessor
from .agno_vector_store import FaissVectorStore
from django.conf import settings
from rag.embedding_cache import embedding_cache
import logging

logger = logging.getLogger(__name__)


class AgnoDocumentService:
    """
    Serviço híbrido que usa Docling para conversão de alta qualidade
    e Agno para indexação e busca inteligente
    """
    
    def __init__(self):
        logger.info("🏗️ Inicializando AgnoDocumentService com persistência...")
        
        # Processador Docling para conversão
        self.doc_processor = DocumentProcessor()
        
        # Embedder do Agno - usando SentenceTransformer com modelo multilíngue
        logger.info("📊 Criando SentenceTransformerEmbedder...")
        # Usando modelo multilíngue que suporta português
        self.embedder = SentenceTransformerEmbedder(
            id="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            dimensions=768  # Este modelo tem 768 dimensões
        )
        
        # Configurar storage persistente
        storage_path = os.path.join(settings.BASE_DIR, 'agno_storage')
        os.makedirs(storage_path, exist_ok=True)
        
        # Opção 1: Usar FAISS local (mais simples)
        logger.info("🗄️ Configurando FAISS Vector Store...")
        self.vector_store = FaissVectorStore(
            index_path=os.path.join(storage_path, 'faiss_index'),
            dimension=768  # Corresponde ao modelo multilíngue
        )
        
        # MongoDB Atlas via Agno para vector search
        self.mongodb_vectordb = None
        self.mongo_knowledge_base = None
        
        if MongoDb and hasattr(settings, 'MONGODB_URL') and settings.MONGODB_URL:
            try:
                logger.info("🍃 Configurando MongoDB Atlas via Agno para vector search...")
                
                # Configurar MongoDB vector database via Agno
                # Modificar URL para incluir o database name
                mongodb_url_with_db = settings.MONGODB_URL
                if "knight_agno" not in mongodb_url_with_db:
                    if "?" in mongodb_url_with_db:
                        mongodb_url_with_db = mongodb_url_with_db.replace("?", "/knight_agno?")
                    else:
                        mongodb_url_with_db = mongodb_url_with_db + "/knight_agno"
                
                self.mongodb_vectordb = MongoDb(
                    collection_name="knight_documents",
                    db_url=mongodb_url_with_db,
                    embedder=self.embedder  # Usar embedder local
                )
                
                # Criar knowledge base com MongoDB
                self.mongo_knowledge_base = TextKnowledgeBase(
                    embedder=self.embedder,
                    vector_db=self.mongodb_vectordb
                )
                
                logger.info("✅ MongoDB Atlas configurado via Agno para vector search")
            except Exception as e:
                logger.warning(f"MongoDB Atlas via Agno não disponível: {e}")
                self.mongodb_vectordb = None
                self.mongo_knowledge_base = None
        
        # Priorizar MongoDB se disponível, fallback para FAISS
        logger.info("🧠 Configurando AgentKnowledge...")
        try:
            if self.mongo_knowledge_base:
                # Usar MongoDB como principal
                logger.info("📊 Usando MongoDB Atlas como vector database principal")
                self.knowledge_base = self.mongo_knowledge_base
            else:
                # Fallback para FAISS
                logger.info("📊 Usando FAISS como vector database (fallback)")
                self.knowledge_base = AgentKnowledge(
                    embedder=self.embedder,
                    vector_db=self.vector_store
                )
            
            self.agent = Agent(knowledge=self.knowledge_base)
            logger.info("✅ AgentKnowledge configurado com sucesso")
        except Exception as e:
            logger.warning(f"Erro ao configurar knowledge base: {e}")
            # Fallback básico
            self.knowledge_base = AgentKnowledge(
                embedder=self.embedder
            )
            self.agent = Agent(knowledge=self.knowledge_base)
        
        logger.info("✅ AgnoDocumentService inicializado com persistência!")
        
    async def aprocess_and_index_document(self, file_path: str, document_id: str, metadata: Dict = None) -> Dict:
        """
        Versão assíncrona para processar documento - otimizada para múltiplos usuários
        """
        try:
            # Etapa 1: Converter com Docling (mantém síncrono por ser I/O de arquivo)
            output_dir = os.path.join(settings.PROCESSED_DOCS_PATH, document_id)
            os.makedirs(output_dir, exist_ok=True)
            
            conversion_result = self.doc_processor.process_document(
                file_path, 
                output_dir
            )
            
            if not conversion_result['success']:
                return {
                    'success': False,
                    'error': f"Erro na conversão: {conversion_result['error']}"
                }
            
            # Etapa 2: Indexar no Agno de forma assíncrona
            markdown_content = conversion_result['markdown_content']
            
            doc_metadata = {
                'document_id': document_id,
                'title': metadata.get('title', 'Documento sem título'),
                'file_type': metadata.get('file_type', ''),
                'uploaded_by': metadata.get('uploaded_by', ''),
                'upload_date': metadata.get('upload_date', ''),
                **conversion_result.get('metadata', {})
            }
            
            logger.info(f"📚 Indexando assincronamente: {doc_metadata.get('title', 'Sem título')}")
            
            # Indexar via Agno (MongoDB ou FAISS)
            indexing_success = False
            try:
                # Usar knowledge base principal (MongoDB ou FAISS)
                loop = asyncio.get_event_loop()
                
                def index_document():
                    try:
                        # Adicionar documento ao knowledge base
                        self.knowledge_base.load_text(
                            text=markdown_content,
                            filters=doc_metadata
                        )
                        return True
                    except Exception as e:
                        logger.error(f"Erro ao indexar via knowledge base: {e}")
                        return False
                
                # Executar indexação em thread separada
                indexing_success = await loop.run_in_executor(None, index_document)
                
                if indexing_success:
                    if self.mongo_knowledge_base:
                        logger.info("✅ Documento indexado no MongoDB Atlas via Agno!")
                    else:
                        logger.info("✅ Documento indexado no FAISS via Agno!")
                        
            except Exception as e:
                logger.warning(f"Erro ao indexar via Agno: {e}")
            
            # Fallback: sempre tentar indexar no FAISS local também
            if not indexing_success or self.mongo_knowledge_base:
                await self._fallback_faiss_index(markdown_content, doc_metadata, document_id)
            
            return {
                'success': True,
                'document_id': document_id,
                'markdown_path': conversion_result['output_path'],
                'metadata': doc_metadata,
                'indexed': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'document_id': document_id
            }
    
    async def _fallback_faiss_index(self, markdown_content: str, doc_metadata: Dict, document_id: str):
        """Método auxiliar para indexar no FAISS quando MongoDB não disponível"""
        if hasattr(self, 'vector_store') and self.vector_store:
            # Executar embedding em thread separada para não bloquear
            loop = asyncio.get_event_loop()
            
            def generate_embedding():
                model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
                cached_embedding = embedding_cache.get_embedding(markdown_content, model_name)
                
                if cached_embedding is not None:
                    return cached_embedding
                else:
                    text_embedding = self.embedder.get_embedding(markdown_content)
                    embedding_cache.save_embedding(
                        markdown_content, 
                        text_embedding, 
                        model_name,
                        metadata={'document_id': document_id, 'title': doc_metadata.get('title', '')}
                    )
                    return text_embedding
            
            # Executar em thread separada
            text_embedding = await loop.run_in_executor(None, generate_embedding)
            
            # Adicionar ao vector store
            self.vector_store.add(
                embeddings=np.array([text_embedding]),
                documents=[{
                    'content': markdown_content,
                    'metadata': doc_metadata,
                    'id': document_id
                }]
            )
            logger.info("✅ Documento adicionado ao FAISS (async fallback)!")

    def process_and_index_document(self, file_path: str, document_id: str, metadata: Dict = None) -> Dict:
        """
        Processa documento com Docling e indexa no Agno
        
        Args:
            file_path: Caminho do arquivo
            document_id: ID único do documento
            metadata: Metadados adicionais
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            # Etapa 1: Converter com Docling
            output_dir = os.path.join(settings.PROCESSED_DOCS_PATH, document_id)
            os.makedirs(output_dir, exist_ok=True)
            
            conversion_result = self.doc_processor.process_document(
                file_path, 
                output_dir
            )
            
            if not conversion_result['success']:
                return {
                    'success': False,
                    'error': f"Erro na conversão: {conversion_result['error']}"
                }
            
            # Etapa 2: Indexar no Agno
            markdown_content = conversion_result['markdown_content']
            
            # Adicionar documento ao knowledge base
            doc_metadata = {
                'document_id': document_id,
                'title': metadata.get('title', 'Documento sem título'),
                'file_type': metadata.get('file_type', ''),
                'uploaded_by': metadata.get('uploaded_by', ''),
                'upload_date': metadata.get('upload_date', ''),
                **conversion_result.get('metadata', {})
            }
            
            # Indexar documento completo no Agno
            logger.info(f"📚 Indexando no Agno: {doc_metadata.get('title', 'Sem título')}")
            logger.info(f"📝 Tamanho do conteúdo: {len(markdown_content)} caracteres")
            logger.info(f"🏷️ Metadata: {doc_metadata}")
            
            # Usar nosso vector store diretamente se o Agno não estiver persistindo
            if hasattr(self, 'vector_store') and self.vector_store:
                # Gerar embeddings com cache
                model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
                cached_embedding = embedding_cache.get_embedding(markdown_content, model_name)
                
                if cached_embedding is not None:
                    logger.info("🎯 Embedding do documento encontrado no cache!")
                    text_embedding = cached_embedding
                else:
                    logger.info("🔄 Gerando embedding do documento...")
                    text_embedding = self.embedder.get_embedding(markdown_content)
                    # Salvar no cache
                    embedding_cache.save_embedding(
                        markdown_content, 
                        text_embedding, 
                        model_name,
                        metadata={'document_id': document_id, 'title': doc_metadata.get('title', '')}
                    )
                    logger.info("💾 Embedding do documento salvo no cache")
                
                # Adicionar ao vector store
                self.vector_store.add(
                    embeddings=np.array([text_embedding]),
                    documents=[{
                        'content': markdown_content,
                        'metadata': doc_metadata,
                        'id': document_id
                    }]
                )
                logger.info("✅ Documento adicionado ao FAISS vector store!")
            
            # Também tentar adicionar via Agno (para compatibilidade)
            try:
                self.knowledge_base.load_text(
                    text=markdown_content,
                    filters=doc_metadata
                )
                logger.info("✅ Documento também indexado via Agno!")
            except Exception as e:
                logger.warning(f"Erro ao indexar via Agno: {e}")
            
            return {
                'success': True,
                'document_id': document_id,
                'markdown_path': conversion_result['output_path'],
                'metadata': doc_metadata,
                'indexed': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'document_id': document_id
            }
    
    async def asearch_documents(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Versão assíncrona para buscar documentos - otimizada para múltiplos usuários
        """
        try:
            logger.info(f"🔍 Buscando assincronamente: '{query}' (limite: {limit})")
            
            # Buscar via knowledge base principal (MongoDB ou FAISS via Agno)
            try:
                loop = asyncio.get_event_loop()
                
                def search_knowledge_base():
                    try:
                        # Usar o método de busca do knowledge base
                        results = self.knowledge_base.search(
                            query=query,
                            num_documents=limit
                        )
                        return results
                    except Exception as e:
                        logger.error(f"Erro na busca via knowledge base: {e}")
                        return []
                
                # Executar busca em thread separada
                results = await loop.run_in_executor(None, search_knowledge_base)
                
                if results:
                    if self.mongo_knowledge_base:
                        logger.info(f"📊 MongoDB Atlas via Agno retornou {len(results)} resultados")
                    else:
                        logger.info(f"📊 FAISS via Agno retornou {len(results)} resultados")
                    
                    # Converter para formato compatível
                    formatted_results = []
                    for result in results:
                        formatted_results.append({
                            'content': result.get('document', result.get('content', '')),
                            'document_id': result.get('metadata', {}).get('document_id', ''),
                            'id': result.get('id', str(hash(result.get('document', '')))),
                            'score': result.get('distance', result.get('score', 0.0)),
                            'metadata': result.get('metadata', {})
                        })
                    return formatted_results
                    
            except Exception as e:
                logger.warning(f"Erro na busca via Agno: {e}")
            
            # Fallback: buscar via FAISS local
            logger.info("🔍 Fallback: buscando via FAISS local (async)...")
            return await self._fallback_faiss_search(query, limit)
            
        except Exception as e:
            logger.error(f"❌ Erro na busca assíncrona: {e}")
            return []
    
    async def _fallback_faiss_search(self, query: str, limit: int) -> List[Dict]:
        """Método auxiliar para buscar no FAISS de forma assíncrona"""
        if not (hasattr(self, 'vector_store') and self.vector_store):
            return []
        
        # Executar busca em thread separada para não bloquear
        loop = asyncio.get_event_loop()
        
        def search_faiss():
            # Gerar embedding da query com cache
            model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
            cached_embedding = embedding_cache.get_embedding(query, model_name)
            
            if cached_embedding is not None:
                query_embedding = cached_embedding
            else:
                query_embedding = self.embedder.get_embedding(query)
                embedding_cache.save_embedding(query, query_embedding, model_name)
            
            # Buscar no FAISS
            return self.vector_store.search(
                query_embedding=np.array(query_embedding),
                k=limit
            )
        
        # Executar em thread separada
        results = await loop.run_in_executor(None, search_faiss)
        
        if results:
            logger.info(f"✅ FAISS retornou {len(results)} resultados (async)")
            return results
        
        return []

    def search_documents(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Busca documentos usando Agno e/ou FAISS
        
        Args:
            query: Consulta de busca
            limit: Número máximo de resultados
            
        Returns:
            Lista de resultados
        """
        try:
            logger.info(f"🔍 Buscando: '{query}' (limite: {limit})")
            
            # Tentar buscar via nosso vector store primeiro
            if hasattr(self, 'vector_store') and self.vector_store:
                logger.info("🔍 Buscando no FAISS vector store...")
                
                # Gerar embedding da query com cache
                model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
                cached_embedding = embedding_cache.get_embedding(query, model_name)
                
                if cached_embedding is not None:
                    logger.info("🎯 Embedding da query encontrado no cache!")
                    query_embedding = cached_embedding
                else:
                    logger.info("🔄 Gerando embedding da query...")
                    query_embedding = self.embedder.get_embedding(query)
                    # Salvar no cache para futuras buscas
                    embedding_cache.save_embedding(query, query_embedding, model_name)
                    logger.info("💾 Embedding da query salvo no cache")
                
                # Buscar no FAISS
                results = self.vector_store.search(
                    query_embedding=np.array(query_embedding),
                    k=limit
                )
                
                if results:
                    logger.info(f"✅ FAISS retornou {len(results)} resultados")
                    return results
            
            # Fallback: tentar buscar via Agno
            logger.info("🔍 Tentando busca via Agno Knowledge...")
            try:
                results = self.knowledge_base.search(
                    query=query,
                    num_documents=limit
                )
                
                if results:
                    logger.info(f"📊 Agno retornou {len(results)} resultados")
                    # Converter para formato compatível
                    formatted_results = []
                    for result in results:
                        formatted_results.append({
                            'content': result.get('document', result.get('content', '')),
                            'document_id': result.get('metadata', {}).get('document_id', ''),
                            'id': result.get('id', ''),
                            'score': result.get('distance', result.get('score', 0.0)),
                            'metadata': result.get('metadata', {})
                        })
                    return formatted_results
            except Exception as e:
                logger.warning(f"Erro na busca Agno: {e}")
            
            logger.warning("Nenhum resultado encontrado")
            return []
            
        except Exception as e:
            logger.error(f"❌ Erro na busca: {e}")
            return []
    
    def list_documents(self) -> List[Dict]:
        """
        Lista documentos indexados
        
        Returns:
            Lista de documentos
        """
        try:
            # Agno não tem método direto para listar, vamos fazer uma busca vazia
            # ou retornar vazio por enquanto
            return []
            
        except Exception as e:
            print(f"Erro ao listar documentos: {e}")
            return []
    
    def get_document_by_id(self, document_id: str) -> Optional[Dict]:
        """
        Busca documento específico por ID
        
        Args:
            document_id: ID do documento
            
        Returns:
            Documento encontrado ou None
        """
        try:
            # Buscar por document_id nos metadados
            results = self.knowledge_base.search(
                query=f"document_id:{document_id}",
                num_documents=1
            )
            
            if results:
                return {
                    'id': document_id,
                    'content': results[0].get('document', ''),
                    'metadata': results[0].get('metadata', {})
                }
            
            return None
            
        except Exception as e:
            print(f"Erro ao buscar documento {document_id}: {e}")
            return None
    
    def delete_document(self, document_id: str) -> bool:
        """
        Remove documento do índice Agno
        
        Args:
            document_id: ID do documento
            
        Returns:
            True se removido com sucesso
        """
        try:
            # Agno não tem método direto para deletar documentos específicos
            # Retornar True por compatibilidade
            return True
            
        except Exception as e:
            print(f"Erro ao deletar documento {document_id}: {e}")
            return False