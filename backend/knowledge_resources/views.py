from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from .models import UsefulLink, DownloadableDocument, ResourceCategory, ResourceUsage
from .serializers import (
    UsefulLinkSerializer, UsefulLinkListSerializer,
    DownloadableDocumentSerializer, DownloadableDocumentListSerializer,
    ResourceCategorySerializer, ResourceUsageSerializer,
    LinkStatsSerializer, DocumentStatsSerializer
)

class UsefulLinkViewSet(viewsets.ModelViewSet):
    """API para gerenciamento de links úteis"""
    queryset = UsefulLink.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UsefulLinkListSerializer
        return UsefulLinkSerializer
    
    def perform_create(self, serializer):
        """Define o criador do link como o usuário atual"""
        serializer.save(created_by=self.request.user)
    
    def get_queryset(self):
        """Filtragem opcional por categoria e status"""
        queryset = UsefulLink.objects.all()
        category = self.request.query_params.get('category', None)
        active_only = self.request.query_params.get('active', None)
        
        if category:
            queryset = queryset.filter(category=category)
        if active_only == 'true':
            queryset = queryset.filter(is_active=True)
            
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def increment_send_count(self, request, pk=None):
        """Incrementa contador quando IA envia o link"""
        link = self.get_object()
        link.send_count += 1
        link.save()
        
        # Registra o uso
        ResourceUsage.objects.create(
            user=request.user,
            resource_type='link',
            resource_id=link.id,
            action='shared',
            query_context=request.data.get('context', ''),
            chat_session_id=request.data.get('chat_session_id'),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({'success': True, 'send_count': link.send_count})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estatísticas dos links úteis"""
        total_links = UsefulLink.objects.count()
        active_links = UsefulLink.objects.filter(is_active=True).count()
        total_sends = UsefulLink.objects.aggregate(total=Sum('send_count'))['total'] or 0
        
        # Top categorias
        top_categories = list(
            UsefulLink.objects.filter(is_active=True)
            .values('category')
            .annotate(count=Count('id'), total_sends=Sum('send_count'))
            .order_by('-total_sends')[:5]
        )
        
        # Atividade recente (últimos 7 dias)
        week_ago = timezone.now() - timedelta(days=7)
        recent_activity = list(
            ResourceUsage.objects.filter(
                resource_type='link',
                created_at__gte=week_ago
            ).values('action').annotate(count=Count('id'))
        )
        
        stats_data = {
            'total_links': total_links,
            'active_links': active_links,
            'total_sends': total_sends,
            'top_categories': top_categories,
            'recent_activity': recent_activity
        }
        
        serializer = LinkStatsSerializer(stats_data)
        return Response(serializer.data)

class DownloadableDocumentViewSet(viewsets.ModelViewSet):
    """API para gerenciamento de documentos baixáveis"""
    queryset = DownloadableDocument.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DownloadableDocumentListSerializer
        return DownloadableDocumentSerializer
    
    def perform_create(self, serializer):
        """Define o criador do documento como o usuário atual"""
        serializer.save(created_by=self.request.user)
    
    def get_queryset(self):
        """Filtragem opcional por categoria e status"""
        queryset = DownloadableDocument.objects.all()
        category = self.request.query_params.get('category', None)
        active_only = self.request.query_params.get('active', None)
        file_type = self.request.query_params.get('file_type', None)
        
        if category:
            queryset = queryset.filter(category=category)
        if active_only == 'true':
            queryset = queryset.filter(is_active=True)
        if file_type:
            queryset = queryset.filter(file_type=file_type)
            
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def increment_download_count(self, request, pk=None):
        """Incrementa contador de download"""
        document = self.get_object()
        document.download_count += 1
        document.save()
        
        # Registra o uso
        ResourceUsage.objects.create(
            user=request.user,
            resource_type='document',
            resource_id=document.id,
            action='downloaded',
            query_context=request.data.get('context', ''),
            chat_session_id=request.data.get('chat_session_id'),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({'success': True, 'download_count': document.download_count})
    
    @action(detail=True, methods=['post'])
    def increment_share_count(self, request, pk=None):
        """Incrementa contador quando IA compartilha o documento"""
        document = self.get_object()
        document.share_count += 1
        document.save()
        
        # Registra o uso
        ResourceUsage.objects.create(
            user=request.user,
            resource_type='document',
            resource_id=document.id,
            action='shared',
            query_context=request.data.get('context', ''),
            chat_session_id=request.data.get('chat_session_id'),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({'success': True, 'share_count': document.share_count})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estatísticas dos documentos baixáveis"""
        total_documents = DownloadableDocument.objects.count()
        active_documents = DownloadableDocument.objects.filter(is_active=True).count()
        total_downloads = DownloadableDocument.objects.aggregate(total=Sum('download_count'))['total'] or 0
        total_shares = DownloadableDocument.objects.aggregate(total=Sum('share_count'))['total'] or 0
        
        # Top categorias
        top_categories = list(
            DownloadableDocument.objects.filter(is_active=True)
            .values('category')
            .annotate(
                count=Count('id'),
                total_downloads=Sum('download_count'),
                total_shares=Sum('share_count')
            )
            .order_by('-total_downloads')[:5]
        )
        
        # Atividade recente (últimos 7 dias)
        week_ago = timezone.now() - timedelta(days=7)
        recent_activity = list(
            ResourceUsage.objects.filter(
                resource_type='document',
                created_at__gte=week_ago
            ).values('action').annotate(count=Count('id'))
        )
        
        stats_data = {
            'total_documents': total_documents,
            'active_documents': active_documents,
            'total_downloads': total_downloads,
            'total_shares': total_shares,
            'top_categories': top_categories,
            'recent_activity': recent_activity
        }
        
        serializer = DocumentStatsSerializer(stats_data)
        return Response(serializer.data)

class ResourceCategoryViewSet(viewsets.ModelViewSet):
    """API para gerenciamento de categorias"""
    queryset = ResourceCategory.objects.all()
    serializer_class = ResourceCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Ordena por ordem definida"""
        return ResourceCategory.objects.filter(is_active=True).order_by('order', 'name')

class ResourceUsageViewSet(viewsets.ReadOnlyModelViewSet):
    """API read-only para visualizar estatísticas de uso"""
    queryset = ResourceUsage.objects.all()
    serializer_class = ResourceUsageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtragem por tipo de recurso e período"""
        queryset = ResourceUsage.objects.all()
        resource_type = self.request.query_params.get('resource_type', None)
        resource_id = self.request.query_params.get('resource_id', None)
        days = self.request.query_params.get('days', None)
        
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)
        if days:
            days_ago = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(created_at__gte=days_ago)
            
        return queryset.order_by('-created_at')
