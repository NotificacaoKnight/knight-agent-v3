#!/bin/bash
# Script para verificar bancos de dados PostgreSQL local

echo "==================================="
echo "Verificando bancos de dados locais"
echo "==================================="

# Listar todos os bancos de dados
echo -e "\n📦 Listando todos os bancos de dados:"
sudo -u postgres psql -c "\l" | grep -E "knight|fastapi"

# Verificar knight_db
echo -e "\n🔍 Verificando banco knight_db:"
sudo -u postgres psql -d knight_db -c "\dt" 2>/dev/null || echo "❌ Banco knight_db não existe"

# Verificar knight_fastapi_db
echo -e "\n🔍 Verificando banco knight_fastapi_db:"
sudo -u postgres psql -d knight_fastapi_db -c "\dt" 2>/dev/null || echo "❌ Banco knight_fastapi_db não existe"

# Verificar outros possíveis bancos
echo -e "\n🔍 Verificando banco knight_backend:"
sudo -u postgres psql -d knight_backend -c "\dt" 2>/dev/null || echo "❌ Banco knight_backend não existe"

echo -e "\n==================================="
echo "Digite o nome do banco que deseja exportar (ou 'none' se não houver):"
read DB_NAME

if [ "$DB_NAME" != "none" ]; then
    echo "📤 Exportando banco $DB_NAME..."
    sudo -u postgres pg_dump $DB_NAME > ${DB_NAME}_backup.sql
    echo "✅ Backup salvo em ${DB_NAME}_backup.sql"
    echo "📊 Tamanho do backup: $(du -h ${DB_NAME}_backup.sql | cut -f1)"
fi