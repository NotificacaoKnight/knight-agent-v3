from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_downloads, name='list_downloads'),
    path('request/', views.request_download, name='request_download'),
    path('file/<str:download_token>/', views.download_file, name='download_file'),
    path('delete/<str:download_token>/', views.delete_download, name='delete_download'),
    path('stats/', views.download_stats, name='download_stats'),
    path('cleanup/', views.cleanup_expired, name='cleanup_expired'),
]