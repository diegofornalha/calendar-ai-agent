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
import uuid
import time

# Configuração do Firebase
FIREBASE_CONFIG = {
    "apiKey": "SUBSTITUA_PELA_SUA_API_KEY",
    "authDomain": "calendario-ia-coflow.firebaseapp.com",
    "projectId": "calendario-ia-coflow",
    "storageBucket": "calendario-ia-coflow.appspot.com",
    "messagingSenderId": "SUBSTITUA_PELO_SEU_MESSAGING_SENDER_ID",
    "appId": "SUBSTITUA_PELO_SEU_APP_ID"
}

# Configuração do Google Cliente OAuth
GOOGLE_CLIENT_ID = "INSIRA_SEU_GOOGLE_CLIENT_ID_AQUI"
GOOGLE_CLIENT_SECRET = "INSIRA_SEU_GOOGLE_CLIENT_SECRET_AQUI"

# Configuração do Firebase com valores padrão que podem ser substituídos pelo usuário
DEFAULT_FIREBASE_CONFIG = {
    "apiKey": "INSIRA_SUA_FIREBASE_API_KEY_AQUI",
    "authDomain": "calendario-ia-coflow.firebaseapp.com",
    "databaseURL": "https://calendario-ia-coflow-default-rtdb.firebaseio.com",
    "projectId": "calendario-ia-coflow",
    "storageBucket": "calendario-ia-coflow.appspot.com",
    "messagingSenderId": "444237029110",
    "appId": "1:444237029110:web:fe9878f54a78e5dcfd7cd1"
}

# Forçar a atualização do FIREBASE_CONFIG global com os valores padrão
FIREBASE_CONFIG = DEFAULT_FIREBASE_CONFIG.copy()

# Função para carregar configuração do Firebase da sessão ou usar os valores padrão
def get_firebase_config():
    if 'firebase_config' in st.session_state:
        return st.session_state.firebase_config
    return DEFAULT_FIREBASE_CONFIG

# Função para salvar nova configuração do Firebase
def save_firebase_config(config):
    # Garantir que todos os campos obrigatórios existam
    required_fields = ["apiKey", "authDomain", "databaseURL", "projectId", "storageBucket", "messagingSenderId", "appId"]
    for field in required_fields:
        if field not in config or not config[field]:
            if field == "databaseURL" and "projectId" in config:
                # Se databaseURL não foi fornecido, crie um a partir do projectId
                config[field] = f"https://{config['projectId']}-default-rtdb.firebaseio.com"
            else:
                return False, f"Campo obrigatório ausente: {field}"
    
    # Salvar configuração na sessão
    st.session_state.firebase_config = config
    # Limpar quaisquer dados de autenticação existentes para forçar novo login
    if 'firebase_user' in st.session_state:
        del st.session_state.firebase_user
    if 'firebase_token' in st.session_state:
        del st.session_state.firebase_token
    if 'google_oauth_token' in st.session_state:
        del st.session_state.google_oauth_token
    
    return True, "Configuração salva com sucesso!"

# Componente para configurar o Firebase
def firebase_config_component(form_key_suffix=""):
    st.write("### Configuração do Firebase")
    
    # Abas para configuração geral, provedores de autenticação e Admin SDK
    config_tab, auth_tab, admin_tab = st.tabs(["Configuração Geral", "Provedores de Autenticação", "Firebase Admin SDK"])
    
    with config_tab:
        # Obter configuração atual
        current_config = get_firebase_config()
        
        # Criar formulário para edição com chave única
        with st.form(f"firebase_config_form_{form_key_suffix}"):
            api_key = st.text_input("API Key", value=current_config.get("apiKey", ""))
            auth_domain = st.text_input("Auth Domain", value=current_config.get("authDomain", ""))
            db_url = st.text_input("Database URL (opcional)", value=current_config.get("databaseURL", ""))
            project_id = st.text_input("Project ID", value=current_config.get("projectId", ""))
            storage_bucket = st.text_input("Storage Bucket", value=current_config.get("storageBucket", ""))
            messaging_sender_id = st.text_input("Messaging Sender ID", value=current_config.get("messagingSenderId", ""))
            app_id = st.text_input("App ID", value=current_config.get("appId", ""))
            measurement_id = st.text_input("Measurement ID (opcional)", value=current_config.get("measurementId", ""))
            
            st.markdown("""
            <details>
            <summary>Como obter estas informações?</summary>
            <ol>
                <li>Acesse o <a href="https://console.firebase.google.com/" target="_blank">Console do Firebase</a></li>
                <li>Selecione seu projeto</li>
                <li>Clique no ícone ⚙️ (Configurações do Projeto)</li>
                <li>Role para baixo até "Seus apps" e selecione seu app web</li>
                <li>As informações estão disponíveis na configuração do Firebase SDK</li>
            </ol>
            </details>
            """, unsafe_allow_html=True)
            
            # Botões de submissão
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("Salvar Configuração")
            with col2:
                reset = st.form_submit_button("Restaurar Padrão")
            
            if submit:
                # Criar nova configuração
                new_config = {
                    "apiKey": api_key,
                    "authDomain": auth_domain,
                    "projectId": project_id,
                    "storageBucket": storage_bucket,
                    "messagingSenderId": messaging_sender_id,
                    "appId": app_id,
                }
                
                # Adicionar campos opcionais se preenchidos
                if db_url:
                    new_config["databaseURL"] = db_url
                if measurement_id:
                    new_config["measurementId"] = measurement_id
                    
                # Salvar nova configuração
                success, message = save_firebase_config(new_config)
                if success:
                    st.success(message)
                    st.rerun()  # Recarregar para aplicar as mudanças
                else:
                    st.error(message)
                    
            if reset:
                # Restaurar configuração padrão
                st.session_state.firebase_config = DEFAULT_FIREBASE_CONFIG
                st.success("Configuração padrão restaurada!")
                st.rerun()  # Recarregar para aplicar as mudanças
    
    with auth_tab:
        st.write("### Configuração dos Provedores de Autenticação")
        st.write("""
        Habilite ou desabilite os provedores de autenticação que deseja usar em seu aplicativo Firebase.
        Depois de alterar aqui, você também precisa habilitar os mesmos provedores no console do Firebase.
        """)
        
        # Verificar as configurações de autenticação atuais ou inicializar com padrões
        if 'auth_providers' not in st.session_state:
            st.session_state.auth_providers = {
                'email': True,
                'google': True,
                'anonymous': False
            }
        
        # Interface para habilitar/desabilitar provedores
        email_enabled = st.checkbox("Email/Senha", value=st.session_state.auth_providers.get('email', True),
                                  help="Permite que os usuários façam login com email e senha")
        
        google_enabled = st.checkbox("Google", value=st.session_state.auth_providers.get('google', True),
                                   help="Permite que os usuários façam login com suas contas Google")
        
        anonymous_enabled = st.checkbox("Anônimo", value=st.session_state.auth_providers.get('anonymous', False),
                                     help="Permite que os usuários acessem o aplicativo sem fazer login")
        
        # Atualizar configurações ao clicar em Salvar
        if st.button("Salvar Configurações de Autenticação"):
            # Atualizar session_state
            st.session_state.auth_providers = {
                'email': email_enabled,
                'google': google_enabled,
                'anonymous': anonymous_enabled
            }
            
            st.success("Configurações de autenticação salvas! Lembre-se de habilitar os mesmos provedores no console do Firebase.")
            
            # Instruções para habilitar provedores no console do Firebase
            st.markdown("""
            #### Como habilitar provedores no console do Firebase:
            
            1. Acesse o [Console do Firebase](https://console.firebase.google.com/)
            2. Selecione seu projeto
            3. No menu à esquerda, vá para "Authentication" > "Sign-in method"
            4. Habilite os provedores selecionados acima
            """)
            
            # Mostrar instruções específicas para autenticação anônima
            if anonymous_enabled:
                st.info("""
                Para habilitar a autenticação anônima no console do Firebase:
                1. Vá para Authentication > Sign-in method
                2. Clique em "Anonymous" na lista de provedores
                3. Clique no botão de alternar para habilitar
                4. Clique em "Save"
                
                O login anônimo já está disponível na interface de login do aplicativo!
                """)
                
                # Exibir código de exemplo para implementação em outros aplicativos - SEM usar expander
                st.markdown("##### Código de exemplo para implementar autenticação anônima:")
                st.code("""
# Para implementar autenticação anônima em outros aplicativos:

# Usando pyrebase4
user = auth_firebase.sign_in_anonymous()
token = user['idToken']
user_id = user['localId']

# OU usando firebase_admin
anonymous_user = auth.create_anonymous_user()
user_id = anonymous_user.uid
                """, language="python")
        
        # Link para documentação do Firebase
        st.markdown("[Documentação oficial de autenticação do Firebase](https://firebase.google.com/docs/auth)")
    
    with admin_tab:
        # Informações sobre o Firebase Admin SDK
        st.info("""
        ### Firebase Admin SDK
        
        O Firebase Admin SDK permite funções administrativas avançadas como:
        
        - Gerenciamento de usuários
        - Verificação de tokens personalizados
        - Operações administrativas no Firebase
        
        Para configurar o Firebase Admin SDK, utilize a seção "Configuração Avançada" na aba principal
        do aplicativo após fazer login.
        """)
        
        # Link para a seção de configuração
        if st.button("Ir para Configuração Admin SDK", key="goto_admin_sdk_config"):
            st.session_state.show_admin_config = True
            st.rerun()

# Usar a configuração do Firebase baseada na sessão
FIREBASE_CONFIG = get_firebase_config()

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

# Função para obter uma instância do Firebase Auth atualizada
def get_firebase_auth():
    config = get_firebase_config()
    firebase_app = pyrebase.initialize_app(config)
    return firebase_app.auth()

def firebase_login_button():
    """
    Exibe uma interface de login com múltiplas opções de autenticação
    """
    st.write("### Autenticação")
    
    # Garantir que estamos usando a configuração atualizada do Firebase
    global FIREBASE_CONFIG
    FIREBASE_CONFIG = get_firebase_config()
    
    # Usar uma instância atualizada do Firebase Auth
    auth_instance = get_firebase_auth()
    
    if 'firebase_user' not in st.session_state:
        st.session_state.firebase_user = None
    
    # Configurações para autenticação via e-mail
    if 'email_link_sent' not in st.session_state:
        st.session_state.email_link_sent = False
        
    if 'email_for_link' not in st.session_state:
        st.session_state.email_for_link = ""
    
    if st.session_state.firebase_user:
        # Usuário já está autenticado
        if st.session_state.firebase_user.get('isAnonymous', False):
            st.success(f"✓ Modo Demonstração Ativo")
        else:
            st.success(f"✓ Autenticado como: {st.session_state.firebase_user['email']}")
        
        if st.button("Sair da Conta", help="Encerrar sua sessão atual"):
            st.session_state.firebase_user = None
            st.session_state.firebase_token = None
            if 'google_token' in st.session_state:
                st.session_state.google_token = None
            if 'is_anonymous' in st.session_state:
                st.session_state.is_anonymous = False
            st.rerun()
    else:
        # Usuário não autenticado - mostrar opções de login
        tabs = st.tabs(["Modo Demonstração", "Configurar E-mail/Senha"])
        
        # Primeira aba - Modo Demonstração (principal)
        with tabs[0]:
            st.success("""
            ### ✅ Modo Demonstração Recomendado
            
            Este modo está pronto para uso e permite visualizar a interface do aplicativo imediatamente:
            - Interface simplificada do calendário
            - Demonstração do layout e funcionalidades
            - Sem necessidade de configuração adicional
            
            Ideal para conhecer o aplicativo rapidamente!
            """)
            
            # Botão para login anônimo - estilo destacado
            if st.button("🚀 Iniciar Modo Demonstração", use_container_width=True, type="primary",
                      help="Acesse uma versão limitada do aplicativo para demonstração. Para funcionalidades completas, configure seu próprio projeto Firebase."):
                try:
                    # Criar um ID único para o usuário anônimo
                    anonymous_id = str(uuid.uuid4())
                    
                    # Criar um objeto de usuário simulado
                    anonymous_user = {
                        'localId': anonymous_id,
                        'displayName': 'Usuário Demonstração',
                        'email': f'anonimo_{anonymous_id[:8]}@exemplo.com',
                        'emailVerified': False,
                        'isAnonymous': True,
                        'providerUserInfo': [{'providerId': 'anonymous'}],
                        'lastLoginAt': str(int(time.time() * 1000)),
                        'createdAt': str(int(time.time() * 1000))
                    }
                    
                    # Criando um token simulado (apenas para fins de demonstração)
                    mock_token = f"demo_token_{anonymous_id}"
                    
                    # Salvar na sessão
                    st.session_state.firebase_user = anonymous_user
                    st.session_state.firebase_token = mock_token
                    st.session_state.is_anonymous = True
                    
                    st.success("Modo demonstração ativado! Funcionalidades limitadas disponíveis.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao ativar modo demonstração: {str(e)}")
            
            st.markdown("""
            **Nota:** O modo demonstração permite visualizar a interface do aplicativo, 
            mas não oferece funcionalidades completas como integração com calendário 
            e assistente de IA avançado.
            """)

        # Segunda aba - Configuração de E-mail/Senha (para usuários avançados)
        with tabs[1]:
            st.write("### Configurar Autenticação por E-mail/Senha")
            st.warning("""
            **⚠️ Configuração Avançada**
            
            Para usar autenticação por e-mail/senha, você precisa:
            1. Criar seu próprio projeto no [Firebase Console](https://console.firebase.google.com)
            2. Habilitar a Authentication > Sign-in method > Email/Password
            3. Habilitar a Identity Toolkit API no Google Cloud
            4. Configurar suas credenciais na aba "Configuração Avançada"
            
            Esta configuração é para usuários que desejam implementar o aplicativo em produção.
            """)
            
            # Link para configurações avançadas
            if st.button("Ir para Configurações Avançadas", use_container_width=True):
                st.session_state.firebase_config_shown = True
                st.rerun()

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
    # Abas para autenticação e configuração
    auth_tab, config_tab = st.tabs(["Autenticação", "Configuração do Firebase"])
    
    with auth_tab:
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
                    
    with config_tab:
        firebase_config_component()

# Componente personalizado para autenticação Google via Firebase
def google_auth_component():
    """
    Componente para autenticação com o Google e acesso à API do Google Calendar
    """
    # Exibir informações sobre o fluxo de autenticação
    st.info("Configure sua integração com a API do Google Calendar.")
    
    # Opções de configuração
    firebase_config_component(form_key_suffix="google_auth")

# Para testar individualmente este módulo
if __name__ == "__main__":
    st.set_page_config(page_title="Firebase Auth Demo", page_icon="🔐")
    st.title("Demo de Autenticação com Firebase")
    show_auth_component() 