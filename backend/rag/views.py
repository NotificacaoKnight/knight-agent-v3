from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
import logging

from .hybrid_vector_service import HybridVectorService
from .llm_providers import LLMManager
from .agentic_rag_service import AgenticRAGServiceSync

logger = logging.getLogger(__name__)

class SearchView(APIView):
    """Agentic RAG search endpoint"""
    permission_classes = [AllowAny]  # Temporário para testes
    
    def __init__(self):
        super().__init__()
        # Usar serviço agentic (que já tem fallback interno)
        self.agentic_rag = AgenticRAGServiceSync()
        self.llm_manager = LLMManager()
    
    def post(self, request):
        try:
            query = request.data.get('query', '')
            k = request.data.get('k', 5)
            provider = request.data.get('provider', None)
            
            if not query:
                return Response(
                    {'error': 'Query parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Usar serviço agentic (que já tem fallback interno)
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
            
        except Exception as e:
            logger.error(f"Erro na busca RAG: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Erro ao processar busca: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AgenticSearchView(APIView):
    """Agentic RAG search endpoint (force agentic mode)"""
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
            
            # Busca agentic direta
            result = self.agentic_rag.search(
                query=query,
                k=k,
                user=getattr(request, 'user', None)
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erro na busca agentic: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TestLLMView(APIView):
    """Endpoint para testar provedores LLM"""
    permission_classes = [AllowAny]
    
    def __init__(self):
        super().__init__()
        self.llm_manager = LLMManager()
    
    def post(self, request):
        prompt = request.data.get('prompt', 'Olá, você está funcionando?')
        provider = request.data.get('provider', None)
        
        response = self.llm_manager.generate_response(
            prompt=prompt,
            provider=provider,
            max_tokens=200
        )
        
        return Response(response)
    
    def get(self, request):
        """Lista provedores disponíveis"""
        available = self.llm_manager.get_available_providers()
        primary = self.llm_manager.primary_provider
        
        return Response({
            'primary_provider': primary,
            'available_providers': available,
            'fallback_order': self.llm_manager.fallback_order
        })

class RAGStatsView(APIView):
    """Estatísticas do sistema RAG"""
    permission_classes = [AllowAny]
    
    def __init__(self):
        super().__init__()
        self.vector_service = HybridVectorService()
    
    def get(self, request):
        try:
            stats = self.vector_service.get_stats()
            return Response(stats)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )