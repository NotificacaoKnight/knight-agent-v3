#!/usr/bin/env python3
"""
Script avançado para alternar facilmente entre provedores LLM
Inclui validação de API keys, teste de conexão e backup automático

Uso: python switch_llm.py [openai|deepseek|gemini|cohere|groq] [options]
Opções:
  --no-test      Pula o teste de conexão
  --no-backup    Pula o backup do .env
  --force        Força a mudança mesmo com falhas
  --reason TEXT  Especifica o motivo da mudança
"""
import os
import sys
import re
import json
import requests
import time
from datetime import datetime
from pathlib import Path


def validate_api_key(provider):
    """Valida se a API key está configurada para o provider"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if not os.path.exists(env_path):
        return False, "Arquivo .env não encontrado"
    
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    key_mapping = {
        'openai': r'OPENAI_API_KEY=(.+)',
        'deepseek': r'DEEPSEEK_API_KEY=(.+)',
        'gemini': r'GEMINI_API_KEY=(.+)',
        'cohere': r'COHERE_API_KEY=(.+)',
        'groq': r'GROQ_API_KEY=(.+)'
    }
    
    pattern = key_mapping.get(provider)
    if not pattern:
        return False, f"Provider {provider} não suportado"
    
    match = re.search(pattern, content)
    if not match:
        return False, f"API key para {provider} não encontrada no .env"
    
    api_key = match.group(1).strip()
    if not api_key or api_key.startswith('your-') or api_key.lower() in ['none', 'null', '']:
        return False, f"API key para {provider} não está configurada"
    
    return True, api_key


def test_connection(provider, api_key):
    """Testa a conexão com o provider"""
    print(f"🔍 Testando conexão com {provider}...")
    
    try:
        if provider == 'openai':
            return test_openai(api_key)
        elif provider == 'deepseek':
            return test_deepseek(api_key)
        elif provider == 'gemini':
            return test_gemini(api_key)
        elif provider == 'cohere':
            return test_cohere(api_key)
        elif provider == 'groq':
            return test_groq(api_key)
        else:
            return False, f"Teste não implementado para {provider}"
    
    except Exception as e:
        return False, f"Erro no teste: {str(e)}"


def test_openai(api_key):
    """Testa conexão com OpenAI"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'gpt-4o-mini',
        'messages': [{'role': 'user', 'content': 'Test'}],
        'max_tokens': 5,
        'temperature': 0.1
    }
    
    response = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers=headers,
        json=data,
        timeout=10
    )
    
    if response.status_code == 200:
        return True, "Conexão bem-sucedida"
    elif response.status_code == 401:
        return False, "API key inválida"
    else:
        return False, f"Erro HTTP {response.status_code}: {response.text[:100]}"


def test_deepseek(api_key):
    """Testa conexão com DeepSeek"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'deepseek-chat',
        'messages': [{'role': 'user', 'content': 'Test'}],
        'max_tokens': 5,
        'temperature': 0.1
    }
    
    response = requests.post(
        'https://api.deepseek.com/v1/chat/completions',
        headers=headers,
        json=data,
        timeout=10
    )
    
    if response.status_code == 200:
        return True, "Conexão bem-sucedida"
    elif response.status_code == 401:
        return False, "API key inválida"
    else:
        return False, f"Erro HTTP {response.status_code}: {response.text[:100]}"


def test_gemini(api_key):
    """Testa conexão com Gemini"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    data = {
        'contents': [{
            'parts': [{'text': 'Test'}]
        }],
        'generationConfig': {
            'maxOutputTokens': 5,
            'temperature': 0.1
        }
    }
    
    response = requests.post(url, json=data, timeout=10)
    
    if response.status_code == 200:
        return True, "Conexão bem-sucedida"
    elif response.status_code == 400:
        error_data = response.json()
        if 'API_KEY_INVALID' in str(error_data):
            return False, "API key inválida"
        return False, f"Erro na requisição: {error_data}"
    else:
        return False, f"Erro HTTP {response.status_code}: {response.text[:100]}"


def test_cohere(api_key):
    """Testa conexão com Cohere"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'message': 'Test',
        'model': 'command-r-plus',
        'max_tokens': 5,
        'temperature': 0.1
    }
    
    response = requests.post(
        'https://api.cohere.ai/v1/chat',
        headers=headers,
        json=data,
        timeout=10
    )
    
    if response.status_code == 200:
        return True, "Conexão bem-sucedida"
    elif response.status_code == 401:
        return False, "API key inválida"
    else:
        return False, f"Erro HTTP {response.status_code}: {response.text[:100]}"


def test_groq(api_key):
    """Testa conexão com Groq"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'llama3-70b-8192',
        'messages': [{'role': 'user', 'content': 'Test'}],
        'max_tokens': 5,
        'temperature': 0.1
    }
    
    response = requests.post(
        'https://api.groq.com/openai/v1/chat/completions',
        headers=headers,
        json=data,
        timeout=10
    )
    
    if response.status_code == 200:
        return True, "Conexão bem-sucedida"
    elif response.status_code == 401:
        return False, "API key inválida"
    else:
        return False, f"Erro HTTP {response.status_code}: {response.text[:100]}"


def backup_env_file():
    """Cria backup do arquivo .env"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if not os.path.exists(env_path):
        return False, "Arquivo .env não encontrado"
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{env_path}.backup_{timestamp}"
    
    try:
        with open(env_path, 'r', encoding='utf-8') as original:
            with open(backup_path, 'w', encoding='utf-8') as backup:
                backup.write(original.read())
        
        return True, backup_path
    
    except Exception as e:
        return False, f"Erro ao criar backup: {e}"


def update_env_file(provider):
    """Atualiza o arquivo .env com o provedor escolhido"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if not os.path.exists(env_path):
        print("❌ Arquivo .env não encontrado!")
        return False
    
    # Ler arquivo atual
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Atualizar LLM_PROVIDER
    pattern = r'LLM_PROVIDER=\w+'
    new_line = f'LLM_PROVIDER={provider}'
    
    if re.search(pattern, content):
        content = re.sub(pattern, new_line, content)
    else:
        # Se não existe, adicionar após as configurações de LLM
        if '# LLM Configuration' in content:
            content = content.replace(
                '# LLM Configuration',
                f'# LLM Configuration\n{new_line}'
            )
        else:
            content += f'\n{new_line}\n'
    
    # Salvar arquivo atualizado
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def log_switch(old_provider, new_provider, reason, success):
    """Registra a mudança de provider"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'old_provider': old_provider,
        'new_provider': new_provider,
        'reason': reason,
        'success': success,
        'script_version': '2.0'
    }
    
    try:
        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / 'llm_switches.log'
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{json.dumps(log_entry, ensure_ascii=False)}\n")
    
    except Exception as e:
        print(f"⚠️ Erro ao gravar log: {e}")


def estimate_cost_impact(old_provider, new_provider):
    """Estima o impacto de custos da mudança"""
    # Custos estimados por 1k tokens (input/output médio)
    provider_costs = {
        'openai': 0.0004,      # GPT-4o-mini médio
        'deepseek': 0.00021,   # DeepSeek médio
        'gemini': 0.0002,      # Gemini 1.5 Flash médio
        'cohere': 0.009,       # Command-R-Plus médio
        'groq': 0.0007         # Llama3-70b médio
    }
    
    old_cost = provider_costs.get(old_provider, 0)
    new_cost = provider_costs.get(new_provider, 0)
    
    if old_cost and new_cost:
        diff_percent = ((new_cost - old_cost) / old_cost) * 100
        monthly_estimate = (new_cost - old_cost) * 100000 * 30  # Assumindo 100k tokens/dia
        
        return {
            'old_cost_per_1k': old_cost,
            'new_cost_per_1k': new_cost,
            'diff_percent': round(diff_percent, 1),
            'monthly_impact_usd': round(monthly_estimate, 2)
        }
    
    return None


def show_current_config():
    """Mostra a configuração atual"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if not os.path.exists(env_path):
        print("❌ Arquivo .env não encontrado!")
        return
    
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extrair provedor atual
    provider_match = re.search(r'LLM_PROVIDER=(\w+)', content)
    current_provider = provider_match.group(1) if provider_match else 'não definido'
    
    # Extrair chaves disponíveis
    available_keys = []
    
    key_patterns = {
        'openai': r'OPENAI_API_KEY=(.+)',
        'deepseek': r'DEEPSEEK_API_KEY=(.+)',
        'gemini': r'GEMINI_API_KEY=(.+)',
        'cohere': r'COHERE_API_KEY=(.+)',
        'groq': r'GROQ_API_KEY=(.+)'
    }
    
    for provider, pattern in key_patterns.items():
        match = re.search(pattern, content)
        if match and match.group(1).strip() and not match.group(1).startswith('your-'):
            available_keys.append(provider)
    
    print(f"\n🤖 **CONFIGURAÇÃO ATUAL DO LLM**")
    print(f"┌─────────────────────────────────")
    print(f"│ Provedor Ativo: {current_provider.upper()}")
    print(f"│ Chaves Configuradas: {', '.join(available_keys) if available_keys else 'Nenhuma'}")
    print(f"└─────────────────────────────────")


def parse_arguments():
    """Parse argumentos da linha de comando"""
    args = {
        'provider': None,
        'no_test': False,
        'no_backup': False,
        'force': False,
        'reason': 'CLI switch'
    }
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg.startswith('--'):
            if arg == '--no-test':
                args['no_test'] = True
            elif arg == '--no-backup':
                args['no_backup'] = True
            elif arg == '--force':
                args['force'] = True
            elif arg == '--reason' and i + 1 < len(sys.argv):
                args['reason'] = sys.argv[i + 1]
                i += 1
            elif arg == '--help':
                print(__doc__)
                sys.exit(0)
        else:
            if not args['provider']:
                args['provider'] = arg.lower()
        
        i += 1
    
    return args


def main():
    """Função principal"""
    
    providers = {
        'openai': {
            'name': 'OpenAI (GPT-4, GPT-3.5)',
            'icon': '🤖',
            'description': 'Qualidade alta, custo médio'
        },
        'deepseek': {
            'name': 'DeepSeek',
            'icon': '🧠',
            'description': 'Custo baixo, boa performance'
        },
        'gemini': {
            'name': 'Google Gemini',
            'icon': '🌟',
            'description': 'Gratuito com limite, rápido'
        },
        'cohere': {
            'name': 'Cohere',
            'icon': '🎯',
            'description': 'Otimizado para RAG'
        },
        'groq': {
            'name': 'Groq',
            'icon': '⚡',
            'description': 'Muito rápido, menos preciso'
        }
    }
    
    # Parse argumentos
    args = parse_arguments()
    
    # Mostrar configuração atual
    show_current_config()
    
    # Se não há provider, mostrar menu
    if not args['provider']:
        print(f"\n🔄 **ALTERNADOR DE LLM AVANÇADO v2.0**")
        print(f"┌─────────────────────────────────────────────────────────────")
        print(f"│ Uso: python switch_llm.py [provedor] [opções]")
        print(f"│")
        print(f"│ Provedores disponíveis:")
        
        for key, info in providers.items():
            print(f"│  {info['icon']} {key:10} - {info['name']:25} ({info['description']})")
        
        print(f"│")
        print(f"│ Opções:")
        print(f"│  --no-test      Pula o teste de conexão")
        print(f"│  --no-backup    Pula o backup do .env")
        print(f"│  --force        Força a mudança mesmo com falhas")
        print(f"│  --reason TEXT  Especifica o motivo da mudança")
        print(f"│  --help         Mostra esta ajuda")
        print(f"└─────────────────────────────────────────────────────────────")
        print(f"\n💡 Exemplos:")
        print(f"   python switch_llm.py openai")
        print(f"   python switch_llm.py deepseek --no-test --reason 'Reduzir custos'")
        return
    
    provider = args['provider']
    
    if provider not in providers:
        print(f"❌ Provedor '{provider}' não é válido!")
        print(f"📝 Provedores disponíveis: {', '.join(providers.keys())}")
        return
    
    # Obter provider atual
    try:
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        with open(env_path, 'r') as f:
            content = f.read()
        current_match = re.search(r'LLM_PROVIDER=(\w+)', content)
        current_provider = current_match.group(1) if current_match else 'não definido'
    except:
        current_provider = 'não definido'
    
    if current_provider.lower() == provider:
        print(f"✅ {providers[provider]['icon']} {providers[provider]['name']} já está ativo!")
        return
    
    print(f"\n🔄 **INICIANDO ALTERNÂNCIA DE PROVIDER**")
    print(f"├─ De: {current_provider.upper()}")
    print(f"├─ Para: {provider.upper()}")
    print(f"├─ Motivo: {args['reason']}")
    print(f"└─ Teste: {'❌ Desabilitado' if args['no_test'] else '✅ Habilitado'}")
    
    success = False
    backup_path = None
    
    try:
        # 1. Validar API key
        print(f"\n📋 **ETAPA 1: VALIDAÇÃO DA API KEY**")
        valid, api_key_or_error = validate_api_key(provider)
        
        if not valid:
            print(f"❌ {api_key_or_error}")
            if not args['force']:
                print(f"💡 Use --force para pular esta validação")
                return
            else:
                print(f"⚠️ Continuando com --force...")
                api_key_or_error = "forced"
        else:
            print(f"✅ API key encontrada e válida")
            api_key = api_key_or_error
        
        # 2. Teste de conexão
        if not args['no_test'] and valid:
            print(f"\n🔍 **ETAPA 2: TESTE DE CONEXÃO**")
            test_success, test_message = test_connection(provider, api_key)
            
            if test_success:
                print(f"✅ {test_message}")
            else:
                print(f"❌ {test_message}")
                if not args['force']:
                    print(f"💡 Use --no-test para pular o teste ou --force para continuar")
                    return
                else:
                    print(f"⚠️ Continuando com --force...")
        else:
            print(f"\n⏭️ **ETAPA 2: TESTE DE CONEXÃO PULADO**")
        
        # 3. Backup do .env
        if not args['no_backup']:
            print(f"\n💾 **ETAPA 3: BACKUP DO ARQUIVO .ENV**")
            backup_success, backup_result = backup_env_file()
            
            if backup_success:
                backup_path = backup_result
                print(f"✅ Backup criado: {os.path.basename(backup_path)}")
            else:
                print(f"❌ {backup_result}")
                if not args['force']:
                    print(f"💡 Use --no-backup para pular o backup ou --force para continuar")
                    return
                else:
                    print(f"⚠️ Continuando com --force...")
        else:
            print(f"\n⏭️ **ETAPA 3: BACKUP PULADO**")
        
        # 4. Estimativa de custos
        print(f"\n💰 **ETAPA 4: ANÁLISE DE CUSTOS**")
        cost_impact = estimate_cost_impact(current_provider, provider)
        
        if cost_impact:
            print(f"├─ Custo atual: ${cost_impact['old_cost_per_1k']:.6f}/1k tokens")
            print(f"├─ Novo custo: ${cost_impact['new_cost_per_1k']:.6f}/1k tokens")
            
            if cost_impact['diff_percent'] > 0:
                print(f"├─ Impacto: +{cost_impact['diff_percent']}% (+${cost_impact['monthly_impact_usd']:.2f}/mês)")
                print(f"└─ ⚠️ Custo AUMENTARÁ")
            elif cost_impact['diff_percent'] < 0:
                print(f"├─ Impacto: {cost_impact['diff_percent']}% (${cost_impact['monthly_impact_usd']:.2f}/mês)")
                print(f"└─ 💰 Economia ESPERADA")
            else:
                print(f"└─ ➡️ Custo similar")
        else:
            print(f"└─ ❓ Não foi possível calcular o impacto")
        
        # 5. Atualizar arquivo .env
        print(f"\n⚙️ **ETAPA 5: ATUALIZANDO CONFIGURAÇÃO**")
        if update_env_file(provider):
            print(f"✅ Arquivo .env atualizado")
            success = True
        else:
            print(f"❌ Falha ao atualizar .env")
            return
        
        # 6. Log da mudança
        print(f"\n📝 **ETAPA 6: REGISTRANDO MUDANÇA**")
        log_switch(current_provider, provider, args['reason'], success)
        print(f"✅ Mudança registrada nos logs")
        
        # Sucesso
        print(f"\n🎉 **ALTERNÂNCIA CONCLUÍDA COM SUCESSO!**")
        print(f"┌─────────────────────────────────────────────────────────────")
        print(f"│ ✅ Provider alterado para: {providers[provider]['name']}")
        print(f"│ 📝 {providers[provider]['description']}")
        print(f"│ 💾 Backup: {os.path.basename(backup_path) if backup_path else 'Não criado'}")
        print(f"│")
        print(f"│ 🚀 PRÓXIMOS PASSOS:")
        print(f"│ 1. Reinicie o servidor Django:")
        print(f"│    cd backend && python manage.py runserver")
        print(f"│")
        print(f"│ 2. Teste uma consulta no sistema para confirmar")
        print(f"└─────────────────────────────────────────────────────────────")
        
    except KeyboardInterrupt:
        print(f"\n\n❌ **OPERAÇÃO CANCELADA PELO USUÁRIO**")
        if backup_path and os.path.exists(backup_path):
            print(f"💾 Backup preservado: {backup_path}")
        return
        
    except Exception as e:
        print(f"\n💥 **ERRO INESPERADO**: {e}")
        print(f"📝 Detalhes do erro foram registrados nos logs")
        
        # Log do erro
        log_switch(current_provider, provider, f"{args['reason']} (FAILED: {e})", False)
        
        # Tentar restaurar backup se houve falha
        if backup_path and os.path.exists(backup_path):
            try:
                env_path = os.path.join(os.path.dirname(__file__), '.env')
                with open(backup_path, 'r') as backup:
                    with open(env_path, 'w') as env_file:
                        env_file.write(backup.read())
                print(f"🔄 Configuração restaurada do backup")
            except:
                print(f"⚠️ Falha ao restaurar backup - restaure manualmente: {backup_path}")
        
        return


if __name__ == '__main__':
    main()