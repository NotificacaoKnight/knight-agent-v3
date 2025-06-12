#!/bin/bash

# Script de instalação do Knight Agent
echo "🏰 Instalando Knight Agent..."

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado. Por favor, instale o Docker primeiro."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não encontrado. Por favor, instale o Docker Compose primeiro."
    exit 1
fi

# Verificar se Python está instalado (para desenvolvimento local)
if ! command -v python3 &> /dev/null; then
    echo "⚠️  Python 3 não encontrado. Recomendado para desenvolvimento local."
fi

# Verificar se Node.js está instalado (para desenvolvimento local)
if ! command -v node &> /dev/null; then
    echo "⚠️  Node.js não encontrado. Recomendado para desenvolvimento local."
fi

# Criar diretórios necessários
echo "📁 Criando diretórios necessários..."
mkdir -p backend/media
mkdir -p backend/staticfiles
mkdir -p backend/logs
mkdir -p backend/vector_store
mkdir -p backend/documents
mkdir -p backend/processed_documents

# Copiar arquivo de configuração
echo "⚙️  Configurando variáveis de ambiente..."
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "✅ Arquivo .env criado. Configure suas credenciais antes de continuar."
else
    echo "✅ Arquivo .env já existe."
fi

# Instalar dependências do backend (desenvolvimento local)
if command -v python3 &> /dev/null; then
    echo "🐍 Configurando ambiente Python..."
    cd backend
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "✅ Ambiente virtual Python criado."
    fi
    
    source venv/bin/activate
    pip install -r requirements.txt
    echo "✅ Dependências Python instaladas."
    cd ..
fi

# Instalar dependências do frontend (desenvolvimento local)
if command -v node &> /dev/null; then
    echo "📦 Instalando dependências do frontend..."
    cd frontend
    npm install
    echo "✅ Dependências Node.js instaladas."
    cd ..
fi

echo ""
echo "🎉 Instalação concluída!"
echo ""
echo "📋 Próximos passos:"
echo "1. Configure suas credenciais em backend/.env"
echo "2. Para desenvolvimento local:"
echo "   - Backend: cd backend && source venv/bin/activate && python manage.py runserver"
echo "   - Frontend: cd frontend && npm start"
echo "3. Para usar Docker:"
echo "   - docker-compose up -d"
echo ""
echo "📖 Consulte a documentação em docs/ para mais detalhes."