"""
API Views para gerenciamento de traduções
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import activate, get_language
from django.contrib.auth.models import AnonymousUser
import logging

from .translation_service import translation_service
from .languages import get_supported_languages, is_supported_language, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

class LanguagesAPIView(APIView):
    """Lista idiomas suportados"""
    
    def get(self, request):
        """Retorna lista de idiomas suportados"""
        try:
            languages = []
            for code, name, flag in get_supported_languages():
                languages.append({
                    'code': code,
                    'name': name,
                    'flag': flag,
                    'isDefault': code == DEFAULT_LANGUAGE
                })
            
            return Response({
                'success': True,
                'languages': languages,
                'defaultLanguage': DEFAULT_LANGUAGE
            })
        except Exception as e:
            logger.error(f"Error getting supported languages: {e}")
            return Response({
                'success': False,
                'error': 'Failed to get supported languages'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TranslationsAPIView(APIView):
    """Fornece traduções para o frontend"""
    
    def get(self, request, language=None):
        """
        Retorna todas as traduções para um idioma
        GET /api/translations/pt-BR/
        """
        if not language:
            language = request.GET.get('lang', DEFAULT_LANGUAGE)
        
        # Valida idioma
        if not is_supported_language(language):
            return Response({
                'success': False,
                'error': f'Unsupported language: {language}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Carrega todas as traduções do frontend
            translations = translation_service.get_all_translations_for_frontend(language)
            
            return Response({
                'success': True,
                'language': language,
                'translations': translations
            })
        except Exception as e:
            logger.error(f"Error getting translations for {language}: {e}")
            return Response({
                'success': False,
                'error': 'Failed to load translations'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserLanguageAPIView(APIView):
    """Gerencia idioma preferido do usuário"""
    
    def get(self, request):
        """Retorna idioma preferido do usuário atual"""
        try:
            # Se usuário está logado, pega da preferência
            if hasattr(request.user, 'preferred_language') and not isinstance(request.user, AnonymousUser):
                user_language = getattr(request.user, 'preferred_language', None)
                if user_language and is_supported_language(user_language):
                    return Response({
                        'success': True,
                        'language': user_language,
                        'source': 'user_preference'
                    })
            
            # Senão, tenta detectar do cabeçalho Accept-Language
            accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
            detected_language = self._detect_language_from_header(accept_language)
            
            return Response({
                'success': True,
                'language': detected_language,
                'source': 'browser_detection' if detected_language != DEFAULT_LANGUAGE else 'default'
            })
        except Exception as e:
            logger.error(f"Error getting user language: {e}")
            return Response({
                'success': True,
                'language': DEFAULT_LANGUAGE,
                'source': 'fallback'
            })
    
    def post(self, request):
        """Define idioma preferido do usuário"""
        try:
            language = request.data.get('language')
            
            if not language:
                return Response({
                    'success': False,
                    'error': 'Language parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not is_supported_language(language):
                return Response({
                    'success': False,
                    'error': f'Unsupported language: {language}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Salva preferência se usuário está logado
            if hasattr(request.user, 'preferred_language') and not isinstance(request.user, AnonymousUser):
                request.user.preferred_language = language
                request.user.save(update_fields=['preferred_language'])
                logger.info(f"Updated user {request.user.id} language preference to {language}")
            
            # Ativa idioma na sessão atual
            activate(language)
            
            return Response({
                'success': True,
                'language': language,
                'message': 'Language preference updated successfully'
            })
        except Exception as e:
            logger.error(f"Error setting user language: {e}")
            return Response({
                'success': False,
                'error': 'Failed to update language preference'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _detect_language_from_header(self, accept_language: str) -> str:
        """Detecta idioma a partir do cabeçalho Accept-Language"""
        if not accept_language:
            return DEFAULT_LANGUAGE
        
        # Parse do cabeçalho Accept-Language
        # Ex: "pt-BR,pt;q=0.9,en;q=0.8,es;q=0.7"
        languages = []
        for lang_info in accept_language.split(','):
            parts = lang_info.strip().split(';')
            lang_code = parts[0].strip()
            
            # Extrai quality factor (padrão 1.0)
            quality = 1.0
            if len(parts) > 1 and parts[1].startswith('q='):
                try:
                    quality = float(parts[1][2:])
                except ValueError:
                    quality = 1.0
            
            languages.append((lang_code, quality))
        
        # Ordena por qualidade (maior primeiro)
        languages.sort(key=lambda x: x[1], reverse=True)
        
        # Tenta encontrar correspondência
        for lang_code, _ in languages:
            # Normaliza códigos (pt-BR -> pt-BR, pt -> pt-BR, en -> en-US)
            if lang_code.lower().startswith('pt'):
                if is_supported_language('pt-BR'):
                    return 'pt-BR'
            elif lang_code.lower().startswith('es'):
                if is_supported_language('es-ES'):
                    return 'es-ES'
            elif lang_code.lower().startswith('sv'):
                if is_supported_language('sv-SE'):
                    return 'sv-SE'
            elif lang_code.lower().startswith('en'):
                if is_supported_language('en-US'):
                    return 'en-US'
        
        return DEFAULT_LANGUAGE

class ClearTranslationCacheAPIView(APIView):
    """Limpa cache de traduções (apenas para desenvolvimento)"""
    
    def post(self, request):
        """Limpa cache de traduções"""
        try:
            language = request.data.get('language')
            category = request.data.get('category')
            
            translation_service.clear_cache(language, category)
            
            return Response({
                'success': True,
                'message': 'Translation cache cleared successfully'
            })
        except Exception as e:
            logger.error(f"Error clearing translation cache: {e}")
            return Response({
                'success': False,
                'error': 'Failed to clear translation cache'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)