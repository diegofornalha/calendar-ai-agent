"""
Aplicativo simplificado de Calendário com Firebase e autenticação anônima.
"""

import streamlit as st
import json
import datetime
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import firebase_auth
import uuid

# Importar o módulo para integração com a API Gemini
try:
    import genkit_integration
    genkit_integration_available = True
except ImportError:
    genkit_integration_available = False

# Tentar importar o módulo de configuração do Firebase Admin SDK
try:
    import firebase_admin_config
    firebase_admin_config_available = True
except ImportError:
    firebase_admin_config_available = False

# Verificar se estamos rodando no Streamlit Cloud
IS_STREAMLIT_CLOUD = os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud'

# Configuração da página
st.set_page_config(
    page_title="Calendário IA Customizável",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Verificar URL hash para /#config
if 'query_params' not in st.session_state:
    st.session_state.query_params = st.experimental_get_query_params()

# Capturar hash da URL via Javascript
config_detector_code = """
<script>
// Função para verificar o hash na URL
function checkHash() {
    // Se o hash for #config, armazenar no session storage
    if (window.location.hash === '#config') {
        sessionStorage.setItem('show_config', 'true');
        // Não redirecionar para remover o hash, apenas para manter o #config na URL
        // window.location.href = window.location.pathname;
    }
    
    // Verificar se devemos mostrar a configuração
    if (sessionStorage.getItem('show_config') === 'true') {
        // Enviar mensagem para o Streamlit
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: true
        }, '*');
    }
}

// Executar ao carregar a página
checkHash();
// Executar quando o hash mudar
window.addEventListener('hashchange', checkHash);
</script>
"""

# Componente para detectar #config na URL
config_detector = st.components.v1.html(config_detector_code, height=0, width=0)

# Verificar se as configurações avançadas devem ser mostradas
show_advanced_config = bool(config_detector) or st.session_state.get('show_advanced_config', False)
if show_advanced_config:
    st.session_state.show_advanced_config = True

# Verificar se a configuração do Firebase está na sessão
if 'firebase_config_shown' not in st.session_state:
    st.session_state.firebase_config_shown = False
    
# Inicializar variáveis de sessão para o chat
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Olá! Sou seu assistente de calendário com IA Gemini. Como posso ajudar você a gerenciar seus eventos e compromissos hoje?"}
    ]

# Configurar a chave API Gemini por padrão
if 'google_genai_api_key' not in st.session_state:
    # Usar a chave API fornecida como padrão
    st.session_state.google_genai_api_key = "AIzaSyBfyAPI__JVt31lBQtOcaPzWtbLqmFmihE"
    
# Configurar a API selecionada
if 'selected_api' not in st.session_state:
    st.session_state.selected_api = 'gemini'  # Gemini como padrão

# Inicializar o contador de créditos de Gemini para usuários com login efetivo
if 'gemini_credits' not in st.session_state:
    st.session_state.gemini_credits = 5  # Cada usuário tem direito a 5 créditos

# Sidebar para autenticação e navegação
with st.sidebar:
    # Verificar se há usuário autenticado
    if 'firebase_user' not in st.session_state or st.session_state.firebase_user is None:
        st.title("Calendário IA")
        
        # Mostrar componente de login do Firebase
        firebase_auth.firebase_login_button()
        
        # Mostrar link para configurações avançadas
        if st.button("⚙️ Configurações Avançadas"):
            # Modificar para usar diretamente o hash #config
            st.markdown('<a href="#config" target="_self">Ir para configurações</a>', unsafe_allow_html=True)
    else:
        # Exibir informações do usuário logado
        st.title("Calendário IA")
        
        # Mostrar ícone do usuário e nome
        if st.session_state.firebase_user.get('isAnonymous', False):
            st.write("👤 Modo Demonstração")
        else:
            user_name = st.session_state.firebase_user.get('displayName', st.session_state.firebase_user.get('email', 'Usuário'))
            st.write(f"👤 {user_name}")
        
        # Botão de logout
        if st.button("Sair"):
            # Limpar dados de sessão
            st.session_state.firebase_user = None
            st.session_state.firebase_token = None
            
            # Limpar tokens do Google se existirem
            if 'google_access_token' in st.session_state:
                del st.session_state.google_access_token
            
            # Recarregar a página
            st.rerun()
        
        # Mostrar link para configurações avançadas
        if not st.session_state.get('show_advanced_config', False):
            st.markdown('<a href="#config" target="_self">⚙️ Configurações Avançadas</a>', unsafe_allow_html=True)
        elif st.session_state.get('show_advanced_config', False) and st.button("🔙 Voltar ao aplicativo"):
            st.session_state.show_advanced_config = False
            st.rerun()

# Conteúdo principal
if st.session_state.get('show_advanced_config', False):
    # Mostrar configurações avançadas
    st.header("⚙️ Configurações Avançadas")
    
    # Criar abas para diferentes tipos de configuração
    firebase_tab, api_tab, debug_tab = st.tabs(["Firebase", "APIs", "Depuração"])
    
    # Aba Firebase
    with firebase_tab:
        firebase_auth.firebase_config_component(form_key_suffix="adv_config")
        
        # Exibir o Firebase Admin SDK se disponível
        if firebase_admin_config_available:
            st.subheader("Firebase Admin SDK")
            firebase_admin_config.admin_config_component()
    
    # Aba APIs
    with api_tab:
        st.subheader("Configuração de APIs")
        
        # API do Google Calendar
        st.write("### Google Calendar API")
        st.write("""
        A API do Google Calendar permite integração com o calendário do usuário.
        Você pode obter credenciais no [Google Cloud Console](https://console.cloud.google.com/).
        """)
        
        # Gemini API
        st.write("### Gemini API")
        gemini_key = st.text_input(
            "Chave API do Gemini",
            value=os.environ.get("GEMINI_API_KEY", ""),
            type="password",
            help="Obtenha sua chave API em https://makersuite.google.com/app/apikey"
        )
        
        if st.button("Salvar Chave Gemini"):
            # Salvar na sessão
            st.session_state.gemini_api_key = gemini_key
            st.success("Chave API salva com sucesso!")
    
    # Aba de depuração
    with debug_tab:
        st.subheader("Informações de Depuração")
        
        # Mostrar informações do ambiente
        st.write("### Ambiente")
        st.code(f"""
        Streamlit Cloud: {IS_STREAMLIT_CLOUD}
        Firebase Admin SDK disponível: {firebase_admin_config_available}
        Gemini Integration disponível: {genkit_integration_available}
        """)
        
        # Mostrar variáveis de sessão
        if st.checkbox("Mostrar variáveis de sessão"):
            st.write("### Session State")
            session_state_dict = {k: v for k, v in st.session_state.items() 
                                if not k.startswith('_') and k not in ['firebase_token', 'google_access_token']}
            st.json(session_state_dict)

elif 'firebase_user' not in st.session_state or st.session_state.firebase_user is None:
    # Usuário não autenticado - mostrar tela de boas-vindas
    st.header("Bem-vindo ao Calendário IA!")
    
    # Usar colunas para layout mais organizado
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("""
        ### Bem-vindo ao aplicativo Calendário IA!
        
        Este aplicativo integra um calendário com recursos de inteligência artificial Gemini.
        """)
        
        # Destacar o modo de demonstração como opção recomendada
        st.success("""
        ## 📣 Recomendação: Use o Modo Demonstração
        
        Devido a limitações na configuração atual da API, recomendamos usar o **Modo Demonstração** 
        para visualizar a aplicação imediatamente.
        
        👉 Selecione a aba **Modo Demonstração** no painel de autenticação à esquerda.
        """)
        
        # Seção de informações sobre as opções
        st.markdown("""
        ## Opções disponíveis:
        """)
        
        # Modo Demonstração
        st.info("""
        ### 🚀 Modo Demonstração
        
        Acesse uma versão simplificada do aplicativo imediatamente, sem configurações adicionais.
        - Visualize a interface básica
        - Explore o layout e os componentes
        - Não requer configuração adicional
        """)
        
        # Configuração personalizada
        st.warning("""
        ### ⚙️ Configuração personalizada
        
        Para usar todas as funcionalidades (incluindo autenticação por e-mail):
        1. Crie seu próprio projeto no [Firebase Console](https://console.firebase.google.com)
        2. Habilite a Identity Toolkit API no Google Cloud
        3. Configure suas credenciais nas configurações avançadas
        
        Esta opção é recomendada para quem deseja implementar o aplicativo em produção.
        """)
    
    with col2:
        st.info("""
        👈 Utilize o painel lateral para acessar o aplicativo
        """)
        
        # Imagem ilustrativa
        st.image("https://cdn-icons-png.flaticon.com/512/55/55281.png", width=180)

    # Informações sobre customização
    st.markdown("---")
    st.subheader("Demonstração do Calendário")
    
    # Calendário simulado
    dates_col, events_col = st.columns([1, 3])
    
    with dates_col:
        view_date = st.date_input("Selecionar data", datetime.datetime.now().date())
    
    with events_col:
        st.write(f"Eventos para {view_date.strftime('%d/%m/%Y')}")
        st.write("Sem eventos para esta data.")
        
        # Adicionar evento de exemplo
        st.button("+ Adicionar Evento")
else:
    # Usuário autenticado - mostrar interface simplificada com calendário e chat
    st.title(f"Olá, {st.session_state.firebase_user.get('displayName', 'Usuário')}! 👋")
    
    # Verificar autenticação anônima
    if st.session_state.firebase_user.get('isAnonymous', False):
        st.error("""
        ### ⚠️ Modo Demonstração Ativo
        
        Você está usando o modo demonstração com funcionalidades limitadas:
        - Interface simplificada do calendário (apenas visualização)
        - O assistente IA Gemini NÃO está disponível
        - Alterações não serão salvas
        
        **Nota:** Para funcionalidades completas, seria necessário configurar seu próprio projeto Firebase
        e habilitar a Identity Toolkit API no Google Cloud Console.
        """)
    else:
        # Mostrar créditos disponíveis para usuários com login efetivo
        st.success(f"""
        ### ✅ Modo Completo Ativo 
        
        Você tem acesso a todas as funcionalidades:
        - Calendário funcional
        - Assistente IA Gemini com {st.session_state.gemini_credits} créditos disponíveis
        - Configurações personalizadas
        """)
        
        # Adicionar acesso ao Google Calendar para usuários autenticados por Google
        if 'google_access_token' in st.session_state and st.session_state.google_access_token:
            calendar_tab, chat_tab, config_tab = st.tabs(["Google Calendar", "Assistente", "Configurações Avançadas"])
            
            # Aba do Google Calendar
            with calendar_tab:
                st.header("Seus Eventos do Google Calendar")
                
                # Função para listar eventos do Google Calendar
                def list_calendar_events(credentials, max_results=10, time_min=None, time_max=None):
                    try:
                        # Construir o serviço do Google Calendar
                        service = build('calendar', 'v3', credentials=credentials)
                        
                        # Definir parâmetros da consulta
                        params = {
                            'calendarId': 'primary',
                            'maxResults': max_results,
                            'singleEvents': True,
                            'orderBy': 'startTime'
                        }
                        
                        # Adicionar intervalo de datas se fornecido
                        if time_min:
                            params['timeMin'] = time_min
                        else:
                            # Por padrão, mostrar eventos a partir de hoje
                            now = datetime.datetime.utcnow().isoformat() + 'Z'
                            params['timeMin'] = now
                            
                        if time_max:
                            params['timeMax'] = time_max
                        
                        # Fazer a chamada à API
                        events_result = service.events().list(**params).execute()
                        events = events_result.get('items', [])
                        
                        return events
                    except Exception as e:
                        st.error(f"Erro ao obter eventos do calendário: {str(e)}")
                        return []
                
                # Obter credenciais para acessar o Google Calendar
                calendar_creds = None
                
                # Tentar usar o token de acesso do Google obtido durante o login
                if 'google_access_token' in st.session_state:
                    try:
                        # Criar credenciais a partir do token de acesso
                        calendar_creds = Credentials(
                            token=st.session_state.google_access_token,
                            scopes=["https://www.googleapis.com/auth/calendar.readonly"]
                        )
                    except Exception as e:
                        st.warning(f"Não foi possível criar credenciais a partir do token: {str(e)}")
                
                # Se não temos credenciais, usar a função existente para obtê-las
                if not calendar_creds:
                    calendar_creds = get_google_calendar_credentials()
                
                if calendar_creds:
                    # Controles de filtro de eventos
                    st.subheader("Filtrar Eventos")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        start_date = st.date_input("De", datetime.date.today())
                    
                    with col2:
                        end_date = st.date_input("Até", datetime.date.today() + datetime.timedelta(days=30))
                    
                    with col3:
                        max_events = st.number_input("Número máximo de eventos", min_value=1, max_value=50, value=10)
                    
                    # Botão para buscar eventos
                    if st.button("Buscar Eventos"):
                        with st.spinner("Buscando eventos..."):
                            # Converter datas para formato ISO 8601
                            time_min = datetime.datetime.combine(start_date, datetime.time.min).isoformat() + 'Z'
                            time_max = datetime.datetime.combine(end_date, datetime.time.max).isoformat() + 'Z'
                            
                            # Buscar eventos
                            events = list_calendar_events(calendar_creds, max_results=max_events, time_min=time_min, time_max=time_max)
                            
                            if not events:
                                st.info("Não foram encontrados eventos para o período selecionado.")
                            else:
                                st.success(f"Foram encontrados {len(events)} eventos.")
                                
                                # Exibir eventos em cards
                                for event in events:
                                    with st.container():
                                        # Estilo CSS para o card
                                        st.markdown("""
                                        <style>
                                        .event-card {
                                            border: 1px solid #ddd;
                                            border-radius: 8px;
                                            padding: 15px;
                                            margin-bottom: 15px;
                                            background-color: #f9f9f9;
                                        }
                                        .event-title {
                                            font-size: 18px;
                                            font-weight: bold;
                                            color: #1E88E5;
                                        }
                                        .event-time {
                                            font-size: 14px;
                                            color: #666;
                                            margin-top: 5px;
                                        }
                                        .event-location {
                                            font-size: 14px;
                                            color: #666;
                                            margin-top: 5px;
                                        }
                                        .event-description {
                                            font-size: 14px;
                                            margin-top: 10px;
                                        }
                                        </style>
                                        """, unsafe_allow_html=True)
                                        
                                        # Obter detalhes do evento
                                        event_title = event.get('summary', 'Evento sem título')
                                        
                                        # Processar data e hora
                                        start = event.get('start', {})
                                        if 'dateTime' in start:
                                            # Evento com hora específica
                                            start_dt = datetime.datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                                            start_str = start_dt.strftime('%d/%m/%Y às %H:%M')
                                        else:
                                            # Evento de dia inteiro
                                            start_str = f"{datetime.datetime.strptime(start['date'], '%Y-%m-%d').strftime('%d/%m/%Y')} (dia inteiro)"
                                        
                                        # Processar local
                                        location = event.get('location', 'Sem local definido')
                                        
                                        # Processar descrição
                                        description = event.get('description', 'Sem descrição')
                                        
                                        # Exibir card
                                        st.markdown(f"""
                                        <div class="event-card">
                                            <div class="event-title">{event_title}</div>
                                            <div class="event-time">🗓️ {start_str}</div>
                                            <div class="event-location">📍 {location}</div>
                                            <div class="event-description">{description}</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                    
                    # Link para o Google Calendar
                    st.markdown("---")
                    st.markdown("""
                    #### Quer mais opções?
                    
                    [Abrir Google Calendar no navegador](https://calendar.google.com/calendar/r) para gerenciar eventos, criar novos compromissos e configurar notificações.
                    """)
                else:
                    st.warning("""
                    ### Credenciais do Google Calendar não disponíveis
                    
                    Para acessar seus eventos, você precisa:
                    1. Fazer login usando sua conta Google
                    2. Autorizar o acesso ao Google Calendar
                    """)
                    
                    # Botão para iniciar autenticação do Google Calendar
                    if st.button("Conectar ao Google Calendar"):
                        firebase_auth.initiate_google_calendar_auth()
        else:
            # Interface padrão para usuários sem acesso ao Google Calendar
            calendar_tab, chat_tab, config_tab = st.tabs(["Calendário", "Assistente", "Configurações Avançadas"])
    
    with chat_tab:
        st.subheader("Assistente de Calendário")
        
        # Componente para configurar a API Gemini (opção para usuário usar própria chave)
        with st.expander("⚙️ Configurar API Gemini"):
            # Verificar se usuário está com login efetivo
            if st.session_state.firebase_user.get('isAnonymous', True):
                st.warning("O assistente com IA Gemini só está disponível para usuários com login efetivo. Por favor, faça login com e-mail ou Google para utilizar esta funcionalidade.")
            else:
                st.write(f"Você está usando a chave API Gemini pré-configurada. Você tem {st.session_state.gemini_credits} créditos restantes.")
                st.write("Opcionalmente, você pode usar sua própria chave:")
                
                # Campo para inserir a chave API personalizada
                custom_api_key = st.text_input(
                    "Sua chave API Gemini (opcional)", 
                    value="",
                    type="password", 
                    help="Insira sua chave API Gemini obtida no Google AI Studio"
                )
                
                # Botão para salvar a chave personalizada
                if st.button("Usar minha chave API"):
                    if custom_api_key:
                        st.session_state.google_genai_api_key = custom_api_key
                        st.success("✅ Sua chave API Gemini foi configurada com sucesso!")
                    else:
                        st.error("❌ Por favor, insira uma chave API válida")
                
                # Botão para restaurar a chave padrão
                if st.button("Restaurar chave padrão"):
                    st.session_state.google_genai_api_key = "AIzaSyBfyAPI__JVt31lBQtOcaPzWtbLqmFmihE"
                    st.success("✅ Restaurada a chave API Gemini padrão")
                
                # Informações sobre como obter uma chave API
                st.markdown("""
                ### Obtenha sua própria chave API Gemini:
                
                1. Acesse o [Google AI Studio](https://makersuite.google.com/app/apikey)
                2. Faça login com sua conta Google
                3. Clique em "Create API Key"
                4. Copie a chave gerada e cole no campo acima
                
                O Google oferece um nível gratuito generoso para a API Gemini que não requer cartão de crédito.
                """)
        
        # Exibir mensagens
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Verificar tipo de usuário para o input
        is_anonymous = st.session_state.firebase_user.get('isAnonymous', True)
        
        if is_anonymous:
            # Para usuário anônimo, mostrar mensagem informativa
            st.info("O assistente com IA Gemini só está disponível para usuários com login efetivo. Por favor, faça login com e-mail ou Google para utilizar esta funcionalidade.")
            # Input desabilitado para usuários anônimos
            st.text_input("Digite sua pergunta sobre o calendário...", disabled=True)
        else:
            # Input do usuário para contas autenticadas
            user_input = st.chat_input("Digite sua pergunta sobre o calendário...")
            if user_input:
                # Adicionar mensagem do usuário
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                # Exibir mensagem do usuário
                with st.chat_message("user"):
                    st.write(user_input)
            
            # Processar resposta usando o Gemini API
            if genkit_integration_available:
                # Verificar se o usuário está autenticado e não é anônimo
                is_anonymous = st.session_state.firebase_user.get('isAnonymous', True)
                
                if is_anonymous:
                    # Usuário anônimo não pode usar o Gemini
                    with st.chat_message("assistant"):
                        response = "Desculpe, o assistente com IA Gemini só está disponível para usuários com login efetivo. Por favor, faça login com e-mail ou Google para utilizar esta funcionalidade."
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.write(response)
                elif st.session_state.gemini_credits <= 0:
                    # Usuário esgotou os créditos
                    with st.chat_message("assistant"):
                        response = "Você já utilizou todos os seus 5 créditos de uso da IA Gemini. Entre em contato com o administrador para adquirir mais créditos."
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.write(response)
                else:
                    # Usuário autenticado com créditos disponíveis
                    with st.chat_message("assistant"):
                        with st.spinner("Processando sua mensagem..."):
                            # Construir o prompt com contexto do calendário
                            prompt = f"""Você é um assistente de calendário inteligente que ajuda a gerenciar eventos.
                            Por favor, responda à seguinte solicitação do usuário:
                            
                            Solicitação: {user_input}
                            
                            Dê uma resposta útil e educada em português. Se for uma solicitação relacionada ao calendário, 
                            explique como você poderia ajudar (ex: agendar eventos, verificar conflitos, sugerir horários).
                            """
                            
                            # Chamar a API Gemini
                            result = genkit_integration.generate_text(prompt, model="gemini-2.0-flash")
                            
                            if "error" in result:
                                response = f"Desculpe, ocorreu um erro: {result['error']}"
                            else:
                                response = result["text"]
                                # Reduzir o número de créditos após uso bem-sucedido
                                st.session_state.gemini_credits -= 1
                            
                            # Adicionar resposta à lista de mensagens
                            st.session_state.messages.append({"role": "assistant", "content": response})
                            st.write(response)
                            
                            # Mostrar créditos restantes
                            st.info(f"Você tem {st.session_state.gemini_credits} créditos restantes para usar o assistente Gemini.")
            else:
                # Fallback para caso o genkit_integration não esteja disponível
                with st.chat_message("assistant"):
                    response = f"Esta é uma demonstração simplificada. Em uma implementação completa, eu responderia perguntas sobre seu calendário, como: '{user_input}'"
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.write(response)
    
    with config_tab:
        st.subheader("Configurações Avançadas")
        
        # Mostrar opções de configuração avançada no conteúdo principal
        st.write("Configure todos os aspectos do aplicativo nesta seção.")
        
        # Mostrar informações sobre a API do Google Calendar
        with st.expander("Referência da API do Google Calendar"):
            st.markdown("""
            ### API do Google Calendar v3
            
            Esta referência da API está organizada por tipo de recurso. Cada tipo de recurso tem uma ou mais representações de dados e um ou mais métodos.
            
            #### Tipos de recurso principais:
            
            **Calendars**
            - `GET /calendars/calendarId` - Retorna metadados de uma agenda
            - `POST /calendars` - Cria uma agenda secundária
            - `PUT /calendars/calendarId` - Atualiza os metadados de uma agenda
            - `DELETE /calendars/calendarId` - Exclui uma agenda secundária
            - `POST /calendars/calendarId/clear` - Apaga uma agenda principal
            
            **Events**
            - `GET /calendars/calendarId/events` - Retorna eventos na agenda especificada
            - `POST /calendars/calendarId/events` - Cria um evento
            - `GET /calendars/calendarId/events/eventId` - Retorna um evento com base no ID
            - `PUT /calendars/calendarId/events/eventId` - Atualiza um evento
            - `DELETE /calendars/calendarId/events/eventId` - Exclui um evento
            - `POST /calendars/calendarId/events/import` - Importa um evento
            
            **FreeBusy**
            - `POST /freeBusy` - Retorna as informações de disponibilidade de um conjunto de agendas
            
            #### Escopos da API utilizados:
            
            **Escopos não confidenciais:**
            - `https://www.googleapis.com/auth/calendar.app.created` - Criar agendas secundárias e gerenciar seus eventos
            - `https://www.googleapis.com/auth/calendar.calendarlist.readonly` - Ver a lista de agendas inscritas
            
            **Escopos confidenciais:**
            - `https://www.googleapis.com/auth/calendar` - Acesso total às agendas
            - `https://www.googleapis.com/auth/calendar.events` - Ver e editar eventos em todas as agendas
            - `https://www.googleapis.com/auth/calendar.readonly` - Ver e baixar qualquer agenda
            
            #### Credenciais do Cliente OAuth:
            - ID do Cliente: `444237029110-9v47qvkh8fpgusnp58ihdqg93u4959pu.apps.googleusercontent.com`
            - Nome do Projeto: `calendario-ia-coflow-app`
            
            #### Para mais informações:
            [Documentação oficial da API do Google Calendar](https://developers.google.com/calendar/api/v3/reference)
            """)
        
        # Firebase Admin SDK (se disponível)
        if firebase_admin_config_available:
            # Verificar se o usuário pediu para mostrar a configuração do administrador
            if "show_admin_config" in st.session_state and st.session_state.show_admin_config:
                st.subheader("Configuração do Firebase Admin SDK")
                # Mostrar a interface de configuração diretamente, sem expander
                firebase_admin_config.admin_config_component()
                
                # Testar a conexão com o Firebase Admin SDK
                if st.button("Testar Conexão com Firebase Admin SDK"):
                    success, message = firebase_admin_config.test_admin_connection()
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                
                # Botão para esconder a configuração do administrador
                if st.button("Esconder Configuração do Administrador"):
                    st.session_state.show_admin_config = False
                    st.rerun()
                
                # Mostrar a ajuda para Firebase Admin SDK
                st.markdown("---")
                firebase_admin_config.show_admin_sdk_help()
            else:
                # Botão para mostrar a configuração do administrador
                if st.button("Mostrar Configuração do Firebase Admin SDK"):
                    st.session_state.show_admin_config = True
                    st.rerun()
        else:
            st.warning("""
            O módulo Firebase Admin SDK não está disponível. Para habilitar funcionalidades avançadas 
            de administração, crie um arquivo 'firebase_admin_config.py' com as credenciais e 
            funções necessárias.
            """)
            
            # Mostrar instruções para criar o arquivo
            with st.expander("Como habilitar o Firebase Admin SDK"):
                st.markdown("""
                ### Como habilitar o Firebase Admin SDK
                
                1. **Crie um arquivo**: Crie um arquivo chamado `firebase_admin_config.py` no mesmo diretório do aplicativo
                
                2. **Adicione as credenciais**: Adicione suas credenciais do Firebase Admin SDK ao arquivo
                
                3. **Implemente as funções necessárias**: Implemente as funções para gerenciar o SDK
                
                #### Exemplo de código:
                ```python
                import os
                import json
                import streamlit as st
                import tempfile
                import firebase_admin
                from firebase_admin import credentials
                
                # Credenciais padrão do Firebase Admin SDK
                DEFAULT_FIREBASE_ADMIN_CONFIG = {
                  "type": "service_account",
                  "project_id": "calendario-ia-coflow",
                  # Adicione as demais credenciais aqui
                }
                
                def get_admin_credentials():
                    # Função para obter as credenciais
                    pass
                    
                def initialize_firebase_admin():
                    # Função para inicializar o SDK
                    pass
                    
                def admin_config_component():
                    # Interface do Streamlit para configuração
                    pass
                ```
                """)
                
        # Firebase Config
        st.subheader("Configuração do Firebase")
        firebase_auth.firebase_config_component(form_key_suffix="config_tab")

