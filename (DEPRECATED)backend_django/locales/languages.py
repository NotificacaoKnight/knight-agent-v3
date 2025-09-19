"""
Configurações de idiomas suportados pelo Knight Agent
"""
from typing import List, Dict, Tuple

# Lista de idiomas suportados
SUPPORTED_LANGUAGES = [
    ('pt-BR', 'Português (Brasil)', '🇧🇷'),
    ('en-US', 'English (United States)', '🇺🇸'),
    ('es-ES', 'Español (España)', '🇪🇸'),
    ('sv-SE', 'Svenska (Sverige)', '🇸🇪'),
]

# Idioma padrão
DEFAULT_LANGUAGE = 'en-US'

# Mapeamento para códigos Django
DJANGO_LANGUAGE_CODES = {
    'pt-BR': 'pt-br',
    'en-US': 'en',
    'es-ES': 'es',
    'sv-SE': 'sv',
}

# Mapeamento reverso
FRONTEND_LANGUAGE_CODES = {
    'pt-br': 'pt-BR',
    'en': 'en-US',
    'es': 'es-ES',
    'sv': 'sv-SE',
}

def get_supported_languages() -> List[Tuple[str, str, str]]:
    """Retorna lista de idiomas suportados"""
    return SUPPORTED_LANGUAGES

def get_language_choices() -> List[Tuple[str, str]]:
    """Retorna choices para uso em models Django"""
    return [(code, f"{flag} {name}") for code, name, flag in SUPPORTED_LANGUAGES]

def get_django_code(frontend_code: str) -> str:
    """Converte código do frontend para Django"""
    return DJANGO_LANGUAGE_CODES.get(frontend_code, 'en')

def get_frontend_code(django_code: str) -> str:
    """Converte código do Django para frontend"""
    return FRONTEND_LANGUAGE_CODES.get(django_code, 'en-US')

def is_supported_language(language_code: str) -> bool:
    """Verifica se um idioma é suportado"""
    return language_code in [code for code, _, _ in SUPPORTED_LANGUAGES]