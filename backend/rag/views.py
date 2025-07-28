from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
import logging

from .services import HybridSearchService
from .llm_providers import LLMManager
from .agentic_rag_service import AgenticRAGServiceSync

logger = logging.getLogger(__name__)

class SearchView(APIView):
    """Agentic RAG search endpoint"""
    permission_classes = [AllowAny]  # Temporário para testes
    
    def __init__(self):
        super().__init__()
        # Usar serviço agentic como principal, híbrido como fallback
        self.agentic_rag = AgenticRAGServiceSync()
        self.hybrid_search = HybridSearchService()  # Fallback
        self.llm_manager = LLMManager()
    
    def post(self, request):
        try:
            query = request.data.get('query', '')
            k = request.data.get('k', 5)
            use_agentic = request.data.get('use_agentic', True)  # Flag para usar versão agentic
            provider = request.data.get('provider', None)
            
            if not query:
                return Response(
                    {'error': 'Query parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Tentar usar serviço agentic primeiro
            if use_agentic:
                try:
                    agentic_result = self.agentic_rag.search(
                        query=query,
                        k=k,
                        user=getattr(request, 'user', None)
                    )
                    
                    # Formatear resultado para compatibilidade com API existente
                    result = {
                        'query': query,
                        'search_id': agentic_result.get('search_id'),
                        'response': agentic_result.get('response'),
                        'results': agentic_result.get('search_results', []),
                        'search_stats': {
                            'total_results': len(agentic_result.get('search_results', [])),
                            'search_duration_ms': agentic_result.get('metadata', {}).get('search_duration_ms', 0),
                            'total_duration_ms': agentic_result.get('metadata', {}).get('total_duration_ms', 0),
                            'search_attempts': agentic_result.get('quality_metrics', {}).get('search_attempts', 1),
                            'quality_score': agentic_result.get('quality_metrics', {}).get('search_quality', 0.0),
                            'provider_used': agentic_result.get('metadata', {}).get('provider_used', 'unknown'),
                            'is_agentic': True
                        },
                        'quality_metrics': agentic_result.get('quality_metrics', {}),
                        'metadata': agentic_result.get('metadata', {}),
                        'sources_used': agentic_result.get('metadata', {}).get('documents_retrieved', 0)
                    }
                    
                    return Response(result, status=status.HTTP_200_OK)
                    
                except Exception as agentic_error:
                    logger.warning(f"Erro no serviço agentic, usando fallback: {str(agentic_error)}")
                    # Continuar para fallback híbrido
            
            # Fallback para serviço híbrido tradicional
            try:
                search_results, search_query = self.hybrid_search.search(
                    query=query,
                    k=k,
                    user=getattr(request, 'user', None)
                )
            except Exception as search_error:
                logger.error(f"Erro na busca híbrida: {str(search_error)}", exc_info=True)
                search_results = []
                search_query = None
            
            # Gerar resposta LLM para fallback
            if search_results:
                context_chunks = [chunk['content'] for chunk in search_results]
            else:
                context_chunks = None
            
            llm_response = self.llm_manager.generate_response(
                prompt=query,
                context=context_chunks,
                provider=provider
            )
            
            # Formato de resposta para fallback
            if search_query:
                result = {
                    'query': query,
                    'search_id': search_query.id,
                    'response': llm_response.get('response', ''),
                    'results': search_results,
                    'search_stats': {
                        'total_results': len(search_results),
                        'search_duration_ms': search_query.search_duration_ms,
                        'embedding_duration_ms': search_query.embedding_duration_ms,
                        'semantic_weight': search_query.semantic_weight,
                        'bm25_weight': search_query.bm25_weight,
                        'is_agentic': False,
                        'fallback_used': True
                    },
                    'llm_response': llm_response,
                    'sources_used': len(context_chunks) if context_chunks else 0
                }
            else:
                result = {
                    'query': query,
                    'search_id': None,
                    'response': llm_response.get('response', ''),
                    'results': search_results,
                    'search_stats': {
                        'total_results': len(search_results),
                        'search_duration_ms': 0,
                        'embedding_duration_ms': 0,
                        'semantic_weight': 0.7,
                        'bm25_weight': 0.3,
                        'is_agentic': False,
                        'fallback_used': True,
                        'error': 'Busca não foi possível - base de conhecimento vazia'
                    },
                    'llm_response': llm_response,
                    'sources_used': 0
                }
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in RAG search: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StatsView(APIView):
    """RAG statistics endpoint"""
    permission_classes = [AllowAny]  # Temporário para testes
    
    def get(self, request):
        try:
            stats = {
                'indexed_documents': 0,
                'vector_store_size': 0,
                'last_update': None
            }
            
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting RAG stats: {str(e)}")
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AgenticSearchView(APIView):
    """Endpoint exclusivo para RAG Agentic usando LangGraph"""
    permission_classes = [AllowAny]
    
    def __init__(self):
        super().__init__()
        self.agentic_rag = AgenticRAGServiceSync()
    
    def post(self, request):
        try:
            query = request.data.get('query', '')
            k = request.data.get('k', 5)
            
            if not query:
                return Response(
                    {'error': 'Query parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Usar apenas serviço agentic
            agentic_result = self.agentic_rag.search(
                query=query,
                k=k,
                user=getattr(request, 'user', None)
            )
            
            # Retornar resultado completo do sistema agentic
            return Response(agentic_result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in Agentic RAG search: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Agentic search failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LLMTestView(APIView):
    """Endpoint simples para testar LLM sem RAG"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            query = request.data.get('query', '')
            provider = request.data.get('provider', None)
            
            if not query:
                return Response(
                    {'error': 'Query parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            llm_manager = LLMManager()
            
            # Testar resposta simples sem RAG
            llm_response = llm_manager.generate_response(
                prompt=query,
                context=None,
                provider=provider
            )
            
            result = {
                'query': query,
                'llm_response': llm_response,
                'available_providers': llm_manager.get_available_providers()
            }
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in LLM test: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Internal server error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )