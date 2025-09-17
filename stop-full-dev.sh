#!/bin/bash

echo "🛑 Parando Knight Agent - Ambiente completo"
echo ""

# Parar containers Docker
echo "🐳 Parando containers Docker..."
cd backend
docker-compose -f docker-compose.dev.yml down
cd ..

# Matar processos nas portas
echo "🔪 Matando processos nas portas..."
lsof -ti:3000 | xargs kill -9 2>/dev/null || true  # React
lsof -ti:8000 | xargs kill -9 2>/dev/null || true  # FastAPI
lsof -ti:8000 | xargs kill -9 2>/dev/null || true  # FastAPI alternativo
lsof -ti:8001 | xargs kill -9 2>/dev/null || true  # FastAPI alternativo

echo "✅ Ambiente parado com sucesso!"
echo ""
echo "📋 Para verificar:"
echo "   docker ps                # Deve estar vazio"
echo "   lsof -i :3000           # Deve estar vazio"
echo "   lsof -i :8000           # Deve estar vazio"