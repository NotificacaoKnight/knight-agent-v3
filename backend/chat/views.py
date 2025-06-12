from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ChatSession, ChatMessage, ChatFeedback
from .serializers import ChatSessionSerializer, ChatMessageSerializer, ChatFeedbackSerializer
from .services import KnightChatService

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """Enviar mensagem para o Knight"""
    message = request.data.get('message', '').strip()
    session_id = request.data.get('session_id')
    
    if not message:
        return Response({'error': 'Mensagem não pode estar vazia'}, 
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
            search_params=request.data.get('search_params', {})
        )
        
        return Response({
            'session_id': session.id,
            'session_title': session.title,
            **result
        })
        
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
    """Enviar feedback sobre uma resposta"""
    message_id = request.data.get('message_id')
    feedback_type = request.data.get('feedback_type')
    comment = request.data.get('comment', '')
    
    if not message_id or not feedback_type:
        return Response({'error': 'message_id e feedback_type são obrigatórios'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Verificar se a mensagem pertence ao usuário
        message = ChatMessage.objects.get(
            id=message_id,
            session__user=request.user,
            message_type='assistant'
        )
        
        # Criar ou atualizar feedback
        feedback, created = ChatFeedback.objects.get_or_create(
            message=message,
            defaults={
                'user': request.user,
                'feedback_type': feedback_type,
                'comment': comment
            }
        )
        
        if not created:
            feedback.feedback_type = feedback_type
            feedback.comment = comment
            feedback.save()
        
        # Atualizar flag na mensagem
        message.is_helpful = feedback_type == 'helpful'
        message.save()
        
        return Response({'message': 'Feedback enviado com sucesso'})
        
    except ChatMessage.DoesNotExist:
        return Response({'error': 'Mensagem não encontrada'}, 
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_stats(request):
    """Estatísticas do chat do usuário"""
    user_sessions = ChatSession.objects.filter(user=request.user, is_active=True)
    user_messages = ChatMessage.objects.filter(session__user=request.user)
    
    stats = {
        'total_sessions': user_sessions.count(),
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
        )['avg_time'] or 0
    }
    
    return Response(stats)