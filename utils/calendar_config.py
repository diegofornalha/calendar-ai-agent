import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import streamlit as st
import tempfile
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Scopes necessários para acessar o Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Caminho para arquivos de credenciais
DEFAULT_CREDENTIALS_PATH = "credentials.json"
DEFAULT_TOKEN_PATH = "token.json"
ENV_CREDENTIALS_PATH = ".env.credentials"

# Credenciais padrão do Google (versão segura sem expor credenciais)
DEFAULT_CLIENT_ID = ""  # Será carregado de variáveis de ambiente ou .env.credentials
DEFAULT_CLIENT_SECRET = ""  # Será carregado de variáveis de ambiente ou .env.credentials

def ensure_default_credentials_exist():
    """
    Verifica se o arquivo de credenciais existe. Se não, busca de variáveis de ambiente
    ou arquivo .env.credentials não versionado.
    """
    if not os.path.exists(DEFAULT_CREDENTIALS_PATH):
        # Tentar obter credenciais de variáveis de ambiente
        client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
        
        # Se não encontrou nas variáveis de ambiente, tentar ler do arquivo .env.credentials
        if not client_id or not client_secret:
            if os.path.exists(ENV_CREDENTIALS_PATH):
                try:
                    with open(ENV_CREDENTIALS_PATH, 'r') as env_file:
                        for line in env_file:
                            if line.startswith('GOOGLE_CLIENT_ID='):
                                client_id = line.split('=')[1].strip().strip('"').strip("'")
                            elif line.startswith('GOOGLE_CLIENT_SECRET='):
                                client_secret = line.split('=')[1].strip().strip('"').strip("'")
                    logger.info("Credenciais carregadas do arquivo .env.credentials")
                except Exception as e:
                    logger.error(f"Erro ao ler arquivo .env.credentials: {str(e)}")
        
        # Verificar se temos as credenciais necessárias
        if not client_id or not client_secret:
            logger.warning("Credenciais do Google não encontradas. Use a interface para configurar.")
            return False
            
        # Criar o arquivo de credenciais com os valores obtidos
        credentials = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost"]
            }
        }
        
        # Salvar o arquivo de credenciais
        with open(DEFAULT_CREDENTIALS_PATH, 'w') as f:
            json.dump(credentials, f)
            
        logger.info(f"Arquivo de credenciais criado: {DEFAULT_CREDENTIALS_PATH}")
        return True
    
    return False

# Tentar criar o arquivo .env.credentials para armazenar as credenciais de forma segura
def create_env_credentials_file(client_id, client_secret):
    """
    Cria ou atualiza o arquivo .env.credentials com as credenciais fornecidas.
    Este arquivo não deve ser versionado (adicionar ao .gitignore).
    """
    try:
        with open(ENV_CREDENTIALS_PATH, 'w') as f:
            f.write(f'GOOGLE_CLIENT_ID="{client_id}"\n')
            f.write(f'GOOGLE_CLIENT_SECRET="{client_secret}"\n')
        logger.info(f"Arquivo {ENV_CREDENTIALS_PATH} criado/atualizado com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao criar arquivo {ENV_CREDENTIALS_PATH}: {str(e)}")
        return False

def get_credentials(credentials_path=DEFAULT_CREDENTIALS_PATH, token_path=DEFAULT_TOKEN_PATH):
    """
    Obtém credenciais do Google Calendar, autenticando se necessário.
    Retorna as credenciais e um status booleano se foi bem-sucedido.
    """
    creds = None
    credentials_exist = os.path.exists(credentials_path)
    token_exists = os.path.exists(token_path)
    
    try:
        # Se o token já existe, carregue-o
        if token_exists:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
        # Se não há credenciais válidas, tente obtê-las
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif credentials_exist:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                return None, False
                
            # Salvar o token para uso futuro
            with open(token_path, "w") as token:
                token.write(creds.to_json())
                
        return creds, True
    except Exception as e:
        logger.error(f"Erro ao obter credenciais: {str(e)}")
        return None, False

def get_calendar_service(credentials_path=DEFAULT_CREDENTIALS_PATH, token_path=DEFAULT_TOKEN_PATH):
    """
    Obtém uma instância do serviço Calendar API autorizada.
    Retorna o serviço e um status booleano se foi bem-sucedido.
    """
    creds, success = get_credentials(credentials_path, token_path)
    if not success:
        return None, False
    
    try:
        service = build("calendar", "v3", credentials=creds)
        return service, True
    except Exception as e:
        logger.error(f"Erro ao criar serviço do Calendar: {str(e)}")
        return None, False

def list_calendars(service=None):
    """
    Lista todos os calendários disponíveis para o usuário.
    Retorna uma lista de dicionários com id e nome dos calendários.
    """
    if service is None:
        service, success = get_calendar_service()
        if not success:
            return []
    
    try:
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])
        
        result = []
        for calendar in calendars:
            result.append({
                'id': calendar['id'],
                'summary': calendar.get('summary', 'Sem nome'),
                'description': calendar.get('description', ''),
                'primary': calendar.get('primary', False)
            })
        
        return result
    except HttpError as e:
        logger.error(f"Erro ao listar calendários: {str(e)}")
        return []

def get_primary_calendar(service=None):
    """
    Retorna o ID do calendário primário do usuário.
    Se não encontrar, retorna 'primary'.
    """
    calendars = list_calendars(service)
    for calendar in calendars:
        if calendar.get('primary', False):
            return calendar['id']
    return 'primary'

def save_uploaded_credentials(uploaded_file):
    """
    Salva o arquivo de credenciais enviado pelo usuário.
    Retorna um booleano indicando sucesso e uma mensagem.
    """
    try:
        # Verificar se o arquivo é um arquivo JSON válido
        content = uploaded_file.read()
        json_content = json.loads(content)
        
        # Verificar se contém os campos necessários
        if not all(key in json_content for key in ['installed', 'web']):
            # Se não tem 'installed' ou 'web', pode não ser um arquivo de credenciais válido
            if not ('client_id' in json_content and 'client_secret' in json_content):
                return False, "O arquivo não parece ser um arquivo de credenciais válido do Google."
        
        # Salvar o arquivo
        with open(DEFAULT_CREDENTIALS_PATH, 'wb') as f:
            uploaded_file.seek(0)
            f.write(uploaded_file.read())
        
        # Remover o token.json existente para forçar nova autenticação
        if os.path.exists(DEFAULT_TOKEN_PATH):
            os.remove(DEFAULT_TOKEN_PATH)
            
        return True, "Credenciais salvas com sucesso! Por favor, autentique-se."
    except json.JSONDecodeError:
        return False, "O arquivo enviado não é um JSON válido."
    except Exception as e:
        return False, f"Erro ao salvar credenciais: {str(e)}"

def get_calendar_info():
    """
    Retorna informações sobre a configuração atual do calendário.
    """
    result = {
        'credentials_exist': os.path.exists(DEFAULT_CREDENTIALS_PATH),
        'token_exist': os.path.exists(DEFAULT_TOKEN_PATH),
        'authenticated': False,
        'calendars': [],
        'primary_calendar': None,
        'selected_calendar': None,
        'is_streamlit_cloud': os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud'
    }
    
    # No Streamlit Cloud, podemos ter problemas de permissão para arquivos
    # e a autenticação OAuth pode ser mais complicada
    if result['is_streamlit_cloud']:
        logger.info("Executando no Streamlit Cloud - modo de compatibilidade ativado")
        
    if result['credentials_exist'] and result['token_exist']:
        service, success = get_calendar_service()
        if success:
            result['authenticated'] = True
            result['calendars'] = list_calendars(service)
            result['primary_calendar'] = get_primary_calendar(service)
            
            # Obter o calendário selecionado da sessão ou default para o primário
            if 'selected_calendar_id' in st.session_state:
                result['selected_calendar'] = st.session_state.selected_calendar_id
            else:
                result['selected_calendar'] = result['primary_calendar']
                
    return result

def get_auth_url():
    """
    Gera a URL de autenticação do Google Calendar, sem abrir automaticamente o navegador.
    Retorna a URL e o flow para uso posterior.
    """
    if not os.path.exists(DEFAULT_CREDENTIALS_PATH):
        return None, "Arquivo de credenciais não encontrado. Por favor, faça o upload primeiro."
    
    try:
        # Criar o fluxo OAuth sem iniciar o servidor
        flow = InstalledAppFlow.from_client_secrets_file(
            DEFAULT_CREDENTIALS_PATH, 
            SCOPES
        )
        # Preparar a URL de redirecionamento, mas não abrir o navegador
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return auth_url, flow
    except Exception as e:
        logger.error(f"Erro ao gerar URL de autenticação: {str(e)}")
        return None, f"Erro ao gerar URL de autenticação: {str(e)}"

def authenticate_with_code(flow, code):
    """
    Conclui o processo de autenticação usando o código recebido após o redirecionamento.
    """
    try:
        # Trocar o código pelo token
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Salvar as credenciais para uso futuro
        with open(DEFAULT_TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
            
        return True, "Autenticação bem-sucedida!"
    except Exception as e:
        logger.error(f"Erro durante a autenticação: {str(e)}")
        return False, f"Erro durante a autenticação: {str(e)}"

def authenticate_google_calendar():
    """
    Inicia o processo de autenticação do Google Calendar de forma automática.
    Esse método abre o navegador automaticamente.
    Retorna um booleano indicando sucesso e uma mensagem.
    """
    if not os.path.exists(DEFAULT_CREDENTIALS_PATH):
        return False, "Arquivo de credenciais não encontrado. Por favor, faça o upload primeiro."
    
    try:
        # Tentar autenticar
        creds, success = get_credentials()
        if not success:
            return False, "Falha na autenticação. Verifique suas credenciais."
        
        # Verificar se podemos acessar o calendário
        service = build("calendar", "v3", credentials=creds)
        service.calendarList().list().execute()
        
        return True, "Autenticação bem-sucedida!"
    except Exception as e:
        return False, f"Erro durante a autenticação: {str(e)}"

def save_client_credentials(client_id: str, client_secret: str = None):
    """
    Salva as credenciais do cliente (Client ID e Client Secret) no arquivo de credenciais.
    Retorna um booleano indicando sucesso e uma mensagem.
    """
    try:
        # Salvar no arquivo .env.credentials (não versionado)
        create_env_credentials_file(client_id, client_secret)
        
        # Criar o arquivo de credenciais para uso imediato
        credentials = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost"]
            }
        }
        
        # Salvar o arquivo
        with open(DEFAULT_CREDENTIALS_PATH, 'w') as f:
            json.dump(credentials, f)
        
        # Remover o token.json existente para forçar nova autenticação
        if os.path.exists(DEFAULT_TOKEN_PATH):
            os.remove(DEFAULT_TOKEN_PATH)
            
        return True, "Credenciais salvas com sucesso! Por favor, autentique-se."
    except Exception as e:
        return False, f"Erro ao salvar credenciais: {str(e)}"

# Tentar carregar credenciais na inicialização do módulo
try:
    # Tentativa de inicializar as credenciais a partir do arquivo .env ou variáveis de ambiente
    created = ensure_default_credentials_exist()
    if created:
        logger.info("Credenciais do Google carregadas com sucesso!")
except Exception as e:
    logger.error(f"Erro ao carregar credenciais: {str(e)}") 