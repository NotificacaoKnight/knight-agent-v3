# Knight Agent - Visão Geral do Sistema

## 📋 Resumo Executivo

Knight Agent é um assistente corporativo inteligente baseado em IA que utiliza **RAG (Retrieval-Augmented Generation)** com arquitetura agentic para fornecer respostas precisas baseadas em documentos internos da empresa. O sistema suporta múltiplos usuários através de autenticação Microsoft Azure AD e processa documentos em português com otimizações específicas para o idioma.

## 🏗️ Arquitetura Principal

### Frontend (React + TypeScript)
- **Interface moderna** com tema claro/escuro
- **Chat em tempo real** com suporte a mensagens de texto e áudio
- **Histórico de conversas** limitado às 10 mais recentes por usuário
- **Gerenciamento de documentos** (apenas administradores)
- **Design responsivo** com componentes shadcn/ui

### Backend (Django REST Framework)
- **API RESTful** com autenticação via token
- **Processamento assíncrono** de documentos com Celery
- **Armazenamento vetorial híbrido** (PostgreSQL pgvector + FAISS)
- **Múltiplos provedores de LLM** com fallback automático

## 🔐 Autenticação e Segurança

### Microsoft Azure AD
- Login único corporativo (SSO)
- Tokens de sessão com expiração de 1 hora
- Isolamento completo de dados por usuário
- Permissões diferenciadas (usuário/admin)

### Segurança de Dados
- Cada usuário vê apenas suas próprias conversas
- Documentos corporativos compartilhados entre todos
- Criptografia em trânsito (HTTPS)
- Sanitização de inputs para prevenir injeções

## 🤖 Sistema RAG Inteligente

### Arquitetura Agentic (LangGraph)
O sistema utiliza uma abordagem de múltiplos agentes para processar consultas:

1. **Planning Agent**: Analisa a complexidade da pergunta
2. **Search Agent**: Executa busca híbrida nos documentos
3. **Quality Agent**: Avalia a qualidade dos resultados
4. **Refinement Agent**: Refina consultas se necessário
5. **Generation Agent**: Gera resposta contextualizada
6. **Validation Agent**: Valida qualidade da resposta

### Busca Híbrida
- **Busca Semântica**: Embeddings BGE-m3 (otimizado para português)
- **Busca por Palavras-chave**: BM25 com tokenização portuguesa
- **Pesos configuráveis**: 70% semântico + 30% keyword (padrão)

### Armazenamento Vetorial
- **Produção**: PostgreSQL com pgvector
  - Suporta 1000+ usuários simultâneos
  - Atualizações atômicas de documentos
  - Índices HNSW para performance
- **Fallback**: FAISS in-memory
  - Backup automático em caso de falha
  - Compatibilidade com ambientes de desenvolvimento

## 💬 Funcionalidades do Chat

### Interface de Conversação
- **Mensagens de texto**: Digitação com suporte a múltiplas linhas
- **Mensagens de áudio**: Gravação e transcrição automática
- **Contexto mantido**: Histórico da sessão para respostas coerentes
- **Feedback**: Sistema de thumbs up/down para melhorias

### Gerenciamento de Sessões
- **Criação automática**: Nova sessão ao iniciar conversa
- **Títulos inteligentes**: Gerados com base na primeira mensagem
- **Histórico navegável**: Acesso às conversas anteriores
- **Exclusão segura**: Com confirmação e limpeza de dados

### Experiência do Usuário
- **Loading states**: Indicadores visuais durante processamento
- **Bloqueio de navegação**: Previne perda de respostas em andamento
- **Atualizações em tempo real**: Histórico atualiza instantaneamente
- **Tratamento de erros**: Mensagens claras e ações de recuperação

## 📄 Processamento de Documentos

### Pipeline de Ingestão
1. **Upload**: Suporte para PDF, DOCX, TXT, etc.
2. **Conversão**: Docling para extração de conteúdo
3. **Chunking**: Divisão em blocos de 700 tokens
4. **Embedding**: Geração de vetores com BGE-m3
5. **Indexação**: Armazenamento em pgvector/FAISS

### Otimizações para Português
- **Tokenização customizada**: Stopwords em português
- **Chunking inteligente**: Respeita estrutura do idioma
- **Prompts otimizados**: Respostas naturais em PT-BR

## 🔄 Provedores de LLM

### Suporte Multi-Provider
- **Cohere**: Melhor para RAG com suporte nativo a documentos
- **Groq**: Inferência mais rápida (<500ms)
- **Together AI**: Variedade de modelos open-source
- **Ollama**: Self-hosted para privacidade de dados

### Sistema de Fallback
1. Tenta provider principal configurado
2. Em caso de erro, tenta próximo na lista
3. Logs detalhados para monitoramento
4. Configuração via variáveis de ambiente

## 📊 Monitoramento e Performance

### Métricas Disponíveis
- Tempo de resposta por mensagem
- Taxa de sucesso de queries
- Uso de contexto (documentos utilizados)
- Feedback dos usuários

### Otimizações de Performance
- Cache de embeddings para documentos
- Batch processing para uploads múltiplos
- Connection pooling para PostgreSQL
- Lazy loading de componentes frontend

## 🚀 Fluxo de Uso Típico

1. **Login**: Usuário autentica via Microsoft AD
2. **Nova Conversa**: Inicia chat ou seleciona do histórico
3. **Pergunta**: Envia texto ou áudio
4. **Processamento**: 
   - Sistema analisa a pergunta
   - Busca documentos relevantes
   - Gera resposta contextualizada
5. **Resposta**: Exibe resultado com indicador de contexto usado
6. **Feedback**: Usuário pode avaliar a resposta
7. **Histórico**: Conversa salva automaticamente

## 🛠️ Configuração e Deployment

### Requisitos Mínimos
- Python 3.8+
- PostgreSQL 13+ com pgvector
- Redis para filas Celery
- Node.js 16+ para frontend

### Variáveis de Ambiente Essenciais
```env
# Azure AD
AZURE_AD_CLIENT_ID=xxx
AZURE_AD_CLIENT_SECRET=xxx
AZURE_AD_TENANT_ID=xxx

# LLM Provider
LLM_PROVIDER=cohere
COHERE_API_KEY=xxx

# Vector Search
USE_PGVECTOR=True
EMBEDDING_MODEL=BAAI/bge-m3
```

### Docker Compose
- Ambiente completo de desenvolvimento
- PostgreSQL, Redis e aplicação
- Hot-reload para desenvolvimento
- Configuração de produção disponível

## 📈 Capacidade e Escalabilidade

### Limites Atuais
- 10 conversas no histórico por usuário
- 1000+ usuários simultâneos (com pgvector)
- Documentos até 50MB por upload
- Áudio até 20MB ou 10 minutos

### Escalabilidade
- Horizontal scaling via Kubernetes
- Cache distribuído com Redis
- CDN para assets estáticos
- Load balancer para múltiplas instâncias

## 🔧 Manutenção e Suporte

### Logs e Debugging
- Logs estruturados com níveis
- Tracing de requisições
- Métricas de performance
- Alertas configuráveis

### Backup e Recuperação
- Backup automático do PostgreSQL
- Versionamento de embeddings
- Recuperação point-in-time
- Testes de disaster recovery

---

**Versão**: 1.0.0  
**Última Atualização**: Janeiro 2025  
**Contato**: Equipe de Desenvolvimento Knight Agent