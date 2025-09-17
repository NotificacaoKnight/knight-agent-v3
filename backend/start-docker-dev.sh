#!/bin/bash
# Script para iniciar desenvolvimento com Docker e hot reload

echo "🚀 Iniciando Knight Agent FastAPI com Docker (Hot Reload)"

# Parar containers existentes
echo "📦 Parando containers existentes..."
docker-compose -f docker-compose.dev.yml down

# Criar arquivo .env para Docker se não existir
if [ ! -f .env.docker ]; then
    echo "⚠️  Arquivo .env.docker não encontrado!"
    echo "   Crie o arquivo .env.docker com suas chaves API"
    echo "   Exemplo: cp .env.docker.example .env.docker"
    exit 1
fi

# Buildar imagens
echo "🔨 Buildando imagens Docker..."
docker-compose -f docker-compose.dev.yml build

# Subir containers
echo "🎬 Iniciando containers..."
docker-compose -f docker-compose.dev.yml --env-file .env.docker up -d

# Aguardar containers iniciarem
echo "⏳ Aguardando containers iniciarem..."
sleep 10

# Mostrar logs do FastAPI
echo "📋 Logs do FastAPI:"
echo "   - FastAPI: http://localhost:8000"
echo "   - Docs: http://localhost:8000/docs"
echo "   - PostgreSQL: localhost:5434"
echo ""
echo "🔄 Hot reload ativado! Edite os arquivos e veja as mudanças automaticamente."
echo ""
echo "📋 Comandos úteis:"
echo "   docker-compose -f docker-compose.dev.yml logs -f fastapi  # Logs FastAPI"
echo "   docker-compose -f docker-compose.dev.yml down             # Parar tudo"
echo "   docker-compose -f docker-compose.dev.yml restart fastapi  # Restart FastAPI"
echo ""

# Seguir logs do FastAPI
echo "📋 Seguindo logs do FastAPI (Ctrl+C para sair):"
docker-compose -f docker-compose.dev.yml logs -f fastapi