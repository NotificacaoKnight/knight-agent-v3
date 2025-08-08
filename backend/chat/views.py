from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import datetime
from django.db import models
from .models import ChatSession, ChatMessage, ChatFeedback
from .serializers import ChatSessionSerializer, ChatMessageSerializer, ChatFeedbackSerializer
from .services import KnightChatService

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """Enviar mensagem para o Knight"""
    message = request.data.get('message', '').strip()
    session_id = request.data.get('session_id')
    audio_file = request.FILES.get('audio_file')
    content_type = request.data.get('content_type', 'text')
    
    # Validar se há conteúdo (texto ou áudio)
    if not message and not audio_file:
        return Response({'error': 'Mensagem de texto ou arquivo de áudio é obrigatório'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        chat_service = KnightChatService()
        
        # Obter ou criar sessão
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                return Response({'error': 'Sessão não encontrada'}, 
                               status=status.HTTP_404_NOT_FOUND)
        else:
            session = chat_service.create_session(request.user)
        
        # Processar mensagem
        result = chat_service.process_message(
            message, 
            session,
            search_params=request.data.get('search_params', {}),
            audio_file=audio_file,
            content_type=content_type
        )
        
        # Estruturar resposta no formato esperado pelo frontend
        if result.get('success'):
            response_data = {
                'session_id': session.id,
                'session_title': session.title,
                'message': {
                    'id': str(result.get('message_id', '')),
                    'type': 'assistant',
                    'content': result.get('response', ''),
                    'timestamp': datetime.now().isoformat()
                },
                'user_message': result.get('user_message_data'),  # Dados da mensagem do usuário
                'context_used': result.get('context_used', 0) > 0,
                'response_time': result.get('response_time_ms', 0)
            }
        else:
            # Em caso de erro, ainda fornecer estrutura básica
            response_data = {
                'session_id': session.id,
                'session_title': session.title,
                'message': {
                    'id': str(datetime.now().timestamp()),
                    'type': 'assistant',
                    'content': result.get('response', 'Desculpe, ocorreu um erro.'),
                    'timestamp': datetime.now().isoformat()
                },
                'context_used': False,
                'response_time': result.get('response_time_ms', 0),
                'error': result.get('error')
            }
        
        return Response(response_data)
        
    except Exception as e:
        return Response({'error': str(e)}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sessions(request):
    """Listar sessões do usuário"""
    chat_service = KnightChatService()
    sessions = chat_service.get_user_sessions(request.user)
    
    return Response({'sessions': sessions})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def new_session(request):
    """Criar nova sessão de chat"""
    chat_service = KnightChatService()
    session = chat_service.create_session(request.user)
    
    return Response({
        'session_id': session.id,
        'title': session.title or f'Novo Chat {session.id}',
        'created_at': session.created_at
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_session_history(request, session_id):
    """Buscar histórico de uma sessão"""
    chat_service = KnightChatService()
    history = chat_service.get_session_history(session_id, request.user)
    
    if not history:
        return Response({'error': 'Sessão não encontrada'}, 
                       status=status.HTTP_404_NOT_FOUND)
    
    return Response({'messages': history})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_session(request, session_id):
    """Deletar sessão"""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        
        # Limpar arquivos de áudio antes de desativar a sessão
        chat_service = KnightChatService()
        chat_service._cleanup_session_audio_files(session)
        
        session.is_active = False
        session.save()
        
        return Response({'message': 'Sessão deletada com sucesso'})
        
    except ChatSession.DoesNotExist:
        return Response({'error': 'Sessão não encontrada'}, 
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_session_title(request, session_id):
    """Atualizar título da sessão"""
    title = request.data.get('title', '').strip()
    
    if not title:
        return Response({'error': 'Título não pode estar vazio'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        session.title = title
        session.save()
        
        return Response({'message': 'Título atualizado com sucesso'})
        
    except ChatSession.DoesNotExist:
        return Response({'error': 'Sessão não encontrada'}, 
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_feedback(request):
    """Enviar feedback sobre uma resposta (thumbs up/down)"""
    message_id = request.data.get('message_id')
    rating = request.data.get('rating')  # 'positive' ou 'negative'
    comment = request.data.get('comment', '')
    
    if not message_id or not rating:
        return Response({'error': 'message_id e rating são obrigatórios'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    if rating not in ['positive', 'negative']:
        return Response({'error': 'rating deve ser "positive" ou "negative"'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Verificar se a mensagem pertence ao usuário
        message = ChatMessage.objects.get(
            id=message_id,
            session__user=request.user,
            message_type='assistant'
        )
        
        # Criar ou atualizar feedback
        feedback, created = ChatFeedback.objects.update_or_create(
            message=message,
            user=request.user,
            defaults={
                'rating': rating,
                'comment': comment,
                'search_query_id': message.search_query_id
            }
        )
        
        # Atualizar flag na mensagem
        message.is_helpful = rating == 'positive'
        message.save()
        
        action = 'enviado' if created else 'atualizado'
        return Response({'message': f'Feedback {action} com sucesso'})
        
    except ChatMessage.DoesNotExist:
        return Response({'error': 'Mensagem não encontrada'}, 
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_stats(request):
    """Estatísticas do chat do usuário"""
    # Contar TODAS as sessões (ativas e inativas) para total histórico
    all_user_sessions = ChatSession.objects.filter(user=request.user)
    user_messages = ChatMessage.objects.filter(session__user=request.user)
    
    # Calcular duração média das sessões (em minutos)
    from django.db.models import F, ExpressionWrapper, DurationField, Avg
    from datetime import timedelta
    
    # Sessões com pelo menos uma mensagem para calcular duração
    sessions_with_duration = all_user_sessions.filter(
        last_message_at__isnull=False
    ).annotate(
        duration=ExpressionWrapper(
            F('last_message_at') - F('created_at'),
            output_field=DurationField()
        )
    )
    
    avg_duration = sessions_with_duration.aggregate(
        avg_duration=Avg('duration')
    )['avg_duration']
    
    # Converter para minutos
    avg_session_duration_minutes = 0
    if avg_duration:
        avg_session_duration_minutes = round(avg_duration.total_seconds() / 60, 1)
    
    stats = {
        'total_sessions': all_user_sessions.count(),  # Total histórico incluindo excluídas
        'total_messages': user_messages.count(),
        'helpful_responses': user_messages.filter(
            message_type='assistant',
            is_helpful=True
        ).count(),
        'avg_response_time': user_messages.filter(
            message_type='assistant',
            response_time_ms__isnull=False
        ).aggregate(
            avg_time=models.Avg('response_time_ms')
        )['avg_time'] or 0,
        'avg_session_duration_minutes': avg_session_duration_minutes  # Nova métrica
    }
    
    return Response(stats)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activity_chart_data(request):
    """Dados de atividade para gráfico histórico"""
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    
    # Definir período (últimos 90 dias, incluindo hoje) - usando timezone do Brasil
    from zoneinfo import ZoneInfo
    import pytz
    
    # Usar timezone do Brasil (GMT-3)
    brazil_tz = pytz.timezone('America/Sao_Paulo')
    now_brazil = timezone.now().astimezone(brazil_tz)
    today = now_brazil.date()
    start_date = today - timedelta(days=89)  # 89 + hoje = 90 dias
    end_date = today
    
    # Buscar sessões criadas por dia (no timezone do Brasil) - CONVERSAS = SESSÕES
    chat_data = ChatSession.objects.filter(
        user=request.user
    ).extra(
        select={'day': "date(chat_chatsession.created_at AT TIME ZONE 'America/Sao_Paulo')"},
        where=["date(chat_chatsession.created_at AT TIME ZONE 'America/Sao_Paulo') BETWEEN %s AND %s"],
        params=[start_date, end_date]
    ).values('day').annotate(
        conversas=Count('id')  # Contar sessões únicas por dia
    ).order_by('day')
    
    # Buscar documentos processados por dia (assumindo que há campo de data de processamento)
    from documents.models import Document
    doc_data = Document.objects.filter(
        uploaded_by=request.user,
        uploaded_at__date__gte=start_date,
        uploaded_at__date__lte=end_date,
        status='processed'
    ).extra(
        select={'day': 'date(documents_document.uploaded_at)'}
    ).values('day').annotate(
        documentos=Count('id')
    ).order_by('day')
    
    # Criar dicionário para facilitar merge
    chat_dict = {item['day'].strftime('%Y-%m-%d'): item['conversas'] for item in chat_data}
    doc_dict = {item['day'].strftime('%Y-%m-%d'): item['documentos'] for item in doc_data}
    
    # Gerar dados para todos os dias no período (incluindo hoje)
    activity_data = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        activity_data.append({
            'date': date_str,
            'conversas': chat_dict.get(date_str, 0),
            'documentos': doc_dict.get(date_str, 0)
        })
        current_date += timedelta(days=1)
    
    return Response(activity_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def access_count_metrics(request):
    """Métricas do sistema de contagem de acesso de documentos"""
    from .access_count_metrics import access_count_metrics
    
    try:
        # Coletar métricas do sistema
        system_metrics = access_count_metrics.collect_system_metrics()
        
        # Analisar padrões recentes de chat (parâmetro opcional)
        days = int(request.GET.get('days', 7))
        chat_patterns = access_count_metrics.analyze_recent_chat_patterns(days=days)
        
        # Relatório de precisão (parâmetro opcional)
        generate_precision = request.GET.get('precision_report', 'false').lower() == 'true'
        precision_report = None
        if generate_precision:
            precision_report = access_count_metrics.generate_precision_report()
        
        response_data = {
            'system_metrics': system_metrics,
            'chat_patterns_analysis': chat_patterns,
            'precision_report': precision_report,
            'collection_timestamp': datetime.now().isoformat(),
            'parameters': {
                'analysis_days': days,
                'precision_report_generated': generate_precision
            }
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response(
            {
                'error': f'Erro ao coletar métricas: {str(e)}',
                'system_metrics': None,
                'chat_patterns_analysis': None
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )