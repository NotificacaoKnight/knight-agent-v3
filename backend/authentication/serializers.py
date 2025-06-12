from rest_framework import serializers
from .models import User, UserSession

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'preferred_name', 'profile_picture', 'theme_preference',
            'department', 'job_title', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'username', 'email', 'created_at', 'updated_at']

class UserSessionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserSession
        fields = [
            'session_token', 'expires_at', 'created_at', 'is_active', 'user'
        ]
        read_only_fields = ['session_token', 'created_at']