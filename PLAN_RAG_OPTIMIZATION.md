# Plano de Otimização do Sistema RAG - Knight Agent

**Data de Criação**: 2025-01-07
**Status**: Em Execução
**Objetivo**: Transformar o RAG em um assistente corporativo natural, rápido e contextual, seguindo as melhores práticas de 2025.

---

## 📊 Problemas Identificados

### Problemas Críticos
1. **Sistema "Agentic" inexistente**: Comentário "TODO: Implement agentic RAG with LangGraph" sem implementação real
2. **Dois modos (fast/deep) desnecessários**: Abordagem ultrapassada que gera respostas artificiais
3. **Prompts robóticos**: Instruções muito técnicas, sem personalidade ou naturalidade
4. **Performance ruim**: Múltiplas tentativas de busca desperdiçando tempo (3x max_attempts)
5. **Sem streaming**: Usuário espera toda resposta carregar antes de ver qualquer coisa

### Problemas Secundários
6. **Contexto verboso**: Formato `[1. Document - Página X]` muito formal
7. **Knowledge resources isolados**: Links e documentos aparecem separados do texto
8. **Sem memória conversacional**: Cada query é tratada isoladamente
9. **Parâmetros fixos**: Temperatura e max_tokens não adaptam ao contexto
10. **UI confusa**: Seletor de modo expõe complexidade desnecessária ao usuário

---

## 🎯 Objetivos do Projeto

### Performance
- ⚡ First token latency < 500ms (tempo até primeira palavra aparecer)
- 🚀 Resposta completa < 3s para 90% das queries
- 💾 Redução de 40% no uso de tokens via compressão de contexto

### Naturalidade
- 🗣️ Respostas conversacionais em português brasileiro natural
- 🎭 Persona consistente: assistente corporativo prestativo e objetivo
- 🔗 Integração orgânica de links e documentos no fluxo da conversa

### Inteligência
- 🧠 Contexto mantido entre 5-10 mensagens consecutivas
- 📚 Busca contextualizada baseada em histórico de conversa
- 🎯 Seleção inteligente de chunks com diversidade (MMR)

### Experiência do Usuário
- 🖥️ Interface simplificada sem opções técnicas
- 📊 Feedback visual claro do que o sistema está fazendo
- ⚡ Sensação de resposta instantânea com streaming

---

## 📋 Etapas de Implementação

### ✅ Etapa 1: Unificação e Simplificação do Pipeline RAG

#### 1.1 Remover Sistema de Modos (fast/deep/auto)
**Arquivo**: `backend/app/services/rag/rag_service.py`

**O que fazer**:
- Eliminar parâmetro `mode` de `RAGQuery` schema
- Remover métodos `_fast_pipeline()` e `_deep_pipeline()`
- Remover método `_detect_complexity()`
- Criar método único `_unified_pipeline()` que decide estratégia internamente
- Atualizar endpoint `/api/rag/generate` para não aceitar `mode`

**Impacto**: Simplifica código, remove decisões do usuário, melhora manutenibilidade

---

#### 1.2 Implementar Busca Inteligente Única
**Arquivo**: `backend/app/services/rag/rag_service.py`

**O que fazer**:
- Substituir loop de `max_attempts=3` por busca única otimizada
- Implementar scoring híbrido com pesos adaptativos:
  - Queries curtas (< 10 palavras): 70% semântico, 30% keyword
  - Queries longas: 50% semântico, 50% keyword
- Implementar threshold adaptativo:
  - Calcular média e desvio padrão dos scores
  - Usar threshold = média - 0.5 * desvio
- Remover método `_refine_query()` (desnecessário com boa busca)

**Impacto**: Reduz latência de 3x para 1x, melhora relevância dos resultados

---

#### 1.3 Otimizar Seleção de Chunks
**Arquivo**: `backend/app/services/rag/context_optimizer.py` (novo)

**O que criar**:
```python
class ContextOptimizer:
    def select_chunks_mmr(chunks, query_embedding, k, lambda_param=0.5):
        """Maximum Marginal Relevance para diversidade"""

    def compress_context(chunks, max_tokens):
        """Remove redundâncias entre chunks"""

    def format_context_natural(chunks):
        """Formata contexto sem marcações técnicas"""
```

**Algoritmo MMR**:
1. Selecionar chunk mais relevante primeiro
2. Para próximos chunks: balancear relevância vs dissimilaridade
3. Evitar chunks muito similares entre si
4. Priorizar chunks com metadados úteis (título seção, data)

**Impacto**: Melhora diversidade de informações, reduz redundância

---

### ✅ Etapa 2: Naturalização de Prompts e Respostas

#### 2.1 Redesign Completo dos System Prompts
**Arquivo**: `backend/app/services/rag/prompt_templates.py` (novo)

**Prompt Atual (Robótico)**:
```
Com base no contexto fornecido, responda à seguinte pergunta de forma clara e precisa.
Se a resposta não estiver no contexto, diga que não há informações suficientes.

Pergunta: {query}

Responda em português brasileiro.
```

**Novo Prompt (Natural)**:
```
Você é o Knight, assistente de IA da empresa. Sua função é ajudar colaboradores com informações corporativas de forma clara, direta e amigável.

Contexto da conversa:
{conversation_history}

Informações disponíveis:
{context}

Recursos adicionais:
{knowledge_resources}

Pergunta do colaborador: {query}

Responda naturalmente em português brasileiro, como se estivesse conversando com um colega. Seja objetivo mas prestativo. Se as informações disponíveis não forem suficientes para responder completamente, seja honesto sobre isso e sugira alternativas quando possível.
```

**Princípios do novo prompt**:
- ✅ Define persona clara (Knight, assistente da empresa)
- ✅ Tom conversacional ("você", "colaborador")
- ✅ Instruções implícitas (naturalidade, objetividade)
- ✅ Remove jargões técnicos ("contexto fornecido", "base de conhecimento")
- ✅ Permite flexibilidade ("quando possível", "sugira alternativas")

---

#### 2.2 Formatação de Contexto Natural
**Arquivo**: `backend/app/services/rag/context_optimizer.py`

**Formato Atual (Técnico)**:
```
[1. Manual do Colaborador - Página 15]
Férias podem ser solicitadas com 30 dias de antecedência...

[2. Política de RH - Página 8]
O processo de férias segue as diretrizes da CLT...
```

**Novo Formato (Natural)**:
```
Segundo o Manual do Colaborador, férias podem ser solicitadas com 30 dias de antecedência...

A Política de RH reforça que o processo de férias segue as diretrizes da CLT...
```

**Implementação**:
```python
def format_context_natural(chunks: List[Dict]) -> str:
    context_parts = []

    for chunk in chunks:
        # Identificar fonte de forma natural
        source = chunk.get('document_title', 'documentação interna')
        content = chunk['content']

        # Integrar fonte no texto naturalmente
        if 'segundo' not in content.lower() and 'de acordo' not in content.lower():
            intro = random.choice([
                f"Segundo {source}, {content}",
                f"De acordo com {source}, {content}",
                f"Conforme {source}, {content}",
                f"{source} informa que {content}"
            ])
            context_parts.append(intro)
        else:
            context_parts.append(content)

    return "\n\n".join(context_parts)
```

---

#### 2.3 Integração Natural de Knowledge Resources
**Arquivo**: `backend/app/services/knowledge_resources_service.py`

**Formato Atual (Separado)**:
```
RECURSOS ADICIONAIS:

LINKS ÚTEIS DISPONÍVEIS:
- [Portal RH](url) - Sistema de RH
- [Intranet](url) - Portal interno

DOCUMENTOS PARA DOWNLOAD:
- Formulário de Férias - formulario.pdf
```

**Novo Formato (Integrado)**:
```python
def format_resources_natural(resources: Dict) -> str:
    """Formata recursos de forma natural para o prompt"""

    if not resources['useful_links'] and not resources['downloadable_documents']:
        return ""

    parts = []

    # Links úteis integrados
    if resources['useful_links']:
        links_intro = random.choice([
            "Você pode acessar:",
            "Links úteis:",
            "Recursos disponíveis:"
        ])
        parts.append(links_intro)

        for link in resources['useful_links']:
            # Contextualizar POR QUE o link é útil
            parts.append(f"- {link['title']} ({link['url']}): {link['description']}")

    # Documentos integrados
    if resources['downloadable_documents']:
        docs_intro = random.choice([
            "Documentos disponíveis para download:",
            "Preparei estes documentos que podem ajudar:",
            "Você pode baixar:"
        ])
        parts.append("\n" + docs_intro)

        for doc in resources['downloadable_documents']:
            parts.append(f"- {doc['title']}: {doc['description']}")

    return "\n".join(parts)
```

**Instrução no System Prompt**:
```
Se houver links ou documentos nos recursos adicionais, mencione-os naturalmente na resposta quando forem relevantes. Por exemplo:
- "Você pode conferir mais detalhes no Portal RH"
- "Preparei o Formulário de Férias para você baixar"
- "Para isso, acesse a Intranet (link acima)"
```

---

### ✅ Etapa 3: Implementação de Streaming de Respostas

#### 3.1 Backend - FastAPI Streaming
**Arquivo**: `backend/app/services/rag/streaming_service.py` (novo)

**Implementação SSE**:
```python
from fastapi.responses import StreamingResponse
import asyncio
import json

class StreamingService:
    async def stream_rag_response(
        self,
        query: str,
        session_id: str,
        db: AsyncSession
    ):
        """Stream RAG response using Server-Sent Events"""

        async def event_generator():
            try:
                # 1. Enviar evento de início
                yield self._format_sse({
                    'type': 'start',
                    'message': 'Buscando informações...'
                })

                # 2. Realizar busca
                search_results = await self.search_service.search(query, k=5, db=db)

                yield self._format_sse({
                    'type': 'search_complete',
                    'chunks_found': len(search_results)
                })

                # 3. Preparar contexto
                context = await self.context_optimizer.prepare_context(search_results, query)

                # 4. Stream de geração LLM
                yield self._format_sse({
                    'type': 'generating',
                    'message': 'Gerando resposta...'
                })

                # 5. Stream tokens do LLM
                async for token in self.llm_provider.stream_generate(
                    prompt=prompt,
                    context=context
                ):
                    yield self._format_sse({
                        'type': 'token',
                        'content': token
                    })

                # 6. Enviar fontes e recursos
                yield self._format_sse({
                    'type': 'sources',
                    'data': search_results[:3]
                })

                # 7. Enviar evento de conclusão
                yield self._format_sse({
                    'type': 'done'
                })

            except Exception as e:
                yield self._format_sse({
                    'type': 'error',
                    'message': str(e)
                })

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    def _format_sse(self, data: dict) -> str:
        """Formata dados como Server-Sent Event"""
        return f"data: {json.dumps(data)}\n\n"
```

---

#### 3.2 Adicionar Suporte a Streaming nos LLM Providers
**Arquivo**: `backend/app/services/rag/llm_providers.py`

**Adicionar método abstrato**:
```python
class LLMProvider(ABC):
    # ... métodos existentes ...

    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream text generation token by token"""
        pass
```

**Implementação para cada provider**:
```python
# OpenAI
async def stream_generate(self, prompt, context, max_tokens, temperature, **kwargs):
    if not self.initialized:
        self.initialize()

    messages = [{"role": "system", "content": context}, {"role": "user", "content": prompt}]

    stream = await self.client.chat.completions.create(
        model=self.model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
        **kwargs
    )

    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# DeepSeek (similar ao OpenAI)
async def stream_generate(self, prompt, context, max_tokens, temperature, **kwargs):
    # Mesma implementação que OpenAI (API compatível)
    ...

# Gemini
async def stream_generate(self, prompt, context, max_tokens, temperature, **kwargs):
    if not self.initialized:
        self.initialize()

    full_prompt = f"{context}\n\n{prompt}" if context else prompt

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: self.model.generate_content(
            full_prompt,
            stream=True,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )
    )

    for chunk in response:
        if chunk.text:
            yield chunk.text
```

---

#### 3.3 Criar Endpoint /api/rag/stream
**Arquivo**: `backend/app/api/rag.py`

```python
from app.services.rag.streaming_service import streaming_service

@router.post("/stream")
async def stream_rag_answer(
    query: str = Body(...),
    session_id: Optional[str] = Body(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Stream RAG answer using Server-Sent Events

    Returns a stream of events:
    - start: Query processing started
    - search_complete: Documents found
    - generating: LLM generation started
    - token: Individual token from LLM
    - sources: Source documents
    - done: Stream complete
    """
    return await streaming_service.stream_rag_response(
        query=query,
        session_id=session_id,
        db=db
    )
```

---

### ✅ Etapa 4: Sistema de Memória Conversacional

#### 4.1 Criar Módulo de Memória Conversacional
**Arquivo**: `backend/app/services/rag/conversation_memory.py` (novo)

```python
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

class ConversationMemory:
    """Gerencia contexto conversacional e histórico de chat"""

    def __init__(self, max_messages: int = 10):
        self.max_messages = max_messages
        self.embedding_service = None  # Lazy load

    async def get_conversation_context(
        self,
        session_id: str,
        db: AsyncSession
    ) -> str:
        """
        Recupera contexto das últimas mensagens da conversa

        Returns:
            String formatada com histórico recente
        """
        from app.models.chat import ChatMessage

        # Buscar últimas N mensagens
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(self.max_messages)
        )
        messages = result.scalars().all()

        if not messages:
            return ""

        # Inverter para ordem cronológica
        messages = list(reversed(messages))

        # Formatar contexto
        context_parts = []
        for msg in messages[-5:]:  # Últimas 5 mensagens
            role = "Você" if msg.message_type == "user" else "Knight"
            content = msg.content[:200]  # Limitar tamanho
            context_parts.append(f"{role}: {content}")

        return "\n".join(context_parts)

    async def get_contextual_embedding(
        self,
        query: str,
        session_id: str,
        db: AsyncSession
    ) -> Optional[List[float]]:
        """
        Gera embedding considerando contexto da conversa

        Combina query atual com tópico da conversa
        """
        # Obter histórico
        history = await self.get_conversation_context(session_id, db)

        if not history:
            # Sem histórico, usar query pura
            return None

        # Extrair tópico principal do histórico
        topic = await self._extract_topic(history)

        # Combinar query com tópico
        contextual_query = f"{topic} {query}" if topic else query

        # Gerar embedding
        if not self.embedding_service:
            from app.services.rag.embedding_service import embedding_service
            self.embedding_service = embedding_service

        embedding = self.embedding_service.encode_text(contextual_query)
        return embedding

    async def _extract_topic(self, history: str) -> str:
        """Extrai tópico principal usando LLM rápido"""
        from app.services.rag.llm_providers import llm_manager

        try:
            prompt = f"""
            Extraia o tópico principal desta conversa em 2-3 palavras:

            {history}

            Tópico:"""

            topic, _ = await llm_manager.generate_with_fallback(
                prompt=prompt,
                max_tokens=20,
                temperature=0.3
            )

            return topic.strip()
        except:
            return ""

    async def should_reset_context(
        self,
        query: str,
        session_id: str,
        db: AsyncSession
    ) -> bool:
        """
        Detecta se houve mudança de tópico (deve resetar contexto)

        Usa similaridade semântica entre query e histórico
        """
        history = await self.get_conversation_context(session_id, db)

        if not history:
            return False

        # Calcular similaridade
        if not self.embedding_service:
            from app.services.rag.embedding_service import embedding_service
            self.embedding_service = embedding_service

        query_emb = self.embedding_service.encode_text(query)
        history_emb = self.embedding_service.encode_text(history)

        from sklearn.metrics.pairwise import cosine_similarity
        similarity = cosine_similarity([query_emb], [history_emb])[0][0]

        # Se similaridade < 0.3, mudou de assunto
        return similarity < 0.3

# Singleton
conversation_memory = ConversationMemory()
```

---

#### 4.2 Integrar Memória no Pipeline RAG
**Arquivo**: `backend/app/services/rag/rag_service.py`

```python
from app.services.rag.conversation_memory import conversation_memory

class RAGService:
    async def generate_answer(
        self,
        query: str,
        session_id: Optional[str] = None,
        # ... outros parâmetros
    ):
        # 1. Obter contexto conversacional
        conversation_context = ""
        if session_id:
            conversation_context = await conversation_memory.get_conversation_context(
                session_id, db
            )

        # 2. Busca contextualizada
        if session_id:
            # Usar embedding contextual
            contextual_embedding = await conversation_memory.get_contextual_embedding(
                query, session_id, db
            )
            search_results = await self.search_service.search(
                query=query,
                query_embedding=contextual_embedding,  # Passa embedding customizado
                k=context_size,
                db=db
            )
        else:
            # Busca normal
            search_results = await self.search_service.search(
                query=query,
                k=context_size,
                db=db
            )

        # 3. Construir prompt com contexto conversacional
        prompt = self.prompt_templates.create_prompt(
            query=query,
            conversation_history=conversation_context,
            context=formatted_context,
            knowledge_resources=resources
        )

        # ... resto da geração
```

---

### ✅ Etapa 5: Refinamento de UX/UI

#### 5.1 Remover Seletor de Modo do Frontend
**Arquivo**: `frontend/src/pages/ChatPage.tsx`

**Remover**:
```typescript
// REMOVER estas linhas
const [responseMode, setResponseMode] = useState<'fast' | 'deep' | 'auto'>('auto');

// REMOVER este componente do JSX
<div className="mode-selector">
  <button onClick={() => setResponseMode('fast')}>Rápido</button>
  <button onClick={() => setResponseMode('deep')}>Profundo</button>
  <button onClick={() => setResponseMode('auto')}>Auto</button>
</div>
```

**Atualizar chamada de API**:
```typescript
// ANTES
await chatApi.sendMessage(sessionId, inputMessage, responseMode);

// DEPOIS
await chatApi.sendMessage(sessionId, inputMessage); // Mode removido
```

---

#### 5.2 Criar Hook useStreamingChat
**Arquivo**: `frontend/src/hooks/useStreamingChat.ts` (novo)

```typescript
import { useState, useCallback, useRef } from 'react';

interface StreamEvent {
  type: 'start' | 'search_complete' | 'generating' | 'token' | 'sources' | 'done' | 'error';
  content?: string;
  message?: string;
  chunks_found?: number;
  data?: any;
}

export function useStreamingChat() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedContent, setStreamedContent] = useState('');
  const [streamStatus, setStreamStatus] = useState<string>('');
  const eventSourceRef = useRef<EventSource | null>(null);

  const streamMessage = useCallback(async (
    query: string,
    sessionId: string,
    onToken: (token: string) => void,
    onComplete: (fullResponse: string, sources?: any[]) => void,
    onError: (error: string) => void
  ) => {
    setIsStreaming(true);
    setStreamedContent('');

    try {
      const response = await fetch('/api/rag/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ query, session_id: sessionId })
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      let sources: any[] = [];

      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6)) as StreamEvent;

            switch (data.type) {
              case 'start':
                setStreamStatus(data.message || 'Iniciando...');
                break;

              case 'search_complete':
                setStreamStatus(`${data.chunks_found} documentos encontrados`);
                break;

              case 'generating':
                setStreamStatus('Gerando resposta...');
                break;

              case 'token':
                if (data.content) {
                  fullResponse += data.content;
                  setStreamedContent(fullResponse);
                  onToken(data.content);
                }
                break;

              case 'sources':
                sources = data.data || [];
                break;

              case 'done':
                setIsStreaming(false);
                setStreamStatus('');
                onComplete(fullResponse, sources);
                break;

              case 'error':
                setIsStreaming(false);
                setStreamStatus('');
                onError(data.message || 'Erro desconhecido');
                break;
            }
          }
        }
      }
    } catch (error) {
      setIsStreaming(false);
      setStreamStatus('');
      onError(error instanceof Error ? error.message : 'Erro ao processar streaming');
    }
  }, []);

  const cancelStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsStreaming(false);
    setStreamStatus('');
  }, []);

  return {
    streamMessage,
    cancelStream,
    isStreaming,
    streamedContent,
    streamStatus
  };
}
```

---

#### 5.3 Atualizar ChatPage com Streaming
**Arquivo**: `frontend/src/pages/ChatPage.tsx`

```typescript
import { useStreamingChat } from '../hooks/useStreamingChat';

export const ChatPage: React.FC = () => {
  const { streamMessage, isStreaming, streamStatus } = useStreamingChat();

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isStreaming) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);

    // Criar mensagem assistente vazia para streaming
    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantMessageId,
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true
    };

    setMessages(prev => [...prev, assistantMessage]);
    setInputMessage('');

    // Iniciar streaming
    await streamMessage(
      inputMessage,
      sessionId || 'new',

      // onToken: atualizar mensagem conforme tokens chegam
      (token) => {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantMessageId
              ? { ...msg, content: msg.content + token }
              : msg
          )
        );
      },

      // onComplete: marcar como completo e adicionar sources
      (fullResponse, sources) => {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantMessageId
              ? { ...msg, content: fullResponse, isLoading: false, sources }
              : msg
          )
        );
      },

      // onError: mostrar erro
      (error) => {
        toast.error(`Erro: ${error}`);
        setMessages(prev =>
          prev.filter(msg => msg.id !== assistantMessageId)
        );
      }
    );
  };

  return (
    <div className="chat-container">
      {/* ... messages ... */}

      {/* Status de streaming */}
      {isStreaming && streamStatus && (
        <div className="stream-status">
          <Loader2 className="animate-spin" />
          <span>{streamStatus}</span>
        </div>
      )}

      {/* ... input ... */}
    </div>
  );
};
```

---

### ✅ Etapa 6: Monitoramento e Qualidade

#### 6.1 Logging Estruturado
**Arquivo**: `backend/app/services/rag/rag_service.py`

```python
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class RAGService:
    async def generate_answer(self, query, ...):
        start_time = datetime.now()

        # Log estruturado
        log_data = {
            'timestamp': start_time.isoformat(),
            'query': query,
            'session_id': session_id,
            'user_id': user_id
        }

        try:
            # ... execução ...

            # Log de sucesso
            log_data.update({
                'status': 'success',
                'response_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'chunks_used': len(search_results),
                'llm_provider': provider_used,
                'tokens_used': tokens_used,
                'has_knowledge_resources': bool(resources)
            })

            logger.info(json.dumps(log_data))

        except Exception as e:
            # Log de erro
            log_data.update({
                'status': 'error',
                'error': str(e),
                'error_type': type(e).__name__
            })

            logger.error(json.dumps(log_data))
            raise
```

---

## 📁 Estrutura de Arquivos

### Novos Arquivos
```
backend/app/services/rag/
├── prompt_templates.py          # Prompts naturalizados
├── context_optimizer.py         # MMR e compressão de contexto
├── streaming_service.py         # SSE streaming
└── conversation_memory.py       # Memória conversacional

frontend/src/hooks/
└── useStreamingChat.ts          # Hook de streaming

PLAN_RAG_OPTIMIZATION.md         # Este documento
```

### Arquivos Modificados
```
backend/app/services/rag/
├── rag_service.py               # Pipeline unificado
├── llm_providers.py             # Suporte a streaming
└── knowledge_resources_service.py # Formatação natural

backend/app/api/
└── rag.py                       # Endpoint de streaming

backend/app/schemas/
└── rag.py                       # Remover schemas de modo

frontend/src/pages/
└── ChatPage.tsx                 # Streaming + UI simplificada
```

---

## 🎯 Métricas de Sucesso

### Performance
- [ ] First token latency < 500ms
- [ ] Resposta completa < 3s (90% queries)
- [ ] Redução 40% em tokens de contexto

### Qualidade
- [ ] Respostas naturais (avaliação humana)
- [ ] Integração orgânica de recursos
- [ ] Contexto mantido entre mensagens

### Experiência
- [ ] UI simplificada (sem seletor de modo)
- [ ] Feedback visual claro
- [ ] Streaming fluido

---

## 📝 Checklist de Implementação

### Etapa 1: Pipeline RAG
- [ ] Remover sistema de modos (fast/deep/auto)
- [ ] Implementar busca única otimizada
- [ ] Criar context_optimizer.py com MMR

### Etapa 2: Naturalização
- [ ] Criar prompt_templates.py
- [ ] Implementar formatação natural de contexto
- [ ] Integrar knowledge resources naturalmente

### Etapa 3: Streaming
- [ ] Criar streaming_service.py
- [ ] Adicionar stream_generate() nos providers
- [ ] Criar endpoint /api/rag/stream
- [ ] Implementar hook useStreamingChat

### Etapa 4: Memória
- [ ] Criar conversation_memory.py
- [ ] Integrar no pipeline RAG
- [ ] Implementar busca contextualizada

### Etapa 5: UI/UX
- [ ] Remover seletor de modo
- [ ] Atualizar ChatPage com streaming
- [ ] Melhorar feedback visual

### Etapa 6: Monitoramento
- [ ] Adicionar logging estruturado
- [ ] Implementar métricas de qualidade
- [ ] Dashboard de analytics (futuro)

---

## 🚀 Próximos Passos

1. Criar `prompt_templates.py` com prompts naturalizados
2. Implementar formatação natural de contexto
3. Adicionar suporte a streaming nos providers
4. Criar endpoint de streaming
5. Implementar hook useStreamingChat no frontend
6. Testar e ajustar prompts

---

**Última Atualização**: 2025-01-07
**Autor**: Claude (Assistente de IA)
**Status**: 🚧 Em Execução
