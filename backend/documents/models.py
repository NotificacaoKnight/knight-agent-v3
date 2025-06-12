from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Document(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('processed', 'Processado'),
        ('error', 'Erro'),
    ]
    
    title = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='documents/')
    processed_path = models.CharField(max_length=500, blank=True)
    markdown_content = models.TextField(blank=True)
    file_type = models.CharField(max_length=50)
    file_size = models.BigIntegerField()
    checksum = models.CharField(max_length=64)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processing_error = models.TextField(blank=True)
    
    is_downloadable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Metadados extraídos
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.title

class DocumentChunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.IntegerField()
    content = models.TextField()
    embedding = models.JSONField(null=True, blank=True)  # Será usado para armazenar embeddings
    chunk_size = models.IntegerField()
    start_position = models.IntegerField(default=0)
    end_position = models.IntegerField(default=0)
    
    # Metadados do chunk
    page_number = models.IntegerField(null=True, blank=True)
    section_title = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']
    
    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"

class ProcessingJob(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Na Fila'),
        ('processing', 'Processando'),
        ('completed', 'Concluído'),
        ('failed', 'Falhado'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='processing_jobs')
    job_type = models.CharField(max_length=50)  # 'markdown_conversion', 'chunking', 'embedding'
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Configurações do job
    config = models.JSONField(default=dict, blank=True)
    
    # Resultados
    result = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.document.title} - {self.job_type} ({self.status})"