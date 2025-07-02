#!/bin/bash
# Script para corrigir as migrações

echo "🔧 Corrigindo migrações do banco de dados..."

# Ativar ambiente virtual
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "❌ Ambiente virtual não encontrado. Execute setup.sh primeiro."
    exit 1
fi

# Criar migrações
echo "📝 Criando arquivos de migração..."
python manage.py makemigrations

# Aplicar migrações
echo "🗄️ Aplicando migrações ao banco de dados..."
python manage.py migrate

# Criar superusuário (opcional)
echo ""
echo "✅ Migrações aplicadas com sucesso!"
echo ""
echo "Deseja criar um superusuário para o Django Admin? (s/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY]|[sS])$ ]]; then
    python manage.py createsuperuser
fi

echo ""
echo "🎉 Pronto! Agora você pode iniciar o servidor:"
echo "python manage.py runserver"