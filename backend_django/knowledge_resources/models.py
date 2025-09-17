from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UsefulLink(models.Model):
    """Links úteis que o Knight Agent pode compartilhar com colaboradores"""
    title = models.CharField(max_length=255, help_text="Título descritivo do link")
    url = models.URLField(help_text="URL do link")
    description = models.TextField(blank=True, help_text="Descrição do conteúdo do link para os colaboradores")
    ai_guidance = models.TextField(blank=True, help_text="Orientações para a IA sobre quando compartilhar este link")
    category = models.CharField(max_length=100, help_text="Categoria do link (RH, TI, Compliance, etc.)")
    
    # Status e controle
    is_active = models.BooleanField(default=True, help_text="Se o link está ativo para ser compartilhado")
    
    # Métricas de uso
    send_count = models.IntegerField(default=0, help_text="Número de vezes que o link foi enviado pela IA")
    
    # Metadados
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_links')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Tags para melhor organização (opcional)
    tags = models.JSONField(default=list, blank=True, help_text="Tags para facilitar busca e organização")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.category})"

class DownloadableDocument(models.Model):
    """Documentos/formulários que podem ser baixados pelos colaboradores"""
    title = models.CharField(max_length=255, help_text="Título do documento")
    description = models.TextField(blank=True, help_text="Descrição do documento e como deve ser usado")
    ai_guidance = models.TextField(blank=True, help_text="Orientações para a IA sobre quando disponibilizar este documento")
    category = models.CharField(max_length=100, help_text="Categoria do documento (RH, Financeiro, Vendas, etc.)")
    
    # Arquivo
    file = models.FileField(upload_to='downloadable_docs/', help_text="Arquivo do documento")
    file_name = models.CharField(max_length=255, help_text="Nome original do arquivo")
    file_size = models.BigIntegerField(help_text="Tamanho do arquivo em bytes")
    file_type = models.CharField(max_length=50, help_text="Tipo do arquivo (pdf, docx, xlsx, etc.)")
    
    # Status e controle
    is_active = models.BooleanField(default=True, help_text="Se o documento está ativo para download")
    
    # Métricas de uso
    download_count = models.IntegerField(default=0, help_text="Número de vezes que foi baixado")
    share_count = models.IntegerField(default=0, help_text="Número de vezes que foi compartilhado pela IA")
    
    # Metadados
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_docs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Tags para melhor organização (opcional)
    tags = models.JSONField(default=list, blank=True, help_text="Tags para facilitar busca e organização")
    
    # Configurações de acesso
    requires_approval = models.BooleanField(default=False, help_text="Se requer aprovação antes do download")
    expiry_date = models.DateTimeField(null=True, blank=True, help_text="Data de expiração do documento")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['file_type']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.file_type.upper()})"
    
    def save(self, *args, **kwargs):
        """Override para extrair metadados do arquivo"""
        if self.file:
            if not self.file_name:
                self.file_name = self.file.name
            if not self.file_size:
                self.file_size = self.file.size
            if not self.file_type:
                import os
                self.file_type = os.path.splitext(self.file.name)[1][1:].lower()
        super().save(*args, **kwargs)

class ResourceCategory(models.Model):
    """Categorias para organizar links e documentos"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color_code = models.CharField(max_length=7, blank=True, help_text="Código de cor hex para UI (#FFFFFF)")
    icon = models.CharField(max_length=50, blank=True, help_text="Nome do ícone para UI")
    
    # Ordem de exibição
    order = models.IntegerField(default=0, help_text="Ordem de exibição (menor valor aparece primeiro)")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Categoria de Recurso"
        verbose_name_plural = "Categorias de Recursos"
    
    def __str__(self):
        return self.name

class ResourceUsage(models.Model):
    """Log de uso de recursos (links e documentos) para análise"""
    RESOURCE_TYPES = [
        ('link', 'Link Útil'),
        ('document', 'Documento'),
    ]
    
    ACTION_TYPES = [
        ('shared', 'Compartilhado pela IA'),
        ('clicked', 'Clicado pelo usuário'),
        ('downloaded', 'Baixado pelo usuário'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    resource_id = models.IntegerField(help_text="ID do link ou documento")
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    
    # Contexto
    chat_session_id = models.IntegerField(null=True, blank=True, help_text="ID da sessão de chat relacionada")
    query_context = models.TextField(blank=True, help_text="Contexto da pergunta que levou à ação")
    
    # Metadados
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['user', 'action']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.resource_type} {self.resource_id}"
