#!/usr/bin/env python
"""
Script de teste para verificar a integração de recursos de conhecimento com o sistema RAG
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knight_backend.settings')
django.setup()

from rag.knowledge_resources_service import KnowledgeResourcesService
from knowledge_resources.models import UsefulLink, DownloadableDocument
from authentication.models import User

def test_knowledge_resources_integration():
    """Testa a integração completa dos recursos de conhecimento"""
    
    print("🧪 Iniciando teste de integração de recursos de conhecimento...")
    print("=" * 60)
    
    # 1. Verificar se existem recursos cadastrados
    print("\n📋 1. Verificando recursos cadastrados:")
    
    links_count = UsefulLink.objects.filter(is_active=True).count()
    docs_count = DownloadableDocument.objects.filter(is_active=True).count()
    
    print(f"   ✅ Links úteis ativos: {links_count}")
    print(f"   ✅ Documentos baixáveis ativos: {docs_count}")
    
    if links_count == 0 and docs_count == 0:
        print("\n⚠️  AVISO: Nenhum recurso cadastrado. Criando recursos de exemplo...")
        
        # Criar usuário admin se não existir
        admin_user = User.objects.filter(username='admin').first()
        if not admin_user:
            admin_user = User.objects.create_user(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
        
        # Criar links de exemplo
        example_links = [
            {
                'title': 'Portal do RH',
                'url': 'https://rh.empresa.com.br',
                'description': 'Acesse o portal do RH para solicitar férias, consultar holerites e benefícios',
                'ai_guidance': 'Compartilhar quando o usuário perguntar sobre RH, férias, benefícios, holerite, folha de pagamento',
                'category': 'RH'
            },
            {
                'title': 'Manual de Conduta',
                'url': 'https://docs.empresa.com.br/manual-conduta',
                'description': 'Manual completo de conduta e ética profissional da empresa',
                'ai_guidance': 'Usar quando houver perguntas sobre ética, conduta profissional, regras da empresa',
                'category': 'Compliance'
            },
            {
                'title': 'Suporte TI',
                'url': 'https://ti.empresa.com.br/suporte',
                'description': 'Portal de abertura de chamados e suporte técnico',
                'ai_guidance': 'Compartilhar para problemas técnicos, computador, software, acesso a sistemas',
                'category': 'TI'
            }
        ]
        
        for link_data in example_links:
            link = UsefulLink.objects.create(
                **link_data,
                created_by=admin_user,
                is_active=True
            )
            print(f"   ➕ Link criado: {link.title}")
        
        # Criar documentos de exemplo
        example_docs = [
            {
                'title': 'Formulário de Férias',
                'description': 'Formulário para solicitação de férias',
                'ai_guidance': 'Fornecer quando o funcionário quiser solicitar férias ou perguntar sobre o processo',
                'category': 'RH',
                'file_name': 'formulario_ferias.pdf',
                'file_size': 150000,
                'file_type': 'pdf'
            },
            {
                'title': 'Política de Reembolso',
                'description': 'Documento com as políticas e procedimentos de reembolso',
                'ai_guidance': 'Usar quando houver perguntas sobre reembolso, despesas, prestação de contas',
                'category': 'Financeiro',
                'file_name': 'politica_reembolso.pdf',
                'file_size': 250000,
                'file_type': 'pdf'
            }
        ]
        
        for doc_data in example_docs:
            # Criar arquivo fake para teste
            from django.core.files.base import ContentFile
            fake_file = ContentFile(b'PDF content here', name=doc_data['file_name'])
            
            doc = DownloadableDocument.objects.create(
                title=doc_data['title'],
                description=doc_data['description'],
                ai_guidance=doc_data['ai_guidance'],
                category=doc_data['category'],
                file=fake_file,
                file_name=doc_data['file_name'],
                file_size=doc_data['file_size'],
                file_type=doc_data['file_type'],
                created_by=admin_user,
                is_active=True
            )
            print(f"   ➕ Documento criado: {doc.title}")
        
        print("\n   ✅ Recursos de exemplo criados com sucesso!")
    
    # 2. Testar o serviço de busca de recursos
    print("\n📋 2. Testando serviço de busca de recursos:")
    
    service = KnowledgeResourcesService()
    
    # Queries de teste
    test_queries = [
        "Como faço para solicitar férias?",
        "Preciso do formulário de reembolso",
        "Qual é a política de conduta da empresa?",
        "Estou com problema no computador",
        "Quero consultar meu holerite"
    ]
    
    for query in test_queries:
        print(f"\n   🔍 Query: '{query}'")
        
        resources = service.find_relevant_resources(
            query=query,
            context="Funcionário solicitando informações"
        )
        
        # Mostrar resultados
        if resources['useful_links']:
            print(f"      📎 Links encontrados:")
            for link in resources['useful_links']:
                print(f"         - {link['title']} ({link['category']}) - Score: {link['relevance_score']:.2f}")
        else:
            print(f"      ❌ Nenhum link encontrado")
        
        if resources['downloadable_documents']:
            print(f"      📄 Documentos encontrados:")
            for doc in resources['downloadable_documents']:
                print(f"         - {doc['title']} ({doc['file_type']}) - Score: {doc['relevance_score']:.2f}")
        else:
            print(f"      ❌ Nenhum documento encontrado")
    
    # 3. Testar formatação para LLM
    print("\n📋 3. Testando formatação de recursos para LLM:")
    
    test_resources = {
        'useful_links': [
            {
                'title': 'Portal RH',
                'url': 'https://rh.empresa.com',
                'category': 'RH',
                'description': 'Portal de recursos humanos'
            }
        ],
        'downloadable_documents': [
            {
                'title': 'Formulário Férias',
                'file_type': 'pdf',
                'category': 'RH',
                'description': 'Formulário para solicitar férias'
            }
        ]
    }
    
    formatted = service.format_resources_for_llm(test_resources)
    if formatted:
        print("\n   📝 Formatação para LLM:")
        print("   " + formatted.replace("\n", "\n   "))
    else:
        print("\n   ❌ Erro na formatação")
    
    print("\n" + "=" * 60)
    print("✅ Teste de integração concluído!")
    
    # 4. Testar integração com RAG (opcional)
    print("\n📋 4. Testando integração com sistema RAG:")
    try:
        from rag.agentic_rag_service import AgenticRAGServiceSync
        
        rag_service = AgenticRAGServiceSync()
        
        # Fazer uma busca simples
        test_query = "Como solicitar férias?"
        print(f"\n   🤖 Testando query RAG: '{test_query}'")
        
        result = rag_service.search(
            query=test_query,
            k=3
        )
        
        # Verificar se recursos foram incluídos
        if result.get('useful_links'):
            print(f"   ✅ Links incluídos na resposta: {len(result['useful_links'])}")
        else:
            print(f"   ⚠️  Nenhum link incluído na resposta")
        
        if result.get('downloadable_documents'):
            print(f"   ✅ Documentos incluídos na resposta: {len(result['downloadable_documents'])}")
        else:
            print(f"   ⚠️  Nenhum documento incluído na resposta")
        
        print(f"\n   📝 Resposta (primeiros 200 chars):")
        print(f"   {result.get('response', '')[:200]}...")
        
    except Exception as e:
        print(f"\n   ❌ Erro ao testar integração RAG: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Todos os testes concluídos!")

if __name__ == "__main__":
    test_knowledge_resources_integration()