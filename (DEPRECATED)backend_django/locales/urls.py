"""
URLs para API de traduções
"""
from django.urls import path
from . import views

urlpatterns = [
    path('languages/', views.LanguagesAPIView.as_view(), name='languages'),
    path('translations/', views.TranslationsAPIView.as_view(), name='translations'),
    path('translations/<str:language>/', views.TranslationsAPIView.as_view(), name='translations_by_language'),
    path('user/language/', views.UserLanguageAPIView.as_view(), name='user_language'),
    path('cache/clear/', views.ClearTranslationCacheAPIView.as_view(), name='clear_cache'),
]