# Hot Reload e WebSockets no Streamlit

## Como Funciona o Sistema de Atualização do Streamlit

O Streamlit possui um sistema integrado de hot reload (recarga automática) que funciona através de WebSockets. Isso significa que você **não precisa reiniciar manualmente** o servidor Streamlit quando faz alterações no código. 

## O Processo de Atualização Automática

1. **WebSockets**: Quando você inicia um aplicativo Streamlit, ele estabelece uma conexão WebSocket entre o navegador do cliente e o servidor Streamlit.

2. **Monitoramento de Arquivos**: O Streamlit monitora constantemente os arquivos do projeto em busca de alterações.

3. **Detecção de Alterações**: Quando você modifica e salva um arquivo Python (.py), o Streamlit detecta automaticamente essa alteração.

4. **Recarga Automática**: O servidor Streamlit recarrega o aplicativo e notifica o navegador através da conexão WebSocket.

5. **Atualização da UI**: O navegador recebe a notificação e atualiza a interface do usuário sem necessidade de atualização manual da página.

## Regras Importantes para Evitar Múltiplas Instâncias

### ⚠️ Não abra múltiplas instâncias do mesmo aplicativo

```bash
# EVITE executar estes comandos repetidamente em terminais diferentes:
.venv/bin/streamlit run firebase_calendar_app.py
```

### ✅ Boas Práticas

1. **Use um único terminal**: Mantenha apenas uma janela de terminal executando o Streamlit.

2. **Verifique portas em uso**: Se o Streamlit já estiver rodando, você verá mensagens como esta:
   ```
   You can now view your Streamlit app in your browser.
   Local URL: http://localhost:8501
   ```

3. **Acesse a URL existente**: Se o aplicativo já estiver rodando, basta acessar a URL indicada (geralmente http://localhost:8501).

4. **Para parar o servidor**: Pressione Ctrl+C no terminal onde o Streamlit está rodando.

5. **Para reiniciar completamente**: Apenas se necessário, use:
   ```bash
   pkill -f streamlit && .venv/bin/streamlit run seu_app.py
   ```

6. **Casos para reinício completo**:
   - Alterações em dependências Python
   - Problemas de cache
   - Erros que não se resolvem com hot reload

## Considerações Específicas para o Projeto Calendar com Firebase

Nosso projeto de Calendário com Firebase tem algumas considerações específicas:

### 1. Estado de Autenticação e Hot Reload

- **Persistência de Sessão**: A autenticação do Firebase e tokens do Google Calendar são armazenados no `st.session_state`, que é preservado durante hot reloads normais.

- **Perda de Sessão**: No entanto, reinícios completos do servidor (usando `pkill -f streamlit`) causarão a perda da sessão, exigindo nova autenticação.

### 2. Fluxo OAuth e WebSockets

- **Processo de Auth**: Durante o fluxo de autenticação OAuth com o Google Calendar, você será redirecionado para a página de consentimento do Google. Após a autorização, você deverá retornar à aplicação Streamlit que continua rodando.

- **Múltiplas Abas**: É normal ter duas abas abertas durante este processo:
  1. A aplicação Streamlit (http://localhost:8501)
  2. A página de autenticação do Google

### 3. Quando Reiniciar é Necessário

Para este projeto específico, você só precisa reiniciar completamente quando:

- Fizer alterações na configuração do Firebase (`firebase_auth.py`)
- Modificar a estrutura de autenticação OAuth
- Adicionar novas dependências Python
- Enfrentar erros específicos de cache do Streamlit

Na maioria dos casos, **o hot reload funcionará automaticamente** e você verá suas alterações refletidas sem precisar reiniciar o servidor.

## Usando o Watchdog para Melhor Performance

O Streamlit recomenda instalar o módulo Watchdog para melhorar a detecção de alterações:

```bash
$ xcode-select --install  # apenas para Mac
$ pip install watchdog
```

## Como Saber se o Hot Reload Está Funcionando

- Você verá um indicador de "Running..." no canto superior direito quando o Streamlit estiver recarregando
- Após a conclusão da recarga, a interface do usuário será atualizada automaticamente

## Solução de Problemas

Se o hot reload não estiver funcionando:

1. Verifique se está editando os arquivos corretos (o Streamlit só monitora arquivos no diretório do projeto)
2. Certifique-se de salvar os arquivos após edição
3. Verifique se há erros de sintaxe que poderiam impedir a recarga

---

**Lembre-se**: Uma única instância do Streamlit já possui hot reload embutido. Não é necessário iniciar múltiplas instâncias para ver suas alterações refletidas na aplicação! 