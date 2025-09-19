# Security Improvements - Knight Agent

## 🔐 Correções de Segurança Implementadas

### 1. ✅ Secrets Seguros
**Arquivos**: `app/core/config.py`, `.env.example`

- Validação de secrets para prevenir uso de valores padrão em produção
- Verificação de comprimento mínimo (32 caracteres)
- Erro em produção se secrets inseguros forem detectados
- Geração de secrets usando `secrets.token_urlsafe(64)`

### 2. ✅ Configurações Azure AD Movidas para Backend
**Arquivos**: `app/api/auth.py`, `frontend/src/context/AuthContext.tsx`

- Endpoint `/api/auth/config` para fornecer configurações públicas
- Frontend busca configurações do backend dinamicamente
- Client ID e Tenant ID não mais expostos no código JavaScript

### 3. ✅ Validação Completa de Tokens Microsoft
**Arquivos**: `app/services/microsoft_token_validator.py`, `app/services/auth_service.py`

- Verificação de assinatura JWT usando chaves públicas da Microsoft
- Cache de chaves públicas por 24 horas
- Validação de issuer, audience, e claims obrigatórios
- Verificação dupla: assinatura + Graph API

### 4. ✅ CORS e CSRF Corrigidos
**Arquivos**: `app/core/config.py`, `app/core/middleware.py`

- `CORS_ALLOW_CREDENTIALS=True` para cookies httpOnly
- CSRF não mais desabilitado em DEBUG mode
- Cookies com flags de segurança apropriadas
- SameSite=lax para OAuth flow

### 5. ✅ Rate Limiting com Redis
**Arquivos**: `app/core/rate_limiter.py`, `app/core/middleware.py`

- Rate limiting distribuído usando Redis
- Algoritmo sliding window
- Fallback para in-memory se Redis não estiver disponível
- Rate limits específicos para endpoints sensíveis
- Headers informativos de rate limit

### 6. ✅ Sanitização de Logs
**Arquivos**: `app/core/log_sanitizer.py`, `app/core/middleware.py`

- Remoção automática de tokens JWT, API keys, senhas
- Sanitização de headers sensíveis
- Truncagem de bodies grandes
- Padrões regex para detectar dados sensíveis

## 📋 Configurações de Segurança

### Variáveis de Ambiente (.env)
```env
# Gerar secrets seguros
SECRET_KEY=<use: python -c "import secrets; print(secrets.token_urlsafe(64))">
JWT_SECRET_KEY=<use: python -c "import secrets; print(secrets.token_urlsafe(64))">

# Segurança de Cookies
COOKIE_SECURE=False  # True em produção (HTTPS)
COOKIE_SAMESITE=lax
USE_HTTPONLY_COOKIES=True

# CSRF
CSRF_ENABLED=True

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# Token Expiration
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15  # Reduzido de 60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=1     # Reduzido de 7
```

## 🛡️ Headers de Segurança

Automaticamente adicionados a todas as respostas:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy` configurado
- `Strict-Transport-Security` (HTTPS apenas)

## 🔍 Validação de Tokens

### Microsoft Token Validation Flow:
1. Decodificar token sem verificação para obter header
2. Buscar chave pública correspondente (kid)
3. Verificar assinatura com chave pública RSA256
4. Validar claims: aud, iss, exp, sub
5. Verificação adicional com Graph API
6. Cache de resultado por duração do token

## 🚦 Rate Limiting

### Limites Padrão:
- **Global**: 100 requisições por minuto
- **Autenticação**: 5 tentativas por minuto (configurável)
- **Endpoints pesados**: 10 requisições por minuto

### Headers de Rate Limit:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
Retry-After: 30
```

## 📝 Padrões de Sanitização de Logs

Dados automaticamente removidos:
- Tokens JWT: `Bearer [REDACTED_JWT]`
- API Keys: `api_key=[REDACTED_API_KEY]`
- Senhas: `password=[REDACTED_PASSWORD]`
- Secrets do Azure AD: `client_secret=[REDACTED_SECRET]`
- Tokens de sessão: `session_token=[REDACTED_SESSION]`
- Números de cartão: `[REDACTED_CARD]`
- Connection strings: `postgresql://[REDACTED_CREDENTIALS]@[REDACTED_HOST]`

## 🔄 Próximos Passos Recomendados

1. **Implementar Token Rotation**
   - Rotacionar refresh tokens após uso
   - Invalidar tokens antigos automaticamente

2. **Adicionar Auditoria**
   - Log de eventos de autenticação
   - Monitoramento de tentativas falhas
   - Alertas para comportamento anômalo

3. **Melhorar CSP**
   - Remover `unsafe-inline`
   - Implementar nonces para scripts necessários

4. **Implementar 2FA**
   - Adicionar autenticação de dois fatores
   - Suporte a TOTP/SMS

5. **Security Headers Adicionais**
   - Permissions-Policy
   - Expect-CT

## 📊 Testes de Segurança

### Como testar as implementações:

```bash
# Testar rate limiting
for i in {1..150}; do curl -X GET http://localhost:8000/api/auth/me; done

# Verificar headers de segurança
curl -I http://localhost:8000/api/auth/config

# Testar CSRF
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Content-Type: application/json" \
  -d '{}' # Deve falhar sem token CSRF

# Verificar sanitização de logs
curl -X POST http://localhost:8000/api/auth/microsoft/token \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{"access_token": "secret123"}'
# Logs não devem mostrar o token real
```

## ⚠️ Avisos Importantes

1. **Sempre use HTTPS em produção**
2. **Gere novos secrets para cada ambiente**
3. **Mantenha Redis rodando para rate limiting efetivo**
4. **Monitore logs regularmente**
5. **Atualize dependências de segurança regularmente**

## 📚 Referências

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Microsoft Identity Platform](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)