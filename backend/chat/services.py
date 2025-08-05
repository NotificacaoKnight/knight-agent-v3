import time
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from django.conf import settings
from django.core.files.storage import default_storage
from documents.models import Document
from rag.agentic_rag_service import AgenticRAGServiceSync
from rag.llm_providers import LLMManager
from .models import ChatSession, ChatMessage, DocumentRequest
from .audio_transcription import GeminiAudioTranscriptionService

class KnightChatService:
    """Serviço principal do agente Knight"""
    
    def __init__(self):
        # Usar apenas sistema agentic (que já tem fallback interno)
        self.agentic_service = AgenticRAGServiceSync()
        self.llm_manager = LLMManager()
        self.transcription_service = GeminiAudioTranscriptionService()
        self.max_context_chunks = 5
        self.max_context_length = 4000
    
    def transcribe_audio(self, audio_file) -> Dict[str, Any]:
        """Transcrever áudio para texto usando Google Gemini"""
        try:
            # Usar o serviço de transcrição Gemini
            result = self.transcription_service.transcribe_audio_with_speakers(audio_file)
            
            if result['success']:
                # Estimar duração do áudio
                duration = self.transcription_service.get_audio_duration_estimate(audio_file)
                result['duration'] = duration
                
                return {
                    'success': True,
                    'transcription': result['transcription'],
                    'duration': duration,
                    'has_speakers': result.get('has_speakers', False),
                    'service': 'gemini'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Erro na transcrição'),
                    'transcription': '',
                    'duration': 0.0
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'transcription': '',
                'duration': 0.0
            }
    
    def process_message(
        self, 
        user_message: str, 
        session: ChatSession,
        search_params: Optional[Dict] = None,
        audio_file=None,
        content_type: str = 'text'
    ) -> Dict[str, Any]:
        """Processa mensagem do usuário e gera resposta"""
        
        start_time = time.time()
        
        try:
            # Processar áudio se fornecido - SEMPRE transcrever antes do agente principal
            transcription = ""
            audio_duration = 0.0
            original_message = user_message
            
            if audio_file and content_type == 'audio':
                transcription_result = self.transcribe_audio(audio_file)
                if transcription_result['success']:
                    transcription = transcription_result['transcription']
                    audio_duration = transcription_result['duration']
                    
                    # IMPORTANTE: O agente principal sempre recebe o texto transcrito
                    # Isso garante que o RAG funcione corretamente com o conteúdo textual
                    user_message = transcription
                    
                    # Se havia texto original, combinar com a transcrição
                    if original_message and original_message.strip():
                        user_message = f"{original_message}\n\n[Transcrição do áudio]: {transcription}"
                        
                else:
                    # Se falhou a transcrição, retornar erro com mais detalhes
                    error_msg = transcription_result.get("error", "Erro desconhecido")
                    
                    # Mensagens de erro mais específicas para o usuário
                    if "Timeout" in error_msg or "not in an ACTIVE state" in error_msg:
                        user_message = "O áudio está sendo processado. Tente novamente em alguns segundos."
                    elif "muito grande" in error_msg.lower() or "20mb" in error_msg.lower():
                        user_message = "Arquivo de áudio muito grande. Por favor, envie um áudio de até 20MB ou com menos de 10 minutos."
                    elif "formato" in error_msg.lower() or "mime" in error_msg.lower():
                        user_message = "Formato de áudio não suportado. Tente gravar novamente."
                    else:
                        user_message = "Não foi possível transcrever o áudio enviado. Tente novamente ou envie uma mensagem de texto."
                    
                    return {
                        'success': False,
                        'error': f'Falha na transcrição do áudio: {error_msg}',
                        'response': user_message
                    }
            
            # Salvar mensagem do usuário
            user_msg = ChatMessage.objects.create(
                session=session,
                message_type='user',
                content_type=content_type,
                content=user_message,
                audio_file=audio_file if content_type == 'audio' else None,
                audio_duration=audio_duration if content_type == 'audio' else None,
                transcription=transcription if content_type == 'audio' else ''
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
            
            # Usar sistema agentic (que já tem fallback interno)
            agentic_result = self.agentic_service.search(
                query=user_message,
                k=self.max_context_chunks,
                user=session.user
            )
            
            # Usar resposta do sistema agentic
            llm_response = {
                'success': True,
                'response': agentic_result.get('response', ''),
                'provider': agentic_result.get('metadata', {}).get('provider_used', 'unknown'),
                'model': agentic_result.get('metadata', {}).get('model_used', '')
            }
            
            # Extrair metadados de contexto
            context_metadata = []
            search_results = agentic_result.get('search_results', [])
            for result in search_results:
                context_metadata.append({
                    'document_id': result.get('document_id'),
                    'chunk_id': result.get('chunk_id'),
                    'score': result.get('score', 0.0)
                })
            
            # Criar search_query para compatibilidade
            search_query = None  # Agentic não retorna search_query
            
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
            
            # Limpar sessões antigas quando uma sessão existente é atualizada
            self._cleanup_old_sessions(session.user)
            
            # Preparar dados da mensagem do usuário para retornar ao frontend
            user_message_data = {
                'id': str(user_msg.id),
                'type': 'user',
                'content': user_msg.content,
                'content_type': user_msg.content_type,
                'timestamp': user_msg.created_at.isoformat(),
                'audio_duration': user_msg.audio_duration,
                'transcription': user_msg.transcription
            }
            
            return {
                'success': True,
                'response': llm_response['response'],
                'message_id': assistant_msg.id,
                'user_message_data': user_message_data,
                'context_used': len(context_metadata),
                'search_results': len(search_results),
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
        
        # Limpar sessões antigas
        self._cleanup_old_sessions(session.user)
        
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
        
        # Limpar sessões antigas
        self._cleanup_old_sessions(session.user)
        
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
                    'content_type': message.content_type,
                    'created_at': message.created_at,
                    'transcription': message.transcription,
                    'audio_duration': message.audio_duration,
                    'audio_file': message.audio_file.url if message.audio_file else None,
                    'context_used': len(message.context_used) if message.context_used else 0,
                    'provider': message.llm_provider,
                    'response_time_ms': message.response_time_ms
                })
            
            return history
            
        except ChatSession.DoesNotExist:
            return []
    
    def create_session(self, user) -> ChatSession:
        """Cria nova sessão de chat e limpa sessões antigas automaticamente"""
        # Criar nova sessão
        new_session = ChatSession.objects.create(user=user)
        
        # Manter apenas as 10 sessões mais recentes (incluindo a nova)
        MAX_SESSIONS = 10
        
        # Buscar todas as sessões ativas do usuário ordenadas por data de atualização
        user_sessions = ChatSession.objects.filter(
            user=user,
            is_active=True
        ).order_by('-updated_at')
        
        # Se temos mais de MAX_SESSIONS, marcar as mais antigas como inativas
        if user_sessions.count() > MAX_SESSIONS:
            # Pegar as sessões que excedem o limite (as mais antigas)
            sessions_to_deactivate = user_sessions[MAX_SESSIONS:]
            
            # Marcar como inativas (exclusão suave)
            for session in sessions_to_deactivate:
                session.is_active = False
                session.save()
        
        return new_session
    
    def _cleanup_old_sessions(self, user):
        """Limpa sessões antigas mantendo apenas as 10 mais recentes"""
        MAX_SESSIONS = 10
        
        # Buscar todas as sessões ativas do usuário ordenadas por data de atualização
        user_sessions = ChatSession.objects.filter(
            user=user,
            is_active=True
        ).order_by('-updated_at')
        
        # Se temos mais de MAX_SESSIONS, marcar as mais antigas como inativas
        if user_sessions.count() > MAX_SESSIONS:
            # Pegar as sessões que excedem o limite (as mais antigas)
            sessions_to_deactivate = user_sessions[MAX_SESSIONS:]
            
            # Limpar arquivos de áudio das sessões que serão desativadas
            for session in sessions_to_deactivate:
                self._cleanup_session_audio_files(session)
                session.is_active = False
                session.save()
    
    def _cleanup_session_audio_files(self, session):
        """Remove arquivos de áudio de uma sessão"""
        # Buscar todas as mensagens com arquivos de áudio na sessão
        audio_messages = session.messages.filter(
            audio_file__isnull=False,
            content_type='audio'
        )
        
        for message in audio_messages:
            if message.audio_file:
                try:
                    # Verificar se o arquivo existe antes de tentar deletar
                    if default_storage.exists(message.audio_file.name):
                        default_storage.delete(message.audio_file.name)
                        print(f"🗑️  Arquivo de áudio removido: {message.audio_file.name}")
                except Exception as e:
                    print(f"⚠️  Erro ao remover arquivo de áudio {message.audio_file.name}: {e}")
                
                # Limpar referência do arquivo na mensagem
                message.audio_file = None
                message.save()
    
    def get_user_sessions(self, user, limit: int = 10) -> List[Dict[str, Any]]:
        """Lista sessões do usuário (limitado às 10 mais recentes)"""
        sessions = ChatSession.objects.filter(
            user=user,
            is_active=True
        ).order_by('-updated_at')[:limit]
        
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