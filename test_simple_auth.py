import os
import json
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Escopos necessários
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Credenciais a partir do arquivo .env.credentials
def get_credentials_from_env():
    """Carrega as credenciais do arquivo .env.credentials"""
    client_id = None
    client_secret = None
    
    # Tenta ler do arquivo .env.credentials
    if os.path.exists(".env.credentials"):
        try:
            with open(".env.credentials", 'r') as env_file:
                for line in env_file:
                    if line.startswith('GOOGLE_CLIENT_ID='):
                        client_id = line.split('=')[1].strip().strip('"').strip("'")
                    elif line.startswith('GOOGLE_CLIENT_SECRET='):
                        client_secret = line.split('=')[1].strip().strip('"').strip("'")
            logger.info("Credenciais carregadas do arquivo .env.credentials")
        except Exception as e:
            logger.error(f"Erro ao ler arquivo .env.credentials: {str(e)}")
    
    return client_id, client_secret

def test_authentication():
    """Testa o processo de autenticação"""
    # Obter credenciais do ambiente
    client_id, client_secret = get_credentials_from_env()
    
    if not client_id or not client_secret:
        logger.error("Credenciais não encontradas no arquivo .env.credentials")
        return
    
    # Exibir as credenciais que serão usadas
    print(f"Usando Client ID: {client_id}")
    print(f"Usando Client Secret: {client_secret[:5]}...")
    
    # Criar o arquivo credentials.json
    credentials = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"]
        }
    }
    
    # Salvar em arquivo temporário
    with open("temp_credentials.json", 'w') as f:
        json.dump(credentials, f)
    print("Arquivo de credenciais temporário criado.")
    
    try:
        # Tentar autenticação
        flow = InstalledAppFlow.from_client_secrets_file(
            "temp_credentials.json", 
            SCOPES,
            redirect_uri="urn:ietf:wg:oauth:2.0:oob"  # Forçar URI de redirecionamento para modo fora do navegador
        )
        
        # Gerar URL de autorização
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        print("\n=== TESTE DE AUTENTICAÇÃO DO GOOGLE CALENDAR ===")
        print("\nPor favor, acesse este URL no seu navegador:")
        print(auth_url)
        print("\nVocê receberá um código de autorização. Cole-o abaixo:")
        
        code = input("Código de autorização: ")
        
        # Trocar o código por um token
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        print("\n✅ Autenticação bem-sucedida!")
        print(f"Token de acesso: {creds.token[:10]}...")
        print(f"Token de atualização: {creds.refresh_token[:10] if creds.refresh_token else 'Nenhum'}...")
        print(f"Expiração: {creds.expiry}")
        
        # Salvar o token para uso futuro
        with open("token.json", "w") as token:
            token.write(creds.to_json())
        print("Token salvo em 'token.json'")
        
        # Teste de acesso ao Google Calendar
        print("\nTestando acesso ao Google Calendar...")
        service = build("calendar", "v3", credentials=creds)
        
        # Listar calendários
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])
        
        if not calendars:
            print("Nenhum calendário encontrado.")
        else:
            print(f"Encontrados {len(calendars)} calendários:")
            for i, calendar in enumerate(calendars, 1):
                primary = " (Padrão)" if calendar.get('primary', False) else ""
                print(f"{i}. {calendar['summary']}{primary}")
        
    except Exception as e:
        print(f"\n❌ Erro durante a autenticação: {str(e)}")
    finally:
        # Limpar arquivo temporário
        if os.path.exists("temp_credentials.json"):
            os.remove("temp_credentials.json")
            print("\nArquivo de credenciais temporário removido.")

if __name__ == "__main__":
    test_authentication() 