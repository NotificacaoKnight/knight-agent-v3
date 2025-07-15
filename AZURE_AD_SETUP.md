# Azure AD - Configuração para LocalTunnel

## 🔗 URLs Fixas para Configuração

Agora o Knight Agent usa subdomínios fixos para evitar mudanças constantes:

- **Frontend**: `https://knight-frontend-dev.loca.lt`
- **Backend**: `https://knight-backend-dev.loca.lt`

## ⚙️ Configuração no Azure AD

### 1. App Registration
No portal Azure AD, vá para App Registrations → Knight Agent:

### 2. Authentication → Redirect URIs
Adicione estas URIs:

```
https://knight-frontend-dev.loca.lt
http://localhost:3000  (para desenvolvimento local)
```

**Nota**: Use apenas a URL base, sem `/auth/callback`

### 3. Authentication → Front-channel logout URLs
**Deixe em branco** - Isso evita a tela branca após logout no tunnel.

~~https://knight-frontend-dev.loca.lt/logout~~ (NÃO usar)
~~http://localhost:3000/logout~~ (NÃO usar)

### 4. Authentication → Implicit grant and hybrid flows
✅ Marque: "Access tokens" e "ID tokens"

### 5. API permissions
- Microsoft Graph → User.Read
- Microsoft Graph → openid
- Microsoft Graph → profile
- Microsoft Graph → email

## 🔄 Como Funciona Agora

1. **Execute**: `./setup-tunnel.sh`
2. **URLs sempre serão**:
   - Frontend: `https://knight-frontend-dev.loca.lt`
   - Backend: `https://knight-backend-dev.loca.lt`
3. **Configure uma vez no Azure AD** e não precisa mais alterar

## ⚠️ Notas Importantes

- As URLs são **fixas** mas ainda dependem do localtunnel estar disponível
- Se o subdomínio `knight-frontend-dev` ou `knight-backend-dev` estiver ocupado, o tunnel pode falhar
- Neste caso, modifique o script para usar outro nome fixo

## 🛠️ Troubleshooting

### Subdomínio ocupado
Se aparecer erro que o subdomínio está ocupado:

1. Edite `setup-tunnel.sh`
2. Mude `knight-${service,,}-dev` para `knight-${service,,}-prod` (ou outro nome)
3. Atualize as URLs no Azure AD

### Tunnel não conecta
- Verifique se os serviços estão rodando (backend na 8000, frontend na 3000)
- Reinicie: `./restart-frontend.sh` e depois `./setup-tunnel.sh`