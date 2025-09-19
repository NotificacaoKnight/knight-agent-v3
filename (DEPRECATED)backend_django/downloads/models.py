from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from documents.models import Document

User = get_user_model()

class DownloadRecord(models.Model):
    """Registro de downloads de documentos"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='downloads')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='download_records')
    
    # Metadados do download
    download_token = models.CharField(max_length=64, unique=True)
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    downloaded_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    download_count = models.IntegerField(default=0)
    
    # IP do usuário
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'document', 'created_at']
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.conf import settings
            retention_days = getattr(settings, 'DOWNLOADS_RETENTION_DAYS', 7)
            self.expires_at = timezone.now() + timedelta(days=retention_days)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def time_remaining(self):
        if self.is_expired:
            return timedelta(0)
        return self.expires_at - timezone.now()
    
    def __str__(self):
        return f"{self.user.preferred_name} - {self.file_name}"

class DownloadSession(models.Model):
    """Sessão de downloads do usuário"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='download_sessions')
    session_token = models.CharField(max_length=64, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_access = models.DateTimeField(auto_now=True)
    
    # Metadados
    downloads_count = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-last_access']
    
    def __str__(self):
        return f"Sessão {self.user.preferred_name} - {self.session_token[:10]}"