import time
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import F
from documents.models import Document
from rag.agentic_rag_service import AgenticRAGServiceSync
from rag.llm_providers import get_llm_manager
from rag.consolidated_multi_agent import consolidated_multi_agent_service
from .models import ChatSession, ChatMessage, DocumentRequest
from .audio_transcription import GeminiAudioTranscriptionService
from .access_count_config import AccessCountConfig
from .agent_detector import agent_detector

class KnightChatService:
    """Serviço principal do agente Knight"""
    
    def __init__(self):
        # Usar apenas sistema agentic (que já tem fallback interno)
        self.agentic_service = AgenticRAGServiceSync()
        self.llm_manager = get_llm_manager()
        self.transcription_service = GeminiAudioTranscriptionService()
        self.max_context_chunks = 5
        self.max_context_length = 4000

    def _increment_document_access_count(self, search_results):
        """
        Incrementa o contador de acesso apenas para documentos mais relevantes
        baseado em threshold mínimo e estratégia configurável
        """
        try:
            config = AccessCountConfig.get_config_summary()
            print(f"🎯 CHAT: Incrementando access_count com estratégia '{config['strategy']}' - {len(search_results)} resultados iniciais")
            print(f"⚙️ CHAT CONFIG: {config['description']}")
            
            if not search_results:
                print(f"⚠️ CHAT: Nenhum resultado de busca fornecido")
                return
            
            # Agrupar resultados por document_id mantendo o melhor score
            document_scores = {}
            for result in search_results:
                if not isinstance(result, dict) or 'document_id' not in result:
                    continue
                
                doc_id = result['document_id']
                score = result.get('combined_score', result.get('score', 0.0))
                
                # Manter apenas o melhor score por documento
                if doc_id not in document_scores or score > document_scores[doc_id]['score']:
                    document_scores[doc_id] = {
                        'score': score,
                        'chunk_id': result.get('chunk_id'),
                        'content_preview': result.get('content', '')[:100] + '...' if result.get('content') else ''
                    }
            
            print(f"📋 CHAT: {len(document_scores)} documentos únicos encontrados")
            
            # Aplicar threshold mínimo
            min_score = config['min_score']
            relevant_docs = {
                doc_id: data for doc_id, data in document_scores.items() 
                if data['score'] >= min_score
            }
            
            print(f"✅ CHAT: {len(relevant_docs)} documentos passaram no threshold ≥ {min_score}")
            
            if not relevant_docs:
                print(f"⚠️ CHAT: Nenhum documento atingiu score mínimo de {min_score}")
                return
            
            # Aplicar estratégia de seleção
            strategy = config['strategy']
            selected_docs = {}
            
            if strategy == 'single_best':
                # Apenas o documento com maior score
                best_doc_id = max(relevant_docs.keys(), key=lambda k: relevant_docs[k]['score'])
                selected_docs[best_doc_id] = relevant_docs[best_doc_id]
                
            elif strategy == 'top_n':
                # Top N documentos mais relevantes
                max_docs = config['max_docs']
                sorted_docs = sorted(relevant_docs.items(), key=lambda x: x[1]['score'], reverse=True)
                selected_docs = dict(sorted_docs[:max_docs])
                
            else:  # threshold_only
                # Todos os documentos que passaram no threshold
                selected_docs = relevant_docs
            
            print(f"🎯 CHAT: {len(selected_docs)} documentos selecionados para incremento:")
            for doc_id, data in selected_docs.items():
                print(f"   📄 Doc {doc_id}: score={data['score']:.3f}")
            
            if selected_docs:
                # Incrementar contador atomicamente
                document_ids = set(selected_docs.keys())
                updated_count = Document.objects.filter(id__in=document_ids).update(
                    access_count=F('access_count') + 1
                )
                print(f"🚀 CHAT SUCCESS: Incrementado access_count para {updated_count} documentos relevantes")
                
                # Debug: verificar resultado
                updated_docs = Document.objects.filter(id__in=document_ids)
                for doc in updated_docs:
                    score = selected_docs[doc.id]['score']
                    print(f"📊 CHAT: {doc.title} (score={score:.3f}) agora tem {doc.access_count} acessos")
                    
        except Exception as e:
            print(f"💥 CHAT ERRO ao incrementar access_count: {e}")
            import traceback
            traceback.print_exc()
    
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
            
            
            
            # 🎯 SISTEMA MULTI-AGENTE
            target_agent, transition_reason = agent_detector.detect_appropriate_agent(user_message)
            
            if target_agent != "knight" and transition_reason:
                # Knight faz a introdução
                handoff_message = agent_detector.generate_handoff_message(target_agent, transition_reason)
                
                knight_msg = ChatMessage.objects.create(
                    session=session,
                    message_type='assistant',
                    content=handoff_message,
                    agent_type='knight',
                    is_handoff=True,
                    llm_provider='handoff',
                    response_time_ms=50  # Resposta instantânea
                )
                
                # Processar com agente específico
                agent_result = self._process_with_agent(user_message, target_agent, session.user)
                
                # Salvar resposta do agente específico
                agent_msg = ChatMessage.objects.create(
                    session=session,
                    message_type='assistant',
                    content=agent_result.get('response', 'Erro no processamento'),
                    agent_type=target_agent,
                    llm_provider=agent_result.get('metadata', {}).get('provider_used', 'unknown'),
                    response_time_ms=agent_result.get('metadata', {}).get('total_duration_ms', 0),
                    context_used=agent_result.get('search_results', [])[:5]  # Top 5 contextos
                )
                
                # Incrementar contador para documentos usados
                if agent_result.get('search_results'):
                    self._increment_document_access_count(agent_result['search_results'])
                
                # Atualizar metadados da sessão (3 mensagens: user + handoff + agent)
                self._update_session_metadata(session, user_message, message_count=3)
                
                # Resposta multi-agente
                return {
                    'success': True,
                    'response': agent_result.get('response', 'Erro no processamento'),
                    'message_id': agent_msg.id,
                    'handoff_message_id': knight_msg.id,
                    'user_message_data': {
                        'id': str(user_msg.id),
                        'type': 'user',
                        'content': user_message,
                        'timestamp': user_msg.created_at.isoformat()
                    },
                    'context_used': len(agent_result.get('search_results', [])),
                    'response_time_ms': int((time.time() - start_time) * 1000),
                    'useful_links': agent_result.get('useful_links', []),
                    'downloadable_documents': agent_result.get('downloadable_documents', []),
                    'agent_type': target_agent,
                    'is_multi_agent': True,
                    'handoff_message': handoff_message
                }
            
            # 🛡️ PROCESSAMENTO TRADICIONAL COM KNIGHT
            knight_result = self._process_with_agent(user_message, 'knight', session.user)
            final_result = knight_result
            
            # Incrementar contador de acesso dos documentos consultados
            search_results = final_result.get('search_results', [])
            self._increment_document_access_count(search_results)
            
            # Usar resposta do sistema final (multi-agent ou fallback)
            llm_response = {
                'success': True,
                'response': final_result.get('response', ''),
                'provider': final_result.get('metadata', {}).get('provider_used', 'unknown'),
                'model': final_result.get('metadata', {}).get('model_used', ''),
                'agent_used': final_result.get('agent_used', 'knight')
            }
            
            # Extrair metadados de contexto
            context_metadata = []
            search_results = final_result.get('search_results', [])
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
                agent_type=llm_response.get('agent_used', 'knight'),
                context_used=context_metadata,
                search_query_id=search_query.id if search_query else None,
                llm_provider=llm_response['provider'],
                llm_model=llm_response.get('model', ''),
                response_time_ms=response_time
            )
            
            # Atualizar metadados da sessão
            self._update_session_metadata(session, user_message, message_count=2)
            
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
                'fallback_used': llm_response.get('fallback_used', False),
                'useful_links': final_result.get('useful_links', []),
                'downloadable_documents': final_result.get('downloadable_documents', []),
                'agent_type': llm_response.get('agent_used', 'knight')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response': "Desculpe, ocorreu um erro interno. Tente novamente ou entre em contato com o suporte técnico.",
                'response_time_ms': int((time.time() - start_time) * 1000)
            }
    
    def _process_with_agent(self, query: str, agent_type: str, user: Any) -> Dict[str, Any]:
        """Processa query com agente específico"""
        import logging
        import traceback
        
        logger = logging.getLogger(__name__)
        
        try:
            if agent_type == 'knight':
                # Usar sistema agentic para Knight
                logger.info(f"Processing with Knight agent for query: {query[:50]}...")
                return self.agentic_service.search(
                    query=query,
                    k=self.max_context_chunks,
                    user=user
                )
            else:
                # Usar consolidated multi-agent para Wizard e Bard
                logger.info(f"Processing with {agent_type} agent for query: {query[:50]}...")
                
                result = consolidated_multi_agent_service.process_query(
                    query=query,
                    user=user,
                    user_profile={
                        'name': getattr(user, 'username', 'Usuário') if user else 'Usuário',
                        'preferred_agent': agent_type
                    },
                    force_mode=agent_type  # Forçar agente específico
                )
                
                # Garantir estrutura de resposta completa
                if not result.get('useful_links'):
                    result['useful_links'] = []
                if not result.get('downloadable_documents'):
                    result['downloadable_documents'] = []
                    
                logger.info(f"Successfully processed with {agent_type} agent")
                return result
                
        except Exception as e:
            logger.error(f"Error processing with {agent_type} agent: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Fallback mockado para testes
            if agent_type == 'wizard':
                return {
                    'response': f"🧙 Olá! Sou o Wizard, especialista em capacitação. Vi que você está interessado em cursos! Posso sugerir:\n\n• Trilha de Desenvolvimento de Liderança\n• Curso de Comunicação Assertiva\n• Workshop de Gestão do Tempo\n• Programa de Mentoria Profissional\n\nQual área mais te interessa desenvolver?",
                    'search_results': [],
                    'metadata': {'provider_used': 'fallback_mock', 'total_duration_ms': 100},
                    'useful_links': [],
                    'downloadable_documents': []
                }
            elif agent_type == 'bard':
                return {
                    'response': f"🎭 Olá! Sou o Bard, especialista em análise de dados. Posso ajudar com:\n\n• Análise de métricas de performance\n• Criação de dashboards personalizados\n• Relatórios de indicadores (KPIs)\n• Insights baseados em dados\n\nQue tipo de análise você precisa?",
                    'search_results': [],
                    'metadata': {'provider_used': 'fallback_mock', 'total_duration_ms': 100},
                    'useful_links': [],
                    'downloadable_documents': []
                }
            else:
                return {
                    'response': f"Desculpe, ocorreu um erro ao processar com o agente {agent_type}. Erro: {str(e)}",
                    'search_results': [],
                    'metadata': {'provider_used': 'error', 'total_duration_ms': 0},
                    'useful_links': [],
                    'downloadable_documents': []
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
        
        # Atualizar metadados da sessão
        self._update_session_metadata(session, user_message, message_count=2)
        
        return {
            'success': False,
            'response': error_response,
            'message_id': assistant_msg.id,
            'error': error
        }
    
    def _update_session_metadata(self, session: ChatSession, user_message: str, message_count: int = 2):
        """Atualiza metadados da sessão (título, contagem, timestamp)"""
        session.message_count += message_count
        session.last_message_at = datetime.now()
        if not session.title:
            session.title = self._generate_session_title(user_message)
        session.save()
        
        # Limpar sessões antigas quando uma sessão existente é atualizada
        self._cleanup_old_sessions(session.user)
    
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
                    'response_time_ms': message.response_time_ms,
                    'agent_type': message.agent_type,
                    'agent_emoji': self._get_agent_emoji(message.agent_type)
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
    
    def _get_agent_emoji(self, agent_type: str) -> str:
        """Retorna emoji correspondente ao tipo de agente"""
        emojis = {
            "knight": "⚔️",
            "wizard": "🪄", 
            "bard": "🎭"
        }
        return emojis.get(agent_type, "🤖")
    
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