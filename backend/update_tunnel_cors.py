#!/usr/bin/env python3
"""
Script para atualizar configurações CORS para aceitar requisições do localtunnel
"""

import os
import sys

def update_cors_settings():
    """Atualiza as configurações CORS no Django settings"""
    
    # Caminho para o arquivo settings.py
    settings_path = os.path.join(os.path.dirname(__file__), 'knight_backend', 'settings.py')
    
    if not os.path.exists(settings_path):
        print("❌ Arquivo settings.py não encontrado!")
        return False
    
    # Ler o arquivo atual
    with open(settings_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Configurações CORS para localtunnel
    cors_config = '''
# CORS Configuration for LocalTunnel
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://*.loca.lt",  # LocalTunnel domains
]

CORS_ALLOW_CREDENTIALS = True

# Para desenvolvimento com tunnel, permitir todos os headers
CORS_ALLOW_ALL_ORIGINS = False  # Manter False para segurança
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.loca\.lt$",  # Regex para dominios localtunnel
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CSRF_TRUSTED_ORIGINS = [
    "https://*.loca.lt",
]
'''
    
    # Verificar se já foi adicionado
    if "LocalTunnel" in content:
        print("✅ Configurações CORS para LocalTunnel já estão presentes!")
        return True
    
    # Adicionar as configurações CORS no final do arquivo
    content += cors_config
    
    # Backup do arquivo original
    backup_path = settings_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(open(settings_path, 'r', encoding='utf-8').read())
    
    # Escrever o arquivo atualizado
    with open(settings_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Configurações CORS atualizadas com sucesso!")
    print(f"📁 Backup salvo em: {backup_path}")
    print("")
    print("🔄 Reinicie o servidor Django para aplicar as mudanças:")
    print("   python manage.py runserver")
    
    return True

def show_usage():
    """Mostra instruções de uso"""
    print("🚀 Script de Configuração CORS para LocalTunnel")
    print("")
    print("Este script atualiza o settings.py para aceitar requisições de localtunnel.")
    print("")
    print("Após executar este script:")
    print("1. Execute o setup-tunnel.sh (Linux/Mac) ou setup-tunnel.bat (Windows)")
    print("2. Reinicie o servidor Django")
    print("3. Compartilhe as URLs geradas com seus testers")
    print("")

if __name__ == "__main__":
    show_usage()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        exit(0)
    
    try:
        success = update_cors_settings()
        if success:
            print("🎯 Próximos passos:")
            print("1. Execute: ./setup-tunnel.sh (ou setup-tunnel.bat no Windows)")
            print("2. Reinicie o servidor: python manage.py runserver")
            print("3. Compartilhe as URLs com os testers!")
        else:
            exit(1)
    except Exception as e:
        print(f"❌ Erro ao atualizar configurações: {e}")
        exit(1)