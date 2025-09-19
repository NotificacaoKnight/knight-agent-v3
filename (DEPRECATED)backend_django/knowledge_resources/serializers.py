from rest_framework import serializers
from .models import UsefulLink, DownloadableDocument, ResourceCategory, ResourceUsage

class ResourceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceCategory
        fields = ['id', 'name', 'description', 'color_code', 'icon', 'order', 'is_active']

class UsefulLinkSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.preferred_name', read_only=True)
    
    class Meta:
        model = UsefulLink
        fields = [
            'id', 'title', 'url', 'description', 'ai_guidance', 'category',
            'is_active', 'send_count', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'tags'
        ]
        read_only_fields = ['id', 'send_count', 'created_at', 'updated_at', 'created_by_name']

class UsefulLinkListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listagem"""
    created_by_name = serializers.CharField(source='created_by.preferred_name', read_only=True)
    
    class Meta:
        model = UsefulLink
        fields = [
            'id', 'title', 'url', 'description', 'ai_guidance', 'category', 
            'is_active', 'send_count', 'created_by_name', 'created_at'
        ]

class DownloadableDocumentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.preferred_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DownloadableDocument
        fields = [
            'id', 'title', 'description', 'ai_guidance', 'category',
            'file', 'file_url', 'file_name', 'file_size', 'file_type',
            'is_active', 'download_count', 'share_count',
            'requires_approval', 'expiry_date',
            'created_by', 'created_by_name', 'created_at', 'updated_at', 'tags'
        ]
        read_only_fields = [
            'id', 'file_name', 'file_size', 'file_type', 'file_url',
            'download_count', 'share_count', 'created_at', 'updated_at', 'created_by_name'
        ]
    
    def get_file_url(self, obj):
        """Retorna URL do arquivo se existe"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

class DownloadableDocumentListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listagem"""
    created_by_name = serializers.CharField(source='created_by.preferred_name', read_only=True)
    
    class Meta:
        model = DownloadableDocument
        fields = [
            'id', 'title', 'description', 'ai_guidance', 'category', 'file_type', 
            'file_size', 'is_active', 'download_count', 'created_by_name', 'created_at'
        ]

class ResourceUsageSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.preferred_name', read_only=True)
    
    class Meta:
        model = ResourceUsage
        fields = [
            'id', 'user', 'user_name', 'resource_type', 'resource_id',
            'action', 'chat_session_id', 'query_context',
            'ip_address', 'user_agent', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'user_name']

# Serializers para estatísticas e dashboards
class LinkStatsSerializer(serializers.Serializer):
    total_links = serializers.IntegerField()
    active_links = serializers.IntegerField()
    total_sends = serializers.IntegerField()
    top_categories = serializers.ListField()
    recent_activity = serializers.ListField()

class DocumentStatsSerializer(serializers.Serializer):
    total_documents = serializers.IntegerField()
    active_documents = serializers.IntegerField()
    total_downloads = serializers.IntegerField()
    total_shares = serializers.IntegerField()
    top_categories = serializers.ListField()
    recent_activity = serializers.ListField()