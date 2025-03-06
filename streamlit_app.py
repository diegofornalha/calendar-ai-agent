import streamlit as st
import json
import datetime
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import sys

# Verificar se estamos rodando no Streamlit Cloud
IS_STREAMLIT_CLOUD = os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud'

# Tentar importar do Anthropic com tratamento de erro
try:
    from ai_models.anthropic import Tool, Function, FunctionParameters, structured_chat_completion as anthropic_chat_completion
    anthropic_import_success = True
except ImportError as e:
    print(f"Erro ao importar módulos do Anthropic: {str(e)}")
    
    # Se no cloud e houve erro na importação, criar versões vazias das classes para evitar erros
    if IS_STREAMLIT_CLOUD:
        # Definições básicas para não quebrar outras partes do código
        from typing import Dict, Any, Optional, List
        from pydantic import BaseModel
        
        class FunctionParameters(BaseModel):
            type: str = "object"
            properties: Dict[str, Dict[str, Any]]
            required: List[str]
            additionalProperties: bool = False
        
        class Function(BaseModel):
            name: str
            description: str
            parameters: FunctionParameters
            strict: bool = True
        
        class Tool(BaseModel):
            type: str = "function"
            function: Function
            
        def anthropic_chat_completion(*args, **kwargs):
            # Versão simplificada que apenas retorna erro
            return json.dumps({"data": "API Anthropic não disponível", "cost": 0, "total_tokens": 0})
            
        anthropic_import_success = False
    else:
        # Em ambiente local, propagar o erro
        raise

# Importar o módulo do Groq
from ai_models.groq_api import structured_chat_completion as groq_chat_completion
from models.response import AIResponse
from utils import calendar_actions
from main import CALENDAR_TOOLS, get_system_message, handle_tool_call
# Importar o módulo de configuração do Google Calendar
from utils import calendar_config

# Configuração da página Streamlit
st.set_page_config(
    page_title="Calendário IA",
    page_icon="📅",
    layout="wide"
)

# Verificar se a URL solicitada é o caminho de verificação ACME
path_info = os.environ.get("PATH_INFO", "")

if "/.well-known/acme-challenge/" in path_info:
    # Extrair o token da URL
    token = path_info.split("/")[-1]
    
    if token == "4xyWfTdjON52ZneQEcTUJLlI1Y8hYoKeT5hU8OSLS6-T0L3WQNvIW-5FNaj87G9K":
        # Este é o conteúdo de verificação que deve ser retornado
        verification_content = "4xyWfTdjON52ZneQEcTUJLlI1Y8hYoKeT5hU8OSLS6-T0L3WQNvIW-5FNaj87G9K.M0-GObbb5ePi63ASQsPKBrDqfgayGnOWpyrEF0nHqug"
        
        # Remover toda a interface do Streamlit
        st.markdown(
            """
            <style>
                #root > div:nth-child(1) > div > div > div > div > section > div {visibility: hidden;}
                header {visibility: hidden;}
                footer {visibility: hidden;}
                #MainMenu {visibility: hidden;}
            </style>
            """,
            unsafe_allow_html=True
        )
        
        # Exibir apenas o conteúdo de verificação
        st.code(verification_content, language=None)
        
        # Tentativa adicional para mostrar como texto puro
        st.markdown(
            f"""
            <script>
                document.body.innerHTML = '{verification_content}';
                document.contentType = 'text/plain';
            </script>
            """,
            unsafe_allow_html=True
        )
        
        # Encerrar o script aqui
        sys.exit()

# Inicializar variáveis de sessão
if 'messages' not in st.session_state:
    st.session_state.messages = [get_system_message()]

if 'history' not in st.session_state:
    st.session_state.history = []

# Inicializar a configuração do Google Calendar na primeira execução
if 'google_calendar_initialized' not in st.session_state:
    try:
        # Garantir que as credenciais padrão existam
        calendar_config.ensure_default_credentials_exist()
        st.session_state.google_calendar_initialized = True
    except Exception as e:
        print(f"Erro ao inicializar credenciais do Google Calendar: {str(e)}")
        st.session_state.google_calendar_initialized = False

# Verificar se estamos rodando no Streamlit Cloud
is_streamlit_cloud = os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud'

# Inicializar a seleção da API
if 'selected_api' not in st.session_state:
    # No ambiente cloud, usar Groq por padrão para evitar problemas com o Anthropic
    if IS_STREAMLIT_CLOUD and not anthropic_import_success:
        st.session_state.selected_api = 'groq'
    else:
        st.session_state.selected_api = 'groq'  # Groq como padrão em qualquer ambiente

# Função para processar a mensagem do usuário
def process_message(user_input):
    if not user_input.strip():
        return
        
    # No ambiente cloud, forçar uso do Groq se Anthropic estiver selecionado mas sem chave ou falha na importação
    if IS_STREAMLIT_CLOUD and st.session_state.selected_api == 'anthropic':
        if not anthropic_import_success:
            st.warning("Biblioteca Anthropic não está disponível no ambiente cloud. Alternando para Groq automaticamente.")
            st.session_state.selected_api = 'groq'
        elif not st.session_state.get('api_key'):
            st.warning("No ambiente Streamlit Cloud, você precisa fornecer sua própria chave API Anthropic. Alternando para Groq automaticamente.")
            st.session_state.selected_api = 'groq'

    # Verificar se a chave da API foi fornecida para a API selecionada
    if st.session_state.selected_api == 'anthropic' and not st.session_state.get('api_key'):
        return "Por favor, insira sua chave da API Anthropic na barra lateral para continuar."

    # Adicionar mensagem do usuário ao histórico
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.history.append({"role": "user", "content": user_input})
    
    # Mostrar mensagem de processamento
    with st.spinner("O assistente está pensando..."):
        try:
            # Atualizar a mensagem do sistema para ter a hora atual
            st.session_state.messages[0] = get_system_message()
            
            # Selecionar a API adequada e configurar as variáveis de ambiente
            if st.session_state.selected_api == 'anthropic':
                # Verificar se o Anthropic está disponível (importação bem-sucedida)
                if not anthropic_import_success:
                    st.error("Biblioteca Anthropic não está disponível. Alternando para Groq.")
                    st.session_state.selected_api = 'groq'
                    st.rerun()
                    return None
                
                # Verificar se o cliente está disponível
                try:
                    from ai_models.anthropic import client as anthropic_client
                    if anthropic_client is None:
                        st.error("Cliente Anthropic não está disponível. Alternando para Groq.")
                        st.session_state.selected_api = 'groq'
                        st.rerun()
                        return None
                except Exception as e:
                    st.error(f"Erro ao acessar cliente Anthropic: {str(e)}. Alternando para Groq.")
                    st.session_state.selected_api = 'groq'
                    st.rerun()
                    return None
                
                # Garantir que a chave de API esteja atualizada
                os.environ["ANTHROPIC_API_KEY"] = st.session_state.api_key
                try:
                    from ai_models.anthropic import client, get_client
                    if hasattr(client, '_api_key') and client._api_key != st.session_state.api_key:
                        client._api_key = st.session_state.api_key
                except Exception as e:
                    st.error(f"Erro ao atualizar cliente Anthropic: {str(e)}. Alternando para Groq.")
                    st.session_state.selected_api = 'groq'
                    st.rerun()
                    return None
                
                # Fazer a chamada à API Anthropic
                try:
                    response = anthropic_chat_completion(
                        messages=st.session_state.messages,
                        output_model=AIResponse,
                        model="claude-3-sonnet-20250219",
                        temperature=0.7,
                        tools=CALENDAR_TOOLS,
                        tool_handler=handle_tool_call
                    )
                except Exception as e:
                    st.error(f"Erro na chamada à API Anthropic: {str(e)}. Alternando para Groq.")
                    st.session_state.selected_api = 'groq'
                    st.rerun()
                    return None
            else:  # Usar Groq
                # Garantir que a chave de API Groq esteja atualizada
                os.environ["GROQ_API_KEY"] = st.session_state.get('groq_api_key', "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")
                from ai_models.groq_api import client, get_client
                if hasattr(client, '_api_key') and client._api_key != st.session_state.get('groq_api_key', "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"):
                    client._api_key = st.session_state.get('groq_api_key', "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")
                
                # Fazer a chamada à API Groq
                response = groq_chat_completion(
                    messages=st.session_state.messages,
                    output_model=AIResponse,
                    model="llama3-8b-8192",  # Usar Llama 3 8B
                    temperature=0.7,
                    tools=CALENDAR_TOOLS,
                    tool_handler=handle_tool_call
                )
            
            response_data = json.loads(response)
            assistant_message = response_data["data"]
            
            # Adicionar resposta do assistente ao histórico
            st.session_state.messages.append({"role": "assistant", "content": assistant_message})
            st.session_state.history.append({"role": "assistant", "content": assistant_message})
            
            # Calcular e registrar custo da API
            if 'total_cost' not in st.session_state:
                st.session_state.total_cost = 0
            st.session_state.total_cost += response_data.get("cost", 0)
            
            return assistant_message
            
        except Exception as e:
            error_message = f"Desculpe, encontrei um erro: {str(e)}"
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            st.session_state.history.append({"role": "assistant", "content": error_message})
            return error_message

# Interface do cabeçalho
st.title("📅 Calendário IA")
st.write("Este assistente pode ajudar você a gerenciar seu calendário do Google. Pergunte sobre seus eventos ou peça para criar novos!")

# Informação sobre as configurações padrão
st.info("""
✨ **Aplicativo pré-configurado!**

Este aplicativo está pré-configurado com:
- **API Groq**: Configurada e pronta para uso (gratuita)
- **Google Calendar API**: Configurada com credenciais padrão (requer apenas autenticação)

Você pode começar a usar imediatamente ou personalizar as configurações na barra lateral.
""")

# Verificar se estamos rodando no Streamlit Cloud
if IS_STREAMLIT_CLOUD:
    st.info(f"""
    ℹ️ **Nota sobre o Streamlit Cloud**: 
    Esta aplicação está rodando no Streamlit Cloud. Estamos usando a API Groq por padrão para maior compatibilidade.
    
    Status do Anthropic: {"✅ Disponível" if anthropic_import_success else "❌ Indisponível"}
    """)
    
    if not anthropic_import_success:
        st.warning("""
        ⚠️ A biblioteca Anthropic não está disponível neste ambiente. 
        A interface mostrará apenas a opção do Groq, que é gratuita.
        """)

# Exibir aviso se a chave da API não estiver configurada para Anthropic quando selecionada
if st.session_state.selected_api == 'anthropic' and not st.session_state.get('api_key'):
    st.warning("⚠️ **Configuração necessária**: Por favor, insira sua chave da API Anthropic na barra lateral para usar o assistente.")
    st.info("Você pode obter uma chave de API no [Console de Desenvolvedores da Anthropic](https://console.anthropic.com/)")

# Sidebar com informações e estatísticas
with st.sidebar:
    st.header("Configurações do Assistente")

    # Verificar se estamos rodando no Streamlit Cloud
    is_streamlit_cloud = os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud'
    if is_streamlit_cloud:
        st.info("""
        ⚠️ **Ambiente Streamlit Cloud**
        
        Esta aplicação está rodando no Streamlit Cloud. Algumas limitações:
        
        1. O OAuth do Google pode ser mais complicado
        2. As sessões são reiniciadas com mais frequência
        3. As credenciais precisam ser configuradas a cada sessão
        
        Para melhor experiência, considere executar a aplicação localmente.
        """)
        
        # Adicionar link para repositório
        st.markdown("[📦 Ver código-fonte no GitHub](https://github.com/seu-usuario/calendar-ai-agent)")

    # Selecionar qual API usar
    st.subheader("Selecione a API")

    # Verificar se o cliente Anthropic está disponível
    anthropic_available = anthropic_import_success
    if anthropic_import_success:
        try:
            from ai_models.anthropic import client as anthropic_client
            anthropic_available = anthropic_client is not None
        except Exception:
            anthropic_available = False

    # Se estamos no cloud e o cliente Anthropic não está disponível, mostrar um aviso
    if IS_STREAMLIT_CLOUD and not anthropic_available:
        st.warning("⚠️ O cliente Anthropic não está disponível no ambiente cloud. A opção Groq será usada por padrão.")

    # Opções de API disponíveis
    api_options = ["Groq (Gratuita)"]
    if anthropic_available or not IS_STREAMLIT_CLOUD:
        api_options.append("Anthropic (Paga)")

    # Índice padrão (Groq)
    default_index = 0
    if st.session_state.selected_api == 'anthropic' and (anthropic_available or not IS_STREAMLIT_CLOUD):
        default_index = 1

    api_selection = st.radio(
        "Escolha qual API utilizar:",
        options=api_options,
        index=default_index,
        help="Groq oferece acesso gratuito com bom desempenho. Anthropic oferece modelos mais avançados, mas requer uma chave de API paga."
    )

    # Atualizar a seleção da API
    new_api = 'groq' if api_selection == "Groq (Gratuita)" else 'anthropic'
    if new_api != st.session_state.selected_api:
        st.session_state.selected_api = new_api
        st.rerun()
    
    # Mostrar detalhes da API selecionada
    if st.session_state.selected_api == 'groq':
        st.write("**API selecionada:** Groq (usando LLaMA 3 8B)")
        st.write("Vantagens: Gratuito, boa velocidade")
        st.write("Desvantagens: Menor capacidade que Claude")
    else:
        st.write("**API selecionada:** Anthropic Claude")
        st.write("Vantagens: Alta capacidade, melhor qualidade")
        st.write("Desvantagens: Requer assinatura paga")
    
    st.divider()
    
    # Configuração da API de acordo com a seleção
    if st.session_state.selected_api == 'anthropic':
        st.subheader("Configuração da API Anthropic")
        
        # Inicializar a chave da API no session_state se não existir
        if 'api_key' not in st.session_state:
            # Tentar obter do arquivo .env primeiro
            from dotenv import load_dotenv
            load_dotenv()
            st.session_state.api_key = os.getenv("ANTHROPIC_API_KEY", "")
            # Inicializar o status de validação
            st.session_state.api_validated = False
        
        # Mostrar status da chave da API
        if 'api_validated' in st.session_state and st.session_state.api_validated:
            st.markdown("**Status:** 🟢 Chave validada")
        elif st.session_state.get('api_key'):
            st.markdown("**Status:** 🟠 Chave não validada (clique em 'Testar Conexão com API')")
        else:
            st.markdown("**Status:** 🔴 Chave não configurada")
        
        # Campo para a chave da API com a chave atual como valor padrão
        new_api_key = st.text_input(
            "Chave da API Anthropic:",
            value=st.session_state.api_key,
            type="password",
            help="Insira sua chave da API Anthropic (formato: sk-ant-api...)"
        )
        
        # Atualizar a chave da API se for alterada
        if new_api_key != st.session_state.api_key:
            st.session_state.api_key = new_api_key
            
            # Atualizar a variável de ambiente
            os.environ["ANTHROPIC_API_KEY"] = new_api_key
            
            # Reinicializar o cliente da API
            from ai_models.anthropic import client
            client._api_key = new_api_key
            
            st.success("Chave da API atualizada com sucesso!")
        
        # Botão para testar a chave da API
        if st.button("Testar Conexão com API") and st.session_state.api_key:
            with st.spinner("Testando a chave da API..."):
                try:
                    # Importar o cliente Anthropic
                    from ai_models.anthropic import client
                    
                    # Testar uma chamada simples à API
                    response = client.messages.create(
                        model="claude-3-haiku-20241022",
                        max_tokens=10,
                        messages=[
                            {"role": "user", "content": "Olá! Isso é um teste de conexão."}
                        ]
                    )
                    
                    # Se não ocorrer erro, a conexão foi bem-sucedida
                    st.success("✅ Conexão bem-sucedida! A chave da API é válida.")
                    
                    # Atualizar o estado da aplicação
                    if 'api_validated' not in st.session_state:
                        st.session_state.api_validated = True
                    
                except Exception as e:
                    st.error(f"❌ Erro de conexão: {str(e)}")
                    st.session_state.api_validated = False
    else:
        # Configuração para API Groq
        st.subheader("Configuração da API Groq")
        st.write("Usando a chave da API Groq fornecida por padrão.")
        st.write("Você também pode usar sua própria chave da API:")
        
        # Inicializar a chave da API no session_state se não existir
        if 'groq_api_key' not in st.session_state:
            # Usar a chave padrão ou tentar obter do arquivo .env
            from dotenv import load_dotenv
            load_dotenv()
            st.session_state.groq_api_key = os.getenv("GROQ_API_KEY", "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")
            # Inicializar o status de validação
            st.session_state.groq_api_validated = True  # Presumir válida inicialmente
        
        # Campo para a chave da API com a chave atual como valor padrão
        new_groq_api_key = st.text_input(
            "Chave da API Groq (opcional):",
            value=st.session_state.groq_api_key,
            type="password",
            help="Insira sua chave da API Groq (formato: gsk_...)"
        )
        
        # Atualizar a chave da API se for alterada
        if new_groq_api_key != st.session_state.groq_api_key:
            st.session_state.groq_api_key = new_groq_api_key
            
            # Atualizar a variável de ambiente
            os.environ["GROQ_API_KEY"] = new_groq_api_key
            
            # Reinicializar o cliente da API
            from ai_models.groq_api import client
            client._api_key = new_groq_api_key
            
            st.success("Chave da API Groq atualizada com sucesso!")
        
        # Botão para testar a chave da API Groq
        if st.button("Testar Conexão com API Groq"):
            with st.spinner("Testando a chave da API Groq..."):
                try:
                    # Importar o cliente Groq
                    from ai_models.groq_api import client
                    
                    # Testar uma chamada simples à API
                    response = client.chat.completions.create(
                        model="llama3-8b-8192",
                        max_tokens=10,
                        messages=[
                            {"role": "user", "content": "Olá! Isso é um teste de conexão."}
                        ]
                    )
                    
                    # Se não ocorrer erro, a conexão foi bem-sucedida
                    st.success("✅ Conexão bem-sucedida! A chave da API Groq é válida.")
                    
                    # Atualizar o estado da aplicação
                    st.session_state.groq_api_validated = True
                    
                except Exception as e:
                    st.error(f"❌ Erro de conexão: {str(e)}")
                    st.session_state.groq_api_validated = False
    
    st.divider()
    
    # Configuração do Google Calendar
    st.subheader("Google Calendar")
    
    # Garantir que as credenciais padrão existam
    calendar_config.ensure_default_credentials_exist()
    
    # Obter informações sobre o calendário atual
    calendar_info = calendar_config.get_calendar_info()
    
    # Exibir status da configuração
    if calendar_info['authenticated']:
        st.success("✅ Google Calendar conectado")
        
        # Mostrar qual calendário está sendo usado
        primary_label = " (Padrão)" if calendar_info['primary_calendar'] == calendar_info['selected_calendar'] else ""
        st.write(f"**Calendário atual:** {next((cal['summary'] for cal in calendar_info['calendars'] if cal['id'] == calendar_info['selected_calendar']), 'Primário')}{primary_label}")
        
        # Opção para selecionar calendário
        if len(calendar_info['calendars']) > 1:
            calendar_options = {f"{cal['summary']}{' (Padrão)' if cal['primary'] else ''}": cal['id'] for cal in calendar_info['calendars']}
            selected_calendar_name = st.selectbox(
                "Selecionar calendário:",
                options=list(calendar_options.keys()),
                index=list(calendar_options.values()).index(calendar_info['selected_calendar']) if calendar_info['selected_calendar'] in calendar_options.values() else 0
            )
            
            # Atualizar o calendário selecionado na sessão
            selected_calendar_id = calendar_options[selected_calendar_name]
            if selected_calendar_id != st.session_state.get('selected_calendar_id'):
                st.session_state.selected_calendar_id = selected_calendar_id
                st.success(f"Calendário alterado para: {selected_calendar_name}")
    else:
        if calendar_info['credentials_exist']:
            st.info("""
            ℹ️ **Credenciais pré-configuradas!** 
            
            O aplicativo já está configurado com credenciais padrão do Google Cloud. 
            Basta autenticar para começar a usar.
            """)
            
            # Inicializar o fluxo de autenticação no estado da sessão, se ainda não existir
            if 'auth_flow' not in st.session_state:
                st.session_state.auth_flow = None
                st.session_state.auth_url = None
            
            # Botão para gerar URL de autenticação
            if st.button("Iniciar Autenticação com Google Calendar"):
                with st.spinner("Gerando link de autenticação..."):
                    auth_url, flow_or_msg = calendar_config.get_auth_url()
                    if auth_url:
                        st.session_state.auth_url = auth_url
                        st.session_state.auth_flow = flow_or_msg
                        st.success("Link de autenticação gerado!")
                    else:
                        st.error(flow_or_msg)
            
            # Exibir o link de autenticação se disponível
            if 'auth_url' in st.session_state and st.session_state.auth_url:
                st.markdown(f"""
                **Clique no link abaixo para autenticar:**
                
                [Abrir página de autenticação do Google]({st.session_state.auth_url})
                """)
                
                # Instruções diferentes baseadas no ambiente
                if IS_STREAMLIT_CLOUD:
                    st.info("""
                    **Instruções para autenticação no Streamlit Cloud:**
                    
                    1. O link acima abrirá a página de autenticação do Google
                    2. Faça login com sua conta Google e autorize o acesso
                    3. Após autorizar, você será redirecionado para uma página que pode não carregar corretamente
                    4. Na barra de endereço do navegador, copie o valor do parâmetro `code=` na URL
                    5. Cole este código abaixo e clique em "Confirmar Autenticação"
                    
                    Atenção: O código é a parte após `code=` e antes de qualquer `&` na URL.
                    """)
                else:
                    st.info("Após a autenticação, você será redirecionado para uma página local. Copie o código da URL e cole abaixo.")
                
                # Campo para inserir o código de autenticação
                auth_code = st.text_input("Cole o código de autenticação aqui (da URL após 'code='):")
                
                # Adicionando explicação visual de como encontrar o código
                st.markdown("""
                **Como encontrar o código:**
                
                Na URL de redirecionamento, o código está após `code=` e antes de qualquer `&`.
                
                Exemplo: `http://localhost:xxxxx/?code=4/P7q-XXXXXXXXXXX-XXXXXXXXXXXXXXX&scope=...`
                
                Você deve copiar apenas a parte `4/P7q-XXXXXXXXXXX-XXXXXXXXXXXXXXX`
                """)
                
                if st.button("Confirmar Autenticação") and auth_code:
                    if st.session_state.auth_flow:
                        with st.spinner("Verificando código de autenticação..."):
                            success, msg = calendar_config.authenticate_with_code(st.session_state.auth_flow, auth_code)
                            if success:
                                st.success(msg)
                                st.session_state.auth_flow = None
                                st.session_state.auth_url = None
                                st.rerun()
                            else:
                                st.error(msg)
        else:
            st.error("❌ Erro nas credenciais padrão do Google Calendar")
        
        # Opções de configuração - Tabs para diferentes métodos
        tab1, tab2 = st.tabs(["Usar Credenciais Padrão", "Configuração Avançada"])
        
        # Tab 1: Usar credenciais padrão
        with tab1:
            st.write("O aplicativo já está pré-configurado com credenciais padrão do Google Cloud.")
            st.info(f"""
            **ID do Cliente pré-configurado:** 
            ```
            {calendar_config.DEFAULT_CLIENT_ID}
            ```
            """)
            
            if st.button("Usar Credenciais Padrão"):
                with st.spinner("Configurando credenciais padrão..."):
                    success = calendar_config.ensure_default_credentials_exist()
                    if success:
                        st.success("Credenciais padrão configuradas com sucesso!")
                        st.info("Clique em 'Iniciar Autenticação com Google Calendar' acima para continuar.")
                    else:
                        st.info("As credenciais padrão já estavam configuradas. Clique em 'Iniciar Autenticação com Google Calendar' acima para continuar.")
        
        # Tab 2: Configuração avançada (antigo Tab 1 e Tab 2)
        with tab2:
            # Sub-tabs para diferentes métodos de configuração avançada
            adv_tab1, adv_tab2 = st.tabs(["ID do Cliente", "Arquivo JSON"])
            
            # Sub-Tab 1: Configuração com ID do Cliente
            with adv_tab1:
                st.write("Insira o ID do cliente do Google Cloud:")
                
                st.info("""
                💡 **Dica**: Você pode inserir apenas o ID do cliente (formato: xxxxx.apps.googleusercontent.com).
                Na maioria dos casos, isso é suficiente para a autenticação básica.
                """)
                
                client_id = st.text_input(
                    "ID do Cliente:", 
                    value="",
                    placeholder="Exemplo: 459301708692-rps1d66oed4sbsg1rcn13jcgthktlg6i.apps.googleusercontent.com",
                    help="O ID do cliente está disponível no console do Google Cloud, na seção 'Credenciais'"
                )
                
                # Opção para expandir e mostrar campo de segredo do cliente
                show_secret = st.checkbox(
                    "Tenho o segredo do cliente (opcional)", 
                    value=False,
                    help="O segredo do cliente pode ser necessário para algumas operações avançadas"
                )
                
                client_secret = None
                if show_secret:
                    client_secret = st.text_input(
                        "Segredo do Cliente:", 
                        type="password",
                        placeholder="GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx",
                        help="O segredo do cliente está disponível no console do Google Cloud, junto com o ID do cliente"
                    )
                
                if st.button("Salvar Credenciais", key="save_client_id"):
                    if client_id:
                        with st.spinner("Salvando credenciais..."):
                            success, msg = calendar_config.save_client_credentials(client_id, client_secret)
                            if success:
                                st.success(msg)
                                # Não iniciar autenticação automaticamente
                                st.info("Credenciais salvas. Clique em 'Iniciar Autenticação com Google Calendar' acima para continuar.")
                            else:
                                st.error(msg)
                    else:
                        st.error("Por favor, forneça pelo menos o ID do cliente.")
            
            # Sub-Tab 2: Upload de arquivo JSON
            with adv_tab2:
                st.write("Faça upload do arquivo de credenciais JSON:")
                
                st.info("""
                💡 **Dica**: Use esta opção se você já fez o download do arquivo JSON de credenciais 
                completo do Google Cloud Console.
                """)
                
                uploaded_file = st.file_uploader(
                    "Arquivo de credenciais JSON", 
                    type=["json"],
                    help="Arquivo JSON baixado do console do Google Cloud, contendo as credenciais OAuth 2.0"
                )
                
                if uploaded_file is not None:
                    if st.button("Salvar Credenciais", key="save_json"):
                        with st.spinner("Salvando credenciais..."):
                            success, msg = calendar_config.save_uploaded_credentials(uploaded_file)
                            if success:
                                st.success(msg)
                                # Não iniciar autenticação automaticamente
                                st.info("Credenciais salvas. Clique em 'Iniciar Autenticação com Google Calendar' acima para continuar.")
                            else:
                                st.error(msg)
    
    st.write("---")
    
    st.write("""
    **Como obter as credenciais do Google Calendar:**
    1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
    2. Crie um projeto ou selecione um existente
    3. Ative a API do Google Calendar em "APIs e serviços" > "Biblioteca"
    4. Configure a tela de consentimento OAuth em "APIs e serviços" > "Tela de consentimento OAuth"
       - Escolha "Externo" como tipo de usuário
       - Preencha os campos obrigatórios (nome do app, email, etc.)
    5. Crie credenciais OAuth 2.0 em "APIs e serviços" > "Credenciais":
       - Clique em "Criar Credenciais" > "ID do cliente OAuth"
       - Selecione "Aplicativo para Desktop" como tipo
       - Dê um nome ao cliente e clique em "Criar"
    6. Copie o ID do cliente (formato: xxxxx.apps.googleusercontent.com)
    """)
    
    st.divider()
    
    st.header("Sobre o Assistente")
    st.write("Este assistente usa modelos de IA para processar linguagem natural e interagir com o Google Calendar.")
    
    st.subheader("Estatísticas")
    if 'total_cost' in st.session_state:
        st.write(f"Custo total da API: ${st.session_state.total_cost:.6f}")
    
    st.subheader("Exemplos de perguntas")
    st.markdown("""
    - Quais são meus eventos para hoje?
    - Agende uma reunião com João amanhã às 14h
    - Mostre meus compromissos da próxima semana
    - Cancele a reunião de sexta-feira
    """)
    
    if st.button("Limpar histórico de conversas"):
        st.session_state.messages = [get_system_message()]
        st.session_state.history = []
        st.session_state.total_cost = 0
        st.rerun()

# Container principal para o chat
chat_container = st.container()

# Exibir histórico de mensagens
with chat_container:
    for message in st.session_state.history:
        if message["role"] == "user":
            st.markdown(f"**Você**: {message['content']}")
        else:
            st.markdown(f"**Assistente**: {message['content']}")
            st.markdown("---")

# Entrada de texto para as perguntas do usuário
api_ready = ((st.session_state.selected_api == 'anthropic' and st.session_state.get('api_key') and st.session_state.get('api_validated', False))
             or (st.session_state.selected_api == 'groq' and st.session_state.get('groq_api_validated', True)))

user_input = st.text_input(
    "Digite sua pergunta:", 
    key="user_input",
    disabled=not api_ready,
    placeholder="Configure a chave da API na barra lateral antes de usar o assistente" if not api_ready else "Digite sua pergunta aqui..."
)

if st.button("Enviar", disabled=not api_ready or not user_input) or (api_ready and user_input and user_input != st.session_state.get("last_input", "")):
    st.session_state.last_input = user_input
    response = process_message(user_input)
    st.rerun()

# Se a API não estiver configurada, mostrar uma mensagem de ajuda
if not api_ready and st.session_state.selected_api == 'anthropic':
    st.info("Para usar o assistente com o Anthropic Claude, você precisa configurar e validar sua chave da API na barra lateral.")

# Adicionar um footer com informações adicionais
st.markdown("---")
st.markdown(f"**Assistente de Calendário IA** | Usando: {st.session_state.selected_api.capitalize()} | Desenvolvido com Streamlit")
