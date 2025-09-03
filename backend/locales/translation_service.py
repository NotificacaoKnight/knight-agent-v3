"""
Serviço central de traduções para o Knight Agent
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import get_language, activate
import logging

from .languages import (
    get_supported_languages, 
    DEFAULT_LANGUAGE, 
    is_supported_language,
    get_django_code,
    get_frontend_code
)

logger = logging.getLogger(__name__)

class TranslationService:
    """Gerenciador central de traduções"""
    
    def __init__(self):
        self.base_path = Path(settings.BASE_DIR) / 'locales'
        self.translations_path = self.base_path / 'translations'
        self.ai_prompts_path = self.base_path / 'ai_prompts'
        self._cache_timeout = 3600  # 1 hora
    
    def _get_cache_key(self, namespace: str, language: str, category: str) -> str:
        """Gera chave do cache"""
        return f"i18n:{namespace}:{language}:{category}"
    
    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Carrega arquivo JSON de tradução"""
        try:
            if not file_path.exists():
                logger.warning(f"Translation file not found: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading translation file {file_path}: {e}")
            return {}
    
    def _get_language_code(self, language: str) -> str:
        """Normaliza código do idioma"""
        if not language:
            return DEFAULT_LANGUAGE
            
        # Converte códigos Django para frontend se necessário
        if language in ['pt-br', 'en', 'es', 'sv']:
            language = get_frontend_code(language)
        
        # Verifica se é suportado
        if not is_supported_language(language):
            logger.warning(f"Unsupported language: {language}, falling back to {DEFAULT_LANGUAGE}")
            return DEFAULT_LANGUAGE
            
        return language
    
    def get_translations(self, language: str, category: str = 'common') -> Dict[str, Any]:
        """
        Carrega traduções para um idioma e categoria específicos
        
        Args:
            language: Código do idioma (pt-BR, en-US, etc.)
            category: Categoria (common, api, errors, validation)
        """
        language = self._get_language_code(language)
        cache_key = self._get_cache_key('translations', language, category)
        
        # Tenta buscar do cache
        cached_translations = cache.get(cache_key)
        if cached_translations is not None:
            return cached_translations
        
        # Carrega do arquivo
        language_folder = language.replace('-', '_')
        file_path = self.translations_path / language_folder / f"{category}.json"
        translations = self._load_json_file(file_path)
        
        # Se não encontrou, tenta o idioma padrão
        if not translations and language != DEFAULT_LANGUAGE:
            default_folder = DEFAULT_LANGUAGE.replace('-', '_')
            fallback_path = self.translations_path / default_folder / f"{category}.json"
            translations = self._load_json_file(fallback_path)
            logger.info(f"Used fallback translations for {language}/{category}")
        
        # Salva no cache
        cache.set(cache_key, translations, self._cache_timeout)
        return translations
    
    def get_ai_prompts(self, language: str, category: str = 'rag_prompts') -> Dict[str, Any]:
        """
        Carrega prompts de IA para um idioma específico
        
        Args:
            language: Código do idioma
            category: Categoria (rag_prompts, agent_prompts, system_prompts)
        """
        language = self._get_language_code(language)
        cache_key = self._get_cache_key('ai_prompts', language, category)
        
        # Tenta buscar do cache
        cached_prompts = cache.get(cache_key)
        if cached_prompts is not None:
            return cached_prompts
        
        # Carrega do arquivo
        language_folder = language.replace('-', '_')
        file_path = self.ai_prompts_path / language_folder / f"{category}.json"
        prompts = self._load_json_file(file_path)
        
        # Se não encontrou, tenta o idioma padrão
        if not prompts and language != DEFAULT_LANGUAGE:
            default_folder = DEFAULT_LANGUAGE.replace('-', '_')
            fallback_path = self.ai_prompts_path / default_folder / f"{category}.json"
            prompts = self._load_json_file(fallback_path)
            logger.info(f"Used fallback AI prompts for {language}/{category}")
        
        # Salva no cache
        cache.set(cache_key, prompts, self._cache_timeout)
        return prompts
    
    def get_translation(self, key: str, language: str = None, category: str = 'common', **kwargs) -> str:
        """
        Obtém uma tradução específica
        
        Args:
            key: Chave da tradução
            language: Idioma (usa o atual se não especificado)
            category: Categoria da tradução
            **kwargs: Variáveis para interpolação
        """
        if not language:
            language = get_language() or DEFAULT_LANGUAGE
            language = get_frontend_code(language)
        
        translations = self.get_translations(language, category)
        
        # Busca a tradução
        translation = translations.get(key)
        if translation is None:
            logger.warning(f"Translation not found: {key} in {language}/{category}")
            return key  # Retorna a chave se não encontrou tradução
        
        # Aplica interpolação se há variáveis
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except Exception as e:
                logger.error(f"Translation interpolation error for {key}: {e}")
        
        return translation
    
    def get_all_translations_for_frontend(self, language: str) -> Dict[str, Dict[str, Any]]:
        """
        Carrega todas as traduções de um idioma para enviar ao frontend
        """
        language = self._get_language_code(language)
        
        categories = ['common', 'navigation', 'dashboard', 'chat', 'documents', 'settings', 'errors']
        all_translations = {}
        
        for category in categories:
            translations = self.get_translations(language, category)
            if translations:
                all_translations[category] = translations
        
        return all_translations
    
    def clear_cache(self, language: str = None, category: str = None):
        """Limpa cache de traduções"""
        if language and category:
            # Limpa categoria específica de um idioma
            cache_key = self._get_cache_key('translations', language, category)
            cache.delete(cache_key)
            cache_key = self._get_cache_key('ai_prompts', language, category)
            cache.delete(cache_key)
        else:
            # Limpa todo o cache de i18n
            cache.delete_pattern("i18n:*")
        
        logger.info(f"Cleared translation cache for language={language}, category={category}")

# Instância singleton
translation_service = TranslationService()