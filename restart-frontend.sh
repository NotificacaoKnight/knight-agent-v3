#!/bin/bash

echo "🔄 Reiniciando Frontend para aplicar configurações do tunnel..."

# Parar processo React se estiver rodando
pkill -f "react-scripts start" 2>/dev/null || echo "React não estava rodando"

# Aguardar um momento
sleep 3

# Ir para pasta frontend
cd frontend

# Iniciar React em background com configurações específicas para tunnel
echo "🚀 Iniciando React com configurações do tunnel..."
npm run start:tunnel > /tmp/react-tunnel.log 2>&1 &
REACT_PID=$!

echo "React PID: $REACT_PID"
echo "Log: tail -f /tmp/react-tunnel.log"

# Aguardar React estar pronto
echo "⏳ Aguardando React iniciar..."
for i in {1..15}; do
    if nc -z localhost 3000 2>/dev/null; then
        echo "✅ React rodando na porta 3000 com configurações do tunnel"
        echo "🌐 Agora você pode executar ./setup-tunnel.sh"
        echo ""
        echo "📋 Configurações aplicadas:"
        echo "   - DANGEROUSLY_DISABLE_HOST_CHECK=true"
        echo "   - HOST=0.0.0.0"
        echo "   - Webhook socket configurado"
        exit 0
    fi
    echo "   Tentativa $i/15..."
    sleep 2
done

echo "❌ Falha ao iniciar React. Verifique o log:"
echo "   tail -f /tmp/react-tunnel.log"