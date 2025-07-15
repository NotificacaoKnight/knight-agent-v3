#!/bin/bash

# Script para configurar local tunnel para o Knight Agent

echo "🚀 Configurando Local Tunnel para Knight Agent..."

# Verificar se o Node.js está instalado
if ! command -v node &> /dev/null
then
    echo "❌ Node.js não está instalado. Por favor, instale o Node.js primeiro."
    exit 1
fi

# Instalar localtunnel globalmente se não estiver instalado
if ! command -v lt &> /dev/null
then
    echo "📦 Instalando localtunnel..."
    npm install -g localtunnel
fi

# Verificar se as portas estão sendo usadas
check_port() {
    local port=$1
    local service=$2
    if ! nc -z localhost $port 2>/dev/null; then
        echo "❌ $service não está rodando na porta $port"
        echo "   Inicie o $service primeiro:"
        if [ "$service" = "Backend" ]; then
            echo "   cd backend && python manage.py runserver"
        else
            echo "   cd frontend && npm start"
        fi
        return 1
    fi
    return 0
}

# Função para capturar URL real do tunnel
capture_tunnel_url() {
    local port=$1
    local service=$2
    # Usar subdomínio fixo para evitar mudanças constantes no Azure AD
    local subdomain="knight-${service,,}-dev"
    
    echo "🔧 Iniciando tunnel para $service (porta $port)..."
    
    # Criar arquivo temporário para capturar a saída
    local temp_file="/tmp/tunnel_${service,,}_output.txt"
    
    # Iniciar tunnel em background e capturar saída
    lt --port $port --subdomain $subdomain > $temp_file 2>&1 &
    local tunnel_pid=$!
    
    # Aguardar tunnel estar pronto
    local max_attempts=10
    local attempt=0
    local tunnel_url=""
    
    while [ $attempt -lt $max_attempts ]; do
        sleep 2
        
        # Tentar extrair URL do arquivo de saída
        if [ -f "$temp_file" ]; then
            tunnel_url=$(grep -o "https://[^[:space:]]*\.loca\.lt" "$temp_file" | head -1)
            if [ ! -z "$tunnel_url" ]; then
                break
            fi
        fi
        
        attempt=$((attempt + 1))
        echo "   Aguardando tunnel... (tentativa $attempt/$max_attempts)"
    done
    
    if [ ! -z "$tunnel_url" ]; then
        echo "✅ $service tunnel iniciado!"
        echo "📌 URL do $service: $tunnel_url"
        
        # Salvar URL para referência
        echo "$tunnel_url" > "/tmp/tunnel_${service,,}_url.txt"
        
        # Definir variáveis globais
        if [ "$service" = "Backend" ]; then
            BACKEND_URL="$tunnel_url"
            BACKEND_PID=$tunnel_pid
        else
            FRONTEND_URL="$tunnel_url"
            FRONTEND_PID=$tunnel_pid
        fi
        
        return 0
    else
        echo "❌ Falha ao iniciar tunnel para $service"
        kill $tunnel_pid 2>/dev/null
        return 1
    fi
}

# Menu de opções
echo ""
echo "Escolha o que deseja expor:"
echo "1) Apenas Backend (API)"
echo "2) Apenas Frontend"
echo "3) Backend e Frontend (Recomendado)"
echo -n "Opção: "
read choice

case $choice in
    1)
        if check_port 8000 "Backend"; then
            if capture_tunnel_url 8000 "Backend"; then
                echo ""
                echo "🔗 Compartilhe esta URL com seus testers:"
                echo "   $BACKEND_URL"
                echo ""
                echo "📋 Para testar a API diretamente:"
                echo "   GET $BACKEND_URL/api/auth/me/"
            fi
        else
            exit 1
        fi
        ;;
    2)
        if check_port 3000 "Frontend"; then
            if capture_tunnel_url 3000 "Frontend"; then
                echo ""
                echo "🔗 Compartilhe esta URL com seus testers:"
                echo "   $FRONTEND_URL"
                echo ""
                echo "⚠️  IMPORTANTE: Configure a variável REACT_APP_API_URL no frontend"
                echo "   para apontar para o tunnel do backend se necessário"
            fi
        else
            exit 1
        fi
        ;;
    3)
        # Verificar ambos os serviços
        backend_ok=false
        frontend_ok=false
        
        if check_port 8000 "Backend"; then
            backend_ok=true
        fi
        
        if check_port 3000 "Frontend"; then
            frontend_ok=true
        fi
        
        if [ "$backend_ok" = false ] || [ "$frontend_ok" = false ]; then
            echo ""
            echo "❌ Inicie os serviços necessários antes de continuar"
            exit 1
        fi
        
        # Iniciar tunnels
        echo ""
        if capture_tunnel_url 8000 "Backend" && capture_tunnel_url 3000 "Frontend"; then
            echo ""
            echo "🎉 Tunnels configurados com sucesso!"
            echo ""
            echo "📨 URLs FIXAS para compartilhar com testers:"
            echo "   Frontend: $FRONTEND_URL"
            echo "   Backend:  $BACKEND_URL"
            echo ""
            echo "🔧 Configure no Azure AD:"
            echo "   Redirect URI: $FRONTEND_URL"
            echo "   Logout URI: $FRONTEND_URL"
            echo "   (Use apenas a URL base, sem /auth/callback)"
            echo ""
            echo "📋 Instruções para os testers:"
            echo "   1. Acesse: $FRONTEND_URL"
            echo "   2. Faça login com Microsoft Azure AD"
            echo "   3. Teste upload de documentos e chat"
            echo ""
            echo "💡 Envie também o arquivo TESTING_GUIDE.md com instruções detalhadas"
        else
            echo "❌ Falha ao configurar tunnels"
            exit 1
        fi
        ;;
    *)
        echo "❌ Opção inválida"
        exit 1
        ;;
esac

echo ""
echo "📝 Notas importantes:"
echo "- As URLs serão válidas enquanto este script estiver rodando"
echo "- Pressione Ctrl+C para parar os tunnels"
echo "- Você pode precisar aceitar os termos do localtunnel na primeira vez"
echo "- URLs salvas em /tmp/tunnel_*_url.txt para referência"
echo ""

# Função para cleanup ao sair
cleanup() {
    echo ""
    echo "🛑 Parando tunnels..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    # Limpar arquivos temporários
    rm -f /tmp/tunnel_*_output.txt
    echo "✅ Tunnels parados"
    exit 0
}

# Registrar função de cleanup
trap cleanup SIGINT SIGTERM

echo "🚦 Tunnels rodando... Pressione Ctrl+C para parar"
echo ""

# Manter o script rodando e mostrar status
while true; do
    sleep 30
    echo "⏰ $(date '+%H:%M:%S') - Tunnels ativos"
done