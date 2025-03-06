"""
Módulo com funções e configurações do assistente de calendário.
"""

from datetime import datetime
from ai_models.anthropic import Tool, Function, FunctionParameters
from main import handle_tool_call

def get_system_message() -> dict:
    """
    Retorna a mensagem do sistema com a hora atual.
    """
    now = datetime.now()
    return {
        "role": "system",
        "content": f"""Você é um assistente útil que ajuda usuários a gerenciar seu Google Calendar.
        A data e hora atual é {now.strftime('%Y-%m-%d %H:%M:%S')}.
        Quando o usuário pedir para interagir com o calendário, você deve usar a ferramenta apropriada.
        Quando criar eventos, sempre use o formato ISO para datas e horários.
        Para datas sem horários específicos, use o formato YYYY-MM-DD.
        Para horários em datas específicas, use o formato YYYY-MM-DDThh:mm:ss.
        
        Para listar eventos, use a ferramenta list_events.
        Para criar eventos, use a ferramenta create_event.
        Para adicionar participantes a eventos, use a ferramenta add_attendee.
        Para excluir eventos, use a ferramenta delete_event.
        
        Ao adicionar participantes a eventos, você pode se referir a eventos por:
        1. ID exato do evento (de resultados anteriores de ferramentas)
        2. Título/resumo exato do evento (não diferencia maiúsculas de minúsculas)
        Sempre use as informações mais recentes de eventos da sua conversa."""
    }

# Configuração das ferramentas do calendário
CALENDAR_TOOLS = [
    Tool(
        type="function",
        function=Function(
            name="create_event",
            description="Criar um novo evento no calendário",
            parameters=FunctionParameters(
                type="object",
                properties={
                    "summary": {"type": "string", "description": "Título do evento"},
                    "start_time": {"type": "string", "description": "Horário de início no formato ISO"},
                    "end_time": {"type": "string", "description": "Horário de término no formato ISO"},
                    "description": {"type": "string", "description": "Descrição opcional do evento"},
                    "location": {"type": "string", "description": "Local opcional do evento"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "Lista opcional de emails dos participantes"}
                },
                required=["summary", "start_time", "end_time", "description", "location", "attendees"]
            )
        )
    ),
    Tool(
        type="function",
        function=Function(
            name="list_events",
            description="Listar eventos do calendário em um intervalo de datas",
            parameters=FunctionParameters(
                type="object",
                properties={
                    "start_date": {"type": "string", "description": "Data de início no formato YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "Data de término no formato YYYY-MM-DD"},
                    "max_results": {"type": "integer", "description": "Número máximo de eventos a retornar"}
                },
                required=["start_date", "end_date"]
            )
        )
    ),
    Tool(
        type="function",
        function=Function(
            name="delete_event",
            description="Excluir um evento do calendário",
            parameters=FunctionParameters(
                type="object",
                properties={
                    "event_id": {"type": "string", "description": "ID do evento a ser excluído"}
                },
                required=["event_id"]
            )
        )
    ),
    Tool(
        type="function",
        function=Function(
            name="add_attendee",
            description="Adicionar participante a um evento existente",
            parameters=FunctionParameters(
                type="object",
                properties={
                    "event_id": {"type": "string", "description": "ID do evento ou título exato"},
                    "email": {"type": "string", "description": "Email do participante a ser adicionado"}
                },
                required=["event_id", "email"]
            )
        )
    )
] 