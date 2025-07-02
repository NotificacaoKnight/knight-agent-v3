#!/bin/bash
# Script de setup rápido para Knight Agent

echo "🚀 Configurando Knight Agent..."

# Backend setup
echo "📦 Configurando Backend..."
cd backend

# Criar e ativar ambiente virtual
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativar venv e instalar dependências
source venv/bin/activate
echo "Instalando dependências do backend..."
pip install -r requirements.txt

# Aplicar migrações
echo "Aplicando migrações do banco de dados..."
python manage.py migrate

echo "✅ Backend configurado!"

# Frontend setup
echo "📦 Configurando Frontend..."
cd ../frontend

# Instalar dependências
if [ ! -d "node_modules" ]; then
    echo "Instalando dependências do frontend..."
    npm install
fi

echo "✅ Frontend configurado!"

# Instruções finais
echo ""
echo "🎉 Setup completo!"
echo ""
echo "Para iniciar o projeto:"
echo ""
echo "Terminal 1 - Backend:"
echo "  cd backend"
echo "  source venv/bin/activate  # No Windows: venv\\Scripts\\activate"
echo "  python manage.py runserver"
echo ""
echo "Terminal 2 - Frontend:"
echo "  cd frontend"
echo "  npm start"
echo ""
echo "Acesse http://localhost:3000 e clique em 'Modo Desenvolvedor' para entrar!"