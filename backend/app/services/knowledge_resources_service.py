"""
Serviço para integrar links úteis e documentos baixáveis ao sistema RAG
Adaptado do Django para FastAPI com SQLAlchemy
"""
import os
import re
import unicodedata
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select, or_, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np

logger = logging.getLogger(__name__)


class KnowledgeResourcesService:
    """Serviço para buscar e integrar recursos de conhecimento ao RAG"""

    def __init__(self):
        self.embedding_model = None
        self.similarity_threshold = 0.8
        self.max_links_per_response = 3
        self.max_documents_per_response = 2
        self._load_embedding_model()

    def _load_embedding_model(self):
        """Carrega modelo de embedding"""
        try:
            # Try to import sentence_transformers if available
            try:
                from sentence_transformers import SentenceTransformer
                from app.core.config import settings

                model_name = settings.EMBEDDING_MODEL
                self.embedding_model = SentenceTransformer(model_name, device='cpu')
                logger.info(f"Modelo de embedding carregado: {model_name}")
            except ImportError:
                logger.warning("sentence_transformers não disponível - busca semântica desabilitada")
                self.embedding_model = None
        except Exception as e:
            logger.error(f"Erro ao carregar modelo de embedding: {e}")
            self.embedding_model = None

    async def find_relevant_resources(
        self,
        query: str,
        context: Optional[str] = None,
        user_id: Optional[int] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Encontra links úteis e documentos relevantes para a query

        Args:
            query: Pergunta do usuário
            context: Contexto adicional da conversa
            user_id: ID do usuário fazendo a consulta
            db: Sessão do banco de dados

        Returns:
            Dict com 'useful_links' e 'downloadable_documents'
        """
        try:
            if not db:
                logger.warning("Sessão do banco não fornecida")
                return {'useful_links': [], 'downloadable_documents': []}

            # Importar modelos
            from app.models.knowledge import UsefulLink, DownloadableDocument

            # Combinar query com contexto
            search_text = query
            if context:
                search_text = f"{query} {context}"

            logger.info(f"Buscando recursos para query: '{query[:50]}...'")

            # Buscar links úteis (sempre sugestivo)
            relevant_links = await self._find_relevant_links(search_text, db)

            # Documentos: apenas quando solicitados
            relevant_documents = []
            if self._is_document_request(query):
                relevant_documents = await self._find_relevant_documents(search_text, db)
                logger.info(f"Solicitação de documento detectada")

            logger.info(f"Encontrados: {len(relevant_links)} links, {len(relevant_documents)} documentos")

            return {
                'useful_links': relevant_links,
                'downloadable_documents': relevant_documents
            }

        except Exception as e:
            logger.error(f"Erro ao buscar recursos: {e}")
            return {'useful_links': [], 'downloadable_documents': []}

    async def _find_relevant_links(
        self,
        search_text: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Busca links úteis relevantes"""
        try:
            from app.models.knowledge import UsefulLink

            # Buscar links ativos
            result = await db.execute(
                select(UsefulLink).where(UsefulLink.is_active == True)
            )
            active_links = result.scalars().all()

            if not active_links:
                return []

            relevant_links = []

            # 1. Busca por palavras-chave
            keyword_matches = await self._find_keyword_matches(
                search_text, active_links, 'link'
            )
            relevant_links.extend(keyword_matches)

            # 2. Busca semântica (se disponível)
            if self.embedding_model and len(relevant_links) < self.max_links_per_response:
                semantic_matches = await self._find_semantic_matches(
                    search_text,
                    active_links,
                    'link',
                    limit=self.max_links_per_response - len(relevant_links)
                )
                relevant_links.extend(semantic_matches)

            # Remover duplicatas
            seen_ids = set()
            unique_links = []
            for link in relevant_links:
                if link['id'] not in seen_ids:
                    unique_links.append(link)
                    seen_ids.add(link['id'])
                    if len(unique_links) >= self.max_links_per_response:
                        break

            return unique_links

        except Exception as e:
            logger.error(f"Erro ao buscar links: {e}")
            return []

    async def _find_relevant_documents(
        self,
        search_text: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Busca documentos baixáveis relevantes"""
        try:
            from app.models.knowledge import DownloadableDocument

            # Buscar documentos ativos
            result = await db.execute(
                select(DownloadableDocument).where(
                    DownloadableDocument.is_active == True
                )
            )
            active_docs = result.scalars().all()

            if not active_docs:
                return []

            relevant_docs = []

            # 1. Busca por palavras-chave
            keyword_matches = await self._find_keyword_matches(
                search_text, active_docs, 'document'
            )
            relevant_docs.extend(keyword_matches)

            # 2. Busca semântica
            if self.embedding_model and len(relevant_docs) < self.max_documents_per_response:
                semantic_matches = await self._find_semantic_matches(
                    search_text,
                    active_docs,
                    'document',
                    limit=self.max_documents_per_response - len(relevant_docs)
                )
                relevant_docs.extend(semantic_matches)

            # Remover duplicatas
            seen_ids = set()
            unique_docs = []
            for doc in relevant_docs:
                if doc['id'] not in seen_ids:
                    unique_docs.append(doc)
                    seen_ids.add(doc['id'])
                    if len(unique_docs) >= self.max_documents_per_response:
                        break

            return unique_docs

        except Exception as e:
            logger.error(f"Erro ao buscar documentos: {e}")
            return []

    async def _find_keyword_matches(
        self,
        search_text: str,
        items: List[Any],
        resource_type: str
    ) -> List[Dict[str, Any]]:
        """Busca baseada em palavras-chave"""
        try:
            keywords = self._extract_keywords(search_text)
            if not keywords:
                return []

            results = []

            for item in items[:20]:  # Limitar para performance
                # Calcular score baseado em matches
                title_match = any(kw in self._normalize_text(item.title or '') for kw in keywords)
                desc_match = any(kw in self._normalize_text(item.description or '') for kw in keywords)
                guidance_match = any(kw in self._normalize_text(item.ai_guidance or '') for kw in keywords)

                # Calcular score
                score = 0.0
                if title_match:
                    score += 0.4
                if desc_match:
                    score += 0.3
                if guidance_match:
                    score += 0.3

                if score >= 0.3:  # Threshold mínimo
                    result = self._format_resource(item, resource_type, score)
                    if result:
                        results.append(result)

            # Ordenar por relevância
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return results[:5]

        except Exception as e:
            logger.error(f"Erro na busca por keywords: {e}")
            return []

    async def _find_semantic_matches(
        self,
        search_text: str,
        items: List[Any],
        resource_type: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Busca semântica usando embeddings"""
        try:
            if not self.embedding_model:
                return []

            # Gerar embedding da query
            query_embedding = self.embedding_model.encode([search_text])

            results = []

            for item in items[:20]:  # Limitar para performance
                # Criar texto combinado
                combined_text = self._create_combined_text(item)

                if combined_text.strip():
                    # Gerar embedding do recurso
                    resource_embedding = self.embedding_model.encode([combined_text])

                    # Calcular similaridade usando numpy
                    from sklearn.metrics.pairwise import cosine_similarity
                    similarity = cosine_similarity(query_embedding, resource_embedding)[0][0]

                    if similarity >= self.similarity_threshold:
                        result = self._format_resource(item, resource_type, float(similarity))
                        if result:
                            results.append(result)

            # Ordenar por similaridade
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return results[:limit]

        except Exception as e:
            logger.error(f"Erro na busca semântica: {e}")
            return []

    def _normalize_text(self, text: str) -> str:
        """Normaliza texto removendo acentos"""
        if not text:
            return ""

        # Remover acentos
        text = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')

        return text.lower().strip()

    def _extract_keywords(self, text: str) -> List[str]:
        """Extrai palavras-chave relevantes"""
        normalized = self._normalize_text(text)

        # Remover pontuação
        clean_text = re.sub(r'[^\w\s]', ' ', normalized)
        words = clean_text.split()

        # Filtrar stopwords
        stopwords = {
            'a', 'o', 'e', 'de', 'do', 'da', 'em', 'um', 'uma', 'para',
            'com', 'por', 'no', 'na', 'os', 'as', 'dos', 'das', 'que'
        }

        keywords = [w for w in words if len(w) > 2 and w not in stopwords]

        return keywords[:10]

    def _create_combined_text(self, resource) -> str:
        """Cria texto combinado do recurso"""
        parts = []

        if hasattr(resource, 'title') and resource.title:
            parts.append(resource.title)

        if hasattr(resource, 'description') and resource.description:
            parts.append(resource.description)

        if hasattr(resource, 'ai_guidance') and resource.ai_guidance:
            parts.append(resource.ai_guidance)

        return ' '.join(parts)

    def _format_resource(
        self,
        resource,
        resource_type: str,
        relevance_score: float
    ) -> Optional[Dict[str, Any]]:
        """Formata recurso para resposta"""
        try:
            base_result = {
                'id': resource.id,
                'title': resource.title,
                'category': resource.category,
                'relevance_score': relevance_score,
                'type': resource_type
            }

            if resource_type == 'link':
                base_result.update({
                    'url': resource.url,
                    'description': resource.description or '',
                    'send_count': resource.send_count
                })
            elif resource_type == 'document':
                base_result.update({
                    'description': resource.description or '',
                    'file_name': resource.file_name,
                    'file_size': resource.file_size,
                    'download_count': resource.download_count
                })

            return base_result

        except Exception as e:
            logger.error(f"Erro ao formatar recurso: {e}")
            return None

    def _is_document_request(self, query: str) -> bool:
        """Detecta se é uma solicitação de documento"""
        query_lower = query.lower()

        # Indicadores de solicitação
        indicators = [
            'preciso', 'quero', 'onde está', 'tem o', 'tem um',
            'formulário', 'documento', 'arquivo', 'baixar', 'download',
            'onde encontro', 'onde pego', 'me envia', 'pode enviar'
        ]

        return any(ind in query_lower for ind in indicators)

    async def increment_resource_usage(
        self,
        resource_type: str,
        resource_id: int,
        action: str,
        user_id: Optional[int] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Incrementa contador de uso do recurso"""
        try:
            if not db:
                return False

            from app.models.knowledge import UsefulLink, DownloadableDocument, ResourceUsage

            # Incrementar contador apropriado
            if resource_type == 'link' and action == 'shared':
                await db.execute(
                    update(UsefulLink)
                    .where(UsefulLink.id == resource_id)
                    .values(send_count=UsefulLink.send_count + 1)
                )
            elif resource_type == 'document' and action == 'downloaded':
                await db.execute(
                    update(DownloadableDocument)
                    .where(DownloadableDocument.id == resource_id)
                    .values(download_count=DownloadableDocument.download_count + 1)
                )

            # Registrar uso
            usage = ResourceUsage(
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action
            )
            db.add(usage)

            await db.commit()
            return True

        except Exception as e:
            logger.error(f"Erro ao incrementar uso: {e}")
            return False

    def format_resources_for_llm(
        self,
        resources: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """Formata recursos para inclusão no prompt do LLM"""
        try:
            if not resources['useful_links'] and not resources['downloadable_documents']:
                return ""

            parts = []

            # Links úteis
            if resources['useful_links']:
                parts.append("LINKS ÚTEIS DISPONÍVEIS:")
                for link in resources['useful_links']:
                    parts.append(
                        f"- [{link['title']}]({link['url']}) - {link['description']}"
                    )
                parts.append("")

            # Documentos
            if resources['downloadable_documents']:
                parts.append("DOCUMENTOS PARA DOWNLOAD:")
                for doc in resources['downloadable_documents']:
                    parts.append(
                        f"- {doc['title']} - {doc['description']}"
                    )
                parts.append("")

            if parts:
                parts.insert(0, "RECURSOS ADICIONAIS:\n")
                parts.append(
                    "INSTRUÇÃO: Inclua estes recursos na resposta quando relevantes."
                )

            return "\n".join(parts)

        except Exception as e:
            logger.error(f"Erro ao formatar recursos: {e}")
            return ""


# Singleton instance
_knowledge_service = None

def get_knowledge_service() -> KnowledgeResourcesService:
    """Retorna instância singleton do serviço"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeResourcesService()
    return _knowledge_service