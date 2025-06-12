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
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'message_type', 'content', 'created_at',
            'context_count', 'llm_provider', 'llm_model',
            'response_time_ms', 'is_helpful'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_context_count(self, obj):
        return len(obj.context_used) if obj.context_used else 0

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