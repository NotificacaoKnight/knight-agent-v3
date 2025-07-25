"""
Serviço específico para MongoDB com Agno Knowledge Base
Implementa vector search nativo do MongoDB Atlas
"""
import os
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

# Forçar uso de CPU para compatibilidade
import torch
torch.cuda.is_available = lambda: False

try:
    from agno.agent import Agent
    from agno.knowledge.text import TextKnowledgeBase
    from agno.vectordb.mongodb import MongoDb
    from agno.embedder.sentence_transformer import SentenceTransformerEmbedder
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False

from django.conf import settings
from .services import DocumentProcessor

logger = logging.getLogger(__name__)


class AgnoMongoDBService:
    """
    Serviço que usa MongoDB Atlas como vector database via Agno
    Otimizado para busca semântica em documentos corporativos em português
    """
    
    def __init__(self):
        if not AGNO_AVAILABLE:
            raise ImportError("Agno não está disponível. Instale com: pip install agno")
        
        if not hasattr(settings, 'MONGODB_URL') or not settings.MONGODB_URL:
            raise ValueError("MONGODB_URL não configurado no settings")
        
        logger.info("🏗️ Inicializando AgnoMongoDBService...")
        
        # Processador de documentos
        self.doc_processor = DocumentProcessor()
        
        # Embedder multilíngue otimizado para português
        logger.info("📊 Configurando SentenceTransformerEmbedder...")
        self.embedder = SentenceTransformerEmbedder(
            id="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            dimensions=768
        )
        
        # Configurar MongoDB vector database com embedder local
        logger.info("🍃 Configurando MongoDB Atlas vector database...")
        self.vector_db = MongoDb(
            collection_name="knight_documents",
            db_url=settings.MONGODB_URL,
            db_name="knight_agno",
            embedder=self.embedder  # Usar embedder local (sem OpenAI)
        )
        
        # Criar knowledge base com MongoDB
        logger.info("🧠 Criando TextKnowledgeBase com MongoDB...")
        self.knowledge_base = TextKnowledgeBase(
            embedder=self.embedder,
            vector_db=self.vector_db
        )
        
        # Criar agente Agno
        logger.info("🤖 Criando Knight Agent...")
        self.agent = Agent(
            name="Knight Agent",
            role="Assistente IA corporativo",
            description="Assistente interno da empresa para responder perguntas baseadas em documentos corporativos",
            instructions=[
                "Você é o Knight, um assistente IA interno da empresa",
                "Responda sempre em português brasileiro de forma clara e útil",
                "Use apenas as informações fornecidas no contexto para responder",
                "Se não souber a resposta, diga que não tem informações suficientes e sugira entrar em contato com o RH"
            ],
            knowledge=self.knowledge_base,
            markdown=True
        )
        
        logger.info("✅ AgnoMongoDBService inicializado com sucesso!")
    
    async def load_document_from_url(self, url: str, metadata: Dict = None) -> Dict:
        """
        Carrega documento de URL (como exemplo do Agno)
        
        Args:
            url: URL do documento PDF
            metadata: Metadados adicionais
            
        Returns:
            Dict com resultado do carregamento
        """
        try:
            logger.info(f"📥 Carregando documento de URL: {url}")
            
            # Usar PDFUrlKnowledgeBase do Agno
            from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
            
            pdf_knowledge = PDFUrlKnowledgeBase(
                urls=[url],
                vector_db=self.vector_db
            )
            
            # Carregar assincronamente
            await pdf_knowledge.aload(recreate=False)
            
            logger.info("✅ Documento carregado do URL com sucesso!")
            
            return {
                'success': True,
                'url': url,
                'metadata': metadata or {},
                'indexed': True
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar documento de URL: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
    
    async def aprocess_and_index_document(self, file_path: str, document_id: str, metadata: Dict = None) -> Dict:
        """
        Processa e indexa documento local no MongoDB via Agno
        
        Args:
            file_path: Caminho do arquivo
            document_id: ID único do documento
            metadata: Metadados adicionais
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            logger.info(f"📄 Processando documento: {file_path}")
            
            # Processar com Docling
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
            
            # Preparar metadados
            doc_metadata = {
                'document_id': document_id,
                'title': metadata.get('title', 'Documento sem título'),
                'file_type': metadata.get('file_type', ''),
                'uploaded_by': metadata.get('uploaded_by', ''),
                'upload_date': metadata.get('upload_date', ''),
                **conversion_result.get('metadata', {})
            }
            
            # Indexar no MongoDB via Agno
            markdown_content = conversion_result['markdown_content']
            
            logger.info(f"📚 Indexando no MongoDB via Agno: {doc_metadata.get('title', 'Sem título')}")
            
            # Executar indexação assíncrona
            loop = asyncio.get_event_loop()
            
            def index_document():
                try:
                    self.knowledge_base.load_text(
                        text=markdown_content,
                        filters=doc_metadata
                    )
                    return True
                except Exception as e:
                    logger.error(f"Erro ao indexar: {e}")
                    return False
            
            # Executar em thread separada
            success = await loop.run_in_executor(None, index_document)
            
            if success:
                logger.info("✅ Documento indexado no MongoDB Atlas via Agno!")
                return {
                    'success': True,
                    'document_id': document_id,
                    'markdown_path': conversion_result['output_path'],
                    'metadata': doc_metadata,
                    'indexed': True
                }
            else:
                return {
                    'success': False,
                    'error': 'Falha na indexação',
                    'document_id': document_id
                }
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento: {e}")
            return {
                'success': False,
                'error': str(e),
                'document_id': document_id
            }
    
    async def asearch_documents(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Busca documentos no MongoDB via Agno
        
        Args:
            query: Consulta de busca
            limit: Número máximo de resultados
            
        Returns:
            Lista de resultados
        """
        try:
            logger.info(f"🔍 Buscando no MongoDB via Agno: '{query}' (limite: {limit})")
            
            # Executar busca assíncrona
            loop = asyncio.get_event_loop()
            
            def search_knowledge():
                try:
                    results = self.knowledge_base.search(
                        query=query,
                        num_documents=limit
                    )
                    return results
                except Exception as e:
                    logger.error(f"Erro na busca: {e}")
                    return []
            
            # Executar em thread separada
            results = await loop.run_in_executor(None, search_knowledge)
            
            if results:
                logger.info(f"📊 MongoDB Atlas retornou {len(results)} resultados")
                
                # Converter para formato compatível
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        'content': result.get('document', result.get('content', '')),
                        'document_id': result.get('metadata', {}).get('document_id', ''),
                        'id': result.get('id', str(hash(result.get('document', '')))),
                        'score': 1.0 - result.get('distance', 0.0),  # Converter distance para score
                        'metadata': result.get('metadata', {})
                    })
                
                return formatted_results
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Erro na busca: {e}")
            return []
    
    async def agenerate_response(self, query: str, context: List[str] = None) -> Dict[str, Any]:
        """
        Gera resposta usando o agente Agno com contexto
        
        Args:
            query: Pergunta do usuário
            context: Contexto adicional (opcional)
            
        Returns:
            Dict com resposta gerada
        """
        try:
            logger.info(f"🤖 Gerando resposta via Agno Agent: '{query}'")
            
            # Preparar mensagem
            if context:
                context_text = "\n\n".join([f"Documento {i+1}:\n{doc}" for i, doc in enumerate(context)])
                full_message = f"Contexto:\n{context_text}\n\nPergunta: {query}"
            else:
                full_message = query
            
            # Executar agente assincronamente
            loop = asyncio.get_event_loop()
            
            def run_agent():
                try:
                    response = self.agent.run(
                        message=full_message,
                        stream=False
                    )
                    return response
                except Exception as e:
                    logger.error(f"Erro no agente: {e}")
                    return None
            
            # Executar em thread separada
            response = await loop.run_in_executor(None, run_agent)
            
            if response:
                # Extrair resposta
                if hasattr(response, 'content'):
                    if isinstance(response.content, list) and len(response.content) > 0:
                        response_text = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
                    else:
                        response_text = str(response.content)
                elif isinstance(response, str):
                    response_text = response
                else:
                    response_text = str(response)
                
                logger.info("✅ Resposta gerada com sucesso!")
                
                return {
                    'success': True,
                    'response': response_text,
                    'provider': 'agno_mongodb',
                    'documents_used': len(context) if context else 0
                }
            
            return {
                'success': False,
                'error': 'Falha na geração de resposta',
                'provider': 'agno_mongodb'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na geração de resposta: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'agno_mongodb'
            }
    
    def is_available(self) -> bool:
        """Verifica se o serviço está disponível"""
        return (
            AGNO_AVAILABLE and 
            hasattr(settings, 'MONGODB_URL') and 
            bool(settings.MONGODB_URL) and
            self.vector_db is not None and
            self.knowledge_base is not None
        )


# Instância global do serviço (singleton)
_agno_mongodb_service = None

def get_agno_mongodb_service() -> Optional[AgnoMongoDBService]:
    """
    Retorna instância singleton do serviço MongoDB Agno
    
    Returns:
        Instância do serviço ou None se não disponível
    """
    global _agno_mongodb_service
    
    if _agno_mongodb_service is None:
        try:
            _agno_mongodb_service = AgnoMongoDBService()
        except Exception as e:
            logger.warning(f"AgnoMongoDBService não disponível: {e}")
            _agno_mongodb_service = None
    
    return _agno_mongodb_service