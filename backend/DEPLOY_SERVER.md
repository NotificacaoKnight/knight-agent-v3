# DEPLOY SERVER - PENDÊNCIAS E CHECKLIST

## 🚨 PENDÊNCIAS CRÍTICAS PARA DEPLOY

### 1. INFRAESTRUTURA NECESSÁRIA

#### Redis (Message Broker para Celery)
- [ ] **Instalar Redis no servidor**
  ```bash
  sudo apt update
  sudo apt install redis-server
  sudo systemctl enable redis-server
  sudo systemctl start redis-server
  ```
- [ ] **Configurar Redis para produção**
  - Configurar autenticação: `requirepass sua_senha_forte`
  - Configurar persistência: `save 900 1`
  - Limitar conexões: `maxclients 1000`
  - Configurar memória: `maxmemory 2gb`

#### Banco de Dados
- [ ] **PostgreSQL em produção**
  ```bash
  sudo apt install postgresql postgresql-contrib
  ```
- [ ] **Configurar usuário e database**
- [ ] **Backup strategy**
- [ ] **Connection pooling (pgbouncer)**

#### Servidor Web
- [ ] **Nginx como proxy reverso**
- [ ] **Certificado SSL (Let's Encrypt)**
- [ ] **Configurar static files**
- [ ] **Configurar media files**

### 2. CONFIGURAÇÕES DE AMBIENTE

#### Variáveis Ambiente (.env produção)
```env
# Django
DEBUG=False
SECRET_KEY=<chave_super_forte_64_chars>
ALLOWED_HOSTS=meudominio.com,www.meudominio.com

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=knight_prod
DB_USER=knight_user
DB_PASSWORD=<senha_forte>
DB_HOST=localhost
DB_PORT=5432

# Redis/Celery
CELERY_BROKER_URL=redis://:senha_redis@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:senha_redis@localhost:6379/0

# Azure AD
AZURE_AD_CLIENT_ID=<client_id_producao>
AZURE_AD_CLIENT_SECRET=<client_secret_producao>
AZURE_AD_TENANT_ID=<tenant_id>

# LLM Provider
LLM_PROVIDER=cohere
COHERE_API_KEY=<api_key_producao>

# Security
TOKEN_ENCRYPTION_SECRET=<chave_64_chars_para_criptografia>
CORS_ALLOWED_ORIGINS=https://meudominio.com

# Paths
MEDIA_ROOT=/var/www/knight/media
STATIC_ROOT=/var/www/knight/static
PROCESSED_DOCS_PATH=/var/www/knight/processed
```

### 3. SERVIÇOS SYSTEMD

#### Django Application
- [ ] **Criar /etc/systemd/system/knight-django.service**
```ini
[Unit]
Description=Knight Agent Django
After=network.target

[Service]
Type=notify
User=knight
Group=knight
WorkingDirectory=/var/www/knight
Environment=PATH=/var/www/knight/venv/bin
EnvironmentFile=/var/www/knight/.env
ExecStart=/var/www/knight/venv/bin/gunicorn knight_backend.wsgi:application --bind 127.0.0.1:8000
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Celery Worker
- [ ] **Criar /etc/systemd/system/knight-celery.service**
```ini
[Unit]
Description=Knight Agent Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=knight
Group=knight
WorkingDirectory=/var/www/knight
Environment=PATH=/var/www/knight/venv/bin
EnvironmentFile=/var/www/knight/.env
ExecStart=/var/www/knight/venv/bin/celery -A knight_backend worker --detach --loglevel=info
ExecStop=/var/www/knight/venv/bin/celery -A knight_backend control shutdown
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Celery Beat (Scheduler)
- [ ] **Criar /etc/systemd/system/knight-celery-beat.service**
```ini
[Unit]
Description=Knight Agent Celery Beat
After=network.target redis.service

[Service]
Type=simple
User=knight
Group=knight
WorkingDirectory=/var/www/knight
Environment=PATH=/var/www/knight/venv/bin
EnvironmentFile=/var/www/knight/.env
ExecStart=/var/www/knight/venv/bin/celery -A knight_backend beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

### 4. NGINX CONFIGURATION

- [ ] **Criar /etc/nginx/sites-available/knight**
```nginx
server {
    listen 80;
    server_name meudominio.com www.meudominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name meudominio.com www.meudominio.com;

    ssl_certificate /etc/letsencrypt/live/meudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/meudominio.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";

    # Static files
    location /static/ {
        alias /var/www/knight/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Media files
    location /media/ {
        alias /var/www/knight/media/;
        expires 7d;
    }

    # Django application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Upload size
        client_max_body_size 50M;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

### 5. SEGURANÇA - CORREÇÕES CRÍTICAS PENDENTES

#### Token Encryption (CRÍTICO)
- [ ] **Implementar criptografia de tokens no banco**
  - Usar `SECURITY_REMEDIATION_CODE.py`
  - Gerar `TOKEN_ENCRYPTION_SECRET`
  - Migrar tokens existentes

#### CORS Security (CRÍTICO)
- [ ] **Corrigir configuração CORS**
  ```python
  CORS_ALLOWED_ORIGINS = [
      "https://meudominio.com",
  ]
  CORS_ALLOW_CREDENTIALS = False
  ```

#### Rate Limiting (CRÍTICO)
- [ ] **Implementar rate limiting rigoroso**
  - Login: 3 tentativas/5min
  - API: 100 requests/min
  - Upload: 5 arquivos/hora

#### JWT Validation (CRÍTICO)
- [ ] **Implementar validação JWT completa**
  - Verificar assinatura
  - Validar issuer/audience
  - Verificar expiração

#### Security Headers (CRÍTICO)
- [ ] **Implementar headers de segurança**
  ```python
  SECURE_SSL_REDIRECT = True
  SECURE_HSTS_SECONDS = 31536000
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True
  ```

### 6. MONITORAMENTO E LOGS

#### Log Configuration
- [ ] **Configurar rotação de logs**
  ```python
  LOGGING = {
      'handlers': {
          'file': {
              'class': 'logging.handlers.RotatingFileHandler',
              'filename': '/var/log/knight/django.log',
              'maxBytes': 10*1024*1024,  # 10MB
              'backupCount': 10,
          }
      }
  }
  ```

#### Health Checks
- [ ] **Implementar health check endpoints**
  - `/health/` - Status geral
  - `/health/database/` - Status do banco
  - `/health/redis/` - Status do Redis
  - `/health/celery/` - Status dos workers

#### Monitoring
- [ ] **Configurar monitoramento**
  - CPU, RAM, Disk usage
  - Queue size (Celery)
  - Response times
  - Error rates

### 7. BACKUP STRATEGY

#### Database Backup
- [ ] **Configurar backup automático PostgreSQL**
  ```bash
  # Cron job diário
  0 2 * * * pg_dump knight_prod | gzip > /backups/knight_$(date +\%Y\%m\%d).sql.gz
  ```

#### Media Files Backup
- [ ] **Configurar backup de arquivos**
  ```bash
  # Sync para cloud storage
  0 3 * * * rsync -av /var/www/knight/media/ s3://knight-backups/media/
  ```

#### Configuration Backup
- [ ] **Backup de configurações**
  - `.env` file
  - Nginx configs
  - Systemd services

### 8. PERFORMANCE OPTIMIZATION

#### Database
- [ ] **Configurar connection pooling**
- [ ] **Índices otimizados**
- [ ] **Query optimization**

#### Caching
- [ ] **Cache de embeddings**
- [ ] **Cache de sessões**
- [ ] **CDN para static files**

#### Celery
- [ ] **Configurar múltiplos workers**
- [ ] **Separar queues por tipo de tarefa**
- [ ] **Monitoring de queue size**

### 9. SSL/TLS SETUP

- [ ] **Instalar Certbot**
  ```bash
  sudo apt install certbot python3-certbot-nginx
  sudo certbot --nginx -d meudominio.com -d www.meudominio.com
  ```
- [ ] **Configurar renovação automática**
  ```bash
  sudo crontab -e
  0 12 * * * /usr/bin/certbot renew --quiet
  ```

### 10. DEPLOYMENT SCRIPTS

#### Deploy Script
- [ ] **Criar script de deploy**
```bash
#!/bin/bash
# deploy.sh

# Pull latest code
git pull origin main

# Install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart knight-django
sudo systemctl restart knight-celery
sudo systemctl restart knight-celery-beat
sudo systemctl reload nginx

echo "Deploy completed!"
```

#### Rollback Script
- [ ] **Criar script de rollback**
```bash
#!/bin/bash
# rollback.sh

# Revert to previous commit
git reset --hard HEAD~1

# Restart services
sudo systemctl restart knight-django
sudo systemctl restart knight-celery

echo "Rollback completed!"
```

### 11. TESTING EM PRODUÇÃO

- [ ] **Smoke tests pós-deploy**
  - Health checks funcionando
  - Login Azure AD
  - Upload de documento
  - Busca RAG
  - Processamento Celery

- [ ] **Load testing**
  - Múltiplos uploads simultâneos
  - Múltiplas buscas RAG
  - Stress test do Celery

### 12. DOCUMENTAÇÃO OPERACIONAL

- [ ] **Runbook para operações**
  - Como fazer deploy
  - Como fazer rollback
  - Como investigar problemas
  - Como escalar workers

- [ ] **Troubleshooting guide**
  - Redis não conecta
  - Celery não processa
  - Django não responde
  - Uploads falham

---

## 📋 ORDEM DE IMPLEMENTAÇÃO RECOMENDADA

### Fase 1: Infraestrutura Base
1. Instalar Redis
2. Configurar PostgreSQL
3. Configurar Nginx
4. Configurar SSL

### Fase 2: Aplicação
1. Configurar variáveis de ambiente
2. Criar serviços systemd
3. Testar Celery workers

### Fase 3: Segurança
1. Implementar correções críticas
2. Configurar rate limiting
3. Configurar security headers

### Fase 4: Monitoramento
1. Configurar logs
2. Implementar health checks
3. Configurar alertas

### Fase 5: Backup e Performance
1. Configurar backups
2. Otimizar performance
3. Load testing

---

## ⚠️ AVISOS IMPORTANTES

1. **NUNCA fazer deploy sem corrigir as vulnerabilidades críticas de segurança**
2. **Sempre testar em ambiente staging primeiro**
3. **Ter plano de rollback preparado**
4. **Monitorar logs durante primeiras horas pós-deploy**
5. **Fazer backup completo antes de qualquer deploy**

---

**Status:** 🔴 **NÃO PRONTO PARA PRODUÇÃO**  
**Próximo passo:** Implementar correções de segurança críticas