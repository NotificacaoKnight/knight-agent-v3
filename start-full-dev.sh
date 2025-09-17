#!/bin/bash

echo "🏰 Knight Agent - Iniciando ambiente completo de desenvolvimento"
echo ""

# Verificar dependências
command -v docker >/dev/null 2>&1 || { echo "❌ Docker não encontrado. Instale primeiro."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js não encontrado. Instale primeiro."; exit 1; }

echo "✅ Dependências verificadas"
echo ""

# Função para verificar se uma porta está livre
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  Porta $1 já está em uso. Matando processos..."
        lsof -ti:$1 | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# Verificar e limpar portas
echo "🔧 Verificando portas..."
check_port 8000  # FastAPI
check_port 3000  # React
check_port 5434  # PostgreSQL

echo "✅ Portas liberadas"
echo ""

# Iniciar Backend com Docker
echo "🚀 Iniciando Backend (FastAPI + PostgreSQL)..."
cd backend

# Verificar arquivo .env.docker
if [ ! -f .env.docker ]; then
    echo "⚠️  Arquivo .env.docker não encontrado!"
    echo "   Criando do exemplo..."
    cp .env.example .env.docker
fi

# Iniciar containers
./start-docker-dev.sh &
BACKEND_PID=$!

echo "⏳ Aguardando backend inicializar (containers Docker)..."
sleep 20

cd ..

echo ""
echo "⚖️  Verificando status do backend..."
# Aguardar API ficar disponível
max_attempts=40
attempt=1
start_time=$(date +%s)
while [ $attempt -le $max_attempts ]; do
    # Verificar healthcheck do Docker primeiro
    health_status=$(docker inspect knight_fastapi_dev --format='{{.State.Health.Status}}' 2>/dev/null || echo "none")

    if [ "$health_status" = "healthy" ] && curl -f http://localhost:8000/health >/dev/null 2>&1; then
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        echo "✅ Backend iniciado com sucesso! (${elapsed}s)"
        break
    fi

    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    echo "   🔄 Tentativa $attempt/$max_attempts (${elapsed}s) - Status: $health_status - Aguardando backend..."
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ Backend não iniciou corretamente"
    echo "   Verifique os logs: docker-compose -f backend/docker-compose.dev.yml logs"
    exit 1
fi

echo ""

# Verificar se frontend existe
if [ ! -d "frontend" ]; then
    echo "❌ Diretório frontend não encontrado!"
    exit 1
fi

# Iniciar Frontend
echo "🎨 Iniciando Frontend (React)..."
cd frontend

# Instalar dependências se necessário
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependências do frontend..."
    npm install
fi

# Verificar .env do frontend
if [ ! -f ".env" ]; then
    echo "📝 Criando .env do frontend..."
    cat > .env << EOF
REACT_APP_API_URL=http://localhost:8002
GENERATE_SOURCEMAP=false
EOF
fi

# Iniciar React
echo "🎬 Iniciando servidor React..."
npm start &
FRONTEND_PID=$!

cd ..

echo ""
echo "🎉 Ambiente completo iniciado!"
echo ""
echo "📋 URLs disponíveis:"
echo "   🎨 Frontend (React):     http://localhost:3000"
echo "   🚀 Backend (FastAPI):    http://localhost:8000"
echo "   📚 API Docs (Swagger):   http://localhost:8000/docs"
echo "   🐘 PostgreSQL:           localhost:5434"
echo ""
echo "📋 Comandos úteis:"
echo "   docker ps                                                    # Ver containers"
echo "   docker-compose -f backend/docker-compose.dev.yml logs fastapi # Logs FastAPI"
echo "   docker-compose -f backend/docker-compose.dev.yml down         # Parar backend"
echo ""
echo "🔄 Hot reload ativo em ambos frontend e backend!"
echo ""
echo "⏹️  Para parar tudo: Ctrl+C ou execute: ./stop-full-dev.sh"

# Aguardar interrupção
wait