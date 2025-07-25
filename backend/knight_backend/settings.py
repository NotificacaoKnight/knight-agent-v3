import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')]) + ['*.loca.lt']

# Security settings - CORS configuration for development and tunnel
CORS_ALLOW_ALL_ORIGINS = True  # Temporariamente true para debug
CSRF_TRUSTED_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000', 'https://*.loca.lt']

# Allowed origins for CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://knight-frontend-dev.loca.lt",
    "https://knight-frontend-dev.loca.lt:3000",  # Para tunnel accessing localhost backend
]

# Permitir all origins temporariamente para debug
CORS_ALLOW_ALL_ORIGINS = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'authentication',
    'documents',
    'rag',
    'chat',
    'downloads',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',  # Temporarily disabled for API
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'authentication.middleware.TokenAuthenticationMiddleware',  # Custom token auth
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CSRF exempt paths for development
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

ROOT_URLCONF = 'knight_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'knight_backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.sqlite3'),
        'NAME': config('DB_NAME', default=BASE_DIR / 'db.sqlite3'),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default=''),
        'PORT': config('DB_PORT', default=''),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'authentication.User'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'authentication.backends.MicrosoftAuthAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS configuration is above in the Security settings section

CORS_ALLOW_CREDENTIALS = False  # Removido pois usamos token auth, não cookies

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Microsoft Azure AD Configuration
AZURE_AD_CLIENT_ID = config('AZURE_AD_CLIENT_ID', default='')
AZURE_AD_CLIENT_SECRET = config('AZURE_AD_CLIENT_SECRET', default='')
AZURE_AD_TENANT_ID = config('AZURE_AD_TENANT_ID', default='')
AZURE_AD_REDIRECT_URI = config('AZURE_AD_REDIRECT_URI', default='http://localhost:8000/auth/microsoft/callback/')

# LLM Configuration
LLM_PROVIDER = config('LLM_PROVIDER', default='cohere')  # cohere, together, groq, ollama, gemini

# Provider API Keys
COHERE_API_KEY = config('COHERE_API_KEY', default='')
TOGETHER_API_KEY = config('TOGETHER_API_KEY', default='')
GROQ_API_KEY = config('GROQ_API_KEY', default='')
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
GOOGLE_API_KEY = config('GOOGLE_API_KEY', default='')
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
GEMINI_MODEL = config('GEMINI_MODEL', default='gemini-1.5-flash')

# DeepSeek Configuration
DEEPSEEK_API_KEY = config('DEEPSEEK_API_KEY', default='')
DEEPSEEK_MODEL = config('DEEPSEEK_MODEL', default='deepseek-chat')

# Agno Configuration
AGNO_MODEL_PROVIDER = config('AGNO_MODEL_PROVIDER', default='openai')
AGNO_MODEL_NAME = config('AGNO_MODEL_NAME', default='gpt-4o-mini')
USE_AGNO_SEARCH = config('USE_AGNO_SEARCH', default=True, cast=bool)

# Ollama Configuration (para self-hosted)
OLLAMA_BASE_URL = config('OLLAMA_BASE_URL', default='http://localhost:11434')
OLLAMA_MODEL = config('OLLAMA_MODEL', default='llama3.2')

# RAG Configuration
EMBEDDING_MODEL = config('EMBEDDING_MODEL', default='BAAI/bge-m3')
CHUNK_SIZE = config('CHUNK_SIZE', default=700, cast=int)  # Otimizado para português
CHUNK_OVERLAP = config('CHUNK_OVERLAP', default=100, cast=int)  # 15% overlap
VECTOR_STORE_PATH = BASE_DIR / 'vector_store'
BM25_WEIGHT = config('BM25_WEIGHT', default=0.3, cast=float)
SEMANTIC_WEIGHT = config('SEMANTIC_WEIGHT', default=0.7, cast=float)

# Document Processing
DOCUMENTS_PATH = BASE_DIR / 'documents'
PROCESSED_DOCS_PATH = BASE_DIR / 'processed_documents'

# Downloads Configuration
DOWNLOADS_RETENTION_DAYS = config('DOWNLOADS_RETENTION_DAYS', default=7, cast=int)

# MongoDB Atlas Configuration (for multiple users)
MONGODB_URL = config('MONGODB_URL', default='')

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
USE_CELERY = config('USE_CELERY', default=False, cast=bool)  # Desabilitado por padrão

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'knight.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}
# LocalTunnel Configuration (integrated above)
# Note: CORS configured with specific origins to support credentials
# ALLOWED_HOSTS includes *.loca.lt
# CSRF_TRUSTED_ORIGINS includes https://*.loca.lt
