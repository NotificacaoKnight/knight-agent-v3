# Knight Agent - Guia de Teste

## 🚀 Acesso ao Sistema

### URLs de Teste
- **Frontend**: As URLs serão fornecidas pelo desenvolvedor
- **Backend API**: As URLs serão fornecidas pelo desenvolvedor

*O desenvolvedor irá executar o script de tunnel e compartilhar as URLs geradas*

### Como o Developer Configura o Tunnel

```bash
# Opção 1: Script completo (recomendado)
./start-dev-tunnel.sh

# Opção 2: Apenas tunnel (se serviços já estão rodando)
./setup-tunnel.sh
```

## 🔐 Autenticação

O sistema usa autenticação Microsoft Azure AD. Para fazer login:

1. Acesse a URL do Frontend
2. Clique em "Entrar com Microsoft"
3. Use suas credenciais corporativas da Microsoft
4. Você será redirecionado para o dashboard

## 🧪 Cenários de Teste

### 1. Upload de Documentos
- **Formatos suportados**: PDF, DOCX, TXT
- **Tamanho máximo**: 10MB
- **Teste**: Faça upload de diferentes tipos de documentos e verifique o processamento

### 2. Busca RAG (Retrieval-Augmented Generation)
- Digite perguntas sobre os documentos carregados
- O sistema deve retornar respostas contextualizadas
- Teste em português e verifique a qualidade das respostas

### 3. Interface de Chat
- Inicie conversas sobre os documentos
- Teste perguntas de follow-up
- Verifique se o contexto da conversa é mantido

### 4. Download de Arquivos
- Alguns documentos podem gerar arquivos para download
- Verifique se os links de download funcionam
- Os arquivos expiram em 7 dias

## 📝 O que Testar

### Funcionalidades Principais
- [ ] Login com Microsoft Azure AD
- [ ] Upload de documentos (PDF, DOCX, TXT)
- [ ] Processamento de documentos (verificar status)
- [ ] Busca por conteúdo nos documentos
- [ ] Chat com contexto dos documentos
- [ ] Download de arquivos gerados
- [ ] Logout do sistema

### Casos de Erro
- [ ] Upload de arquivo inválido
- [ ] Upload de arquivo muito grande (>10MB)
- [ ] Busca sem documentos carregados
- [ ] Perguntas sem contexto relevante
- [ ] Acesso sem autenticação

## 🐛 Reportando Bugs

Ao encontrar um problema, por favor informe:

1. **Descrição**: O que aconteceu?
2. **Passos**: Como reproduzir o erro?
3. **Esperado**: O que deveria acontecer?
4. **Atual**: O que realmente aconteceu?
5. **Screenshots**: Se possível, anexe imagens
6. **Console**: Erros no console do navegador (F12)

### Exemplo de Report
```
Descrição: Erro ao fazer upload de PDF
Passos:
1. Fazer login
2. Ir para "Documentos"
3. Clicar em "Upload"
4. Selecionar arquivo PDF de 5MB
5. Clicar em "Enviar"

Esperado: Documento processado com sucesso
Atual: Erro "Failed to upload document"
Console: TypeError: Cannot read property 'id' of undefined
```

## 💡 Dicas

- Use o Chrome ou Edge para melhor compatibilidade
- Limpe o cache se encontrar problemas de login
- O processamento de documentos pode levar alguns minutos
- As respostas são otimizadas para português brasileiro

## 📞 Contato

Em caso de dúvidas ou problemas críticos, entre em contato com o desenvolvedor.

---

**Obrigado por testar o Knight Agent!** 🎯