#!/bin/bash

# Script completo para iniciar o Knight Agent com tunnel para testes

echo "🚀 Knight Agent - Deploy para Testes"
echo "===================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para logging colorido
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Verificar dependências
check_dependencies() {
    log_info "Verificando dependências..."
    
    # Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js não encontrado. Instale o Node.js primeiro."
        exit 1
    fi
    
    # Python
    if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
        log_error "Python não encontrado. Instale o Python primeiro."
        exit 1
    fi
    
    # Verificar se está no diretório correto
    if [ ! -f "setup-tunnel.sh" ]; then
        log_error "Execute este script da pasta raiz do projeto (onde está o setup-tunnel.sh)"
        exit 1
    fi
    
    log_success "Dependências verificadas!"
}

# Iniciar serviços
start_services() {
    log_info "Iniciando serviços..."
    
    # Ir para backend e ativar ambiente virtual se existir
    cd backend
    
    if [ -d "venv" ]; then
        log_info "Ativando ambiente virtual..."
        source venv/bin/activate
    fi
    
    # Verificar se requirements estão instalados
    if ! python -c "import django" &> /dev/null; then
        log_warning "Dependências do Django não encontradas. Instalando..."
        pip install -r requirements.txt
    fi
    
    # Aplicar migrações se necessário
    log_info "Verificando migrações..."
    python manage.py migrate --check &> /dev/null
    if [ $? -ne 0 ]; then
        log_info "Aplicando migrações..."
        python manage.py migrate
    fi
    
    # Iniciar Django em background
    log_info "Iniciando servidor Django..."
    python manage.py runserver 8000 > /tmp/django.log 2>&1 &
    DJANGO_PID=$!
    
    # Aguardar Django estar pronto
    sleep 5
    if ! nc -z localhost 8000 2>/dev/null; then
        log_error "Falha ao iniciar Django. Verifique /tmp/django.log"
        exit 1
    fi
    log_success "Django rodando na porta 8000"
    
    # Voltar para raiz e iniciar frontend
    cd ..
    cd frontend
    
    # Verificar se node_modules existe
    if [ ! -d "node_modules" ]; then
        log_warning "Dependências do Node.js não encontradas. Instalando..."
        npm install
    fi
    
    # Iniciar React em background
    log_info "Iniciando servidor React..."
    npm start > /tmp/react.log 2>&1 &
    REACT_PID=$!
    
    # Aguardar React estar pronto
    sleep 10
    if ! nc -z localhost 3000 2>/dev/null; then
        log_error "Falha ao iniciar React. Verifique /tmp/react.log"
        exit 1
    fi
    log_success "React rodando na porta 3000"
    
    cd ..
}

# Iniciar tunnels
start_tunnels() {
    log_info "Configurando tunnels..."
    
    # Executar script de tunnel
    ./setup-tunnel.sh
}

# Função de cleanup
cleanup() {
    log_warning "Parando serviços..."
    
    # Parar processes
    if [ ! -z "$DJANGO_PID" ]; then
        kill $DJANGO_PID 2>/dev/null
        log_info "Django parado"
    fi
    
    if [ ! -z "$REACT_PID" ]; then
        kill $REACT_PID 2>/dev/null
        log_info "React parado"
    fi
    
    # Limpar logs temporários
    rm -f /tmp/django.log /tmp/react.log
    
    log_success "Cleanup concluído"
    exit 0
}

# Registrar cleanup
trap cleanup SIGINT SIGTERM

# Menu principal
main() {
    echo ""
    echo "Este script irá:"
    echo "1. Verificar dependências"
    echo "2. Iniciar backend Django (porta 8000)"
    echo "3. Iniciar frontend React (porta 3000)"
    echo "4. Configurar tunnels para acesso externo"
    echo ""
    read -p "Continuar? (y/N): " confirm
    
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo "Operação cancelada."
        exit 0
    fi
    
    check_dependencies
    start_services
    start_tunnels
}

# Executar script principal
main