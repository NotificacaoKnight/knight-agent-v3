"""
Streaming Service - Server-Sent Events para respostas em tempo real
Implementação FastAPI com suporte a streaming de LLM
"""
import json
import asyncio
import logging
from typing import AsyncIterator, Dict, Any, Optional, List
from datetime import datetime

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.rag_service import rag_service
from app.services.rag.llm_providers import llm_manager, ProviderType
from app.services.rag.prompt_templates import prompt_templates
from app.services.rag.context_optimizer import context_optimizer
from app.services.rag.hybrid_search_service import get_hybrid_search_service
from app.services.knowledge_resources_service import get_knowledge_service
from app.models.chat import ChatMessage, ChatSession
from app.core.config import settings

logger = logging.getLogger(__name__)


class StreamingRAGService:
    """
    Serviço de streaming para respostas RAG em tempo real

    Implementa Server-Sent Events (SSE) para enviar tokens conforme são gerados
    """

    def __init__(self):
        self.search_service = get_hybrid_search_service()
        self.knowledge_service = get_knowledge_service()
        self.llm_manager = llm_manager

    async def stream_response(
        self,
        query: str,
        session_id: Optional[int] = None,
        context_size: int = 5,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        language: str = "pt",
        llm_provider: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        stream_delay: float = 0.03,  # Delay entre tokens em segundos (30ms padrão)
        user_id: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        Stream RAG response usando Server-Sent Events

        Yields eventos SSE no formato:
        data: {"type": "event_type", "content": "..."}

        Tipos de eventos:
        - start: Início do processamento
        - status: Atualização de status
        - search_complete: Busca concluída
        - token: Token individual da resposta
        - sources: Fontes encontradas
        - links: Links úteis
        - documents: Documentos para download
        - done: Streaming completo
        - error: Erro durante processamento
        """

        start_time = datetime.now()

        try:
            # ===== 0. CRIAR/OBTER SESSÃO =====
            from app.models.chat import ChatSession, ChatMessage
            from sqlalchemy import select

            # Variável para controlar se é uma nova sessão
            is_new_session = False

            if not session_id and db and user_id:
                # Criar nova sessão com título temporário
                from app.core.timezone_utils import utc_now
                new_session = ChatSession(
                    user_id=user_id,
                    title=f"Chat {utc_now().strftime('%Y-%m-%d %H:%M')}",
                    is_active=True,
                    language=language
                )
                db.add(new_session)
                await db.flush()
                session_id = new_session.id
                is_new_session = True
                logger.info(f"Nova sessão criada: {session_id} para user {user_id}")

                # Enviar evento de nova sessão imediatamente
                yield self._format_sse({
                    "type": "session_created",
                    "session_id": session_id,
                    "title": new_session.title
                })

            # ===== 1. EVENTO INICIAL =====
            yield self._format_sse({
                "type": "start",
                "message": "Iniciando busca...",
                "timestamp": start_time.isoformat()
            })

            # ===== 2. BUSCA =====
            yield self._format_sse({
                "type": "status",
                "message": "Buscando informações relevantes..."
            })

            # Buscar chunks relevantes
            search_result = await self.search_service.search(
                query=query,
                k=context_size * 2,
                search_type="hybrid",
                db=db
            )

            chunks = search_result if isinstance(search_result, list) else []

            yield self._format_sse({
                "type": "search_complete",
                "chunks_found": len(chunks),
                "message": f"{len(chunks)} documentos encontrados"
            })

            # ===== 3. PREPARAR CONTEXTO =====
            yield self._format_sse({
                "type": "status",
                "message": "Preparando contexto..."
            })

            # Otimizar contexto com MMR
            query_embedding = None  # TODO: gerar embedding se disponível
            optimized_context = context_optimizer.prepare_optimized_context(
                chunks=chunks,
                query_embedding=query_embedding,
                k=context_size,
                language=language
            )

            # ===== 4. BUSCAR KNOWLEDGE RESOURCES =====
            knowledge_resources = await self.knowledge_service.find_relevant_resources(
                query=query,
                context=optimized_context,
                db=db
            )

            # Enviar links e documentos se encontrados
            if knowledge_resources['useful_links']:
                yield self._format_sse({
                    "type": "links",
                    "data": knowledge_resources['useful_links']
                })

            if knowledge_resources['downloadable_documents']:
                yield self._format_sse({
                    "type": "documents",
                    "data": knowledge_resources['downloadable_documents']
                })

            # ===== 5. CONSTRUIR PROMPT =====
            yield self._format_sse({
                "type": "status",
                "message": "Gerando resposta..."
            })

            # Formatar recursos para o prompt
            resources_formatted = self.knowledge_service.format_resources_for_llm(
                resources=knowledge_resources,
                language=language
            )

            # Criar prompt naturalizado
            full_prompt = prompt_templates.create_main_prompt(
                query=query,
                context=optimized_context,
                conversation_history="",  # TODO: implementar conversation_memory
                knowledge_resources=resources_formatted,
                language=language
            )

            # ===== 6. STREAM DE GERAÇÃO =====
            # Temperatura adaptativa
            adaptive_temp = self._adaptive_temperature(query, temperature)

            # Obter provider
            if llm_provider:
                provider = self.llm_manager.get_provider(ProviderType(llm_provider))
                provider_name = llm_provider
            else:
                # Usar provider padrão
                provider = self.llm_manager.get_provider()
                provider_name = str(settings.LLM_PROVIDER)

            # Stream tokens
            full_response = []
            token_count = 0

            # Verificar se provider suporta streaming
            if hasattr(provider, 'stream_generate'):
                # Streaming nativo
                async for token in provider.stream_generate(
                    prompt=full_prompt,
                    context="",
                    max_tokens=max_tokens,
                    temperature=adaptive_temp
                ):
                    full_response.append(token)
                    token_count += 1

                    # Enviar token
                    yield self._format_sse({
                        "type": "token",
                        "content": token,
                        "index": token_count
                    })

                    # Delay configurável entre tokens para controlar velocidade
                    await asyncio.sleep(stream_delay)
            else:
                # Fallback: geração completa e simulação de streaming
                logger.info(f"Provider {provider_name} não suporta streaming, simulando...")

                response = await provider.generate(
                    prompt=full_prompt,
                    max_tokens=max_tokens,
                    temperature=adaptive_temp
                )

                # Simular streaming dividindo em palavras
                words = response.split(' ')
                for i, word in enumerate(words):
                    # Adicionar espaço antes da palavra (exceto primeira)
                    if i > 0:
                        yield self._format_sse({
                            "type": "token",
                            "content": " " + word,
                            "index": i
                        })
                    else:
                        yield self._format_sse({
                            "type": "token",
                            "content": word,
                            "index": i
                        })

                    # Delay configurável para simular streaming
                    await asyncio.sleep(stream_delay * 2)  # Um pouco mais lento na simulação

                full_response = [response]

            # ===== 7. ENVIAR FONTES =====
            if chunks:
                # Enviar top 3 fontes usadas
                sources_data = []
                for chunk in chunks[:3]:
                    sources_data.append({
                        "document_title": chunk.get('document_title', 'Documento'),
                        "content": chunk.get('content', '')[:200] + "...",
                        "score": chunk.get('score', 0)
                    })

                yield self._format_sse({
                    "type": "sources",
                    "data": sources_data
                })

            # ===== 8. CALCULAR TEMPO DE RESPOSTA =====
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # ===== 9. SALVAR MENSAGENS NO BANCO =====
            if session_id and db:
                # Criar mensagem do usuário
                user_message = ChatMessage(
                    session_id=session_id,
                    message_type="user",
                    content=query,
                    content_type="text"
                )

                # Criar mensagem do assistente
                full_response_text = ''.join(full_response)
                assistant_message = ChatMessage(
                    session_id=session_id,
                    message_type="assistant",
                    content=full_response_text,
                    content_type="text",
                    llm_provider=provider_name,
                    response_time_ms=response_time_ms,
                    useful_links=knowledge_resources.get('useful_links', []),
                    downloadable_documents=knowledge_resources.get('downloadable_documents', [])
                )

                # Batch insert - mais eficiente que 2x db.add()
                db.add_all([user_message, assistant_message])

                # Atualizar contador de mensagens e timestamp da sessão
                from sqlalchemy import select, update
                from app.core.timezone_utils import utc_now
                session_result = await db.execute(
                    select(ChatSession).where(ChatSession.id == session_id)
                )
                current_session = session_result.scalar_one_or_none()
                if current_session:
                    current_session.message_count = (current_session.message_count or 0) + 2
                    current_session.last_message_at = utc_now()
                    current_session.updated_at = utc_now()

                    # Se é nova sessão, atualizar título com primeiras palavras da query
                    if is_new_session and current_session.title.startswith("Chat ") and " " in current_session.title:
                        first_words = query[:30].strip()
                        if len(query) > 30:
                            first_words += "..."
                        current_date = utc_now().strftime('%d/%m/%Y')
                        current_session.title = f"{first_words} [{current_date}]"
                        logger.info(f"Título da sessão atualizado: {current_session.title}")

                await db.commit()
                logger.info(f"Mensagens salvas na sessão {session_id} (total: {current_session.message_count if current_session else 'N/A'})")

            # ===== 10. CONCLUSÃO =====

            yield self._format_sse({
                "type": "done",
                "message": "Resposta completa",
                "response_time_ms": response_time_ms,
                "provider": provider_name,
                "total_tokens": len(''.join(full_response).split()),
                "session_id": session_id
            })

        except Exception as e:
            logger.error(f"Erro no streaming: {e}", exc_info=True)
            yield self._format_sse({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            })

    def _format_sse(self, data: Dict[str, Any]) -> str:
        """
        Formata dados como Server-Sent Event

        Formato SSE:
        data: {json}

        (linha em branco após cada evento)
        """
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def _adaptive_temperature(self, query: str, base_temp: float) -> float:
        """
        Ajusta temperatura baseado no tipo de query

        Queries factuais: temperatura mais baixa (0.3-0.5)
        Queries criativas: temperatura mais alta (0.7-0.9)
        """
        query_lower = query.lower()

        # Indicadores de query factual
        factual_keywords = [
            "qual", "quando", "onde", "quem", "quanto", "quantos",
            "data", "horário", "telefone", "email", "número", "código"
        ]

        # Indicadores de query criativa
        creative_keywords = [
            "como", "por que", "explique", "detalhe",
            "sugira", "recomende", "ideias", "sugestões"
        ]

        is_factual = any(kw in query_lower for kw in factual_keywords)
        is_creative = any(kw in query_lower for kw in creative_keywords)

        if is_factual:
            return min(base_temp * 0.6, 0.5)
        elif is_creative:
            return min(base_temp * 1.2, 0.9)
        else:
            return base_temp

    async def create_streaming_response(
        self,
        query: str,
        session_id: Optional[int] = None,
        context_size: int = 5,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        language: str = "pt",
        llm_provider: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        stream_delay: float = 0.03,
        user_id: Optional[int] = None
    ) -> StreamingResponse:
        """
        Cria StreamingResponse para FastAPI

        Returns:
            StreamingResponse configurada para SSE
        """
        return StreamingResponse(
            self.stream_response(
                query=query,
                session_id=session_id,
                context_size=context_size,
                max_tokens=max_tokens,
                temperature=temperature,
                language=language,
                llm_provider=llm_provider,
                db=db,
                stream_delay=stream_delay,
                user_id=user_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Desabilita buffering no nginx
            }
        )


# Singleton instance
streaming_service = StreamingRAGService()