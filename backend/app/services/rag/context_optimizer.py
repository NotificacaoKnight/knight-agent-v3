"""
Context Optimizer - Seleção e Formatação Inteligente de Contexto
Implementa MMR, compressão de redundâncias e formatação natural
"""
import logging
import random
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class ContextOptimizer:
    """
    Otimizador de contexto para RAG

    Funcionalidades:
    - Maximum Marginal Relevance (MMR) para diversidade
    - Compressão de redundâncias
    - Formatação natural de contexto
    - Limite adaptativo de tokens
    """

    def __init__(
        self,
        lambda_param: float = 0.5,
        max_tokens: int = 4000,
        similarity_threshold: float = 0.85
    ):
        """
        Inicializa otimizador

        Args:
            lambda_param: Balanceamento MMR (0=diversidade, 1=relevância)
            max_tokens: Limite máximo de tokens no contexto
            similarity_threshold: Threshold para detectar redundância
        """
        self.lambda_param = lambda_param
        self.max_tokens = max_tokens
        self.similarity_threshold = similarity_threshold

    def select_chunks_mmr(
        self,
        chunks: List[Dict[str, Any]],
        query_embedding: Optional[np.ndarray] = None,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Seleciona chunks usando Maximum Marginal Relevance

        MMR balanceia relevância vs diversidade para evitar redundância

        Args:
            chunks: Lista de chunks com scores
            query_embedding: Embedding da query (opcional, usa scores se None)
            k: Número de chunks a selecionar

        Returns:
            Lista de k chunks selecionados por MMR
        """
        if not chunks:
            return []

        if len(chunks) <= k:
            return chunks

        try:
            # Se não tiver embeddings, usar apenas scores
            if query_embedding is None or not all('embedding' in c for c in chunks):
                return self._select_by_scores_only(chunks, k)

            # Implementação MMR com embeddings
            selected = []
            remaining = list(chunks)

            # Extrair embeddings
            chunk_embeddings = np.array([c['embedding'] for c in remaining])
            query_emb = query_embedding.reshape(1, -1)

            # 1. Selecionar chunk mais relevante primeiro
            relevance_scores = cosine_similarity(query_emb, chunk_embeddings)[0]
            first_idx = np.argmax(relevance_scores)
            selected.append(remaining.pop(first_idx))

            # 2. Selecionar chunks restantes usando MMR
            while len(selected) < k and remaining:
                # Embeddings dos chunks restantes
                remaining_embeddings = np.array([c['embedding'] for c in remaining])

                # Relevância para query
                relevance = cosine_similarity(query_emb, remaining_embeddings)[0]

                # Similaridade máxima com chunks já selecionados
                if len(selected) == 1:
                    selected_embeddings = np.array([selected[0]['embedding']]).reshape(1, -1)
                else:
                    selected_embeddings = np.array([c['embedding'] for c in selected])

                max_sim_to_selected = np.max(
                    cosine_similarity(remaining_embeddings, selected_embeddings),
                    axis=1
                )

                # Score MMR: λ * relevância - (1-λ) * similaridade_com_selecionados
                mmr_scores = (
                    self.lambda_param * relevance -
                    (1 - self.lambda_param) * max_sim_to_selected
                )

                # Selecionar chunk com maior score MMR
                best_idx = np.argmax(mmr_scores)
                selected.append(remaining.pop(best_idx))

            logger.info(f"MMR selecionou {len(selected)} chunks com diversidade")
            return selected

        except Exception as e:
            logger.error(f"Erro no MMR, usando fallback por scores: {e}")
            return self._select_by_scores_only(chunks, k)

    def _select_by_scores_only(
        self,
        chunks: List[Dict[str, Any]],
        k: int
    ) -> List[Dict[str, Any]]:
        """
        Fallback: seleciona chunks apenas por score, garantindo diversidade de documentos

        Args:
            chunks: Lista de chunks
            k: Quantidade a selecionar

        Returns:
            Top k chunks com diversidade de documentos
        """
        if not chunks:
            return []

        # Ordenar por score
        sorted_chunks = sorted(
            chunks,
            key=lambda x: x.get('score', 0),
            reverse=True
        )

        # Selecionar garantindo diversidade de documentos
        selected = []
        seen_docs = set()

        for chunk in sorted_chunks:
            if len(selected) >= k:
                break

            doc_id = chunk.get('document_id')

            # Adicionar se for de novo documento OU score muito alto
            if doc_id not in seen_docs or chunk.get('score', 0) > 0.9:
                selected.append(chunk)
                seen_docs.add(doc_id)

        return selected

    def compress_context(
        self,
        chunks: List[Dict[str, Any]],
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Remove redundâncias e limita tokens

        Args:
            chunks: Lista de chunks
            max_tokens: Limite de tokens (usa self.max_tokens se None)

        Returns:
            Lista de chunks comprimidos
        """
        if not chunks:
            return []

        max_tokens = max_tokens or self.max_tokens

        # Remover chunks muito similares
        deduped = self._remove_similar_chunks(chunks)

        # Limitar por tokens
        limited = self._limit_by_tokens(deduped, max_tokens)

        logger.info(
            f"Compressão: {len(chunks)} → {len(deduped)} (dedup) → {len(limited)} (tokens)"
        )

        return limited

    def _remove_similar_chunks(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove chunks muito similares entre si

        Args:
            chunks: Lista de chunks

        Returns:
            Chunks sem redundâncias
        """
        if len(chunks) <= 1:
            return chunks

        # Se tiver embeddings, usar similaridade
        if all('embedding' in c for c in chunks):
            return self._dedup_by_embeddings(chunks)

        # Senão, usar similaridade de texto
        return self._dedup_by_text(chunks)

    def _dedup_by_embeddings(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove chunks similares usando embeddings"""
        try:
            unique = [chunks[0]]  # Primeiro chunk sempre incluído

            for chunk in chunks[1:]:
                # Verificar similaridade com chunks já selecionados
                chunk_emb = np.array(chunk['embedding']).reshape(1, -1)
                unique_embs = np.array([c['embedding'] for c in unique])

                similarities = cosine_similarity(chunk_emb, unique_embs)[0]
                max_similarity = np.max(similarities)

                # Adicionar apenas se não for muito similar
                if max_similarity < self.similarity_threshold:
                    unique.append(chunk)

            return unique

        except Exception as e:
            logger.error(f"Erro em dedup por embeddings: {e}")
            return chunks

    def _dedup_by_text(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove chunks com texto muito similar (fallback)"""
        unique = [chunks[0]]

        for chunk in chunks[1:]:
            content = chunk.get('content', '').lower()

            # Verificar overlap de palavras com chunks existentes
            is_unique = True
            for existing in unique:
                existing_content = existing.get('content', '').lower()

                # Calcular Jaccard similarity simples
                words1 = set(content.split())
                words2 = set(existing_content.split())

                if words1 and words2:
                    intersection = len(words1 & words2)
                    union = len(words1 | words2)
                    jaccard = intersection / union

                    if jaccard > 0.7:  # 70% de overlap
                        is_unique = False
                        break

            if is_unique:
                unique.append(chunk)

        return unique

    def _limit_by_tokens(
        self,
        chunks: List[Dict[str, Any]],
        max_tokens: int
    ) -> List[Dict[str, Any]]:
        """
        Limita chunks pelo número de tokens

        Args:
            chunks: Lista de chunks
            max_tokens: Máximo de tokens

        Returns:
            Chunks que cabem no limite
        """
        # Estimativa: ~4 caracteres por token para português
        chars_per_token = 4
        max_chars = max_tokens * chars_per_token

        selected = []
        total_chars = 0

        for chunk in chunks:
            content = chunk.get('content', '')
            chunk_chars = len(content)

            if total_chars + chunk_chars <= max_chars:
                selected.append(chunk)
                total_chars += chunk_chars
            else:
                # Truncar último chunk se necessário
                remaining_chars = max_chars - total_chars
                if remaining_chars > 200:  # Só incluir se sobrar > 200 chars
                    truncated_chunk = chunk.copy()
                    truncated_chunk['content'] = content[:remaining_chars] + "..."
                    selected.append(truncated_chunk)
                break

        return selected

    def format_context_natural(
        self,
        chunks: List[Dict[str, Any]],
        language: str = "pt"
    ) -> str:
        """
        Formata contexto de forma natural (sem marcações técnicas)

        Args:
            chunks: Lista de chunks selecionados
            language: Idioma

        Returns:
            String com contexto formatado naturalmente
        """
        if not chunks:
            return ""

        context_parts = []

        for chunk in chunks:
            content = chunk.get('content', '').strip()
            if not content:
                continue

            # Informações de fonte
            doc_title = chunk.get('document_title', '')
            section = chunk.get('section_title', '')
            page = chunk.get('page_number')

            # Criar introdução natural da fonte
            source_intro = self._create_source_intro(
                doc_title, section, page, language
            )

            # Integrar fonte com conteúdo
            formatted = self._integrate_source_with_content(
                source_intro, content, language
            )

            context_parts.append(formatted)

        # Juntar com espaçamento
        return "\n\n".join(context_parts)

    def _create_source_intro(
        self,
        doc_title: str,
        section: str,
        page: Optional[int],
        language: str
    ) -> str:
        """
        Cria introdução natural da fonte

        Args:
            doc_title: Título do documento
            section: Título da seção
            page: Número da página
            language: Idioma

        Returns:
            String com introdução da fonte
        """
        # Usar título do documento ou seção (o que for mais específico)
        source_name = section if section else (doc_title or "documentação interna")

        if language == "pt":
            # Variações de introdução em português
            templates = [
                f"Segundo {source_name}",
                f"De acordo com {source_name}",
                f"Conforme {source_name}",
                f"{source_name} informa que",
                f"{source_name} diz que",
                f"Em {source_name}",
            ]
        else:
            # Variações em inglês
            templates = [
                f"According to {source_name}",
                f"As stated in {source_name}",
                f"{source_name} indicates that",
                f"{source_name} states that",
                f"In {source_name}",
            ]

        intro = random.choice(templates)

        # Adicionar página se disponível e relevante
        if page and page > 1 and language == "pt":
            intro += f" (página {page})"
        elif page and page > 1:
            intro += f" (page {page})"

        return intro

    def _integrate_source_with_content(
        self,
        source_intro: str,
        content: str,
        language: str
    ) -> str:
        """
        Integra introdução da fonte com o conteúdo

        Args:
            source_intro: Introdução da fonte
            content: Conteúdo do chunk
            language: Idioma

        Returns:
            Texto integrado
        """
        # Se conteúdo já começa com referência, não adicionar
        content_lower = content.lower()

        if language == "pt":
            skip_words = ["segundo", "de acordo", "conforme", "em"]
        else:
            skip_words = ["according", "as stated", "in"]

        # Verificar se conteúdo já tem referência
        starts_with_reference = any(
            content_lower.strip().startswith(word) for word in skip_words
        )

        if starts_with_reference:
            return content

        # Integrar introdução com conteúdo
        # Se conteúdo termina com pontuação de fim, integrar diretamente
        first_sentence = content.split('.')[0] if '.' in content else content

        if len(first_sentence) < 100:  # Primeira frase curta
            # Integrar na mesma linha
            return f"{source_intro}, {content[0].lower()}{content[1:]}"
        else:
            # Separar em linhas
            return f"{source_intro}:\n{content}"

    def prepare_optimized_context(
        self,
        chunks: List[Dict[str, Any]],
        query_embedding: Optional[np.ndarray] = None,
        k: int = 5,
        language: str = "pt"
    ) -> str:
        """
        Pipeline completo: seleciona, comprime e formata contexto

        Args:
            chunks: Chunks brutos da busca
            query_embedding: Embedding da query
            k: Número de chunks a selecionar
            language: Idioma

        Returns:
            Contexto otimizado e formatado
        """
        if not chunks:
            return ""

        # 1. Selecionar chunks com MMR
        selected = self.select_chunks_mmr(chunks, query_embedding, k)

        # 2. Comprimir (remover redundâncias e limitar tokens)
        compressed = self.compress_context(selected)

        # 3. Formatar naturalmente
        formatted = self.format_context_natural(compressed, language)

        logger.info(
            f"Contexto otimizado: {len(chunks)} chunks → "
            f"{len(selected)} selecionados → "
            f"{len(compressed)} comprimidos → "
            f"{len(formatted)} chars formatados"
        )

        return formatted

    def get_context_stats(
        self,
        context: str
    ) -> Dict[str, Any]:
        """
        Retorna estatísticas do contexto gerado

        Args:
            context: Contexto formatado

        Returns:
            Dicionário com estatísticas
        """
        # Estimativas
        chars = len(context)
        tokens_estimate = chars // 4  # ~4 chars por token
        words = len(context.split())

        return {
            'characters': chars,
            'tokens_estimate': tokens_estimate,
            'words': words,
            'paragraphs': context.count('\n\n') + 1
        }


# Singleton instance
context_optimizer = ContextOptimizer()
