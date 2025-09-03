"""
Serviço para integrar links úteis e documentos baixáveis ao sistema RAG
"""
import os
import re
from typing import List, Dict, Any, Optional
from django.db.models import Q, F
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging

from knowledge_resources.models import UsefulLink, DownloadableDocument, ResourceUsage
from .model_cache import get_cached_model

logger = logging.getLogger(__name__)


class KnowledgeResourcesService:
    """Serviço para buscar e integrar recursos de conhecimento ao RAG"""
    
    def __init__(self):
        self.embedding_model = None
        self._load_embedding_model()
        
        # Configurações
        self.similarity_threshold = 0.6  # Limite mínimo para considerar relevante
        self.max_links_per_response = 3
        self.max_documents_per_response = 2
    
    def _load_embedding_model(self):
        """Carrega modelo de embedding usando cache global thread-safe"""
        try:
            from django.conf import settings
            model_name = getattr(settings, 'EMBEDDING_MODEL', 'BAAI/bge-m3')
            self.embedding_model = get_cached_model(model_name, device='cpu')
            if self.embedding_model is not None:
                logger.info(f"Modelo de embedding obtido do cache: {model_name}")
            else:
                logger.warning(f"Modelo de embedding não disponível: {model_name}")
        except Exception as e:
            logger.error(f"Erro ao carregar modelo de embedding: {e}")
            self.embedding_model = None
    
    def find_relevant_resources(
        self, 
        query: str, 
        context: Optional[str] = None,
        user: Optional[Any] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Encontra links úteis e documentos relevantes para a query
        
        Args:
            query: Pergunta do usuário
            context: Contexto adicional da conversa
            user: Usuário fazendo a consulta
            
        Returns:
            Dict com 'useful_links' e 'downloadable_documents'
        """
        try:
            # Combinar query com contexto para busca mais precisa
            search_text = query
            if context:
                search_text = f"{query} {context}"
            
            logger.info(f"Buscando recursos para query: '{query[:50]}...'")
            
            # Buscar recursos relevantes
            relevant_links = self._find_relevant_links(search_text)
            relevant_documents = self._find_relevant_documents(search_text)
            
            logger.info(f"Encontrados: {len(relevant_links)} links, {len(relevant_documents)} documentos")
            
            # Log detalhado dos documentos encontrados
            if relevant_documents:
                for doc in relevant_documents:
                    logger.info(f"Documento encontrado: {doc.get('title', 'N/A')} (ID: {doc.get('id', 'N/A')})")
            
            return {
                'useful_links': relevant_links,
                'downloadable_documents': relevant_documents
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar recursos relevantes: {e}")
            return {'useful_links': [], 'downloadable_documents': []}
    
    def _find_relevant_links(self, search_text: str) -> List[Dict[str, Any]]:
        """Busca links úteis relevantes"""
        try:
            # Buscar links ativos
            active_links = UsefulLink.objects.filter(is_active=True)
            
            if not active_links.exists():
                return []
            
            relevant_links = []
            
            # 1. Busca por palavras-chave (mais rápida)
            keyword_matches = self._find_keyword_matches(search_text, active_links, 'link')
            relevant_links.extend(keyword_matches)
            
            # 2. Busca semântica (mais precisa)
            if self.embedding_model and len(relevant_links) < self.max_links_per_response:
                semantic_matches = self._find_semantic_matches(
                    search_text, 
                    active_links, 
                    'link',
                    limit=self.max_links_per_response - len(relevant_links)
                )
                relevant_links.extend(semantic_matches)
            
            # Remover duplicatas e limitar resultado
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
            logger.error(f"Erro ao buscar links relevantes: {e}")
            return []
    
    def _find_relevant_documents(self, search_text: str) -> List[Dict[str, Any]]:
        """Busca documentos baixáveis relevantes"""
        try:
            # Buscar documentos ativos
            active_docs = DownloadableDocument.objects.filter(is_active=True)
            logger.info(f"Total de documentos ativos disponíveis: {active_docs.count()}")
            
            if not active_docs.exists():
                logger.warning("Nenhum documento ativo encontrado na base")
                return []
            
            relevant_docs = []
            
            # 1. Busca por palavras-chave
            keyword_matches = self._find_keyword_matches(search_text, active_docs, 'document')
            relevant_docs.extend(keyword_matches)
            
            # 2. Busca semântica
            if self.embedding_model and len(relevant_docs) < self.max_documents_per_response:
                semantic_matches = self._find_semantic_matches(
                    search_text,
                    active_docs,
                    'document',
                    limit=self.max_documents_per_response - len(relevant_docs)
                )
                relevant_docs.extend(semantic_matches)
            
            # Remover duplicatas e limitar resultado
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
            logger.error(f"Erro ao buscar documentos relevantes: {e}")
            return []
    
    def _find_keyword_matches(
        self, 
        search_text: str, 
        queryset, 
        resource_type: str
    ) -> List[Dict[str, Any]]:
        """Busca baseada em palavras-chave nos campos de texto"""
        try:
            # Extrair palavras-chave relevantes
            keywords = self._extract_keywords(search_text)
            if not keywords:
                return []
            
            # Construir query Q para busca em múltiplos campos
            q_objects = Q()
            
            for keyword in keywords:
                # Buscar em campos relevantes
                q_objects |= Q(title__icontains=keyword)
                q_objects |= Q(description__icontains=keyword)
                q_objects |= Q(ai_guidance__icontains=keyword)
                q_objects |= Q(category__icontains=keyword)
            
            # Executar busca
            matches = queryset.filter(q_objects).distinct()[:5]
            
            results = []
            for item in matches:
                result = self._format_resource(item, resource_type, 0.8)  # Score alto para keyword match
                if result:
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Erro na busca por palavras-chave: {e}")
            return []
    
    def _find_semantic_matches(
        self, 
        search_text: str, 
        queryset, 
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
            
            for item in queryset[:20]:  # Limitar para performance
                # Criar texto combinado para comparação
                combined_text = self._create_combined_text(item)
                
                if combined_text.strip():
                    # Gerar embedding do recurso
                    resource_embedding = self.embedding_model.encode([combined_text])
                    
                    # Calcular similaridade
                    similarity = cosine_similarity(query_embedding, resource_embedding)[0][0]
                    
                    if similarity >= self.similarity_threshold:
                        result = self._format_resource(item, resource_type, float(similarity))
                        if result:
                            results.append(result)
            
            # Ordenar por similaridade e limitar
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Erro na busca semântica: {e}")
            return []
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrai palavras-chave relevantes do texto"""
        # Remover pontuação e converter para minúsculas
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Dividir em palavras
        words = clean_text.split()
        
        # Filtrar palavras muito curtas e stopwords básicas
        stopwords = {
            'a', 'o', 'e', 'de', 'do', 'da', 'em', 'um', 'uma', 'para', 'com', 'por', 'no', 'na',
            'os', 'as', 'dos', 'das', 'nos', 'nas', 'que', 'se', 'ao', 'até', 'pelo', 'pela',
            'este', 'esta', 'esse', 'essa', 'aquele', 'aquela', 'me', 'te', 'lhe', 'nos', 'vos'
        }
        
        keywords = [word for word in words if len(word) > 2 and word not in stopwords]
        
        # Retornar até 10 palavras-chave mais relevantes
        return keywords[:10]
    
    def _create_combined_text(self, resource) -> str:
        """Cria texto combinado do recurso para comparação semântica"""
        parts = []
        
        if hasattr(resource, 'title') and resource.title:
            parts.append(resource.title)
        
        if hasattr(resource, 'description') and resource.description:
            parts.append(resource.description)
        
        if hasattr(resource, 'ai_guidance') and resource.ai_guidance:
            parts.append(resource.ai_guidance)
        
        if hasattr(resource, 'category') and resource.category:
            parts.append(resource.category)
        
        return ' '.join(parts)
    
    def _format_resource(self, resource, resource_type: str, relevance_score: float) -> Optional[Dict[str, Any]]:
        """Formata recurso para inclusão na resposta"""
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
                    'file_type': resource.file_type,
                    'download_count': resource.download_count
                })
            
            return base_result
            
        except Exception as e:
            logger.error(f"Erro ao formatar recurso: {e}")
            return None
    
    def increment_resource_usage(
        self, 
        resource_type: str, 
        resource_id: int, 
        action: str,
        user: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Incrementa contador de uso do recurso
        
        Args:
            resource_type: 'link' ou 'document'  
            resource_id: ID do recurso
            action: 'shared', 'clicked', 'downloaded'
            user: Usuário que acionou
            context: Contexto adicional (chat_session_id, query, etc.)
        """
        try:
            if resource_type == 'link' and action == 'shared':
                # Incrementar contador do link
                UsefulLink.objects.filter(id=resource_id).update(
                    send_count=F('send_count') + 1
                )
            elif resource_type == 'document':
                if action == 'shared':
                    DownloadableDocument.objects.filter(id=resource_id).update(
                        share_count=F('share_count') + 1
                    )
                elif action == 'downloaded':
                    DownloadableDocument.objects.filter(id=resource_id).update(
                        download_count=F('download_count') + 1
                    )
            
            # Registrar uso para analytics
            ResourceUsage.objects.create(
                user=user,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                query_context=context.get('query', '') if context else '',
                chat_session_id=context.get('chat_session_id') if context else None
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao incrementar uso do recurso: {e}")
            return False
    
    def format_resources_for_llm(self, resources: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Formata recursos para inclusão no prompt do LLM
        
        Returns:
            String formatada com recursos disponíveis
        """
        try:
            if not resources['useful_links'] and not resources['downloadable_documents']:
                return ""
            
            formatted_parts = []
            
            # Links úteis
            if resources['useful_links']:
                formatted_parts.append("LINKS ÚTEIS DISPONÍVEIS:")
                for link in resources['useful_links']:
                    formatted_parts.append(
                        f"- [{link['title']}]({link['url']}) "
                        f"(Categoria: {link['category']}) - {link['description']}"
                    )
                formatted_parts.append("")
            
            # Documentos baixáveis
            if resources['downloadable_documents']:
                formatted_parts.append("DOCUMENTOS PARA DOWNLOAD:")
                for doc in resources['downloadable_documents']:
                    formatted_parts.append(
                        f"- {doc['title']} ({doc['file_type'].upper()}) "
                        f"(Categoria: {doc['category']}) - {doc['description']}"
                    )
                formatted_parts.append("")
            
            if formatted_parts:
                formatted_parts.insert(0, "RECURSOS ADICIONAIS DISPONÍVEIS:\n")
                formatted_parts.append(
                    "INSTRUÇÃO: Inclua estes recursos na sua resposta quando relevantes, "
                    "explicando como podem ajudar o usuário."
                )
            
            return "\n".join(formatted_parts)
            
        except Exception as e:
            logger.error(f"Erro ao formatar recursos para LLM: {e}")
            return ""