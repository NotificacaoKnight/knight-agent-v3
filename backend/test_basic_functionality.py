#!/usr/bin/env python3
"""
Script básico para testar funcionalidades do Knight Agent FastAPI
"""

import requests
import asyncio
import sys
import json
from pathlib import Path

# Configuração da API
API_BASE = "http://localhost:8000"

def test_basic_endpoints():
    """Testa endpoints básicos"""
    print("🔍 Testando endpoints básicos...")

    # Health check
    response = requests.get(f"{API_BASE}/health")
    print(f"Health: {response.status_code} - {response.json()}")

    # Ping
    response = requests.get(f"{API_BASE}/api/ping")
    print(f"Ping: {response.status_code} - {response.json()}")

    # OpenAPI docs
    response = requests.get(f"{API_BASE}/openapi.json")
    print(f"OpenAPI: {response.status_code} - Docs carregadas")

    return True

def test_rag_endpoints():
    """Testa endpoints do sistema RAG"""
    print("\n🤖 Testando sistema RAG...")

    # Test search endpoint sem autenticação (para ver se está funcionando)
    search_data = {
        "query": "teste básico de funcionamento",
        "k": 5
    }

    response = requests.post(f"{API_BASE}/api/rag/search", json=search_data)
    print(f"RAG Search: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"  - Resposta recebida: {len(result.get('response', ''))} chars")
        print(f"  - Documentos encontrados: {len(result.get('documents', []))}")
        print(f"  - Sistema usado: {result.get('system_used', 'N/A')}")
        return True
    else:
        print(f"  - Erro: {response.text}")
        return False

def test_documents_endpoint():
    """Testa endpoint de documentos"""
    print("\n📄 Testando sistema de documentos...")

    # Stats endpoint (não precisa autenticação para stats básicas)
    response = requests.get(f"{API_BASE}/api/documents/stats")
    print(f"Documents Stats: {response.status_code}")

    if response.status_code == 200:
        stats = response.json()
        print(f"  - Total de documentos: {stats.get('total_documents', 0)}")
        print(f"  - Documentos processados: {stats.get('processed_documents', 0)}")
        return True
    else:
        print(f"  - Erro: {response.text}")
        return False

def test_auth_endpoints():
    """Testa endpoints de autenticação"""
    print("\n🔐 Testando sistema de autenticação...")

    # Teste endpoint protegido sem token
    response = requests.get(f"{API_BASE}/api/auth/me")
    print(f"Auth Me (sem token): {response.status_code}")

    if response.status_code == 403:
        print("  ✅ Proteção funcionando corretamente")
        return True
    else:
        print(f"  ❌ Erro inesperado: {response.text}")
        return False

def main():
    """Executa todos os testes"""
    print("🚀 Iniciando testes do Knight Agent FastAPI\n")

    # Verificar se servidor está rodando
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Servidor não está respondendo corretamente")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Servidor não está rodando na porta 8000")
        sys.exit(1)

    # Executar testes
    tests = [
        test_basic_endpoints,
        test_auth_endpoints,
        test_documents_endpoint,
        test_rag_endpoints
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Erro no teste {test.__name__}: {e}")
            results.append(False)

    # Resultados finais
    print(f"\n📊 Resultados dos testes:")
    print(f"✅ Passaram: {sum(results)}/{len(results)}")
    print(f"❌ Falharam: {len(results) - sum(results)}/{len(results)}")

    if all(results):
        print("\n🎉 Todos os testes básicos passaram!")
        return 0
    else:
        print("\n⚠️ Alguns testes falharam, verificar logs acima")
        return 1

if __name__ == "__main__":
    sys.exit(main())