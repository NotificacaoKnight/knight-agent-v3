#!/usr/bin/env python
"""
Script para testar a integração do Agno com o Knight Agent
"""

import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knight_backend.settings')
django.setup()

from rag.llm_providers import AgnoProvider, LLMManager
from django.conf import settings

def test_agno_provider():
    """Testa o provider Agno diretamente"""
    print("=== Testando Agno Provider ===")
    
    # Criar provider
    provider = AgnoProvider()
    
    # Verificar disponibilidade
    if provider.is_available():
        print("✓ Agno provider está disponível")
        print(f"  - Model Provider: {provider.model_provider}")
        print(f"  - Model Name: {provider.model_name}")
    else:
        print("✗ Agno provider NÃO está disponível")
        print("  Verifique as configurações no .env:")
        print("  - AGNO_MODEL_PROVIDER")
        print("  - AGNO_MODEL_NAME")
        print("  - API key do provider escolhido")
        return False
    
    # Testar geração simples
    print("\n--- Teste 1: Geração simples ---")
    response = provider.generate_response(
        prompt="Olá! Quem é você?",
        max_tokens=200
    )
    
    if response['success']:
        print(f"✓ Resposta gerada com sucesso")
        print(f"Resposta: {response['response'][:200]}...")
    else:
        print(f"✗ Erro: {response['error']}")
        return False
    
    # Testar com contexto
    print("\n--- Teste 2: Geração com contexto ---")
    context = [
        "O Knight Agent é um assistente IA corporativo desenvolvido para a empresa XYZ.",
        "Ele foi criado para responder perguntas sobre políticas e documentos internos.",
        "O sistema usa RAG (Retrieval Augmented Generation) para fornecer respostas precisas."
    ]
    
    response = provider.generate_response(
        prompt="O que é o Knight Agent?",
        context=context,
        max_tokens=300
    )
    
    if response['success']:
        print(f"✓ Resposta com contexto gerada com sucesso")
        print(f"Documentos usados: {response['documents_used']}")
        print(f"Resposta: {response['response'][:300]}...")
    else:
        print(f"✗ Erro: {response['error']}")
        return False
    
    return True

def test_llm_manager():
    """Testa o LLMManager com Agno"""
    print("\n\n=== Testando LLM Manager com Agno ===")
    
    # Criar manager
    manager = LLMManager()
    
    # Listar providers disponíveis
    available = manager.get_available_providers()
    print(f"Providers disponíveis: {', '.join(available)}")
    
    if 'agno' in available:
        print("✓ Agno está disponível no LLMManager")
    else:
        print("✗ Agno NÃO está disponível no LLMManager")
        return False
    
    # Testar geração via manager
    print("\n--- Teste via LLMManager ---")
    response = manager.generate_response(
        prompt="Qual é o horário de funcionamento do RH?",
        provider='agno',
        max_tokens=200
    )
    
    if response['success']:
        print(f"✓ Resposta gerada via LLMManager")
        print(f"Provider usado: {response['provider']}")
        print(f"Resposta: {response['response'][:200]}...")
    else:
        print(f"✗ Erro: {response['error']}")
        return False
    
    return True

def main():
    """Executa todos os testes"""
    print("Iniciando testes de integração Agno...\n")
    
    # Verificar configurações
    print("Configurações atuais:")
    print(f"- LLM_PROVIDER: {settings.LLM_PROVIDER}")
    print(f"- AGNO_MODEL_PROVIDER: {getattr(settings, 'AGNO_MODEL_PROVIDER', 'não configurado')}")
    print(f"- AGNO_MODEL_NAME: {getattr(settings, 'AGNO_MODEL_NAME', 'não configurado')}")
    print()
    
    # Executar testes
    success = True
    
    if not test_agno_provider():
        success = False
    
    if not test_llm_manager():
        success = False
    
    # Resultado final
    print("\n" + "="*50)
    if success:
        print("✓ TODOS OS TESTES PASSARAM!")
        print("\nPróximos passos:")
        print("1. Configure LLM_PROVIDER=agno no .env para usar Agno como provider principal")
        print("2. Execute o servidor: python manage.py runserver")
        print("3. Teste via API ou interface web")
    else:
        print("✗ Alguns testes falharam.")
        print("Verifique as configurações e tente novamente.")

if __name__ == "__main__":
    main()