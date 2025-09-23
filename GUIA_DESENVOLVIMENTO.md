# Guia de Desenvolvimento - Knight Agent

## Pré-requisitos

- Docker e Docker Compose instalados
- Node.js 16+ e npm
- Python 3.9+

## Setup Inicial

### 1. Clone e configure o projeto

```bash
git clone <repository-url>
cd knight-agent
```

### 2. Configure variáveis de ambiente

```bash
# Copie o arquivo de exemplo para .env
cd backend
cp .env.example .env

# Edite o .env com suas configurações
nano .env  # ou seu editor preferido
```

**Configurações mínimas necessárias no .env:**
```env
DEBUG=True
SECRET_KEY=seu-secret-key-aqui
JWT_SECRET_KEY=seu-jwt-secret-aqui

# Azure AD (obrigatório para auth)
AZURE_AD_CLIENT_ID=seu-client-id
AZURE_AD_CLIENT_SECRET=seu-client-secret
AZURE_AD_TENANT_ID=seu-tenant-id

# LLM Provider (escolha um)
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sua-api-key

# Database (Docker PostgreSQL na porta padrão)
DB_HOST=localhost
DB_PORT=5432
DB_USER=knight_user
DB_PASSWORD=knight_password
DB_NAME=knight_fastapi_db
```

## Executando o Projeto

### Terminal 1: Preparar ambiente e subir containers

```bash
# PRIMEIRO: Desativar serviços locais para evitar conflitos de porta
sudo systemctl stop postgresql redis-server
sudo systemctl disable postgresql redis-server

# Na raiz do projeto
cd backend
docker-compose up postgres redis -d

# Verificar se os containers estão rodando
docker ps

# PostgreSQL: porta 5432, Redis: porta 6379 (portas padrão)
```

### Terminal 2: Backend (FastAPI)

```bash
cd backend

# Criar e ativar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Executar migrações do banco
alembic upgrade head

# Rodar servidor de desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 3: Frontend (React)

```bash
cd frontend

# Instalar dependências
npm install

# Rodar servidor de desenvolvimento
npm start
```

## URLs de Acesso

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Documentação API**: http://localhost:8000/docs

## Comandos Úteis

### Backend

```bash
cd backend
source venv/bin/activate  # Sempre ativar o venv primeiro

# Verificar status do banco
alembic current

# Criar nova migração (se modificar models)
alembic revision --autogenerate -m "descrição da mudança"

# Aplicar migrações
alembic upgrade head

# Testar API
curl http://localhost:8000/health

# Executar testes
pytest

# Linting
black .
flake8 .
```

### Frontend

```bash
cd frontend

# Instalar nova dependência
npm install <package-name>

# Build para produção
npm run build

# Executar testes
npm test

# Linting
npm run lint
npm run lint:fix
```

### Docker

```bash
# Ver logs dos containers
docker-compose logs postgres
docker-compose logs redis

# Parar containers
docker-compose down

# Parar e remover volumes (CUIDADO: apaga dados do banco)
docker-compose down -v

# Reconstruir containers
docker-compose up --build
```

## Estrutura de Desenvolvimento

```
knight-agent/
├── backend/                 # FastAPI + Python
│   ├── app/                # Código da aplicação
│   ├── alembic/            # Migrações do banco
│   ├── requirements.txt    # Dependências Python
│   └── .env               # Variáveis de ambiente
├── frontend/               # React + TypeScript
│   ├── src/               # Código React
│   ├── public/            # Assets estáticos
│   └── package.json       # Dependências Node
└── docker-compose.yml      # Configuração Docker
```

## Solução de Problemas

### Backend não conecta no banco

```bash
# Verificar se PostgreSQL está rodando
docker-compose ps

# Ver logs do PostgreSQL
docker-compose logs postgres

# Recriar container do banco
docker-compose down postgres
docker-compose up postgres -d
```

### Erro de migrações

```bash
cd backend
source venv/bin/activate

# Ver status atual
alembic current

# Voltar para migração anterior
alembic downgrade -1

# Aplicar novamente
alembic upgrade head
```

### Frontend não carrega

```bash
cd frontend

# Limpar cache do npm
npm cache clean --force

# Reinstalar dependências
rm -rf node_modules package-lock.json
npm install

# Verificar se backend está rodando
curl http://localhost:8000/health
```

### Erro de autenticação

1. Verificar se Azure AD está configurado no `.env`
2. Verificar se as URLs de redirect estão corretas no Azure
3. Limpar localStorage do browser: F12 → Application → Storage → Clear

## Próximos Passos

1. Configure Azure AD seguindo `AZURE_AD_SETUP.md`
2. Adicione documentos para testar o RAG
3. Configure um provider de LLM (DeepSeek, Cohere, etc.)
4. Teste o sistema de chat e busca