"""
Aplicativo Streamlit de exemplo usando Firebase para autenticação e Google Calendar.
"""

import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import datetime
import firebase_auth

# Configuração do aplicativo Streamlit
st.set_page_config(
    page_title="Calendário com Firebase",
    page_icon="📅",
    layout="wide"
)

# Título do aplicativo
st.title("📅 Gerenciador de Calendário com Firebase")
st.write("Este aplicativo usa o Firebase para autenticação e acessa a API do Google Calendar.")

# Mostrar componente de autenticação
with st.sidebar:
    st.header("Autenticação")
    firebase_auth.show_auth_component()

# Conteúdo principal
if 'firebase_user' not in st.session_state or not st.session_state.firebase_user:
    # Usuário não autenticado
    st.info("👈 Por favor, faça login no painel lateral para acessar seu calendário.")
    
    # Exemplo de como o aplicativo funciona
    with st.expander("Como este aplicativo funciona?"):
        st.write("""
        ### Fluxo de Autenticação e Acesso ao Calendário
        
        1. **Login via Firebase**: Usamos o Firebase Authentication para gerenciar o login dos usuários de forma segura.
        
        2. **Token de Acesso**: Após o login bem-sucedido, obtemos um token de acesso que pode ser trocado por um token OAuth do Google.
        
        3. **Acesso ao Google Calendar**: Com o token OAuth, acessamos a API do Google Calendar para exibir e gerenciar eventos.
        
        ### Vantagens desta Abordagem
        
        - **Segurança**: As credenciais do usuário são gerenciadas pelo Firebase, um serviço confiável do Google.
        - **Facilidade de Uso**: O Firebase simplifica o processo de autenticação e gerenciamento de usuários.
        - **Escalabilidade**: Esta abordagem pode ser expandida para incluir mais funcionalidades e serviços.
        """)
        
        st.image("https://firebase.google.com/images/social.png", width=300)
else:
    # Usuário autenticado
    st.success(f"✓ Autenticado como: {st.session_state.firebase_user['email']}")
    
    # Link rápido para o Google Calendar
    st.markdown("""
    <div style="text-align: right;">
        <a href="https://calendar.google.com/" target="_blank">
            <button style="background-color:#4285F4; color:white; border:none; border-radius:4px; padding:5px 15px; font-size:14px; cursor:pointer;">
                🔗 Acessar Google Calendar
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    # Conteúdo do aplicativo após autenticação
    st.header("Seus Eventos do Calendário")
    
    # Obter credenciais do Google Calendar
    credentials = firebase_auth.get_google_calendar_credentials()
    
    if credentials:
        try:
            # Criar serviço Calendar
            service = build("calendar", "v3", credentials=credentials)
            
            # Obter a data atual
            now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indica o fuso horário UTC
            
            # Filtros para exibição de eventos
            st.write("### Filtrar Eventos")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Seleção de calendário
                calendars_result = service.calendarList().list().execute()
                calendars = calendars_result.get('items', [])
                calendar_options = {cal['summary']: cal['id'] for cal in calendars}
                selected_calendar = st.selectbox(
                    "Calendário", 
                    options=list(calendar_options.keys()),
                    index=0
                )
                calendar_id = calendar_options[selected_calendar]
            
            with col2:
                # Período
                periodo = st.selectbox(
                    "Período",
                    options=["Próximos 7 dias", "Próximos 30 dias", "Próximos 90 dias"],
                    index=0
                )
                
                # Definir data final com base no período
                if periodo == "Próximos 7 dias":
                    max_time = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + 'Z'
                elif periodo == "Próximos 30 dias":
                    max_time = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat() + 'Z'
                else:
                    max_time = (datetime.datetime.utcnow() + datetime.timedelta(days=90)).isoformat() + 'Z'
            
            with col3:
                # Número máximo de eventos
                max_results = st.number_input("Máx. Eventos", min_value=1, max_value=50, value=10)
            
            # Obter eventos do calendário selecionado
            eventos_result = service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                timeMax=max_time,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            eventos = eventos_result.get('items', [])
            
            if not eventos:
                st.info("Não foram encontrados eventos para o período selecionado.")
            else:
                st.write(f"### Próximos Eventos ({len(eventos)})")
                
                # Exibir eventos em cards
                for evento in eventos:
                    with st.container():
                        col1, col2 = st.columns([1, 3])
                        
                        with col1:
                            # Obter data e hora do evento
                            start = evento['start'].get('dateTime', evento['start'].get('date'))
                            end = evento['end'].get('dateTime', evento['end'].get('date'))
                            
                            # Verificar se é um evento de dia inteiro
                            if 'T' in start:  # Evento com hora específica
                                data_inicio = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                                data_fim = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))
                                st.write(f"**{data_inicio.strftime('%d/%m/%Y')}**")
                                st.write(f"{data_inicio.strftime('%H:%M')} - {data_fim.strftime('%H:%M')}")
                            else:  # Evento de dia inteiro
                                data_inicio = datetime.datetime.fromisoformat(start)
                                st.write(f"**{data_inicio.strftime('%d/%m/%Y')}**")
                                st.write("Dia inteiro")
                        
                        with col2:
                            st.write(f"**{evento.get('summary', 'Evento sem título')}**")
                            if 'description' in evento:
                                st.write(evento['description'])
                            if 'location' in evento and evento['location']:
                                st.write(f"📍 {evento['location']}")
                            
                            # Link para ver detalhes
                            if 'htmlLink' in evento:
                                st.markdown(f"[Ver detalhes]({evento['htmlLink']})")
                        
                        st.divider()
        except Exception as e:
            st.error(f"Erro ao acessar eventos: {str(e)}")
            st.info("Tente reconectar ao Google Calendar.")
            
            # Mostrar botão para reconectar
            if st.button("Reconectar ao Google Calendar"):
                if 'google_oauth_token' in st.session_state:
                    del st.session_state.google_oauth_token
                firebase_auth.initiate_google_calendar_auth()
    else:
        # Instruções para conectar ao Google Calendar
        st.info("👉 Para ver seus eventos, primeiro conecte-se ao Google Calendar através do painel lateral.")
        
        # Mostrar explicação com exemplo
        with st.expander("Ver exemplos de como os eventos serão exibidos"):
            st.write("### Exemplo de Eventos")
            
            # Simulação de eventos
            eventos_exemplo = [
                {
                    "summary": "Reunião de Equipe",
                    "start": {"dateTime": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()},
                    "end": {"dateTime": (datetime.datetime.now() + datetime.timedelta(days=1, hours=1)).isoformat()},
                    "description": "Discussão sobre os próximos projetos"
                },
                {
                    "summary": "Almoço com Cliente",
                    "start": {"dateTime": (datetime.datetime.now() + datetime.timedelta(days=2)).isoformat()},
                    "end": {"dateTime": (datetime.datetime.now() + datetime.timedelta(days=2, hours=2)).isoformat()},
                    "description": "Restaurante: A definir"
                },
                {
                    "summary": "Entrega do Projeto",
                    "start": {"dateTime": (datetime.datetime.now() + datetime.timedelta(days=5)).isoformat()},
                    "end": {"dateTime": (datetime.datetime.now() + datetime.timedelta(days=5, hours=1)).isoformat()},
                    "description": "Prazo final para a entrega do projeto"
                }
            ]
            
            # Exibir eventos em cards
            for evento in eventos_exemplo:
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        data = datetime.datetime.fromisoformat(evento["start"]["dateTime"].replace("Z", "+00:00"))
                        st.write(f"**{data.strftime('%d/%m/%Y')}**")
                        st.write(f"{data.strftime('%H:%M')} - {(data + datetime.timedelta(hours=1)).strftime('%H:%M')}")
                    
                    with col2:
                        st.write(f"**{evento['summary']}**")
                        st.write(evento["description"])
                    
                    st.divider()

    # Exemplo de adição de evento
    st.write("### Adicionar Novo Evento")
    with st.form("novo_evento"):
        titulo = st.text_input("Título do Evento")
        data = st.date_input("Data", datetime.date.today())
        hora_inicio = st.time_input("Hora de Início", datetime.time(9, 0))
        hora_fim = st.time_input("Hora de Término", datetime.time(10, 0))
        descricao = st.text_area("Descrição")
        
        submitted = st.form_submit_button("Adicionar Evento")
        if submitted:
            # Obter as credenciais do Google Calendar
            credentials = firebase_auth.get_google_calendar_credentials()
            
            if credentials:
                try:
                    # Criar serviço Calendar
                    service = build("calendar", "v3", credentials=credentials)
                    
                    # Formatar datas para o formato do Google Calendar
                    start_datetime = datetime.datetime.combine(data, hora_inicio)
                    end_datetime = datetime.datetime.combine(data, hora_fim)
                    
                    # Formatação para timezone local
                    timezone = "America/Sao_Paulo"  # Ajuste conforme sua localização
                    
                    # Criar evento
                    event = {
                        'summary': titulo,
                        'description': descricao,
                        'start': {
                            'dateTime': start_datetime.isoformat(),
                            'timeZone': timezone,
                        },
                        'end': {
                            'dateTime': end_datetime.isoformat(),
                            'timeZone': timezone,
                        },
                    }
                    
                    # Inserir evento no calendário primário do usuário
                    event = service.events().insert(calendarId='primary', body=event).execute()
                    
                    # Mostrar mensagem de sucesso
                    st.success(f"✅ Evento '{titulo}' adicionado com sucesso ao seu Google Calendar!")
                    
                    # Link para ver o evento
                    event_link = event.get('htmlLink', 'https://calendar.google.com/')
                    st.markdown(f"""
                    <a href="{event_link}" target="_blank">
                        <button style="background-color:#4285F4; color:white; border:none; border-radius:4px; padding:10px 20px; font-size:16px; cursor:pointer;">
                            Ver Evento no Calendar
                        </button>
                    </a>
                    """, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Erro ao adicionar evento: {str(e)}")
                    
                    # Adicionar links alternativos
                    st.markdown("""
                    ### 🔗 Acesse sua agenda
                    
                    Clique em uma das opções abaixo:
                    """)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("""
                        <a href="https://calendar.google.com/" target="_blank">
                            <button style="background-color:#4285F4; color:white; border:none; border-radius:4px; padding:10px 20px; font-size:16px; cursor:pointer; width:100%;">
                                Ver Google Calendar
                            </button>
                        </a>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        # Formatando a data e hora para o URL do Google Calendar
                        data_formatada = data.strftime("%Y%m%d")
                        hora_inicio_formatada = hora_inicio.strftime("%H%M")
                        hora_fim_formatada = hora_fim.strftime("%H%M")
                        titulo_codificado = titulo.replace(" ", "+")
                        descricao_codificada = descricao.replace(" ", "+")
                        
                        # URL para criar um evento no Google Calendar com os dados preenchidos
                        url_criar_evento = f"https://calendar.google.com/calendar/r/eventedit?text={titulo_codificado}&dates={data_formatada}T{hora_inicio_formatada}00/{data_formatada}T{hora_fim_formatada}00&details={descricao_codificada}"
                        
                        st.markdown(f"""
                        <a href="{url_criar_evento}" target="_blank">
                            <button style="background-color:#34A853; color:white; border:none; border-radius:4px; padding:10px 20px; font-size:16px; cursor:pointer; width:100%;">
                                Criar Este Evento
                            </button>
                        </a>
                        """, unsafe_allow_html=True)
            else:
                st.error("⚠️ Você não está conectado ao Google Calendar. Por favor, conecte-se primeiro.")
                
                # Mostrar botão para conectar
                if st.button("Conectar ao Google Calendar"):
                    firebase_auth.initiate_google_calendar_auth()

# Rodapé
st.divider()
st.write("🔐 Autenticação via Firebase | 📅 Google Calendar API")
st.write("Este é um exemplo educacional. Em um ambiente de produção, as credenciais devem ser gerenciadas com segurança.") 