from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Metadados da sessão
    message_count = models.IntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.preferred_name} - {self.title or f'Sessão {self.id}'}"

class ChatMessage(models.Model):
    MESSAGE_TYPES = [
        ('user', 'Usuário'),
        ('assistant', 'Assistente'),
        ('system', 'Sistema'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    
    # Metadados para mensagens do assistente
    context_used = models.JSONField(default=list, blank=True)  # Chunks usados como contexto
    search_query_id = models.IntegerField(null=True, blank=True)  # ID da busca RAG
    llm_provider = models.CharField(max_length=20, blank=True)
    llm_model = models.CharField(max_length=50, blank=True)
    
    # Performance
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    # Status da mensagem
    is_helpful = models.BooleanField(null=True, blank=True)  # Feedback do usuário
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."

class DocumentRequest(models.Model):
    """Requisições de documentos feitas durante o chat"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='document_requests')
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='document_requests')
    
    document_name = models.CharField(max_length=255)
    document_id = models.IntegerField(null=True, blank=True)  # ID do documento se encontrado
    
    status = models.CharField(max_length=20, choices=[
        ('requested', 'Solicitado'),
        ('found', 'Encontrado'),
        ('not_found', 'Não Encontrado'),
        ('downloaded', 'Baixado'),
    ], default='requested')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Solicitação: {self.document_name}"

class ChatFeedback(models.Model):
    """Feedback sobre respostas do chat com sistema de thumbs up/down"""
    RATING_CHOICES = [
        ('positive', 'Positivo'),
        ('negative', 'Negativo'),
    ]
    
    message = models.OneToOneField(ChatMessage, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    rating = models.CharField(max_length=20, choices=RATING_CHOICES, default='positive')
    comment = models.TextField(blank=True, help_text="Comentário opcional sobre o feedback")
    
    # Referência para a busca RAG se aplicável
    search_query_id = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback: {self.rating} - Mensagem {self.message.id}"