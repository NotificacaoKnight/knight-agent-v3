from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    microsoft_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    preferred_name = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    theme_preference = models.CharField(
        max_length=10,
        choices=[('light', 'Light'), ('dark', 'Dark')],
        default='light'
    )
    department = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.preferred_name or self.username or self.email

class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=255, unique=True)
    microsoft_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.session_token[:10]}..."