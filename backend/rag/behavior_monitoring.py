"""
Sistema de Monitoramento de Comportamento Inteligente
Coleta métricas de desempenho e qualidade das respostas
"""
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.core.cache import cache
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class BehaviorMonitor:
    """Monitor de comportamento e qualidade das respostas"""
    
    def __init__(self):
        self.cache_prefix = "behavior_monitor"
        self.metrics_retention_hours = 24
    
    def log_response_metrics(
        self,
        query: str,
        agent_used: str,
        response: str,
        analysis: Dict[str, Any],
        quality_validation: Dict[str, Any],
        processing_time_ms: int,
        user_context: Dict[str, Any] = None
    ):
        """Registra métricas de uma resposta"""
        
        timestamp = datetime.now()
        metrics = {
            "timestamp": timestamp.isoformat(),
            "query_length": len(query),
            "query_hash": hash(query),
            "agent_used": agent_used,
            "response_length": len(response),
            "processing_time_ms": processing_time_ms,
            "complexity_score": analysis.get("complexity_score", 0.0),
            "processing_mode": analysis.get("processing_mode", "unknown"),
            "intent_confidence": analysis.get("intent_confidence", 0.0),
            "urgency_level": analysis.get("urgency_level", "medium"),
            "quality_score": quality_validation.get("overall_score", 0.0),
            "quality_issues_count": len(quality_validation.get("issues", [])),
            "user_department": user_context.get("department") if user_context else None,
            "user_role": user_context.get("role") if user_context else None,
            "estimated_time_accuracy": self._calculate_time_accuracy(
                analysis.get("estimated_time", {}), processing_time_ms
            )
        }
        
        # Armazenar no cache com TTL
        cache_key = f"{self.cache_prefix}_metrics_{timestamp.strftime('%Y%m%d_%H')}"
        current_metrics = cache.get(cache_key, [])
        current_metrics.append(metrics)
        
        # Manter apenas últimas N entradas por hora
        if len(current_metrics) > 100:
            current_metrics = current_metrics[-100:]
        
        cache.set(cache_key, current_metrics, 3600 * self.metrics_retention_hours)
        
        # Log crítico se qualidade muito baixa
        if metrics["quality_score"] < 0.4:
            logger.warning(
                f"Low quality response detected - Agent: {agent_used}, "
                f"Quality: {metrics['quality_score']:.2f}, Query: {query[:50]}..."
            )
    
    def log_user_feedback(
        self,
        query_hash: int,
        feedback_type: str,  # 'helpful', 'not_helpful', 'incomplete', 'wrong'
        feedback_details: str = "",
        user_context: Dict[str, Any] = None
    ):
        """Registra feedback do usuário"""
        
        timestamp = datetime.now()
        feedback = {
            "timestamp": timestamp.isoformat(),
            "query_hash": query_hash,
            "feedback_type": feedback_type,
            "feedback_details": feedback_details,
            "user_department": user_context.get("department") if user_context else None,
            "user_role": user_context.get("role") if user_context else None
        }
        
        cache_key = f"{self.cache_prefix}_feedback_{timestamp.strftime('%Y%m%d')}"
        current_feedback = cache.get(cache_key, [])
        current_feedback.append(feedback)
        
        cache.set(cache_key, current_feedback, 3600 * 24)  # 24h retention
        
        logger.info(f"User feedback received: {feedback_type} for query hash {query_hash}")
    
    def get_performance_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Gera resumo de performance das últimas N horas"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        
        all_metrics = []
        
        # Coletar métricas de todas as horas no período
        current_time = start_time.replace(minute=0, second=0, microsecond=0)
        while current_time <= end_time:
            cache_key = f"{self.cache_prefix}_metrics_{current_time.strftime('%Y%m%d_%H')}"
            hour_metrics = cache.get(cache_key, [])
            all_metrics.extend(hour_metrics)
            current_time += timedelta(hours=1)
        
        if not all_metrics:
            return {"error": "No metrics available"}
        
        # Calcular estatísticas
        total_requests = len(all_metrics)
        avg_processing_time = sum(m["processing_time_ms"] for m in all_metrics) / total_requests
        avg_quality_score = sum(m["quality_score"] for m in all_metrics) / total_requests
        
        # Distribuição por agente
        agent_distribution = {}
        for metric in all_metrics:
            agent = metric["agent_used"]
            if agent not in agent_distribution:
                agent_distribution[agent] = {"count": 0, "avg_quality": 0, "avg_time": 0}
            agent_distribution[agent]["count"] += 1
        
        # Calcular médias por agente
        for agent in agent_distribution:
            agent_metrics = [m for m in all_metrics if m["agent_used"] == agent]
            agent_distribution[agent]["avg_quality"] = (
                sum(m["quality_score"] for m in agent_metrics) / len(agent_metrics)
            )
            agent_distribution[agent]["avg_time"] = (
                sum(m["processing_time_ms"] for m in agent_metrics) / len(agent_metrics)
            )
        
        # Distribuição por modo de processamento
        mode_distribution = {}
        for metric in all_metrics:
            mode = metric["processing_mode"]
            mode_distribution[mode] = mode_distribution.get(mode, 0) + 1
        
        # Problemas de qualidade
        quality_issues = [m for m in all_metrics if m["quality_score"] < 0.5]
        quality_issue_rate = len(quality_issues) / total_requests if total_requests > 0 else 0
        
        # Análise temporal (últimas 6 horas)
        hourly_performance = {}
        for i in range(6):
            hour_start = end_time - timedelta(hours=i+1)
            hour_end = end_time - timedelta(hours=i)
            hour_metrics = [
                m for m in all_metrics 
                if hour_start <= datetime.fromisoformat(m["timestamp"]) < hour_end
            ]
            
            hourly_performance[f"hour_{i+1}"] = {
                "requests": len(hour_metrics),
                "avg_quality": sum(m["quality_score"] for m in hour_metrics) / len(hour_metrics) if hour_metrics else 0,
                "avg_time_ms": sum(m["processing_time_ms"] for m in hour_metrics) / len(hour_metrics) if hour_metrics else 0
            }
        
        return {
            "summary": {
                "total_requests": total_requests,
                "time_period_hours": hours_back,
                "avg_processing_time_ms": round(avg_processing_time, 2),
                "avg_quality_score": round(avg_quality_score, 3),
                "quality_issue_rate": round(quality_issue_rate, 3)
            },
            "agent_performance": {
                agent: {
                    **data,
                    "avg_quality": round(data["avg_quality"], 3),
                    "avg_time": round(data["avg_time"], 2),
                    "percentage": round((data["count"] / total_requests) * 100, 1)
                }
                for agent, data in agent_distribution.items()
            },
            "processing_modes": {
                mode: {
                    "count": count,
                    "percentage": round((count / total_requests) * 100, 1)
                }
                for mode, count in mode_distribution.items()
            },
            "hourly_performance": hourly_performance,
            "quality_analysis": {
                "high_quality_rate": round(
                    len([m for m in all_metrics if m["quality_score"] >= 0.8]) / total_requests, 3
                ),
                "medium_quality_rate": round(
                    len([m for m in all_metrics if 0.5 <= m["quality_score"] < 0.8]) / total_requests, 3
                ),
                "low_quality_rate": round(quality_issue_rate, 3)
            }
        }
    
    def get_quality_insights(self, hours_back: int = 24) -> Dict[str, Any]:
        """Análise detalhada de qualidade"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        
        all_metrics = []
        current_time = start_time.replace(minute=0, second=0, microsecond=0)
        while current_time <= end_time:
            cache_key = f"{self.cache_prefix}_metrics_{current_time.strftime('%Y%m%d_%H')}"
            hour_metrics = cache.get(cache_key, [])
            all_metrics.extend(hour_metrics)
            current_time += timedelta(hours=1)
        
        if not all_metrics:
            return {"error": "No metrics available"}
        
        # Análise de correlações
        correlations = {}
        
        # Correlação complexidade x qualidade
        complex_queries = [m for m in all_metrics if m["complexity_score"] > 0.7]
        simple_queries = [m for m in all_metrics if m["complexity_score"] < 0.4]
        
        if complex_queries and simple_queries:
            correlations["complexity_quality"] = {
                "complex_avg_quality": sum(m["quality_score"] for m in complex_queries) / len(complex_queries),
                "simple_avg_quality": sum(m["quality_score"] for m in simple_queries) / len(simple_queries)
            }
        
        # Correlação urgência x tempo de resposta
        urgent_queries = [m for m in all_metrics if m["urgency_level"] == "high"]
        normal_queries = [m for m in all_metrics if m["urgency_level"] == "medium"]
        
        if urgent_queries and normal_queries:
            correlations["urgency_time"] = {
                "urgent_avg_time": sum(m["processing_time_ms"] for m in urgent_queries) / len(urgent_queries),
                "normal_avg_time": sum(m["processing_time_ms"] for m in normal_queries) / len(normal_queries)
            }
        
        # Problemas mais comuns
        quality_issues = [m for m in all_metrics if m["quality_issues_count"] > 0]
        
        # Análise por departamento/função
        dept_performance = {}
        for metric in all_metrics:
            dept = metric.get("user_department")
            if dept:
                if dept not in dept_performance:
                    dept_performance[dept] = {"count": 0, "avg_quality": 0, "quality_sum": 0}
                dept_performance[dept]["count"] += 1
                dept_performance[dept]["quality_sum"] += metric["quality_score"]
        
        # Calcular médias por departamento
        for dept in dept_performance:
            dept_performance[dept]["avg_quality"] = (
                dept_performance[dept]["quality_sum"] / dept_performance[dept]["count"]
            )
            del dept_performance[dept]["quality_sum"]
        
        return {
            "correlations": correlations,
            "quality_issues": {
                "total_with_issues": len(quality_issues),
                "issue_rate": len(quality_issues) / len(all_metrics) if all_metrics else 0,
                "avg_issues_per_response": sum(m["quality_issues_count"] for m in quality_issues) / len(quality_issues) if quality_issues else 0
            },
            "department_performance": dept_performance,
            "recommendations": self._generate_quality_recommendations(all_metrics, correlations)
        }
    
    def get_user_feedback_summary(self, days_back: int = 7) -> Dict[str, Any]:
        """Resumo do feedback dos usuários"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        all_feedback = []
        current_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        while current_time <= end_time:
            cache_key = f"{self.cache_prefix}_feedback_{current_time.strftime('%Y%m%d')}"
            day_feedback = cache.get(cache_key, [])
            all_feedback.extend(day_feedback)
            current_time += timedelta(days=1)
        
        if not all_feedback:
            return {"message": "No feedback available"}
        
        # Distribuição por tipo de feedback
        feedback_distribution = {}
        for feedback in all_feedback:
            ftype = feedback["feedback_type"]
            feedback_distribution[ftype] = feedback_distribution.get(ftype, 0) + 1
        
        total_feedback = len(all_feedback)
        satisfaction_rate = (
            feedback_distribution.get("helpful", 0) / total_feedback
            if total_feedback > 0 else 0
        )
        
        return {
            "summary": {
                "total_feedback": total_feedback,
                "satisfaction_rate": round(satisfaction_rate, 3),
                "days_analyzed": days_back
            },
            "feedback_distribution": {
                ftype: {
                    "count": count,
                    "percentage": round((count / total_feedback) * 100, 1)
                }
                for ftype, count in feedback_distribution.items()
            },
            "recent_feedback": sorted(
                all_feedback[-10:], 
                key=lambda x: x["timestamp"], 
                reverse=True
            )
        }
    
    def _calculate_time_accuracy(self, estimated_time: Dict[str, Any], actual_time_ms: int) -> float:
        """Calcula precisão da estimativa de tempo"""
        
        if not estimated_time or "average_seconds" not in estimated_time:
            return 0.0
        
        estimated_ms = estimated_time["average_seconds"] * 1000
        actual_seconds = actual_time_ms / 1000
        
        if estimated_ms == 0:
            return 0.0
        
        # Calcular precisão (quanto mais próximo de 1.0, melhor)
        accuracy = 1.0 - abs(actual_seconds - estimated_time["average_seconds"]) / estimated_time["average_seconds"]
        return max(0.0, min(1.0, accuracy))
    
    def _generate_quality_recommendations(
        self, 
        metrics: List[Dict[str, Any]], 
        correlations: Dict[str, Any]
    ) -> List[str]:
        """Gera recomendações baseadas na análise de qualidade"""
        
        recommendations = []
        
        avg_quality = sum(m["quality_score"] for m in metrics) / len(metrics)
        
        if avg_quality < 0.6:
            recommendations.append("🚨 Qualidade geral baixa - Revisar prompts e validação")
        
        # Analisar performance por agente
        agents = set(m["agent_used"] for m in metrics)
        for agent in agents:
            agent_metrics = [m for m in metrics if m["agent_used"] == agent]
            agent_avg_quality = sum(m["quality_score"] for m in agent_metrics) / len(agent_metrics)
            
            if agent_avg_quality < 0.5:
                recommendations.append(f"🔧 Agente {agent.upper()} com baixa qualidade - Otimizar prompts específicos")
        
        # Analisar correlações
        if "complexity_quality" in correlations:
            complex_quality = correlations["complexity_quality"]["complex_avg_quality"]
            simple_quality = correlations["complexity_quality"]["simple_avg_quality"]
            
            if complex_quality < simple_quality - 0.2:
                recommendations.append("📈 Queries complexas com qualidade baixa - Melhorar processamento completo")
        
        # Analisar problemas de qualidade
        quality_issues = [m for m in metrics if m["quality_issues_count"] > 2]
        if len(quality_issues) > len(metrics) * 0.3:
            recommendations.append("⚠️ Alto índice de problemas de qualidade - Revisar validação")
        
        # Analisar tempo de resposta
        avg_time = sum(m["processing_time_ms"] for m in metrics) / len(metrics)
        if avg_time > 15000:  # Mais de 15 segundos
            recommendations.append("⏱️ Tempo de resposta alto - Otimizar cache e processamento")
        
        return recommendations


# Instância singleton
behavior_monitor = BehaviorMonitor()