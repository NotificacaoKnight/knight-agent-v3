# 🚀 Plano de Melhorias do Sistema RAG Knight Agent

## 📊 Status Atual e Problemas Identificados

### Performance
- ⚠️ **Tempo de resposta**: 5-15 segundos (inaceitável)
- ⚠️ **Sem cache**: Recalcula embeddings sempre
- ⚠️ **LLM lento**: Usando modelos pesados sem streaming
- ⚠️ **Buscas redundantes**: Deep mode faz múltiplas buscas desnecessárias

### Naturalidade das Respostas
- ⚠️ **Prompts robóticos**: Textos genéricos sem personalidade
- ⚠️ **Sem contextualização**: Ignora contexto corporativo
- ⚠️ **Formatação pobre**: Respostas em bloco sem estrutura
- ⚠️ **Linguagem formal demais**: Não soa natural em PT-BR

### Arquitetura
- ⚠️ **Falso agêntico**: Não usa LangGraph apesar de mencionado
- ⚠️ **Fallback ineficiente**: Provider manager sem priorização inteligente
- ⚠️ **Sem observabilidade**: Falta logging e métricas detalhadas

## 🎯 Melhorias Prioritárias

### Fase 1: Performance Crítica (Implementar Imediatamente)

#### 1.1 Otimização de Cache
```python
# Implementar cache Redis para embeddings e resultados
- Cache de embeddings de documentos
- Cache de resultados de busca por query
- TTL configurável por tipo de cache
```

#### 1.2 Streaming de Respostas
```python
# Implementar Server-Sent Events (SSE) para streaming
- Respostas aparecem em tempo real
- Feedback visual durante processamento
- Suporte a cancelamento de requisições
```

#### 1.3 LLM Provider Otimizado
```python
# Configurar modelos mais leves e rápidos
- Usar Gemini Flash ou GPT-4o-mini para fast mode
- DeepSeek apenas para deep mode
- Implementar timeout agressivo (5s fast, 15s deep)
```

### Fase 2: Naturalidade e UX (Esta Semana)

#### 2.1 Sistema de Prompts Naturais
```python
# Novo sistema de prompts com personalidade
- Criar persona "Knight" - assistente corporativo amigável
- Templates específicos por tipo de pergunta
- Usar linguagem corporativa natural em PT-BR
- Incluir emojis e formatação markdown
```

#### 2.2 Contextualização Inteligente
```python
# Melhorar uso de contexto
- Detectar departamento/cargo do usuário
- Personalizar respostas por perfil
- Manter histórico de conversas recentes
- Sugerir links e documentos relacionados
```

#### 2.3 Formatação Rica
```python
# Melhorar apresentação das respostas
- Usar markdown para estruturar conteúdo
- Bullets e numeração para listas
- Destacar informações importantes
- Incluir links clicáveis para fontes
```

### Fase 3: Arquitetura Agêntica Real (Próxima Sprint)

#### 3.1 Implementar LangGraph
```python
# RAG agêntico verdadeiro com state machine
- Planner Node: Analisa e planeja estratégia
- Search Node: Busca inteligente multi-step
- Validator Node: Verifica qualidade
- Refiner Node: Melhora respostas
- Knowledge Node: Sugere recursos adicionais
```

#### 3.2 Multi-Agent System
```python
# Agentes especializados por domínio
- HR Agent: Questões de RH e benefícios
- IT Agent: Suporte técnico e sistemas
- Finance Agent: Questões financeiras
- General Agent: Perguntas gerais
```

#### 3.3 Observabilidade Completa
```python
# Sistema de métricas e logging
- Traces de cada etapa do pipeline
- Métricas de latência por componente
- Dashboard de monitoramento
- Alertas automáticos
```

## 💻 Implementação Imediata

### 1. Novo Sistema de Prompts Naturais

```python
# app/services/rag/prompts.py

KNIGHT_PERSONALITY = """
Você é o Knight, assistente virtual da empresa. Seja:
- 🤝 Amigável e acolhedor
- 💬 Natural e conversacional
- 📋 Objetivo mas não robótico
- 😊 Use emojis com moderação
- ✅ Estruture bem as respostas

Evite:
- Linguagem excessivamente formal
- Respostas genéricas
- Blocos de texto sem formatação
"""

RESPONSE_TEMPLATES = {
    "greeting": "Olá! 👋 Sou o Knight, seu assistente virtual. {context}",
    "not_found": "Hmm, não encontrei essa informação específica nos documentos. 🤔 {suggestion}",
    "multiple_results": "Encontrei algumas informações relevantes sobre isso:\n\n{results}",
    "single_result": "Aqui está o que encontrei: {result}\n\n📎 Fonte: {source}"
}
```

### 2. Cache Redis Otimizado

```python
# app/services/cache_service.py

class CacheService:
    def __init__(self):
        self.redis = Redis.from_url(settings.REDIS_URL)

    async def get_cached_search(self, query_hash: str):
        """Cache de resultados de busca por 1 hora"""
        return await self.redis.get(f"search:{query_hash}")

    async def cache_embeddings(self, doc_id: str, embeddings):
        """Cache permanente de embeddings"""
        await self.redis.set(f"emb:{doc_id}", embeddings)
```

### 3. Streaming com SSE

```python
# app/api/rag_stream.py

@router.get("/stream/generate")
async def stream_answer(query: str):
    async def generate():
        # Yield status inicial
        yield f"data: {json.dumps({'status': 'searching'})}\n\n"

        # Busca com yield de progresso
        results = await rag_service.search(query)
        yield f"data: {json.dumps({'status': 'generating', 'sources': len(results)})}\n\n"

        # Stream da resposta token por token
        async for token in llm_stream_generate(prompt):
            yield f"data: {json.dumps({'token': token})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### 4. Detector de Complexidade Melhorado

```python
# app/services/rag/complexity_detector.py

class ComplexityDetector:
    def detect(self, query: str) -> str:
        # Análise mais inteligente
        word_count = len(query.split())
        has_multiple_questions = '?' in query and query.count('?') > 1

        # Categorização melhorada
        if word_count < 5 and not has_multiple_questions:
            return "instant"  # Resposta imediata do cache
        elif self._is_navigation_query(query):
            return "navigation"  # Apenas links e redirecionamentos
        elif self._is_complex_analysis(query):
            return "deep"  # Análise profunda
        else:
            return "fast"  # Busca padrão rápida
```

## 📈 Métricas de Sucesso

### Targets de Performance
- ✅ **Fast mode**: < 2 segundos
- ✅ **Deep mode**: < 5 segundos
- ✅ **Instant mode**: < 500ms (cache)
- ✅ **Time to First Token**: < 1 segundo

### Qualidade das Respostas
- ✅ **Naturalidade**: Score > 8/10 em testes
- ✅ **Relevância**: Precision > 85%
- ✅ **Completude**: Recall > 80%
- ✅ **Satisfação**: NPS > 70

## 🚦 Próximos Passos

1. **Hoje**: Implementar cache Redis e prompts naturais
2. **Amanhã**: Adicionar streaming SSE
3. **Esta semana**: Otimizar LLM providers
4. **Próxima sprint**: Implementar LangGraph agêntico

## 📝 Notas de Implementação

- Manter compatibilidade com API atual
- Fazer rollout gradual com feature flags
- Monitorar métricas em produção
- Coletar feedback dos usuários

---
*Documento criado em 07/10/2025 - Sistema Knight Agent v2.0*