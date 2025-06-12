# Configuração de Provedores LLM - Knight Agent

## 🤖 Visão Geral

O Knight suporta múltiplos provedores LLM com fallback automático para garantir alta disponibilidade. O sistema é otimizado para RAG (Retrieval-Augmented Generation) e funciona tanto com APIs externas quanto modelos self-hosted.

## 🏆 Provedores Recomendados

### 1. Cohere (Recomendado para RAG)
**Melhor opção para produção**

**Vantagens:**
- RAG nativo otimizado
- Suporte para citações automáticas
- Baixa latência
- Excelente qualidade para português
- Custo-benefício superior

**Configuração:**
```env
LLM_PROVIDER=cohere
COHERE_API_KEY=sua-api-key
```

**Modelos disponíveis:**
- `command-r-plus` (recomendado)
- `command-r`
- `command`

### 2. Groq (Melhor Performance)
**Mais rápido para respostas em tempo real**

**Vantagens:**
- Latência ultra-baixa (<500ms)
- Boa qualidade
- Preços competitivos

**Configuração:**
```env
LLM_PROVIDER=groq
GROQ_API_KEY=sua-api-key
```

**Modelos disponíveis:**
- `llama3-70b-8192`
- `llama3-8b-8192`
- `mixtral-8x7b-32768`

### 3. Together AI (Variedade de Modelos)
**Boa opção para experimentação**

**Vantagens:**
- Muitos modelos disponíveis
- Preços acessíveis
- Suporte a modelos open-source

**Configuração:**
```env
LLM_PROVIDER=together
TOGETHER_API_KEY=sua-api-key
```

### 4. Ollama (Self-hosted)
**Melhor para controle total e privacidade**

**Vantagens:**
- Dados ficam internos
- Sem custos por token
- Controle total do modelo
- Offline capability

**Configuração:**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## 🔧 Configuração Detalhada

### Cohere Setup

#### 1. Obter API Key
1. Acesse [Cohere Dashboard](https://dashboard.cohere.com/)
2. Crie uma conta
3. Gere uma API key
4. Configure no `.env`

#### 2. Configurações Específicas
```python
# backend/rag/llm_providers.py - CohereProvider
self.model = "command-r-plus"  # Modelo otimizado para RAG

# Configurações do chat
response = self.client.chat(
    message=prompt,
    documents=documents,  # RAG nativo
    model=self.model,
    max_tokens=1000,
    temperature=0.7,
    preamble="Você é o Knight..."  # System prompt
)
```

#### 3. Features Avançadas
```python
# Citações automáticas
citations = response.citations
for citation in citations:
    print(f"Fonte: {citation.document_ids}")
    print(f"Texto: {citation.text}")
```

### Groq Setup

#### 1. Obter API Key
1. Acesse [Groq Console](https://console.groq.com/)
2. Crie uma conta
3. Gere uma API key
4. Configure no `.env`

#### 2. Modelos Recomendados
```python
# Para máxima velocidade
GROQ_MODEL = "llama3-8b-8192"

# Para melhor qualidade
GROQ_MODEL = "llama3-70b-8192"

# Para textos longos
GROQ_MODEL = "mixtral-8x7b-32768"
```

### Together AI Setup

#### 1. Configuração
```env
TOGETHER_API_KEY=sua-api-key
TOGETHER_MODEL=meta-llama/Llama-2-70b-chat-hf
```

#### 2. Modelos Disponíveis
- `meta-llama/Llama-2-70b-chat-hf`
- `mistralai/Mixtral-8x7B-Instruct-v0.1`
- `togethercomputer/RedPajama-INCITE-7B-Chat`

### Ollama Setup

#### 1. Instalação
```bash
# Linux/macOS
curl -fsSL https://ollama.ai/install.sh | sh

# Windows - baixe do site oficial
```

#### 2. Baixar Modelos
```bash
# Modelos recomendados para português
ollama pull llama3.2          # Rápido, boa qualidade
ollama pull mistral           # Equilibrado
ollama pull qwen2.5:14b       # Excelente para português

# Modelos menores para desenvolvimento
ollama pull llama3.2:1b       # Muito rápido
ollama pull phi3              # Eficiente
```

#### 3. Configuração de Produção
```bash
# Systemd service para Ollama
sudo systemctl enable ollama
sudo systemctl start ollama

# GPU support (NVIDIA)
sudo docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

#### 4. Customização de Modelos
```bash
# Criar modelo customizado para empresa
cat > Modelfile << 'EOF'
FROM llama3.2

PARAMETER temperature 0.7
PARAMETER num_ctx 4096

SYSTEM """
Você é o Knight, assistente IA da [NOME_EMPRESA]. 
Responda sempre em português brasileiro.
Use apenas informações dos documentos fornecidos.
Seja prestativo e profissional.
"""
EOF

ollama create knight-empresa -f Modelfile
```

## ⚡ Otimização de Performance

### 1. Configurações por Provedor

#### Cohere
```python
# Otimizações para RAG
COHERE_CONFIG = {
    'max_tokens': 1000,
    'temperature': 0.7,
    'k': 0,  # Não usar top-k
    'p': 0.9,  # Top-p para diversidade controlada
    'frequency_penalty': 0.1,
    'presence_penalty': 0.1
}
```

#### Groq
```python
# Configurações para velocidade máxima
GROQ_CONFIG = {
    'max_tokens': 800,  # Menos tokens = mais rápido
    'temperature': 0.5,  # Menos criatividade = mais consistência
    'top_p': 0.9,
    'stream': False  # Desabilitar streaming para batch
}
```

#### Ollama
```python
# Configurações para qualidade
OLLAMA_CONFIG = {
    'num_predict': 1000,
    'temperature': 0.7,
    'top_k': 40,
    'top_p': 0.9,
    'num_ctx': 4096,  # Contexto maior para RAG
    'num_thread': 8  # Ajustar conforme CPU
}
```

### 2. Sistema de Fallback

```python
# Ordem de fallback configurável
FALLBACK_ORDER = [
    'cohere',    # Primary
    'groq',      # Fast fallback
    'together',  # Secondary
    'ollama'     # Local fallback
]

# Timeout por provedor
PROVIDER_TIMEOUTS = {
    'cohere': 30,
    'groq': 15,
    'together': 45,
    'ollama': 60
}
```

## 📊 Comparação de Provedores

| Provedor | Latência | Qualidade | Custo | RAG Nativo | Português |
|----------|----------|-----------|--------|------------|-----------|
| Cohere   | Média    | Alta      | Médio  | ✅         | ⭐⭐⭐⭐⭐ |
| Groq     | Baixa    | Boa       | Baixo  | ❌         | ⭐⭐⭐⭐   |
| Together | Alta     | Boa       | Baixo  | ❌         | ⭐⭐⭐     |
| Ollama   | Variável | Variável  | Zero   | ❌         | ⭐⭐⭐⭐   |

## 🔄 Configuração de Fallback Automático

### 1. Health Checks
```python
# Verificação automática de saúde dos provedores
def check_provider_health():
    for provider_name, provider in providers.items():
        try:
            # Teste simples de conectividade
            result = provider.generate_response(
                "Teste de conectividade", 
                max_tokens=10, 
                timeout=5
            )
            if result['success']:
                mark_provider_healthy(provider_name)
            else:
                mark_provider_unhealthy(provider_name)
        except Exception:
            mark_provider_unhealthy(provider_name)
```

### 2. Métricas e Monitoramento
```python
# Coleta de métricas por provedor
PROVIDER_METRICS = {
    'cohere': {
        'total_requests': 1500,
        'success_rate': 0.99,
        'avg_latency_ms': 800,
        'cost_per_1k_tokens': 0.03
    },
    'groq': {
        'total_requests': 3000,
        'success_rate': 0.95,
        'avg_latency_ms': 200,
        'cost_per_1k_tokens': 0.01
    }
}
```

## 🏢 Configurações por Ambiente

### Desenvolvimento
```env
# Usar Ollama local para desenvolvimento
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:1b  # Modelo pequeno e rápido
```

### Teste
```env
# Groq para testes rápidos
LLM_PROVIDER=groq
GROQ_API_KEY=test-key
```

### Produção
```env
# Cohere para produção
LLM_PROVIDER=cohere
COHERE_API_KEY=prod-key

# Fallback configurado
FALLBACK_PROVIDERS=groq,together,ollama
```

## 🔒 Segurança e Compliance

### 1. Proteção de Dados
```python
# Configurações de privacidade por provedor
PRIVACY_SETTINGS = {
    'cohere': {
        'log_requests': False,
        'store_conversations': False
    },
    'ollama': {
        'local_only': True,
        'no_telemetry': True
    }
}
```

### 2. Rate Limiting
```python
# Limites por provedor
RATE_LIMITS = {
    'cohere': {'requests_per_minute': 100},
    'groq': {'requests_per_minute': 300},
    'together': {'requests_per_minute': 60},
    'ollama': {'requests_per_minute': 1000}  # Sem limite externo
}
```

## 🚀 Recomendações de Uso

### Para Produção Empresarial
1. **Primary**: Cohere (RAG nativo, alta qualidade)
2. **Fallback**: Groq (velocidade)
3. **Local**: Ollama (dados sensíveis)

### Para Desenvolvimento
1. **Primary**: Ollama (sem custos)
2. **Teste**: Groq (verificar velocidade)

### Para Escala Massiva
1. **Primary**: Groq (custo baixo, velocidade)
2. **Quality**: Cohere (casos importantes)
3. **Backup**: Together AI (diversidade)

## 📝 Troubleshooting

### Problemas Comuns

#### Cohere não responde
```bash
# Verificar quota
curl -H "Authorization: Bearer $COHERE_API_KEY" \
     https://api.cohere.ai/v1/check-api-key

# Testar conectividade
curl -X POST https://api.cohere.ai/v1/chat \
     -H "Authorization: Bearer $COHERE_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"message": "test"}'
```

#### Ollama não conecta
```bash
# Verificar status
curl http://localhost:11434/api/tags

# Verificar logs
docker logs ollama

# Restart service
sudo systemctl restart ollama
```

#### Performance lenta
```python
# Monitorar tempo de resposta
import time
start = time.time()
response = llm.generate_response(prompt)
duration = time.time() - start
print(f"Response time: {duration:.2f}s")
```