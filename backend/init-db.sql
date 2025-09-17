-- Script de inicialização do PostgreSQL
-- Executado automaticamente quando o container do PostgreSQL é criado

-- Criar extensão pgvector (essencial para o sistema RAG)
CREATE EXTENSION IF NOT EXISTS vector;

-- Criar usuário e banco (caso não existam)
-- Nota: No docker-compose já configuramos via env vars

-- Configurações de performance para desenvolvimento
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- Reload configuração
SELECT pg_reload_conf();