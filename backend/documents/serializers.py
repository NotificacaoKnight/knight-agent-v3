from rest_framework import serializers
from .models import Document, DocumentChunk, ProcessingJob

class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    chunks_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'original_filename', 'file_type', 'file_size', 'file_size_mb',
            'status', 'processing_error', 'is_downloadable', 'is_active',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at', 'processed_at', 'updated_at',
            'metadata', 'chunks_count'
        ]
        read_only_fields = [
            'id', 'file_size', 'checksum', 'status', 'processing_error',
            'uploaded_by', 'uploaded_at', 'processed_at', 'updated_at', 'metadata'
        ]
    
    def get_uploaded_by_name(self, obj):
        """Método seguro para obter nome do usuário"""
        if obj.uploaded_by:
            return obj.uploaded_by.preferred_name or obj.uploaded_by.username or obj.uploaded_by.email
        return 'Sistema'
    
    def get_file_size_mb(self, obj):
        return round(obj.file_size / (1024 * 1024), 2) if obj.file_size else 0
    
    def get_chunks_count(self, obj):
        try:
            return obj.chunks.count()
        except Exception:
            return 0

class DocumentChunkSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    
    class Meta:
        model = DocumentChunk
        fields = [
            'id', 'document', 'document_title', 'chunk_index', 'content',
            'chunk_size', 'start_position', 'end_position',
            'page_number', 'section_title', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class ProcessingJobSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    
    class Meta:
        model = ProcessingJob
        fields = [
            'id', 'document', 'document_title', 'job_type', 'status',
            'started_at', 'completed_at', 'error_message',
            'config', 'result', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']