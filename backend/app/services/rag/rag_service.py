"""
Main RAG Service for FastAPI - Versão Otimizada 2025
Pipeline unificado com prompts naturalizados e contexto otimizado
"""
import time
import logging
import pytz
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.hybrid_search_service import get_hybrid_search_service
from app.services.rag.llm_providers import llm_manager, ProviderType
from app.services.rag.prompt_templates import prompt_templates
from app.services.rag.context_optimizer import context_optimizer
from app.services.knowledge_resources_service import get_knowledge_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """
    Main RAG service para geração de respostas

    Versão 2025:
    - Pipeline unificado (sem modos fast/deep)
    - Prompts naturalizados em português
    - Contexto otimizado com MMR
    - Integração natural de knowledge resources
    """

    def __init__(self):
        self.search_service = get_hybrid_search_service()
        self.llm_manager = llm_manager
        self.knowledge_service = get_knowledge_service()

    async def search(
        self,
        query: str,
        k: int = 5,
        search_type: str = "hybrid",
        threshold: Optional[float] = None,
        filter_document_ids: Optional[List[int]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Realiza busca semântica e keyword

        Args:
            query: Query de busca
            k: Número de resultados
            search_type: Tipo de busca (hybrid, semantic, keyword)
            threshold: Threshold de similaridade
            filter_document_ids: Filtro de documentos
            db: Sessão do banco

        Returns:
            Resultados da busca
        """
        start_time = time.time()

        try:
            # Construir filtros
            filter_conditions = {}
            if filter_document_ids:
                filter_conditions['document_ids'] = filter_document_ids

            # Executar busca
            results = await self.search_service.search(
                query=query,
                k=k,
                search_type=search_type,
                threshold=threshold,
                filter_conditions=filter_conditions,
                db=db
            )

            search_time_ms = int((time.time() - start_time) * 1000)

            return {
                'success': True,
                'query': query,
                'results': results,
                'total_results': len(results),
                'search_type': search_type,
                'search_time_ms': search_time_ms
            }

        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                'success': False,
                'query': query,
                'results': [],
                'total_results': 0,
                'error': str(e),
                'search_time_ms': int((time.time() - start_time) * 1000)
            }

    async def generate_answer(
        self,
        query: str,
        session_id: Optional[str] = None,
        context_size: int = 5,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        include_sources: bool = True,
        language: str = "pt",
        llm_provider: Optional[str] = None,
        filter_document_ids: Optional[List[int]] = None,
        db: Optional[AsyncSession] = None,
        **kwargs  # Captura parâmetros antigos (mode, etc) para compatibilidade
    ) -> Dict[str, Any]:
        """
        Gera resposta usando RAG com pipeline unificado

        NOVA VERSÃO 2025:
        - Sem distinção de modo (fast/deep) - pipeline único otimizado
        - Prompts naturalizados em português brasileiro
        - Contexto formatado naturalmente (sem [1. Document])
        - Knowledge resources integrados organicamente

        Args:
            query: Pergunta do usuário
            session_id: ID da sessão (para memória conversacional - futuro)
            context_size: Número de chunks de contexto
            max_tokens: Máximo de tokens na resposta
            temperature: Temperatura de geração
            include_sources: Incluir fontes na resposta
            language: Idioma da resposta (pt ou en)
            llm_provider: Provider específico (opcional)
            filter_document_ids: Filtro de documentos
            db: Sessão do banco

        Returns:
            Resposta gerada com fontes e metadados
        """
        start_time = time.time()

        try:
            # ===== 1. BUSCA OTIMIZADA =====
            logger.info(f"Iniciando geração de resposta para: '{query[:50]}...'")

            # Buscar chunks relevantes (busca única otimizada)
            search_result = await self.search(
                query=query,
                k=context_size * 2,  # Buscar mais para ter opções
                search_type="hybrid",
                filter_document_ids=filter_document_ids,
                db=db
            )

            chunks = search_result.get('results', [])

            # ===== 2. OTIMIZAÇÃO DE CONTEXTO =====
            # Usar MMR para selecionar chunks com diversidade
            query_embedding = None
            if chunks and 'embedding' in chunks[0]:
                # Se tiver embeddings, usar MMR completo
                query_embedding = await self._get_query_embedding(query)

            # Preparar contexto otimizado (MMR + compressão + formatação natural)
            optimized_context = context_optimizer.prepare_optimized_context(
                chunks=chunks,
                query_embedding=query_embedding,
                k=context_size,
                language=language
            )

            # ===== 3. BUSCAR KNOWLEDGE RESOURCES =====
            # Links úteis e documentos relevantes
            knowledge_resources = await self.knowledge_service.find_relevant_resources(
                query=query,
                context=optimized_context,
                db=db
            )

            # Formatar recursos naturalmente
            resources_formatted = self.knowledge_service.format_resources_for_llm(
                resources=knowledge_resources,
                language=language
            )

            # ===== 4. CONSTRUIR PROMPT NATURALIZADO =====
            # Usar prompt templates naturalizados
            conversation_history = ""  # TODO: implementar com conversation_memory

            # Obter horário atual para saudações contextuais
            # Configurar timezone (ajuste conforme necessário - usando America/Sao_Paulo como padrão)
            tz = pytz.timezone('America/Sao_Paulo')
            now = datetime.now(tz)
            hour = now.hour

            # Determinar período do dia
            if 5 <= hour < 12:
                period = "manhã"
            elif 12 <= hour < 18:
                period = "tarde"
            else:
                period = "noite"

            current_time = f"{now.strftime('%H:%M')} - {period}"

            full_prompt = prompt_templates.create_main_prompt(
                query=query,
                context=optimized_context,
                conversation_history=conversation_history,
                knowledge_resources=resources_formatted,
                language=language,
                current_time=current_time
            )

            # ===== 5. GERAR RESPOSTA COM LLM =====
            logger.info(f"Gerando resposta com prompt naturalizado ({len(full_prompt)} chars)")

            # Ajustar temperatura dinamicamente
            adaptive_temp = self._adaptive_temperature(query, temperature)

            if llm_provider:
                # Provider específico
                provider = self.llm_manager.get_provider(ProviderType(llm_provider))
                answer = await provider.generate(
                    prompt=full_prompt,
                    max_tokens=max_tokens,
                    temperature=adaptive_temp
                )
                provider_used = llm_provider
            else:
                # Fallback automático
                answer, provider_used = await self.llm_manager.generate_with_fallback(
                    prompt=full_prompt,
                    max_tokens=max_tokens,
                    temperature=adaptive_temp
                )

            # ===== 6. FORMATAR RESPOSTA =====
            response_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Resposta gerada em {response_time_ms}ms "
                f"usando {provider_used} com {len(chunks)} chunks"
            )

            response = {
                'success': True,
                'query': query,
                'answer': answer,
                'llm_provider': str(provider_used),
                'response_time_ms': response_time_ms,
                'chunks_used': len(chunks),
                'context_length': len(optimized_context)
            }

            # Incluir fontes se solicitado
            if include_sources and chunks:
                # Retornar top chunks usados
                selected_chunks = chunks[:context_size]
                response['sources'] = selected_chunks

            # Incluir knowledge resources na resposta
            if knowledge_resources['useful_links'] or knowledge_resources['downloadable_documents']:
                response['useful_links'] = knowledge_resources['useful_links']
                response['downloadable_documents'] = knowledge_resources['downloadable_documents']

            return response

        except Exception as e:
            logger.error(f"Generation error: {e}", exc_info=True)
            return {
                'success': False,
                'query': query,
                'answer': self._get_error_message(language),
                'error': str(e),
                'response_time_ms': int((time.time() - start_time) * 1000)
            }

    def _adaptive_temperature(self, query: str, base_temp: float) -> float:
        """
        Ajusta temperatura baseado no tipo de query

        Queries factuais: temperatura mais baixa (0.3-0.5)
        Queries criativas/abertas: temperatura mais alta (0.7-0.9)

        Args:
            query: Query do usuário
            base_temp: Temperatura base

        Returns:
            Temperatura ajustada
        """
        query_lower = query.lower()

        # Indicadores de query factual (precisa de precisão)
        factual_keywords = [
            "qual", "quando", "onde", "quem", "quanto", "quantos",
            "data", "horário", "telefone", "email", "número", "código",
            "endereço", "nome"
        ]

        # Indicadores de query criativa (pode ter variação)
        creative_keywords = [
            "como", "por que", "porque", "explique", "detalhe",
            "sugira", "recomende", "ideias", "sugestões", "opções"
        ]

        is_factual = any(kw in query_lower for kw in factual_keywords)
        is_creative = any(kw in query_lower for kw in creative_keywords)

        if is_factual:
            # Query factual: baixar temperatura para precisão
            return min(base_temp * 0.6, 0.5)
        elif is_creative:
            # Query criativa: manter ou aumentar temperatura
            return min(base_temp * 1.2, 0.9)
        else:
            # Neutro: usar temperatura base
            return base_temp

    async def _get_query_embedding(self, query: str) -> Optional[np.ndarray]:
        """
        Gera embedding da query

        Args:
            query: Query text

        Returns:
            Embedding ou None se falhar
        """
        try:
            # Lazy import para evitar dependência circular
            from app.services.rag.embedding_service import embedding_service
            embedding = embedding_service.encode_text(query)
            return np.array(embedding)
        except Exception as e:
            logger.warning(f"Erro ao gerar embedding da query: {e}")
            return None

    def _get_error_message(self, language: str) -> str:
        """
        Mensagem de erro amigável

        Args:
            language: Idioma

        Returns:
            Mensagem de erro
        """
        if language == "pt":
            return (
                "Desculpe, tive um problema ao processar sua pergunta. "
                "Pode tentar novamente ou reformular de outra forma?"
            )
        else:
            return (
                "Sorry, I had a problem processing your question. "
                "Can you try again or rephrase it differently?"
            )

    async def get_stats(self, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Estatísticas do sistema RAG"""
        stats = {
            'search': await self.search_service.get_stats(db),
            'llm_providers': self.llm_manager.get_available_providers()
        }
        return stats

    async def build_indices(self, db: Optional[AsyncSession] = None):
        """Rebuild search indices"""
        await self.search_service.build_indices(db)

    async def test_llm(
        self,
        prompt: str,
        provider: Optional[str] = None,
        max_tokens: int = 100,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Testa LLM provider"""
        start_time = time.time()

        try:
            if provider:
                llm_provider = self.llm_manager.get_provider(ProviderType(provider))
                response = await llm_provider.generate(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                provider_used = provider
            else:
                response, provider_used = await self.llm_manager.generate_with_fallback(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

            return {
                'success': True,
                'provider': str(provider_used),
                'response': response,
                'response_time_ms': int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            return {
                'success': False,
                'provider': provider or 'unknown',
                'error': str(e),
                'response_time_ms': int((time.time() - start_time) * 1000)
            }


# Global RAG service instance
rag_service = RAGService()
