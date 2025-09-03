from rest_framework import serializers
from .models import ChatSession, ChatMessage, ChatFeedback, DocumentRequest

class ChatSessionSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(read_only=True)
    last_message_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'title', 'created_at', 'updated_at', 'is_active',
            'message_count', 'last_message_at', 'last_message_preview'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'message_count', 'last_message_at']
    
    def get_last_message_preview(self, obj):
        last_message = obj.messages.filter(message_type='user').last()
        if last_message:
            return last_message.content[:100] + '...' if len(last_message.content) > 100 else last_message.content
        return ''

class ChatMessageSerializer(serializers.ModelSerializer):
    context_count = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()
    agent_emoji = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'message_type', 'content_type', 'content', 'created_at',
            'context_count', 'llm_provider', 'llm_model',
            'response_time_ms', 'is_helpful', 'audio_file', 'audio_url',
            'audio_duration', 'transcription', 'agent_type', 'is_handoff', 'agent_emoji'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_context_count(self, obj):
        return len(obj.context_used) if obj.context_used else 0
    
    def get_audio_url(self, obj):
        if obj.audio_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.audio_file.url)
        return None
    
    def get_agent_emoji(self, obj):
        """Retorna emoji identificador do agente"""
        from .agent_detector import agent_detector
        return agent_detector.get_agent_emoji(obj.agent_type)

class DocumentRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentRequest
        fields = [
            'id', 'document_name', 'document_id', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class ChatFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatFeedback
        fields = [
            'id', 'message', 'feedback_type', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']