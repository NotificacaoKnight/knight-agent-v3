import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from django.conf import settings
from documents.models import Document
from rag.services import HybridSearchService
from rag.llm_providers import LLMManager
from documents.agno_document_service import AgnoDocumentService
from .models import ChatSession, ChatMessage, DocumentRequest

class KnightChatService:
    """Serviço principal do agente Knight"""
    
    def __init__(self):
        self.search_service = HybridSearchService()
        self.agno_service = AgnoDocumentService()
        self.llm_manager = LLMManager()
        self.max_context_chunks = 5
        self.max_context_length = 4000
        self.use_agno_search = getattr(settings, 'USE_AGNO_SEARCH', True)
    
    def process_message(
        self, 
        user_message: str, 
        session: ChatSession,
        search_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Processa mensagem do usuário e gera resposta"""
        
        start_time = time.time()
        
        try:
            # Salvar mensagem do usuário
            user_msg = ChatMessage.objects.create(
                session=session,
                message_type='user',
                content=user_message
            )
            
            # Verificar se é solicitação de documento
            document_request = self._detect_document_request(user_message)
            
            if document_request:
                return self._handle_document_request(
                    user_message, 
                    session, 
                    user_msg, 
                    document_request
                )
            
            # Buscar contexto relevante
            try:
                if self.use_agno_search:
                    # Usar Agno para busca de contexto
                    search_results = self.agno_service.search_documents(
                        query=user_message,
                        limit=self.max_context_chunks
                    )
                    search_query = None  # Agno gerencia queries internamente
                    
                    # Converter resultados do Agno para formato compatível
                    formatted_results = []
                    for result in search_results:
                        # Garantir que temos um document_id válido
                        doc_id = result.get('document_id') or result.get('metadata', {}).get('document_id') or result.get('id', 'unknown')
                        
                        formatted_results.append({
                            'content': result.get('content', ''),
                            'document_id': doc_id,
                            'chunk_id': result.get('id', ''),
                            'combined_score': result.get('score', 0.0)
                        })
                    search_results = formatted_results
                else:
                    # Usar sistema híbrido tradicional
                    search_results, search_query = self.search_service.search(
                        user_message,
                        k=self.max_context_chunks,
                        user=session.user,
                        **(search_params or {})
                    )
            except Exception as search_error:
                # Se a busca falhar, continuar sem contexto
                search_results = []
                search_query = None
            
            # Preparar contexto para o LLM
            context_chunks = []
            context_metadata = []
            
            for result in search_results:
                if len('\n'.join(context_chunks)) < self.max_context_length:
                    context_chunks.append(result['content'])
                    context_metadata.append({
                        'document_id': result['document_id'],
                        'chunk_id': result['chunk_id'],
                        'score': result['combined_score']
                    })
            
            # Gerar resposta com contexto de fontes
            source_info = []
            for i, result in enumerate(search_results[:len(context_chunks)]):
                # Buscar informações do documento original
                try:
                    from documents.models import Document
                    doc_id = result['document_id']
                    
                    # Se for um ID numérico, buscar no banco
                    if doc_id.isdigit():
                        doc = Document.objects.get(id=int(doc_id))
                        source_info.append({
                            'index': i + 1,
                            'title': doc.title,
                            'filename': doc.original_filename,
                            'score': result['combined_score']
                        })
                    else:
                        # Para IDs de teste ou metadados, usar informações do resultado
                        title = result.get('metadata', {}).get('title', f'Documento {doc_id}')
                        source_info.append({
                            'index': i + 1,
                            'title': title,
                            'filename': 'Documento de teste',
                            'score': result['combined_score']
                        })
                except (Document.DoesNotExist, ValueError):
                    # Usar informações dos metadados se disponíveis
                    title = result.get('metadata', {}).get('title', f'Documento {result["document_id"]}')
                    source_info.append({
                        'index': i + 1,
                        'title': title,
                        'filename': 'N/A',
                        'score': result['combined_score']
                    })
            
            # Preparar prompt com instruções para citar fontes
            enhanced_prompt = self._prepare_prompt_with_citations(
                user_message, 
                context_chunks, 
                source_info
            )
            
            llm_response = self.llm_manager.generate_response(
                prompt=enhanced_prompt,
                context=context_chunks,
                max_tokens=1200,  # Aumentar para acomodar citações
                temperature=0.7
            )
            
            if not llm_response['success']:
                return self._handle_llm_error(session, user_msg, llm_response['error'])
            
            # Salvar resposta do assistente
            response_time = int((time.time() - start_time) * 1000)
            
            assistant_msg = ChatMessage.objects.create(
                session=session,
                message_type='assistant',
                content=llm_response['response'],
                context_used=context_metadata,
                search_query_id=search_query.id if search_query else None,
                llm_provider=llm_response['provider'],
                llm_model=llm_response.get('model', ''),
                response_time_ms=response_time
            )
            
            # Atualizar sessão
            session.message_count += 2  # user + assistant
            session.last_message_at = datetime.now()
            if not session.title:
                session.title = self._generate_session_title(user_message)
            session.save()
            
            return {
                'success': True,
                'response': llm_response['response'],
                'message_id': assistant_msg.id,
                'context_used': len(context_chunks),
                'search_results': len(search_results),
                'sources': source_info,
                'response_time_ms': response_time,
                'provider_used': llm_response['provider'],
                'fallback_used': llm_response.get('fallback_used', False)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response': "Desculpe, ocorreu um erro interno. Tente novamente ou entre em contato com o suporte técnico.",
                'response_time_ms': int((time.time() - start_time) * 1000)
            }
    
    def _detect_document_request(self, message: str) -> Optional[str]:
        """Detecta se a mensagem é uma solicitação de documento"""
        message_lower = message.lower()
        
        # Palavras-chave que indicam solicitação de documento
        document_keywords = [
            'baixar', 'download', 'enviar', 'mandar', 'preciso do',
            'me mande', 'pode enviar', 'formulário', 'documento',
            'arquivo', 'modelo', 'template'
        ]
        
        if any(keyword in message_lower for keyword in document_keywords):
            return message
        
        return None
    
    def _handle_document_request(
        self, 
        user_message: str, 
        session: ChatSession,
        user_msg: ChatMessage,
        document_request: str
    ) -> Dict[str, Any]:
        """Lida com solicitações de documentos"""
        
        # Buscar documentos baixáveis relacionados
        search_results, _ = self.search_service.search(
            document_request,
            k=5,
            user=session.user
        )
        
        # Filtrar apenas documentos baixáveis
        downloadable_docs = []
        for result in search_results:
            try:
                document = Document.objects.get(
                    id=result['document_id'],
                    is_downloadable=True,
                    is_active=True
                )
                downloadable_docs.append({
                    'id': document.id,
                    'title': document.title,
                    'filename': document.original_filename,
                    'score': result['combined_score']
                })
            except Document.DoesNotExist:
                continue
        
        # Gerar resposta
        if downloadable_docs:
            # Criar requisições de documento
            for doc in downloadable_docs[:3]:  # Máximo 3 documentos
                DocumentRequest.objects.create(
                    session=session,
                    message=user_msg,
                    document_name=doc['title'],
                    document_id=doc['id'],
                    status='found'
                )
            
            doc_list = "\n".join([
                f"• {doc['title']} ({doc['filename']})"
                for doc in downloadable_docs[:3]
            ])
            
            response = (
                f"Encontrei os seguintes documentos relacionados à sua solicitação:\n\n"
                f"{doc_list}\n\n"
                f"Você pode baixá-los na seção de Downloads. "
                f"Se não encontrou o que procura, entre em contato com o RH."
            )
        else:
            # Nenhum documento encontrado
            DocumentRequest.objects.create(
                session=session,
                message=user_msg,
                document_name=document_request,
                status='not_found'
            )
            
            response = (
                "Não encontrei documentos baixáveis relacionados à sua solicitação. "
                "Entre em contato com o RH para obter os documentos necessários."
            )
        
        # Salvar resposta
        assistant_msg = ChatMessage.objects.create(
            session=session,
            message_type='assistant',
            content=response,
            llm_provider='document_search'
        )
        
        # Atualizar sessão
        session.message_count += 2
        session.last_message_at = datetime.now()
        if not session.title:
            session.title = "Solicitação de Documentos"
        session.save()
        
        return {
            'success': True,
            'response': response,
            'message_id': assistant_msg.id,
            'documents_found': len(downloadable_docs),
            'document_request': True
        }
    
    def _handle_llm_error(self, session: ChatSession, user_msg: ChatMessage, error: str) -> Dict[str, Any]:
        """Lida com erros do LLM"""
        
        error_response = (
            "Desculpe, estou tendo dificuldades técnicas no momento. "
            "Tente novamente em alguns instantes ou entre em contato com o suporte técnico. "
            f"Você também pode contatar o RH diretamente para questões urgentes."
        )
        
        assistant_msg = ChatMessage.objects.create(
            session=session,
            message_type='assistant',
            content=error_response,
            llm_provider='error_handler'
        )
        
        session.message_count += 2
        session.last_message_at = datetime.now()
        session.save()
        
        return {
            'success': False,
            'response': error_response,
            'message_id': assistant_msg.id,
            'error': error
        }
    
    def _generate_session_title(self, first_message: str) -> str:
        """Gera título para a sessão baseado na primeira mensagem"""
        # Simplificar para primeiras palavras
        words = first_message.split()
        if len(words) > 5:
            return ' '.join(words[:5]) + '...'
        return first_message[:50]
    
    def get_session_history(self, session_id: int, user) -> List[Dict[str, Any]]:
        """Busca histórico de mensagens da sessão"""
        try:
            session = ChatSession.objects.get(id=session_id, user=user)
            messages = session.messages.all()
            
            history = []
            for message in messages:
                history.append({
                    'id': message.id,
                    'type': message.message_type,
                    'content': message.content,
                    'created_at': message.created_at,
                    'context_used': len(message.context_used) if message.context_used else 0,
                    'provider': message.llm_provider,
                    'response_time_ms': message.response_time_ms
                })
            
            return history
            
        except ChatSession.DoesNotExist:
            return []
    
    def create_session(self, user) -> ChatSession:
        """Cria nova sessão de chat"""
        return ChatSession.objects.create(user=user)
    
    def get_user_sessions(self, user, limit: int = 20) -> List[Dict[str, Any]]:
        """Lista sessões do usuário"""
        sessions = ChatSession.objects.filter(
            user=user,
            is_active=True
        )[:limit]
        
        session_list = []
        for session in sessions:
            session_list.append({
                'id': session.id,
                'title': session.title or f'Chat {session.id}',
                'message_count': session.message_count,
                'last_message_at': session.last_message_at,
                'created_at': session.created_at
            })
        
        return session_list
    
    def _prepare_prompt_with_citations(
        self, 
        user_message: str, 
        context_chunks: List[str], 
        source_info: List[Dict[str, Any]]
    ) -> str:
        """Prepara prompt com instruções para incluir citações"""
        
        if not context_chunks:
            return user_message
        
        # Preparar lista de fontes
        sources_list = []
        for source in source_info:
            sources_list.append(f"[{source['index']}] {source['title']}")
        
        # Montar contexto numerado
        numbered_context = []
        for i, chunk in enumerate(context_chunks):
            numbered_context.append(f"[Fonte {i+1}]\n{chunk}")
        
        enhanced_prompt = f"""Baseando-se nas informações fornecidas abaixo, responda à pergunta do usuário de forma clara e precisa em português brasileiro.

IMPORTANTE: 
- Sempre que usar informações do contexto, cite a fonte usando o formato [1], [2], etc.
- Se não tiver informações suficientes no contexto, diga isso claramente
- Seja específico e objetivo nas respostas
- Use um tom profissional e prestativo

CONTEXTO DISPONÍVEL:
{chr(10).join(numbered_context)}

FONTES:
{chr(10).join(sources_list)}

PERGUNTA DO USUÁRIO: {user_message}

RESPOSTA:"""
        
        return enhanced_prompt