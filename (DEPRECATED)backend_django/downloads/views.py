import os
import uuid
from django.http import HttpResponse, Http404
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from documents.models import Document
from .models import DownloadRecord, DownloadSession
from .serializers import DownloadRecordSerializer, DownloadSessionSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_downloads(request):
    """Lista downloads disponíveis do usuário"""
    downloads = DownloadRecord.objects.filter(
        user=request.user,
        is_active=True,
        expires_at__gt=timezone.now()
    ).select_related('document')
    
    serializer = DownloadRecordSerializer(downloads, many=True)
    return Response({'downloads': serializer.data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_download(request):
    """Solicita download de um documento"""
    document_id = request.data.get('document_id')
    
    if not document_id:
        return Response({'error': 'document_id é obrigatório'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        document = Document.objects.get(
            id=document_id,
            is_downloadable=True,
            is_active=True
        )
        
        # Verificar se já existe download ativo
        existing_download = DownloadRecord.objects.filter(
            user=request.user,
            document=document,
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()
        
        if existing_download:
            serializer = DownloadRecordSerializer(existing_download)
            return Response({
                'message': 'Download já disponível',
                'download': serializer.data
            })
        
        # Criar novo registro de download
        download_token = str(uuid.uuid4())
        
        download_record = DownloadRecord.objects.create(
            user=request.user,
            document=document,
            download_token=download_token,
            file_name=document.original_filename,
            file_size=document.file_size,
            ip_address=get_client_ip(request)
        )
        
        serializer = DownloadRecordSerializer(download_record)
        
        return Response({
            'message': 'Download preparado com sucesso',
            'download': serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except Document.DoesNotExist:
        return Response({'error': 'Documento não encontrado ou não disponível para download'}, 
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_file(request, download_token):
    """Fazer download do arquivo"""
    try:
        download_record = DownloadRecord.objects.get(
            download_token=download_token,
            user=request.user,
            is_active=True
        )
        
        # Verificar se não expirou
        if download_record.is_expired:
            return Response({'error': 'Link de download expirado'}, 
                           status=status.HTTP_410_GONE)
        
        # Verificar se o arquivo existe
        if not download_record.document.file_path or not os.path.exists(download_record.document.file_path.path):
            return Response({'error': 'Arquivo não encontrado no servidor'}, 
                           status=status.HTTP_404_NOT_FOUND)
        
        # Atualizar estatísticas
        download_record.download_count += 1
        download_record.downloaded_at = timezone.now()
        download_record.save()
        
        # Servir arquivo
        file_path = download_record.document.file_path.path
        
        with open(file_path, 'rb') as file:
            response = HttpResponse(
                file.read(),
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{download_record.file_name}"'
            response['Content-Length'] = download_record.file_size
            
            return response
            
    except DownloadRecord.DoesNotExist:
        return Response({'error': 'Token de download inválido'}, 
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_download(request, download_token):
    """Remover download da lista"""
    try:
        download_record = DownloadRecord.objects.get(
            download_token=download_token,
            user=request.user
        )
        
        download_record.is_active = False
        download_record.save()
        
        return Response({'message': 'Download removido da lista'})
        
    except DownloadRecord.DoesNotExist:
        return Response({'error': 'Download não encontrado'}, 
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_stats(request):
    """Estatísticas de downloads do usuário"""
    user_downloads = DownloadRecord.objects.filter(user=request.user)
    
    stats = {
        'total_downloads': user_downloads.count(),
        'active_downloads': user_downloads.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).count(),
        'expired_downloads': user_downloads.filter(
            expires_at__lt=timezone.now()
        ).count(),
        'most_downloaded': user_downloads.filter(
            download_count__gt=0
        ).order_by('-download_count').first()
    }
    
    # Adicionar informações do documento mais baixado
    if stats['most_downloaded']:
        stats['most_downloaded'] = {
            'document_title': stats['most_downloaded'].document.title,
            'download_count': stats['most_downloaded'].download_count,
            'file_name': stats['most_downloaded'].file_name
        }
    
    return Response(stats)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cleanup_expired(request):
    """Limpar downloads expirados do usuário"""
    expired_count = DownloadRecord.objects.filter(
        user=request.user,
        expires_at__lt=timezone.now()
    ).update(is_active=False)
    
    return Response({
        'message': f'{expired_count} downloads expirados removidos',
        'expired_count': expired_count
    })

def get_client_ip(request):
    """Obter IP do cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip