"""
Teste básico e seguro da API do Google Calendar.
Este script NÃO contém credenciais hardcoded.
"""
import os
import json
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuração
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TEMP_CREDS_FILE = "temp_credentials.json"
TEMP_TOKEN_FILE = "temp_token.json"

def main():
    """Executa o teste básico da API"""
    print("\n=== TESTE BÁSICO DA API DO GOOGLE CALENDAR ===\n")
    
    # Verificar .env.credentials
    if not os.path.exists(".env.credentials"):
        print("Erro: Arquivo .env.credentials não encontrado!")
        print("Crie este arquivo com suas credenciais no formato:")
        print('GOOGLE_CLIENT_ID="seu-client-id"')
        print('GOOGLE_CLIENT_SECRET="seu-client-secret"')
        return
    
    # Carregar credenciais
    client_id = None
    client_secret = None
    
    with open(".env.credentials", 'r') as env_file:
        for line in env_file:
            if line.startswith('GOOGLE_CLIENT_ID='):
                client_id = line.split('=')[1].strip().strip('"').strip("'")
            elif line.startswith('GOOGLE_CLIENT_SECRET='):
                client_secret = line.split('=')[1].strip().strip('"').strip("'")
    
    if not client_id or not client_secret:
        print("Credenciais não encontradas no arquivo .env.credentials")
        return
    
    print(f"Credenciais carregadas do arquivo .env.credentials")
    
    try:
        # Criar arquivo temporário de credenciais
        credentials = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
            }
        }
        
        with open(TEMP_CREDS_FILE, 'w') as f:
            json.dump(credentials, f)
        
        # Iniciar fluxo de autenticação
        flow = InstalledAppFlow.from_client_secrets_file(
            TEMP_CREDS_FILE, SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob"
        )
        
        # Gerar URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        print("\nAcesse esta URL para autorizar o aplicativo:")
        print(auth_url)
        print("\nApós autorizar, você será redirecionado para urn:ietf:wg:oauth:2.0:oob")
        print("Copie o código da URL após 'code=' e cole abaixo:")
        
        code = input("\nInsira o código de autorização: ")
        
        # Obter token
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Salvar token
        with open(TEMP_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
        
        print("\nAutenticação bem-sucedida! Token salvo.")
        
        # Testar API
        print("\nTestando acesso ao Google Calendar...")
        service = build("calendar", "v3", credentials=creds)
        calendars = service.calendarList().list().execute().get('items', [])
        
        if calendars:
            print(f"Sucesso! Encontrados {len(calendars)} calendários.")
            for i, calendar in enumerate(calendars, 1):
                primary = " (Padrão)" if calendar.get('primary', False) else ""
                print(f"{i}. {calendar['summary']}{primary}")
        else:
            print("Nenhum calendário encontrado.")
        
        print("\nTeste concluído com sucesso!")
        
    except Exception as e:
        print(f"Erro: {str(e)}")
    
    finally:
        # Limpar arquivos temporários
        for arquivo in [TEMP_CREDS_FILE, TEMP_TOKEN_FILE]:
            if os.path.exists(arquivo):
                os.remove(arquivo)
                print(f"Arquivo temporário removido: {arquivo}")

if __name__ == "__main__":
    main() 