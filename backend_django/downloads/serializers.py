from rest_framework import serializers
from .models import DownloadRecord, DownloadSession

class DownloadRecordSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    time_remaining_hours = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = DownloadRecord
        fields = [
            'id', 'download_token', 'document_title', 'file_name', 
            'file_size', 'file_size_mb', 'created_at', 'expires_at',
            'downloaded_at', 'download_count', 'is_active', 'is_expired',
            'time_remaining_hours'
        ]
        read_only_fields = [
            'id', 'download_token', 'created_at', 'expires_at',
            'downloaded_at', 'download_count'
        ]
    
    def get_time_remaining_hours(self, obj):
        time_remaining = obj.time_remaining
        return int(time_remaining.total_seconds() / 3600) if time_remaining else 0
    
    def get_file_size_mb(self, obj):
        return round(obj.file_size / (1024 * 1024), 2) if obj.file_size else 0

class DownloadSessionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.preferred_name', read_only=True)
    
    class Meta:
        model = DownloadSession
        fields = [
            'id', 'session_token', 'user_name', 'created_at', 'last_access',
            'downloads_count', 'is_active'
        ]
        read_only_fields = ['id', 'session_token', 'created_at', 'last_access']