# Guia de Instalação - Knight Agent

## 📋 Pré-requisitos

### Para Desenvolvimento Local
- Python 3.11+
- Node.js 18+
- PostgreSQL 13+ (ou usar SQLite para desenvolvimento)
- Redis 6+ (para Celery)

### Para Produção com Docker
- Docker 20.10+
- Docker Compose v2.0+

## 🚀 Instalação Rápida

### Opção 1: Script Automático
```bash
git clone <repository-url>
cd knight-agent
chmod +x scripts/install.sh
./scripts/install.sh
```

### Opção 2: Docker (Recomendado)
```bash
git clone <repository-url>
cd knight-agent
cp backend/.env.example backend/.env
# Configure suas credenciais no .env
docker-compose up -d
```

## ⚙️ Configuração Detalhada

### 1. Configuração do Backend

#### Ambiente Virtual Python
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Variáveis de Ambiente
Copie e configure o arquivo `.env`:
```bash
cp .env.example .env
```

Configure as seguintes variáveis essenciais:
```env
# Azure AD (Obrigatório)
AZURE_AD_CLIENT_ID=seu-client-id
AZURE_AD_CLIENT_SECRET=seu-client-secret
AZURE_AD_TENANT_ID=seu-tenant-id

# Provedor LLM (Escolha um)
LLM_PROVIDER=cohere
COHERE_API_KEY=sua-api-key

# Banco de Dados (Opcional - usa SQLite por padrão)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=knight_db
DB_USER=knight_user
DB_PASSWORD=sua-senha
```

#### Migrações do Banco
```bash
python manage.py migrate
python manage.py createsuperuser  # Opcional
```

#### Iniciar Servidor
```bash
python manage.py runserver
```

### 2. Configuração do Frontend

```bash
cd frontend
npm install
npm start
```

### 3. Configuração de Serviços Auxiliares

#### Redis (para Celery)
```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# Docker
docker run -d -p 6379:6379 redis:7-alpine
```

#### Celery Worker
```bash
cd backend
celery -A knight_backend worker -l info
```

## 🔧 Configuração de Provedores LLM

### Cohere (Recomendado para RAG)
1. Acesse [Cohere Dashboard](https://dashboard.cohere.com/)
2. Crie uma conta e obtenha sua API key
3. Configure no `.env`:
```env
LLM_PROVIDER=cohere
COHERE_API_KEY=sua-cohere-api-key
```

### Together AI
```env
LLM_PROVIDER=together
TOGETHER_API_KEY=sua-together-api-key
```

### Groq
```env
LLM_PROVIDER=groq
GROQ_API_KEY=sua-groq-api-key
```

### Ollama (Self-hosted)
1. Instale Ollama: https://ollama.ai/
2. Baixe um modelo:
```bash
ollama pull llama3.2
```
3. Configure no `.env`:
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## 🏢 Configuração Microsoft Azure AD

### 1. Registrar Aplicação no Azure
1. Acesse [Azure Portal](https://portal.azure.com/)
2. Vá para "Azure Active Directory" > "App registrations"
3. Clique em "New registration"
4. Configure:
   - Nome: "Knight Agent"
   - Supported account types: "Accounts in this organizational directory only"
   - Redirect URI: `http://localhost:8000/auth/microsoft/callback/`

### 2. Configurar Permissões
1. Vá para "API permissions"
2. Adicione as permissões:
   - Microsoft Graph: `User.Read`
   - Microsoft Graph: `offline_access`

### 3. Criar Client Secret
1. Vá para "Certificates & secrets"
2. Clique em "New client secret"
3. Copie o valor para o `.env`

## 🐳 Deployment com Docker

### Desenvolvimento
```bash
docker-compose -f docker-compose.yml up -d
```

### Produção
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 📁 Upload de Documentos Internos

### 1. Via Interface Web
1. Faça login como administrador
2. Acesse "Documentos" > "Upload"
3. Selecione arquivos e marque como "Baixável" se necessário

### 2. Via API
```bash
curl -X POST http://localhost:8000/api/documents/upload/ \
  -H "Authorization: Bearer SEU_TOKEN" \
  -F "file=@documento.pdf" \
  -F "title=Manual do Funcionário" \
  -F "is_downloadable=true"
```

### 3. Processamento Automático
Os documentos são processados automaticamente:
1. Conversão para Markdown (Docling)
2. Divisão em chunks (500-800 tokens)
3. Geração de embeddings (BGE-m3)
4. Indexação para busca

## 🔍 Verificação da Instalação

### 1. Healthcheck
```bash
curl http://localhost:8000/api/health/
```

### 2. Teste de Autenticação
```bash
curl http://localhost:8000/api/auth/microsoft/login/
```

### 3. Teste do Chat
1. Acesse http://localhost:3000
2. Faça login com sua conta Microsoft
3. Inicie um novo chat
4. Digite uma pergunta

## 🔧 Solução de Problemas

### Backend não inicia
- Verifique se todas as variáveis do `.env` estão configuradas
- Confirme se o banco de dados está acessível
- Execute `python manage.py check`

### Frontend não carrega
- Verifique se o backend está rodando
- Confirme as variáveis de ambiente do React
- Execute `npm run build` para verificar erros

### Erro de autenticação Microsoft
- Verifique as credenciais Azure AD
- Confirme o redirect URI
- Teste as permissões da aplicação

### Documentos não são processados
- Verifique se o Celery worker está rodando
- Confirme se o Redis está acessível
- Verifique logs em `backend/logs/`

## 📊 Monitoramento

### Logs
```bash
# Backend
tail -f backend/logs/knight.log

# Docker
docker-compose logs -f backend
```

### Métricas
- Acesse `/admin/` para painel administrativo
- Use `/api/stats/` para métricas da API
- Monitore Celery tasks via Redis

## 🔄 Atualizações

```bash
git pull origin main
docker-compose pull
docker-compose up -d --build
```