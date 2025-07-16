from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
import logging

from .services import HybridSearchService
from .llm_providers import LLMManager

logger = logging.getLogger(__name__)

class SearchView(APIView):
    """RAG search endpoint"""
    permission_classes = [AllowAny]  # Temporário para testes
    
    def __init__(self):
        super().__init__()
        self.hybrid_search = HybridSearchService()
        self.llm_manager = LLMManager()
    
    def post(self, request):
        try:
            query = request.data.get('query', '')
            k = request.data.get('k', 5)
            include_llm_response = request.data.get('include_llm_response', True)
            provider = request.data.get('provider', None)
            
            if not query:
                return Response(
                    {'error': 'Query parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Realizar busca híbrida
            try:
                search_results, search_query = self.hybrid_search.search(
                    query=query,
                    k=k,
                    user=getattr(request, 'user', None)
                )
            except Exception as search_error:
                logger.error(f"Erro na busca híbrida: {str(search_error)}", exc_info=True)
                # Se a busca falhar, continuar sem documentos
                search_results = []
                search_query = None
            
            if search_query:
                result = {
                    'query': query,
                    'search_id': search_query.id,
                    'results': search_results,
                    'search_stats': {
                        'total_results': len(search_results),
                        'search_duration_ms': search_query.search_duration_ms,
                        'embedding_duration_ms': search_query.embedding_duration_ms,
                        'semantic_weight': search_query.semantic_weight,
                        'bm25_weight': search_query.bm25_weight
                    }
                }
            else:
                result = {
                    'query': query,
                    'search_id': None,
                    'results': search_results,
                    'search_stats': {
                        'total_results': len(search_results),
                        'search_duration_ms': 0,
                        'embedding_duration_ms': 0,
                        'semantic_weight': 0.7,
                        'bm25_weight': 0.3,
                        'error': 'Busca não foi possível - base de conhecimento vazia'
                    }
                }
            
            # Gerar resposta LLM se solicitado
            if include_llm_response:
                if search_results:
                    # Se há documentos encontrados, usar como contexto
                    context_chunks = [chunk['content'] for chunk in search_results]
                    result['sources_used'] = len(context_chunks)
                else:
                    # Se não há documentos, responder sem contexto
                    context_chunks = None
                    result['sources_used'] = 0
                
                llm_response = self.llm_manager.generate_response(
                    prompt=query,
                    context=context_chunks,
                    provider=provider
                )
                
                result['llm_response'] = llm_response
            
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