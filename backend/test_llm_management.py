#!/usr/bin/env python3
"""
Script de teste para o sistema de gestão de LLM
Testa os endpoints da API sem necessidade do Django rodando
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000/api/rag"

def test_endpoint(endpoint, method="GET", data=None, headers=None):
    """Testa um endpoint específico"""
    url = f"{BASE_URL}/{endpoint}"
    
    if headers is None:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token'  # Token de teste
        }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        
        print(f"\n🔍 Testando: {method} {endpoint}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Sucesso!")
            data = response.json()
            print(f"Resposta: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
        else:
            print(f"❌ Erro: {response.text[:200]}")
        
        return response.status_code == 200, response
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Erro de conexão - servidor Django não está rodando?")
        return False, None
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False, None


def main():
    print("🧪 TESTE DO SISTEMA DE GESTÃO DE LLM")
    print("=" * 50)
    
    # Lista de endpoints para testar
    endpoints = [
        ("llm/current/", "GET"),
        ("llm/available/", "GET"),
        ("llm/metrics/", "GET"),
        ("llm/costs/", "GET"),
        ("llm/history/", "GET"),
    ]
    
    results = []
    
    for endpoint, method in endpoints:
        success, response = test_endpoint(endpoint, method)
        results.append((endpoint, success))
    
    # Teste de alternância (simulado)
    print(f"\n🔄 Testando alternância de provider...")
    switch_data = {
        "provider": "deepseek",
        "test_connection": False,
        "reason": "Teste automatizado"
    }
    
    success, response = test_endpoint("llm/switch/", "POST", switch_data)
    results.append(("llm/switch/", success))
    
    # Teste de conexão
    print(f"\n🔍 Testando conexão...")
    test_data = {
        "provider": "openai"
    }
    
    success, response = test_endpoint("llm/test/", "POST", test_data)
    results.append(("llm/test/", success))
    
    # Resumo dos resultados
    print(f"\n📊 RESUMO DOS TESTES")
    print("=" * 50)
    
    successful = 0
    total = len(results)
    
    for endpoint, success in results:
        status = "✅ OK" if success else "❌ FALHOU"
        print(f"{endpoint:20} - {status}")
        if success:
            successful += 1
    
    print(f"\nResultado: {successful}/{total} testes passaram")
    
    if successful == total:
        print("🎉 Todos os testes passaram!")
        return 0
    else:
        print("⚠️ Alguns testes falharam")
        return 1


def test_switch_script():
    """Testa o script switch_llm.py"""
    print(f"\n🔧 TESTE DO SCRIPT SWITCH_LLM.PY")
    print("=" * 50)
    
    import subprocess
    import os
    
    script_path = "/home/felipealbertuxd/knight-agent/backend/switch_llm.py"
    
    if not os.path.exists(script_path):
        print(f"❌ Script não encontrado: {script_path}")
        return False
    
    try:
        # Teste do menu (sem argumentos)
        result = subprocess.run([
            sys.executable, script_path
        ], capture_output=True, text=True, timeout=10)
        
        if "ALTERNADOR DE LLM AVANÇADO" in result.stdout:
            print("✅ Menu principal OK")
        else:
            print("❌ Menu principal falhou")
            print(f"Output: {result.stdout[:200]}")
            return False
        
        # Teste com --help
        result = subprocess.run([
            sys.executable, script_path, "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if "Script avançado" in result.stdout:
            print("✅ Help OK")
        else:
            print("❌ Help falhou")
            return False
        
        print("✅ Script switch_llm.py funcionando corretamente")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Script demorou muito para responder")
        return False
    except Exception as e:
        print(f"❌ Erro ao testar script: {e}")
        return False


if __name__ == "__main__":
    # Teste dos endpoints da API
    api_result = main()
    
    # Teste do script de alternância
    script_result = test_switch_script()
    
    print(f"\n🏁 RESULTADO FINAL")
    print("=" * 50)
    print(f"API Endpoints: {'✅ OK' if api_result == 0 else '❌ FALHOU'}")
    print(f"Script Switch: {'✅ OK' if script_result else '❌ FALHOU'}")
    
    if api_result == 0 and script_result:
        print(f"\n🎉 SISTEMA DE GESTÃO DE LLM PRONTO!")
        print(f"✨ Acesse: http://localhost:3000/settings (como admin)")
        print(f"🔧 CLI: python switch_llm.py [provider]")
    else:
        print(f"\n⚠️ Sistema precisa de ajustes")
        print(f"📝 Verifique se o servidor Django está rodando")
        print(f"🔐 Verifique se você tem permissões de admin")
    
    sys.exit(0 if api_result == 0 and script_result else 1)