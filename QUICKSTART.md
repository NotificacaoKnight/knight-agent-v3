# 🚀 Knight Agent - Guia de Início Rápido

## Pré-requisitos

- Python 3.8+
- Node.js 16+
- npm ou yarn
- Git

## 1. Backend (Django)

### Instalação e Configuração

```bash
# Navegar para o diretório backend
cd backend

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Criar banco de dados
python manage.py migrate

# Criar superusuário (opcional)
python manage.py createsuperuser
```

### Iniciar o servidor backend

```bash
# Certifique-se de estar no diretório backend com o venv ativado
python manage.py runserver
```

O backend estará rodando em: http://localhost:8000

## 2. Frontend (React)

### Instalação e Configuração

```bash
# Em um novo terminal, navegar para o diretório frontend
cd frontend

# Instalar dependências
npm install
```

### Iniciar o servidor frontend

```bash
npm start
```

O frontend estará rodando em: http://localhost:3000

## 3. Acessar a aplicação

1. Abra o navegador em http://localhost:3000
2. Você verá a tela de login
3. Faça login usando suas credenciais do Microsoft Azure AD

## 4. Serviços Opcionais

### Redis (para processamento assíncrono)

Se você quiser usar o processamento de documentos com Celery:

```bash
# Instalar Redis (Windows - usar WSL ou Docker)
# Linux:
sudo apt-get install redis-server
redis-server

# macOS:
brew install redis
redis-server
```

### Celery Worker

```bash
# Em outro terminal, no diretório backend com venv ativado
celery -A knight_backend worker -l info
```

## 5. Verificar se está funcionando

- **Backend API**: http://localhost:8000/api/
- **Frontend**: http://localhost:3000
- **Admin Django**: http://localhost:8000/admin/

## Troubleshooting

### Problemas de Login

1. **Verificar se o backend está rodando**:
   ```bash
   # No terminal do backend, você deve ver:
   # Starting development server at http://127.0.0.1:8000/
   ```

2. **Verificar configurações do Azure AD**:
   - Certifique-se de que as credenciais do Azure AD estão configuradas no arquivo .env
   - Verifique se o redirect URI está configurado corretamente no Azure AD

3. **Verificar migrações**:
   ```bash
   cd backend
   python manage.py migrate
   ```

4. **Verificar logs do console**:
   - Abra o console do navegador (F12)
   - Veja se há erros de rede na aba Network
   - Procure por erros 404, 500 ou CORS

### Erro de CORS
Se houver problemas de CORS, verifique se o backend está rodando na porta 8000.

### Erro de conexão com API
Certifique-se de que o proxy no package.json está apontando para http://localhost:8000

### Erro 403 Forbidden

Se você receber erro 403:

1. **Verificar proxy do React**:
   - O arquivo `frontend/package.json` deve conter:
   ```json
   "proxy": "http://localhost:8000"
   ```
   
2. **Reiniciar ambos os servidores**:
   - Pare o frontend (Ctrl+C)
   - Pare o backend (Ctrl+C)
   - Inicie o backend primeiro
   - Depois inicie o frontend

## Estrutura dos Serviços

```
Frontend (React)     :3000
    ↓
Backend (Django)     :8000
    ↓
Database (SQLite)    (arquivo local)
    ↓
Redis (opcional)     :6379
```

## Comandos Úteis

```bash
# Backend - Ver logs
python manage.py runserver --verbosity 2

# Frontend - Build de produção
npm run build

# Limpar cache do npm
npm cache clean --force

# Reinstalar dependências
rm -rf node_modules package-lock.json
npm install
```