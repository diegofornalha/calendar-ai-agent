"""
Componente de autenticação do Firebase para Streamlit.
Este módulo gerencia a autenticação com o Firebase e troca tokens para uso com a API do Google Calendar.
"""

import os
import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import pyrebase
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import datetime

# Configuração do Firebase
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

# Configuração do Google Cliente OAuth
GOOGLE_CLIENT_ID = "YOUR_CLIENT_ID"
GOOGLE_CLIENT_SECRET = "YOUR_CLIENT_SECRET"

# Inicialização do Firebase Admin SDK (para verificação de tokens)
# Nota: Em produção, use um arquivo de credenciais do Firebase Admin seguro
try:
    # Tentativa de inicializar o app do Firebase Admin
    firebase_admin.initialize_app()
except ValueError:
    # Se já estiver inicializado, pegue a instância existente
    pass

# Inicialização do Pyrebase (para autenticação client-side)
firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
auth_firebase = firebase.auth()

def firebase_login_button():
    """
    Exibe uma interface de login com o Firebase usando o Google OAuth
    """
    st.write("### Autenticação com Google via Firebase")
    
    if 'firebase_user' not in st.session_state:
        st.session_state.firebase_user = None
    
    if st.session_state.firebase_user:
        st.success(f"✓ Autenticado como: {st.session_state.firebase_user['email']}")
        if st.button("Sair"):
            st.session_state.firebase_user = None
            st.session_state.google_token = None
            st.rerun()
    else:
        # Tabs para Login e Registro
        tab1, tab2 = st.tabs(["Login", "Registrar"])
        
        # Tab de Login
        with tab1:
            email = st.text_input("Email", key="login_email_input")
            password = st.text_input("Senha", type="password", key="login_password_input")
            
            col1, col2 = st.columns(2)
            
            # Login com email/senha
            with col1:
                if st.button("Login com Email"):
                    try:
                        user = auth_firebase.sign_in_with_email_and_password(email, password)
                        st.session_state.firebase_user = auth_firebase.get_account_info(user['idToken'])['users'][0]
                        st.session_state.firebase_token = user['idToken']
                        st.success("Login bem-sucedido!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro no login: {str(e)}")
            
            # Login com Google
            with col2:
                if st.button("Login com Google"):
                    st.info("""
                    Para implementar o login com o Google, precisamos:
                    1. Adicionar um componente JavaScript para autenticação via popup
                    2. Receber o token na callback
                    
                    Isso requer um componente Streamlit customizado ou uma página HTML separada.
                    
                    Neste exemplo simulado, você seria redirecionado para o login do Google.
                    """)
        
        # Tab de Registro
        with tab2:
            reg_email = st.text_input("Email", key="register_email_input")
            reg_password = st.text_input("Senha", type="password", key="register_password_input")
            reg_password_confirm = st.text_input("Confirmar Senha", type="password", key="register_password_confirm_input")
            
            if st.button("Registrar Nova Conta"):
                if reg_password != reg_password_confirm:
                    st.error("As senhas não correspondem!")
                elif len(reg_password) < 6:
                    st.error("A senha deve ter pelo menos 6 caracteres!")
                else:
                    try:
                        # Criar novo usuário no Firebase
                        user = auth_firebase.create_user_with_email_and_password(reg_email, reg_password)
                        st.session_state.firebase_user = auth_firebase.get_account_info(user['idToken'])['users'][0]
                        st.session_state.firebase_token = user['idToken']
                        st.success("Conta criada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar conta: {str(e)}")

def get_google_calendar_credentials():
    """
    Obtém credenciais do Google Calendar a partir da autenticação do Firebase
    """
    if 'firebase_user' not in st.session_state or not st.session_state.firebase_user:
        return None
    
    # Verificar se já temos um token OAuth do Google
    if 'google_oauth_token' in st.session_state and st.session_state.google_oauth_token:
        try:
            # Criar objeto de credenciais a partir do token salvo na sessão
            credentials = Credentials(
                token=st.session_state.google_oauth_token.get('access_token'),
                refresh_token=st.session_state.google_oauth_token.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=GOOGLE_CLIENT_ID,
                client_secret=GOOGLE_CLIENT_SECRET,
                scopes=["https://www.googleapis.com/auth/calendar"],
                expiry=datetime.datetime.fromisoformat(st.session_state.google_oauth_token.get('expiry'))
            )
            
            # Atualizar o token se necessário
            if credentials.expired:
                credentials.refresh(Request())
                # Atualizar o token na sessão
                st.session_state.google_oauth_token = {
                    'access_token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'expiry': credentials.expiry.isoformat(),
                }
            
            return credentials
        except Exception as e:
            st.error(f"Erro ao recuperar credenciais do Google: {str(e)}")
            # Limpar o token em caso de erro para forçar nova autenticação
            if 'google_oauth_token' in st.session_state:
                del st.session_state.google_oauth_token
    
    return None

def initiate_google_calendar_auth():
    """
    Inicia o fluxo de autenticação do Google Calendar
    """
    try:
        # Criar um fluxo de autenticação OAuth
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
        
        # Gerar URL de autorização
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Guardar o fluxo na sessão para uso posterior
        st.session_state.auth_flow = flow
        
        # Exibir instruções para o usuário
        st.markdown("""
        ### Autenticação do Google Calendar
        
        Siga os passos abaixo para conectar sua conta Google:
        
        1. Clique no botão para abrir a página de autenticação do Google
        2. Faça login na sua conta Google (se ainda não estiver logado)
        3. Autorize o acesso ao seu calendário
        4. Copie o código de autorização que será exibido
        5. Cole o código no campo abaixo e clique em "Confirmar"
        """)
        
        # Botão para abrir a URL de autenticação
        st.markdown(f"""
        <a href="{auth_url}" target="_blank">
            <button style="background-color:#4285F4; color:white; border:none; border-radius:4px; padding:10px 20px; font-size:16px; cursor:pointer;">
                Abrir Página de Autenticação do Google
            </button>
        </a>
        """, unsafe_allow_html=True)
        
        # Campo para o código de autorização
        auth_code = st.text_input("Cole o código de autorização aqui:", key="auth_code")
        
        if st.button("Confirmar Código"):
            if auth_code:
                # Trocar o código pelo token
                flow = st.session_state.auth_flow
                flow.fetch_token(code=auth_code)
                credentials = flow.credentials
                
                # Salvar o token na sessão
                st.session_state.google_oauth_token = {
                    'access_token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
                }
                
                # Limpar o fluxo da sessão
                st.session_state.auth_flow = None
                
                st.success("✅ Autenticação com Google Calendar concluída com sucesso!")
                st.rerun()
            else:
                st.error("⚠️ Por favor, insira o código de autorização.")
    except Exception as e:
        st.error(f"Erro ao iniciar autenticação com Google Calendar: {str(e)}")

# Função principal para mostrar o componente de autenticação
def show_auth_component():
    """
    Função principal para mostrar o componente de autenticação do Firebase
    """
    firebase_login_button()
    
    # Se autenticado, exibir informações do usuário
    if 'firebase_user' in st.session_state and st.session_state.firebase_user:
        st.write("### Informações do Usuário")
        st.json(st.session_state.firebase_user)
        
        # Exibir opções do Google Calendar
        st.write("### Acesso ao Google Calendar")
        
        # Verificar se já temos credenciais do Google Calendar
        credentials = get_google_calendar_credentials()
        
        if credentials:
            # Tentar acessar o Google Calendar para confirmar que a autenticação é válida
            try:
                service = build('calendar', 'v3', credentials=credentials)
                # Tentar obter a lista de calendários para verificar se as credenciais são válidas
                calendar_list = service.calendarList().list().execute()
                
                st.success("✅ Conectado ao Google Calendar com sucesso!")
                
                # Mostrar informações dos calendários disponíveis
                st.write("### Seus Calendários")
                calendars = calendar_list.get('items', [])
                for calendar in calendars:
                    st.write(f"📅 **{calendar['summary']}**")
                
                # Botão para desconectar
                if st.button("Desconectar do Google Calendar"):
                    # Limpar as credenciais
                    if 'google_oauth_token' in st.session_state:
                        del st.session_state.google_oauth_token
                    st.success("Desconectado do Google Calendar com sucesso.")
                    st.rerun()
                
            except Exception as e:
                st.error(f"Erro ao acessar o Google Calendar: {str(e)}")
                # Limpar as credenciais em caso de erro
                if 'google_oauth_token' in st.session_state:
                    del st.session_state.google_oauth_token
                st.info("Por favor, reconecte-se ao Google Calendar.")
                initiate_google_calendar_auth()
        else:
            # Se não temos credenciais, iniciar o fluxo de autenticação
            if st.button("Conectar ao Google Calendar"):
                initiate_google_calendar_auth()

# Para testar individualmente este módulo
if __name__ == "__main__":
    st.set_page_config(page_title="Firebase Auth Demo", page_icon="🔐")
    st.title("Demo de Autenticação com Firebase")
    show_auth_component() 