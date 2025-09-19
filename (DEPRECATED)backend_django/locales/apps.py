"""
Configuration for locales app
"""
from django.apps import AppConfig

class LocalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'locales'
    verbose_name = 'Internationalization'