from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UsefulLinkViewSet,
    DownloadableDocumentViewSet,
    ResourceCategoryViewSet,
    ResourceUsageViewSet
)

router = DefaultRouter()
router.register(r'useful-links', UsefulLinkViewSet, basename='usefullink')
router.register(r'downloadable-documents', DownloadableDocumentViewSet, basename='downloadadbledocument')
router.register(r'categories', ResourceCategoryViewSet, basename='resourcecategory')
router.register(r'usage', ResourceUsageViewSet, basename='resourceusage')

urlpatterns = [
    path('api/knowledge-resources/', include(router.urls)),
]