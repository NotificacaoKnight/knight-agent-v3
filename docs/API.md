# Documentação da API - Knight Agent

## 🔑 Autenticação

Todas as APIs (exceto login) requerem autenticação via token Bearer:
```http
Authorization: Bearer YOUR_SESSION_TOKEN
```

## 🔐 Endpoints de Autenticação

### POST `/api/auth/microsoft/login/`
Inicia processo de login Microsoft
```json
{
  "auth_url": "https://login.microsoftonline.com/...",
  "state": "uuid-string"
}
```

### POST `/api/auth/microsoft/callback/`
Callback do Microsoft Azure AD
```json
{
  "code": "authorization-code",
  "state": "uuid-string"
}
```

**Resposta:**
```json
{
  "user": {
    "id": 1,
    "username": "user@empresa.com",
    "preferred_name": "João Silva",
    "theme_preference": "light"
  },
  "session_token": "session-token",
  "expires_at": "2024-01-01T12:00:00Z"
}
```

### GET `/api/auth/profile/`
Busca perfil do usuário atual

### PUT `/api/auth/profile/update/`
Atualiza perfil do usuário
```json
{
  "preferred_name": "João Silva",
  "theme_preference": "dark"
}
```

### POST `/api/auth/logout/`
Faz logout do usuário

## 💬 Endpoints de Chat

### POST `/api/chat/send/`
Envia mensagem para o Knight
```json
{
  "message": "Como solicitar férias?",
  "session_id": 123,
  "search_params": {
    "semantic_weight": 0.7,
    "bm25_weight": 0.3
  }
}
```

**Resposta:**
```json
{
  "session_id": 123,
  "session_title": "Solicitação de Férias",
  "success": true,
  "response": "Para solicitar férias, acesse o portal RH...",
  "message_id": 456,
  "context_used": 3,
  "search_results": 5,
  "response_time_ms": 1200,
  "provider_used": "cohere",
  "fallback_used": false
}
```

### GET `/api/chat/sessions/`
Lista sessões de chat do usuário
```json
{
  "sessions": [
    {
      "id": 123,
      "title": "Solicitação de Férias",
      "message_count": 6,
      "last_message_at": "2024-01-01T12:00:00Z",
      "created_at": "2024-01-01T10:00:00Z"
    }
  ]
}
```

### POST `/api/chat/sessions/new/`
Cria nova sessão de chat

### GET `/api/chat/sessions/{id}/`
Busca histórico de uma sessão
```json
{
  "messages": [
    {
      "id": 456,
      "type": "user",
      "content": "Como solicitar férias?",
      "created_at": "2024-01-01T12:00:00Z",
      "context_used": 0,
      "provider": null,
      "response_time_ms": null
    },
    {
      "id": 457,
      "type": "assistant",
      "content": "Para solicitar férias...",
      "created_at": "2024-01-01T12:00:05Z",
      "context_used": 3,
      "provider": "cohere",
      "response_time_ms": 1200
    }
  ]
}
```

### DELETE `/api/chat/sessions/{id}/delete/`
Remove sessão de chat

### PUT `/api/chat/sessions/{id}/title/`
Atualiza título da sessão
```json
{
  "title": "Novo título da sessão"
}
```

### POST `/api/chat/feedback/`
Envia feedback sobre resposta
```json
{
  "message_id": 457,
  "feedback_type": "helpful",
  "comment": "Resposta muito útil!"
}
```

## 📄 Endpoints de Documentos

### GET `/api/documents/`
Lista documentos disponíveis
```json
{
  "count": 25,
  "results": [
    {
      "id": 1,
      "title": "Manual do Funcionário",
      "original_filename": "manual.pdf",
      "file_type": ".pdf",
      "file_size_mb": 2.5,
      "status": "processed",
      "is_downloadable": true,
      "uploaded_by_name": "Admin",
      "uploaded_at": "2024-01-01T10:00:00Z",
      "chunks_count": 45
    }
  ]
}
```

### POST `/api/documents/upload/`
Upload de novo documento
```http
Content-Type: multipart/form-data

file: arquivo.pdf
title: "Manual do Funcionário"
is_downloadable: true
```

### GET `/api/documents/{id}/content/`
Busca conteúdo processado do documento
```json
{
  "title": "Manual do Funcionário",
  "content": "# Manual do Funcionário\n\n...",
  "metadata": {
    "pages": 50,
    "processing_method": "docling"
  },
  "chunks_count": 45
}
```

### GET `/api/documents/{id}/download/`
Download do arquivo original (apenas se `is_downloadable=true`)

### POST `/api/documents/{id}/reprocess/`
Reprocessa documento

### GET `/api/documents/stats/`
Estatísticas dos documentos
```json
{
  "total_documents": 25,
  "processed_documents": 23,
  "pending_documents": 1,
  "processing_documents": 1,
  "error_documents": 0,
  "downloadable_documents": 15,
  "total_chunks": 1250
}
```

## 📥 Endpoints de Downloads

### GET `/api/downloads/`
Lista downloads disponíveis do usuário
```json
{
  "downloads": [
    {
      "id": 1,
      "download_token": "uuid-token",
      "document_title": "Manual do Funcionário",
      "file_name": "manual.pdf",
      "file_size_mb": 2.5,
      "created_at": "2024-01-01T10:00:00Z",
      "expires_at": "2024-01-08T10:00:00Z",
      "time_remaining_hours": 168,
      "download_count": 0,
      "is_expired": false
    }
  ]
}
```

### POST `/api/downloads/request/`
Solicita download de um documento
```json
{
  "document_id": 1
}
```

**Resposta:**
```json
{
  "message": "Download preparado com sucesso",
  "download": {
    "download_token": "uuid-token",
    "expires_at": "2024-01-08T10:00:00Z"
  }
}
```

### GET `/api/downloads/file/{token}/`
Faz download do arquivo
- Retorna arquivo binário
- Headers: `Content-Disposition: attachment; filename="arquivo.pdf"`

### DELETE `/api/downloads/delete/{token}/`
Remove download da lista

### GET `/api/downloads/stats/`
Estatísticas de downloads do usuário

### POST `/api/downloads/cleanup/`
Remove downloads expirados

## 🔍 Endpoints de Busca RAG

### POST `/api/rag/search/`
Busca híbrida nos documentos
```json
{
  "query": "como solicitar férias",
  "k": 5,
  "semantic_weight": 0.7,
  "bm25_weight": 0.3
}
```

**Resposta:**
```json
{
  "results": [
    {
      "document_id": 1,
      "chunk_id": 123,
      "content": "Para solicitar férias...",
      "combined_score": 0.85,
      "semantic_score": 0.9,
      "bm25_score": 0.8
    }
  ],
  "search_duration_ms": 150
}
```

## 📊 Endpoints de Estatísticas

### GET `/api/stats/general/`
Estatísticas gerais do sistema
```json
{
  "total_users": 150,
  "total_documents": 25,
  "total_chats": 1200,
  "total_downloads": 350,
  "avg_response_time_ms": 800
}
```

### GET `/api/chat/stats/`
Estatísticas de chat do usuário
```json
{
  "total_sessions": 15,
  "total_messages": 120,
  "helpful_responses": 95,
  "avg_response_time": 750
}
```

## ⚙️ Configuração de Parâmetros RAG

### Chunking Otimizado para Português
- **Chunk Size**: 500-800 tokens
- **Overlap**: 10-20% (100 tokens)
- **Preserva estrutura**: Cabeçalhos e parágrafos

### Embeddings
- **Modelo padrão**: `BAAI/bge-m3`
- **Dimensões**: 1024
- **Normalização**: Ativa para similaridade coseno

### Busca Híbrida
- **Semantic Weight**: 0.7 (padrão)
- **BM25 Weight**: 0.3 (padrão)
- **Top-K**: 5 chunks
- **Re-ranking**: Automático

## 🚨 Códigos de Erro

### 400 Bad Request
```json
{
  "error": "Mensagem não pode estar vazia"
}
```

### 401 Unauthorized
```json
{
  "error": "Token de autenticação necessário"
}
```

### 403 Forbidden
```json
{
  "error": "Este documento não está disponível para download"
}
```

### 404 Not Found
```json
{
  "error": "Sessão não encontrada"
}
```

### 500 Internal Server Error
```json
{
  "error": "Erro interno do servidor",
  "response": "Desculpe, ocorreu um erro. Tente novamente ou entre em contato com o suporte."
}
```

## 📝 Rate Limiting

- **Chat**: 60 mensagens por minuto por usuário
- **Upload**: 10 arquivos por hora por usuário
- **Downloads**: 50 downloads por hora por usuário
- **API Geral**: 1000 requests por hora por usuário

## 🔒 Segurança

### Headers Obrigatórios
```http
Authorization: Bearer TOKEN
Content-Type: application/json
```

### CORS
- Permitido apenas para origins configurados
- Credenciais permitidas para domínios autorizados

### Validação
- Todos os inputs são validados e sanitizados
- Upload de arquivos limitado a tipos permitidos
- Tamanho máximo de arquivo: 50MB