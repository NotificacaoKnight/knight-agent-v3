-- Script para instalar e configurar pgvector
-- Execute este script como superusuário do PostgreSQL

-- 1. Criar extensão pgvector se não existir
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Verificar se a extensão foi instalada
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 3. Testar se a extensão funciona
SELECT '[1,2,3]'::vector;

-- 4. Verificar operadores disponíveis para o tipo vector
SELECT
    o.oprname AS operator,
    o.oprcode AS function_name,
    t1.typname AS left_type,
    t2.typname AS right_type
FROM pg_operator o
JOIN pg_type t1 ON o.oprleft = t1.oid
JOIN pg_type t2 ON o.oprright = t2.oid
WHERE t1.typname = 'vector' OR t2.typname = 'vector'
ORDER BY o.oprname;

-- Se você vir operadores como <->, <#>, <=> então está tudo funcionando!