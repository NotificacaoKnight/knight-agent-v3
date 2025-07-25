from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import datetime
from django.db import models
from django.conf import settings
from .models import ChatSession, ChatMessage, ChatFeedback
from .serializers import ChatSessionSerializer, ChatMessageSerializer, ChatFeedbackSerializer
from .services import KnightChatService
from .transcription_service import transcription_service

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
                'context_used': result.get('context_used', 0) > 0,
                'sources': result.get('sources', []),
                'search_results_count': result.get('search_results', 0),
                'response_time': result.get('response_time_ms', 0),
                'provider_used': result.get('provider_used', ''),
                'agno_used': True  # Indicar que Agno foi usado
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transcribe_audio(request):
    """Transcrever áudio para texto usando Whisper"""
    
    if 'audio' not in request.FILES:
        return Response(
            {'error': 'Arquivo de áudio é obrigatório'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    audio_file = request.FILES['audio']
    
    # Verificar tamanho do arquivo (limite de 25MB)
    if audio_file.size > 25 * 1024 * 1024:
        return Response(
            {'error': 'Arquivo muito grande. Máximo 25MB permitido'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar se o serviço está disponível
    if not transcription_service.is_available():
        return Response(
            {'error': 'Serviço de transcrição não configurado'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        # Ler conteúdo do arquivo
        audio_content = audio_file.read()
        
        # Transcrever áudio
        result = transcription_service.transcribe_audio(
            audio_file_content=audio_content,
            filename=audio_file.name,
            language='pt'
        )
        
        if result['success']:
            return Response({
                'transcription': result['transcription'],
                'language': result['language'],
                'model': result['model']
            })
        else:
            return Response(
                {'error': result['error']}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        return Response(
            {'error': f'Erro ao processar áudio: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_audio_message(request):
    """Enviar mensagem de áudio (transcreve e processa)"""
    
    if 'audio' not in request.FILES:
        return Response(
            {'error': 'Arquivo de áudio é obrigatório'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    audio_file = request.FILES['audio']
    session_id = request.data.get('session_id')
    
    # Verificar tamanho do arquivo
    if audio_file.size > 25 * 1024 * 1024:
        return Response(
            {'error': 'Arquivo muito grande. Máximo 25MB permitido'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar se o serviço está disponível
    if not transcription_service.is_available():
        return Response(
            {'error': 'Serviço de transcrição não configurado'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        # Transcrever áudio
        audio_content = audio_file.read()
        print(f"Recebido áudio: {audio_file.name}, Tamanho: {len(audio_content)} bytes")
        
        transcription_result = transcription_service.transcribe_audio(
            audio_file_content=audio_content,
            filename=audio_file.name,
            language='pt'
        )
        
        print(f"Resultado da transcrição: {transcription_result}")
        
        if not transcription_result['success']:
            print(f"Erro na transcrição: {transcription_result['error']}")
            return Response(
                {'error': transcription_result['error']}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        transcribed_text = transcription_result['transcription']
        
        if not transcribed_text.strip():
            return Response(
                {'error': 'Não foi possível transcrever o áudio'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Se for áudio vazio, retornar sem processar no chat
        if transcribed_text == '[ÁUDIO_VAZIO]':
            return Response({
                'session_id': session_id or '',
                'session_title': 'Chat de Áudio',
                'transcription': '[ÁUDIO_VAZIO]',
                'message': {
                    'id': str(datetime.now().timestamp()),
                    'type': 'system',
                    'content': 'Não foi detectada fala no áudio. Por favor, fale próximo ao microfone.',
                    'timestamp': datetime.now().isoformat()
                },
                'context_used': False,
                'response_time': 0,
                'audio_processed': True
            })
        
        # Processar como mensagem de texto normal
        chat_service = KnightChatService()
        
        # Obter ou criar sessão
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                return Response(
                    {'error': 'Sessão não encontrada'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            session = chat_service.create_session(request.user)
        
        # Processar mensagem transcrita
        result = chat_service.process_message(
            transcribed_text, 
            session,
            search_params=request.data.get('search_params', {})
        )
        
        # Estruturar resposta
        if result.get('success'):
            response_data = {
                'session_id': session.id,
                'session_title': session.title,
                'transcription': transcribed_text,
                'message': {
                    'id': str(result.get('message_id', '')),
                    'type': 'assistant',
                    'content': result.get('response', ''),
                    'timestamp': datetime.now().isoformat()
                },
                'context_used': result.get('context_used', 0) > 0,
                'sources': result.get('sources', []),
                'search_results_count': result.get('search_results', 0),
                'response_time': result.get('response_time_ms', 0),
                'provider_used': result.get('provider_used', ''),
                'agno_used': True,
                'audio_processed': True
            }
        else:
            response_data = {
                'session_id': session.id,
                'session_title': session.title,
                'transcription': transcribed_text,
                'message': {
                    'id': str(datetime.now().timestamp()),
                    'type': 'assistant',
                    'content': result.get('response', 'Desculpe, ocorreu um erro.'),
                    'timestamp': datetime.now().isoformat()
                },
                'context_used': False,
                'response_time': result.get('response_time_ms', 0),
                'error': result.get('error'),
                'audio_processed': True
            }
        
        return Response(response_data)
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"=== ERRO COMPLETO NO ENDPOINT DE ÁUDIO ===")
        print(f"Erro: {str(e)}")
        print(f"Traceback: {error_traceback}")
        print("=" * 50)
        
        return Response(
            {
                'error': f'Erro ao processar áudio: {str(e)}',
                'debug_info': error_traceback if getattr(settings, 'DEBUG', False) else None
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )