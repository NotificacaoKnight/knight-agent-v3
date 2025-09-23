#!/bin/bash
# Entrypoint script for Docker container
# Executa migrações e inicia o servidor

set -e

echo "🚀 Starting Knight Agent FastAPI..."

# Aguarda PostgreSQL estar pronto
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "✅ PostgreSQL is ready!"

# Executa migrações do Alembic
echo "🔄 Running database migrations..."
alembic upgrade head

echo "✅ Migrations complete!"

# Inicia o servidor
echo "🚀 Starting FastAPI server..."
exec "$@"