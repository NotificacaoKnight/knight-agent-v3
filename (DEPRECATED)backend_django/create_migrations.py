#!/usr/bin/env python
"""
Script para criar todas as migrações necessárias
"""
import os
import sys
import django

# Adicionar o diretório backend ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knight_backend.settings')
django.setup()

from django.core.management import call_command

# Lista de apps
apps = ['authentication', 'documents', 'rag', 'chat', 'downloads']

print("🔧 Criando diretórios de migrações...")
for app in apps:
    migrations_dir = os.path.join(app, 'migrations')
    if not os.path.exists(migrations_dir):
        os.makedirs(migrations_dir)
        # Criar __init__.py
        init_file = os.path.join(migrations_dir, '__init__.py')
        open(init_file, 'a').close()
        print(f"✅ Criado diretório de migrações para {app}")

print("\n📝 Criando arquivos de migração...")
for app in apps:
    try:
        call_command('makemigrations', app)
        print(f"✅ Migrações criadas para {app}")
    except Exception as e:
        print(f"⚠️  Erro ao criar migrações para {app}: {e}")

print("\n🗄️ Aplicando migrações...")
try:
    call_command('migrate')
    print("✅ Todas as migrações foram aplicadas!")
except Exception as e:
    print(f"❌ Erro ao aplicar migrações: {e}")

print("\n🎉 Processo concluído!")
print("Agora você pode executar: python manage.py runserver")