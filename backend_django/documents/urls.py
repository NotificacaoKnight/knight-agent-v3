from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.DocumentViewSet, basename='document')

urlpatterns = [
    path('stats/', views.document_stats, name='document_stats'),
    path('processing/', views.processing_status, name='processing_status'),
] + router.urls