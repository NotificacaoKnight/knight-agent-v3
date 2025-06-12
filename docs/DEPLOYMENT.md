# Guia de Deployment - Knight Agent

## 🚀 Deployment em Produção

### Preparação do Ambiente

#### 1. Servidor Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+ (16GB recomendado)
- **Storage**: 100GB+ SSD
- **OS**: Ubuntu 20.04+ ou equivalente
- **Docker**: 20.10+
- **Docker Compose**: v2.0+

#### 2. Configurações de Rede
```bash
# Portas necessárias
80/443   # Nginx/Load Balancer
8000     # Django Backend
3000     # React Frontend (desenvolvimento)
5432     # PostgreSQL
6379     # Redis
11434    # Ollama (opcional)
```

### Configuração de Produção

#### 1. Variáveis de Ambiente
Crie `/opt/knight-agent/.env.prod`:
```env
# Django Production
SECRET_KEY=sua-chave-secreta-muito-forte
DEBUG=False
ALLOWED_HOSTS=knight.suaempresa.com,api.suaempresa.com

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=knight_prod
DB_USER=knight_user
DB_PASSWORD=senha-muito-forte
DB_HOST=postgres
DB_PORT=5432

# Azure AD Production
AZURE_AD_CLIENT_ID=seu-client-id-prod
AZURE_AD_CLIENT_SECRET=seu-client-secret-prod
AZURE_AD_TENANT_ID=seu-tenant-id
AZURE_AD_REDIRECT_URI=https://knight.suaempresa.com/auth/microsoft/callback/

# LLM Provider
LLM_PROVIDER=cohere
COHERE_API_KEY=sua-cohere-api-key-prod

# Security
SECURE_SSL_REDIRECT=True
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Performance
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

#### 2. Docker Compose Produção
`docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - static_files:/var/www/static
      - media_files:/var/www/media
    depends_on:
      - backend
      - frontend
    networks:
      - knight-network

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: knight_prod
      POSTGRES_USER: knight_user
      POSTGRES_PASSWORD: senha-muito-forte
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres-backup:/backup
    networks:
      - knight-network
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - knight-network
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    env_file:
      - .env.prod
    volumes:
      - media_files:/app/media
      - static_files:/app/staticfiles
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    networks:
      - knight-network
    restart: unless-stopped

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    command: celery -A knight_backend worker -l info
    env_file:
      - .env.prod
    volumes:
      - media_files:/app/media
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    networks:
      - knight-network
    restart: unless-stopped

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    command: celery -A knight_backend beat -l info
    env_file:
      - .env.prod
    volumes:
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    networks:
      - knight-network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    environment:
      - REACT_APP_API_URL=https://api.suaempresa.com
    networks:
      - knight-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  static_files:
  media_files:

networks:
  knight-network:
    driver: bridge
```

#### 3. Dockerfile de Produção - Backend
`backend/Dockerfile.prod`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Create directories
RUN mkdir -p media staticfiles logs vector_store documents processed_documents

# Collect static files
RUN python manage.py collectstatic --noinput

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "knight_backend.wsgi:application"]
```

#### 4. Nginx Configuration
`nginx.conf`:
```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=chat:10m rate=1r/s;

    server {
        listen 80;
        server_name knight.suaempresa.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name knight.suaempresa.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API Backend
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Chat API (more restrictive)
        location /api/chat/ {
            limit_req zone=chat burst=5 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Increase timeout for LLM responses
            proxy_read_timeout 120s;
            proxy_connect_timeout 10s;
        }

        # Static files
        location /static/ {
            alias /var/www/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Media files
        location /media/ {
            alias /var/www/media/;
            expires 1d;
        }

        # Admin (restrict access)
        location /admin/ {
            allow 10.0.0.0/8;  # Internal network only
            deny all;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### Deploy Script

#### 1. Script de Deploy
`scripts/deploy.sh`:
```bash
#!/bin/bash

set -e

echo "🚀 Iniciando deploy do Knight Agent..."

# Variáveis
DEPLOY_DIR="/opt/knight-agent"
BACKUP_DIR="/opt/knight-backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Criar backup
echo "📦 Criando backup..."
mkdir -p $BACKUP_DIR
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U knight_user knight_prod > $BACKUP_DIR/db_backup_$DATE.sql

# Parar serviços
echo "⏹️  Parando serviços..."
docker-compose -f docker-compose.prod.yml down

# Atualizar código
echo "📥 Atualizando código..."
git pull origin main

# Build novas imagens
echo "🔨 Construindo imagens..."
docker-compose -f docker-compose.prod.yml build --no-cache

# Executar migrações
echo "🗃️  Executando migrações..."
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py migrate

# Coletar arquivos estáticos
echo "📁 Coletando arquivos estáticos..."
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py collectstatic --noinput

# Iniciar serviços
echo "▶️  Iniciando serviços..."
docker-compose -f docker-compose.prod.yml up -d

# Verificar saúde
echo "🔍 Verificando saúde dos serviços..."
sleep 30
curl -f http://localhost/health/ || echo "⚠️  Serviço pode não estar saudável"

echo "✅ Deploy concluído!"
```

#### 2. Backup Automático
`scripts/backup.sh`:
```bash
#!/bin/bash

BACKUP_DIR="/opt/knight-backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Criar diretório de backup
mkdir -p $BACKUP_DIR

# Backup do banco
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U knight_user knight_prod | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Backup dos arquivos
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz -C /opt/knight-agent media/

# Limpar backups antigos
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup concluído: $DATE"
```

### Monitoramento

#### 1. Health Checks
Adicione ao Django `backend/health/views.py`:
```python
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

def health_check(request):
    try:
        # Test database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Test cache
        cache.set('health_check', 'ok', 30)
        cache.get('health_check')
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'ok',
            'cache': 'ok'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)
```

#### 2. Logging de Produção
`backend/knight_backend/settings_prod.py`:
```python
import os
from .settings import *

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/knight.log',
            'maxBytes': 50*1024*1024,  # 50MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/knight_errors.log',
            'maxBytes': 50*1024*1024,
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'knight': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### SSL/TLS

#### 1. Let's Encrypt
```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d knight.suaempresa.com

# Auto-renovação
sudo crontab -e
# Adicionar: 0 12 * * * /usr/bin/certbot renew --quiet
```

#### 2. Configuração SSL
```nginx
# Strong SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_dhparam /etc/nginx/ssl/dhparam.pem;
```

### Performance

#### 1. Otimizações Django
```python
# settings_prod.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'conn_max_age': 600,
        }
    }
}

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50}
        }
    }
}
```

#### 2. Gunicorn Configuration
`backend/gunicorn.conf.py`:
```python
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 120
keepalive = 2
preload_app = True
```

### Segurança

#### 1. Firewall
```bash
# UFW rules
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

#### 2. Docker Security
```yaml
# docker-compose.prod.yml security
services:
  backend:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/log
```

### Manutenção

#### 1. Limpeza Automática
```bash
# Crontab para limpeza
0 2 * * * docker system prune -f
0 3 * * 0 docker image prune -a -f
```

#### 2. Monitoramento de Recursos
```bash
# Script de monitoramento
#!/bin/bash
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
df -h /opt/knight-agent
```