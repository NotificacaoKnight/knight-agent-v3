from rest_framework import serializers
from .models import User, UserSession

class UserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'preferred_name', 'profile_picture', 'theme_preference',
            'department', 'job_title', 'is_admin', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'username', 'email', 'is_admin', 'created_at', 'updated_at']
    
    def get_profile_picture(self, obj):
        """Safely handle profile_picture field with None values"""
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            return obj.profile_picture.url
        return None

class UserSessionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserSession
        fields = [
            'session_token', 'expires_at', 'created_at', 'is_active', 'user'
        ]
        read_only_fields = ['session_token', 'created_at']