#!/usr/bin/env python
"""
Script para resetar o banco de dados e recriar todas as migrações
"""
import os
import sys
import shutil

# Diretório do backend
backend_dir = os.path.dirname(os.path.abspath(__file__))

print("🗑️  Removendo banco de dados SQLite...")
db_file = os.path.join(backend_dir, 'db.sqlite3')
if os.path.exists(db_file):
    os.remove(db_file)
    print("✅ Banco de dados removido")

print("\n🗑️  Removendo arquivos de migração...")
apps = ['authentication', 'documents', 'rag', 'chat', 'downloads']
for app in apps:
    migrations_dir = os.path.join(backend_dir, app, 'migrations')
    if os.path.exists(migrations_dir):
        # Manter apenas __init__.py
        for filename in os.listdir(migrations_dir):
            if filename != '__init__.py' and filename.endswith('.py'):
                file_path = os.path.join(migrations_dir, filename)
                os.remove(file_path)
                print(f"✅ Removido: {file_path}")
        
        # Remover diretório __pycache__ se existir
        pycache_dir = os.path.join(migrations_dir, '__pycache__')
        if os.path.exists(pycache_dir):
            shutil.rmtree(pycache_dir)

print("\n✅ Limpeza concluída!")
print("\nAgora execute os seguintes comandos:")
print("1. python manage.py makemigrations")
print("2. python manage.py migrate")
print("3. python manage.py runserver")