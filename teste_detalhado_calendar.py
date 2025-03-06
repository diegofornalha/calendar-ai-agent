import os
import json
import logging
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuração de logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TEMP_CREDS_FILE = "temp_credentials.json"
TEMP_TOKEN_FILE = "temp_token.json"

# Cores para output do terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_section(title):
    """Imprime um título de seção formatado"""
    print("\n" + Colors.BOLD + Colors.HEADER + "=" * 50 + Colors.ENDC)
    print(Colors.BOLD + Colors.HEADER + f" {title}" + Colors.ENDC)
    print(Colors.BOLD + Colors.HEADER + "=" * 50 + Colors.ENDC + "\n")

def print_success(message):
    """Imprime uma mensagem de sucesso formatada"""
    print(Colors.GREEN + "✅ " + message + Colors.ENDC)

def print_info(message):
    """Imprime uma mensagem informativa formatada"""
    print(Colors.BLUE + "ℹ️ " + message + Colors.ENDC)

def print_warning(message):
    """Imprime uma mensagem de aviso formatada"""
    print(Colors.WARNING + "⚠️ " + message + Colors.ENDC)

def print_error(message):
    """Imprime uma mensagem de erro formatada"""
    print(Colors.FAIL + "❌ " + message + Colors.ENDC)

def limpar_arquivos_temporarios():
    """Remove arquivos temporários de credenciais e tokens"""
    for arquivo in [TEMP_CREDS_FILE, TEMP_TOKEN_FILE]:
        if os.path.exists(arquivo):
            try:
                os.remove(arquivo)
                print_info(f"Arquivo temporário removido: {arquivo}")
            except Exception as e:
                print_error(f"Erro ao remover arquivo {arquivo}: {str(e)}")

def carregar_credenciais():
    """Carrega as credenciais do ambiente"""
    print_section("1. CARREGANDO CREDENCIAIS")
    
    # Verificar arquivo .env.credentials
    if not os.path.exists(".env.credentials"):
        print_error("Arquivo .env.credentials não encontrado!")
        return None, None
    
    print_info("Arquivo .env.credentials encontrado.")
    
    # Ler credenciais do arquivo
    client_id = None
    client_secret = None
    
    try:
        with open(".env.credentials", 'r') as env_file:
            for line in env_file:
                if line.startswith('GOOGLE_CLIENT_ID='):
                    client_id = line.split('=')[1].strip().strip('"').strip("'")
                elif line.startswith('GOOGLE_CLIENT_SECRET='):
                    client_secret = line.split('=')[1].strip().strip('"').strip("'")
        
        if not client_id or not client_secret:
            print_error("Credenciais não encontradas no arquivo .env.credentials")
            return None, None
            
        # Mostrar parte das credenciais (por segurança)
        print_success(f"Client ID carregado: {client_id[:15]}...{client_id[-10:]}")
        print_success(f"Client Secret carregado: {client_secret[:5]}...{client_secret[-4:]}")
        
        return client_id, client_secret
    
    except Exception as e:
        print_error(f"Erro ao ler credenciais: {str(e)}")
        return None, None

def criar_arquivo_credenciais(client_id, client_secret):
    """Cria um arquivo de credenciais temporário para o OAuth"""
    print_section("2. CRIANDO ARQUIVO DE CREDENCIAIS")
    
    credentials = {
        "web": {  # Alterado de "installed" para "web"
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost:8080"]  # Porta específica
        }
    }
    
    try:
        with open(TEMP_CREDS_FILE, 'w') as f:
            json.dump(credentials, f, indent=2)
        print_success(f"Arquivo de credenciais criado: {TEMP_CREDS_FILE}")
        return True
    except Exception as e:
        print_error(f"Erro ao criar arquivo de credenciais: {str(e)}")
        return False

def gerar_url_autorizacao():
    """Gera a URL de autorização para o usuário"""
    print_section("3. GERANDO URL DE AUTORIZAÇÃO")
    
    try:
        # Criar o fluxo OAuth com o URI de redirecionamento para clientes WEB
        flow = InstalledAppFlow.from_client_secrets_file(
            TEMP_CREDS_FILE,
            SCOPES,
            redirect_uri="http://localhost:8080"  # URI compatível com clientes WEB
        )
        
        # Gerar URL de autorização
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Forçar consentimento para garantir refresh_token
        )
        
        print_info("URL de autorização gerada:")
        print("\n" + Colors.CYAN + auth_url + Colors.ENDC + "\n")
        
        print_info("INSTRUÇÕES:")
        print("1. Copie a URL acima e abra em seu navegador")
        print("2. Faça login com sua conta Google") 
        print("3. Conceda as permissões solicitadas")
        print("4. Você será redirecionado para http://localhost:8080 com um código na URL")
        print("5. Copie o código da URL (após 'code=') e cole abaixo\n")
        
        return flow
    
    except Exception as e:
        print_error(f"Erro ao gerar URL de autorização: {str(e)}")
        return None

def obter_token(flow):
    """Obtém o token de acesso usando o código fornecido pelo usuário"""
    print_section("4. OBTENDO TOKEN DE ACESSO")
    
    if not flow:
        print_error("Fluxo de autorização não foi iniciado corretamente")
        return None
    
    try:
        code = input(Colors.BOLD + "Cole o código de autorização aqui: " + Colors.ENDC)
        
        # Trocar o código por um token
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Verificar se o token foi obtido com sucesso
        if not creds or not creds.token:
            print_error("Falha ao obter token de acesso")
            return None
            
        print_success("Token de acesso obtido com sucesso!")
        print_info(f"Token: {creds.token[:10]}...{creds.token[-5:]}")
        
        if creds.refresh_token:
            print_info(f"Refresh Token: {creds.refresh_token[:10]}...{creds.refresh_token[-5:]}")
        else:
            print_warning("Nenhum refresh token recebido. Isso pode limitar a capacidade de renovação automática do token.")
            
        if creds.expiry:
            print_info(f"Expira em: {creds.expiry}")
        
        # Salvar o token em arquivo temporário
        with open(TEMP_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
        print_success(f"Token salvo em {TEMP_TOKEN_FILE}")
        
        return creds
        
    except Exception as e:
        print_error(f"Erro ao obter token: {str(e)}")
        return None

def testar_servico_calendario(creds):
    """Testa o acesso ao Google Calendar usando as credenciais"""
    print_section("5. TESTANDO ACESSO AO GOOGLE CALENDAR")
    
    if not creds:
        print_error("Credenciais não disponíveis para teste")
        return False
    
    try:
        print_info("Construindo serviço do Google Calendar...")
        service = build("calendar", "v3", credentials=creds)
        
        # Teste 1: Listar calendários
        print_info("Teste 1: Listando calendários...")
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])
        
        if not calendars:
            print_warning("Nenhum calendário encontrado.")
        else:
            print_success(f"Encontrados {len(calendars)} calendários:")
            for i, calendar in enumerate(calendars, 1):
                primary = " (Padrão)" if calendar.get('primary', False) else ""
                print(f"  {i}. {calendar['summary']}{primary}")
        
        # Teste 2: Listar eventos do calendário primário
        print_info("\nTeste 2: Listando próximos eventos do calendário primário...")
        
        # Obter data atual
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indica UTC
        
        # Listar eventos
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=5,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        if not events:
            print_warning("Nenhum evento futuro encontrado.")
        else:
            print_success(f"Encontrados {len(events)} eventos:")
            for i, event in enumerate(events, 1):
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(f"  {i}. [{start}] {event['summary']}")
        
        # Teste 3: Tentar criar um evento de teste (opcional)
        criar_evento = input("\nDeseja criar um evento de teste? (s/n): ").lower()
        
        if criar_evento == 's':
            print_info("Teste 3: Criando evento de teste...")
            
            # Obter data/hora atual e adicionar 1 dia
            amanha = datetime.datetime.now() + datetime.timedelta(days=1)
            inicio = amanha.replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
            fim = amanha.replace(hour=16, minute=0, second=0, microsecond=0).isoformat()
            
            # Criar o evento
            event = {
                'summary': 'Evento de Teste via API',
                'description': 'Este é um evento de teste criado pelo script de teste da API do Google Calendar',
                'start': {
                    'dateTime': inicio,
                    'timeZone': 'America/Sao_Paulo',
                },
                'end': {
                    'dateTime': fim,
                    'timeZone': 'America/Sao_Paulo',
                },
                'reminders': {
                    'useDefault': True,
                },
            }
            
            event = service.events().insert(calendarId='primary', body=event).execute()
            print_success(f"Evento criado com sucesso!")
            print_info(f"Título: {event['summary']}")
            print_info(f"ID: {event['id']}")
            print_info(f"Link: {event.get('htmlLink')}")
        
        print_success("Todos os testes completados com sucesso!")
        return True
        
    except HttpError as error:
        print_error(f"Erro de API: {error}")
        return False
    except Exception as e:
        print_error(f"Erro ao acessar o Google Calendar: {str(e)}")
        return False

def realizar_teste_completo():
    """Realiza o teste completo de ponta a ponta"""
    try:
        # Limpar arquivos temporários antes de começar
        limpar_arquivos_temporarios()
        
        # Passo 1: Carregar credenciais
        client_id, client_secret = carregar_credenciais()
        if not client_id or not client_secret:
            return False
            
        # Passo 2: Criar arquivo de credenciais
        if not criar_arquivo_credenciais(client_id, client_secret):
            return False
            
        # Passo 3: Gerar URL de autorização
        flow = gerar_url_autorizacao()
        if not flow:
            return False
            
        # Passo 4: Obter token
        creds = obter_token(flow)
        if not creds:
            return False
            
        # Passo 5: Testar serviço do calendário
        sucesso = testar_servico_calendario(creds)
        
        # Resumo do teste
        print_section("RESUMO DO TESTE")
        if sucesso:
            print_success("O teste de ponta a ponta foi concluído com SUCESSO!")
            print_info("Todas as etapas foram concluídas sem erros críticos.")
            print_info("A aplicação deve funcionar corretamente com o Google Calendar API.")
        else:
            print_warning("O teste foi concluído, mas com alguns problemas.")
            print_info("Verifique as mensagens de erro acima para resolver os problemas.")
        
        return sucesso
    
    finally:
        # Perguntar se deseja manter os arquivos temporários
        manter = input("\nDeseja manter os arquivos temporários para uso futuro? (s/n): ").lower()
        if manter != 's':
            limpar_arquivos_temporarios()
        else:
            print_info("Arquivos temporários mantidos para uso futuro.")

if __name__ == "__main__":
    print_section("TESTE PONTA A PONTA - GOOGLE CALENDAR API")
    print_info("Este script testará cada etapa do processo de autenticação e uso da API")
    print_info("Siga as instruções em cada etapa para completar o teste")
    
    input(Colors.BOLD + "\nPressione ENTER para iniciar o teste..." + Colors.ENDC)
    
    realizar_teste_completo() 