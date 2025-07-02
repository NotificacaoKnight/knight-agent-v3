#!/usr/bin/env python
"""
Script para testar o login de desenvolvedor
"""
import requests
import json

# URL base da API
BASE_URL = "http://localhost:8000"

print("🔍 Testando endpoint de verificação do modo desenvolvedor...")
try:
    response = requests.get(f"{BASE_URL}/api/auth/dev/check/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"❌ Erro ao verificar modo dev: {e}")

print("\n🔐 Testando login de desenvolvedor...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/dev/login/",
        headers={"Content-Type": "application/json"},
        json={}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ Login de desenvolvedor funcionando!")
        data = response.json()
        print(f"Token de sessão: {data.get('session_token')}")
        print(f"Usuário: {data.get('user', {}).get('email')}")
except Exception as e:
    print(f"❌ Erro no login: {e}")

print("\n📝 Instruções para resolver problemas comuns:")
print("1. Certifique-se de que o backend está rodando: python manage.py runserver")
print("2. Verifique se DEV_MODE=True está no arquivo backend/.env")
print("3. Certifique-se de que as migrações foram aplicadas: python manage.py migrate")