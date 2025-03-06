# Firebase Calendar - Aplicativo Streamlit com Autenticação Firebase e Google Calendar

## Visão Geral

Este aplicativo demonstra a integração entre:
- **Firebase Authentication** para gerenciamento de usuários e autenticação
- **Google Calendar API** para visualização e gerenciamento de eventos
- **Streamlit** para a interface do usuário

## Funcionalidades

### Autenticação Firebase
- Registro de novos usuários
- Login com email/senha
- Sistema de sessão seguro

### Integração com Google Calendar
- Autenticação OAuth2 com Google Calendar
- Visualização de eventos do calendário
- Filtragem de eventos por data, calendário e quantidade
- Criação de novos eventos
- Links diretos para o Google Calendar

## Pré-requisitos

- Python 3.7+
- Conta no Firebase (com Email/Password como método de autenticação ativado)
- Credenciais de API do Google Cloud para acesso ao Google Calendar

## Configuração

### 1. Ambiente Virtual

```bash
# Criar e ativar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows
```

### 2. Dependências

```bash
pip install streamlit firebase-admin pyrebase4 google-auth google-auth-oauthlib google-api-python-client
```

### 3. Configuração do Firebase

As credenciais do Firebase estão configuradas no arquivo `firebase_auth.py`:

```python
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyDF3Mk5DfoiHY4wCRY8uuizaB2Dqztjp7o",
    "authDomain": "carbem-cf.firebaseapp.com",
    "databaseURL": "https://carbem-cf-default-rtdb.firebaseio.com",
    "projectId": "carbem-cf",
    "storageBucket": "carbem-cf.firebasestorage.app",
    "messagingSenderId": "331147305475",
    "appId": "1:331147305475:web:7d3edc17610097496d2436",
    "measurementId": "G-JTDSZFHZKW"
}
```

### 4. Configuração do Google Calendar

As credenciais do Google OAuth estão configuradas no arquivo `firebase_auth.py`:

```python
GOOGLE_CLIENT_ID = "YOUR_CLIENT_ID"
GOOGLE_CLIENT_SECRET = "YOUR_CLIENT_SECRET"
```

Estas credenciais precisam ter acesso à API do Google Calendar ativada no Console Google Cloud.

## Como Executar

```bash
.venv/bin/streamlit run firebase_calendar_app.py
```

O aplicativo estará disponível em:
- URL Local: http://localhost:8501
- URL de Rede: http://IP-LOCAL:8501

## Fluxo de Uso

1. **Registro/Login**: Utilize o painel lateral para se registrar ou fazer login com email e senha

2. **Autenticação com Google Calendar**: 
   - Após o login bem-sucedido, clique em "Conectar ao Google Calendar" 
   - Siga as instruções para autorizar o acesso
   - Cole o código de autorização no campo indicado

3. **Visualização de Eventos**:
   - Após autenticação, seus calendários e eventos serão exibidos
   - Use os filtros para personalizar a visualização
   - Clique em "Ver detalhes" para cada evento para mais informações

4. **Criação de Eventos**:
   - Preencha o formulário "Adicionar Novo Evento"
   - Clique em "Adicionar Evento" para salvar
   - Use o link fornecido para visualizar o evento no Google Calendar

## Estrutura do Código

- **firebase_auth.py**: Gerenciamento de autenticação Firebase e Google OAuth
- **firebase_calendar_app.py**: Aplicativo Streamlit principal

## Solução de Problemas

Veja o arquivo `streamlit_hot_reload.md` para informações sobre:
- Como funciona o hot reload do Streamlit
- Como evitar múltiplas instâncias do aplicativo
- Quando reiniciar o servidor é necessário

## Segurança

**Importante**: Em um ambiente de produção, as credenciais devem ser gerenciadas de forma segura, usando variáveis de ambiente ou serviços de gerenciamento de segredos.

## Licença

Este projeto é fornecido como exemplo educacional. 