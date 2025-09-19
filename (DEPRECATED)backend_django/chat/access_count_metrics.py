"""
Sistema de métricas para monitorar o impacto do sistema de contagem de acesso
Coleta dados sobre precisão, distribuição e qualidade das métricas geradas
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.db.models import Count, Sum, Avg, Q
from django.core.cache import cache
from documents.models import Document
from chat.models import ChatMessage
from .access_count_config import access_count_config


class AccessCountMetrics:
    """Sistema de coleta e análise de métricas de contagem de acesso"""
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutos
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Coleta métricas gerais do sistema"""
        cache_key = 'access_count_system_metrics'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Métricas básicas
        active_docs = Document.objects.filter(is_active=True)
        total_docs = active_docs.count()
        total_accesses = active_docs.aggregate(total=Sum('access_count'))['total'] or 0
        avg_access = active_docs.aggregate(avg=Avg('access_count'))['avg'] or 0
        
        # Distribuição de acessos
        never_accessed = active_docs.filter(access_count=0).count()
        low_access = active_docs.filter(access_count__gte=1, access_count__lte=5).count()
        medium_access = active_docs.filter(access_count__gte=6, access_count__lte=20).count()
        high_access = active_docs.filter(access_count__gte=21).count()
        
        # Métricas de qualidade
        gini_coefficient = self._calculate_gini_coefficient(active_docs)
        top_10_concentration = self._calculate_top_n_concentration(active_docs, 10)
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'total_documents': total_docs,
            'total_accesses': total_accesses,
            'average_accesses': round(avg_access, 2),
            'distribution': {
                'never_accessed': never_accessed,
                'low_access_1_5': low_access,
                'medium_access_6_20': medium_access,
                'high_access_21_plus': high_access,
                'percentages': {
                    'never_accessed': round(never_accessed / total_docs * 100, 1) if total_docs > 0 else 0,
                    'low_access': round(low_access / total_docs * 100, 1) if total_docs > 0 else 0,
                    'medium_access': round(medium_access / total_docs * 100, 1) if total_docs > 0 else 0,
                    'high_access': round(high_access / total_docs * 100, 1) if total_docs > 0 else 0,
                }
            },
            'quality_metrics': {
                'gini_coefficient': round(gini_coefficient, 3),
                'top_10_concentration': round(top_10_concentration, 3),
                'effective_documents': self._count_effective_documents(active_docs)
            },
            'configuration': access_count_config.get_strategy_config()
        }
        
        cache.set(cache_key, metrics, self.cache_timeout)
        return metrics
    
    def analyze_recent_chat_patterns(self, days: int = 7) -> Dict[str, Any]:
        """Analisa padrões de chat recentes para validar precisão"""
        since_date = datetime.now() - timedelta(days=days)
        
        recent_messages = ChatMessage.objects.filter(
            created_at__gte=since_date,
            message_type='assistant',
            context_used__isnull=False
        ).exclude(context_used=[])
        
        # Analisar contexto usado vs documentos populares
        context_document_ids = []
        for message in recent_messages:
            if message.context_used:
                for context in message.context_used:
                    if isinstance(context, dict) and 'document_id' in context:
                        context_document_ids.append(context['document_id'])
        
        # Contar frequência de uso real
        from collections import Counter
        actual_usage = Counter(context_document_ids)
        
        # Comparar com access_count registrado
        usage_analysis = []
        for doc_id, actual_count in actual_usage.most_common(20):
            try:
                doc = Document.objects.get(id=doc_id, is_active=True)
                registered_count = doc.access_count
                
                usage_analysis.append({
                    'document_id': doc_id,
                    'title': doc.title,
                    'actual_usage_recent': actual_count,
                    'registered_access_count': registered_count,
                    'accuracy_ratio': registered_count / max(actual_count, 1),  # Evitar divisão por zero
                })
            except Document.DoesNotExist:
                continue
        
        return {
            'analysis_period_days': days,
            'total_recent_messages': recent_messages.count(),
            'unique_documents_used': len(actual_usage),
            'top_documents_analysis': usage_analysis[:10],
            'accuracy_summary': self._calculate_accuracy_summary(usage_analysis)
        }
    
    def generate_precision_report(self, threshold_range: tuple = (0.5, 0.8)) -> Dict[str, Any]:
        """Gera relatório de precisão para diferentes configurações"""
        min_threshold, max_threshold = threshold_range
        step = 0.1
        
        results = []
        current_threshold = min_threshold
        
        while current_threshold <= max_threshold:
            # Simular configuração
            temp_config = access_count_config
            original_threshold = temp_config.MIN_SCORE_THRESHOLD
            temp_config.MIN_SCORE_THRESHOLD = current_threshold
            
            # Calcular métricas simuladas
            precision_score = self._estimate_precision_for_threshold(current_threshold)
            coverage_score = self._estimate_coverage_for_threshold(current_threshold)
            
            results.append({
                'threshold': round(current_threshold, 1),
                'estimated_precision': round(precision_score, 3),
                'estimated_coverage': round(coverage_score, 3),
                'f1_score': round(2 * (precision_score * coverage_score) / (precision_score + coverage_score), 3) if (precision_score + coverage_score) > 0 else 0
            })
            
            current_threshold += step
            
        # Restaurar configuração original
        temp_config.MIN_SCORE_THRESHOLD = original_threshold
        
        # Encontrar threshold ótimo
        best_config = max(results, key=lambda x: x['f1_score'])
        
        return {
            'threshold_analysis': results,
            'recommended_threshold': best_config['threshold'],
            'best_f1_score': best_config['f1_score'],
            'current_threshold': access_count_config.MIN_SCORE_THRESHOLD,
            'improvement_potential': best_config['f1_score'] - next(
                (r['f1_score'] for r in results if r['threshold'] == access_count_config.MIN_SCORE_THRESHOLD), 0
            )
        }
    
    def _calculate_gini_coefficient(self, queryset) -> float:
        """Calcula coeficiente de Gini para distribuição de acessos"""
        access_counts = list(queryset.values_list('access_count', flat=True))
        if not access_counts:
            return 0.0
        
        access_counts.sort()
        n = len(access_counts)
        
        if sum(access_counts) == 0:
            return 0.0
        
        numerator = sum((2 * i + 1) * count for i, count in enumerate(access_counts))
        denominator = n * sum(access_counts)
        
        return (numerator / denominator) - (n + 1) / n
    
    def _calculate_top_n_concentration(self, queryset, n: int) -> float:
        """Calcula concentração dos top N documentos"""
        total_accesses = queryset.aggregate(total=Sum('access_count'))['total'] or 0
        if total_accesses == 0:
            return 0.0
        
        top_n_accesses = sum(
            queryset.order_by('-access_count')[:n].values_list('access_count', flat=True)
        )
        
        return top_n_accesses / total_accesses
    
    def _count_effective_documents(self, queryset) -> int:
        """Conta documentos com acesso significativo (>= 5% da média)"""
        avg_access = queryset.aggregate(avg=Avg('access_count'))['avg'] or 0
        threshold = max(1, avg_access * 0.05)  # 5% da média ou pelo menos 1
        
        return queryset.filter(access_count__gte=threshold).count()
    
    def _calculate_accuracy_summary(self, usage_analysis: List[Dict]) -> Dict[str, float]:
        """Calcula resumo de precisão baseado na análise de uso"""
        if not usage_analysis:
            return {'mean_accuracy': 0.0, 'median_accuracy': 0.0, 'accuracy_std': 0.0}
        
        accuracy_ratios = [item['accuracy_ratio'] for item in usage_analysis]
        
        import statistics
        return {
            'mean_accuracy': round(statistics.mean(accuracy_ratios), 3),
            'median_accuracy': round(statistics.median(accuracy_ratios), 3),
            'accuracy_std': round(statistics.stdev(accuracy_ratios), 3) if len(accuracy_ratios) > 1 else 0.0
        }
    
    def _estimate_precision_for_threshold(self, threshold: float) -> float:
        """Estima precisão baseada no threshold (heurística)"""
        # Heurística: thresholds maiores = maior precisão, menor cobertura
        base_precision = 0.6
        threshold_bonus = (threshold - 0.5) * 0.8  # Escala de 0.5 a 1.0
        return min(1.0, base_precision + threshold_bonus)
    
    def _estimate_coverage_for_threshold(self, threshold: float) -> float:
        """Estima cobertura baseada no threshold (heurística)"""
        # Heurística: thresholds menores = maior cobertura, menor precisão
        base_coverage = 0.7
        threshold_penalty = (threshold - 0.5) * 0.5  # Redução com threshold alto
        return max(0.1, base_coverage - threshold_penalty)


# Instância global das métricas
access_count_metrics = AccessCountMetrics()