#!/usr/bin/env python
"""
Teste básico do sistema multi-agent
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knight_backend.settings')
django.setup()

def test_multi_agent_import():
    """Testa imports do sistema multi-agent consolidado"""
    try:
        from rag.consolidated_multi_agent import consolidated_multi_agent_service
        print("✅ Sistema consolidado importado com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro no import: {e}")
        return False

def test_multi_agent_basic():
    """Testa funcionalidade básica do sistema consolidado"""
    try:
        from rag.consolidated_multi_agent import consolidated_multi_agent_service
        
        # Teste com query simples
        result = consolidated_multi_agent_service.process_query(
            query="Olá, como está funcionando?",
            user=None
        )
        
        print(f"✅ Processamento consolidado funcionou")
        print(f"   Agente usado: {result.get('agent_used', 'unknown')}")
        print(f"   Modo: {result.get('metadata', {}).get('processing_mode', 'unknown')}")
        print(f"   Resposta: {result.get('response', 'N/A')[:100]}...")
        print(f"   Caminho execução: {result.get('execution_path', [])}")
        
        return True
    except Exception as e:
        print(f"❌ Erro no processamento: {e}")
        return False

def test_endpoints_import():
    """Testa imports dos endpoints"""
    try:
        from rag.multi_agent_views import (
            MultiAgentSearchView,
            BardReportsView,
            WizardTrainingView
        )
        print("✅ Views multi-agent importadas com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro no import das views: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testando sistema multi-agent Knight...")
    print()
    
    # Testes de import
    print("1. Testando imports...")
    test_multi_agent_import()
    test_endpoints_import()
    print()
    
    # Teste básico
    print("2. Testando funcionalidade básica...")
    test_multi_agent_basic()
    print()
    
    print("🎯 Teste concluído!")