import datetime
import os.path
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ai_models.anthropic import Tool, Function, FunctionParameters, structured_chat_completion
from models.response import AIResponse
from utils import calendar_actions
from utils import calendar_config

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Define the tools for the AI agent
CALENDAR_TOOLS = [
    Tool(
        type="function",
        function=Function(
            name="create_event",
            description="Create a new calendar event",
            parameters=FunctionParameters(
                type="object",
                properties={
                    "summary": {"type": "string", "description": "Title of the event"},
                    "start_time": {"type": "string", "description": "Start time in ISO format"},
                    "end_time": {"type": "string", "description": "End time in ISO format"},
                    "description": {"type": "string", "description": "Optional description of the event"},
                    "location": {"type": "string", "description": "Optional location of the event"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "Optional list of attendee emails"}
                },
                required=["summary", "start_time", "end_time", "description", "location", "attendees"]
            )
        )
    ),
    Tool(
        type="function",
        function=Function(
            name="list_events",
            description="List events within a date range",
            parameters=FunctionParameters(
                type="object",
                properties={
                    "start_date": {"type": "string", "description": "Start date in ISO format"},
                    "end_date": {"type": "string", "description": "End date in ISO format"},
                    "max_results": {"type": "integer", "description": "Maximum number of events to return"}
                },
                required=["start_date", "end_date", "max_results"]
            )
        )
    ),
    Tool(
        type="function",
        function=Function(
            name="add_attendee",
            description="Add an attendee to an existing event",
            parameters=FunctionParameters(
                type="object",
                properties={
                    "event_id": {"type": "string", "description": "ID of the event"},
                    "attendee_email": {"type": "string", "description": "Email of the attendee to add"}
                },
                required=["event_id", "attendee_email"]
            )
        )
    ),
    Tool(
        type="function",
        function=Function(
            name="delete_event",
            description="Delete a calendar event",
            parameters=FunctionParameters(
                type="object",
                properties={
                    "event_id": {"type": "string", "description": "ID of the event to delete"}
                },
                required=["event_id"]
            )
        )
    )
]

def handle_tool_call(tool_call, args):
    """Handle tool calls from the AI agent"""
    try:
        service = get_calendar_service()
        
        if tool_call.function.name == "create_event":
            result = calendar_actions.create_event(service, **args)
            return {
                'success': True,
                'data': result,
                'message': f"Event '{result['summary']}' created successfully. View it here: {result['link']}"
            }
        elif tool_call.function.name == "list_events":
            result = calendar_actions.list_events(service, **args)
            return {
                'success': True,
                'data': result,
                'message': f"Found {len(result)} events in the specified date range."
            }
        elif tool_call.function.name == "add_attendee":
            result = calendar_actions.add_attendee(service, **args)
            return {
                'success': True,
                'data': result,
                'message': f"Added attendee to event '{result['summary']}'. Current attendees: {', '.join(result['attendees'])}"
            }
        elif tool_call.function.name == "delete_event":
            result = calendar_actions.delete_event(service, **args)
            return {
                'success': True,
                'data': result,
                'message': result['message']
            }
        else:
            raise ValueError(f"Unknown tool: {tool_call.function.name}")
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f"Failed to {tool_call.function.name.replace('_', ' ')}: {str(e)}"
        }

def get_calendar_service():
    """Get an authorized Calendar API service instance."""
    service, success = calendar_config.get_calendar_service()
    if not success:
        raise Exception("Failed to create calendar service. Please check your credentials.")
    return service

def get_system_message():
    """Get the system message for the AI agent."""
    now = datetime.datetime.now()
    return {
        "role": "system",
        "content": f"""You are a helpful assistant that helps users manage their Google Calendar.
        The current date and time is {now.strftime('%Y-%m-%d %H:%M:%S')}.
        When the user asks you to interact with their calendar, you should use the appropriate tool.
        When creating events, always use ISO format for dates and times.
        For dates without specific times, use YYYY-MM-DD format.
        For times on specific dates, use YYYY-MM-DDThh:mm:ss format.
        
        When listing events, use list_events tool.
        When creating events, use create_event tool.
        When adding attendees to events, use add_attendee tool.
        When deleting events, use delete_event tool.
        
        When adding attendees to events, you can refer to events by either:
        1. Their exact event ID (from previous tool results)
        2. Their exact event title/summary (case-insensitive)
        Always use the most recent event information from your conversation history.
        """
    }

def main():
    """Main function to run the calendar agent."""
    print("Welcome to your AI Calendar Assistant! Type 'quit' to exit.")
    
    # Initialize conversation history with system message
    messages = [get_system_message()]
    
    while True:
        user_input = input("\n> ")
        if user_input.lower() in ['quit', 'exit']:
            break
        
        # Add user message to history
        messages.append({"role": "user", "content": user_input})
        
        try:
            # Update system message with current time
            messages[0] = get_system_message()
            
            response = structured_chat_completion(
                messages=messages,
                output_model=AIResponse,
                model="claude-3-sonnet-20250219",
                temperature=0.7,
                tools=CALENDAR_TOOLS,
                tool_handler=handle_tool_call
            )
            
            response_data = json.loads(response)
            assistant_message = response_data["data"]
            
            # Add assistant's response to history
            messages.append({"role": "assistant", "content": assistant_message})
            
            print("\nAssistant:", assistant_message)
            
        except Exception as e:
            error_message = f"Sorry, I encountered an error: {str(e)}"
            messages.append({"role": "assistant", "content": error_message})
            print("\nAssistant:", error_message)

# Exportar as funções e variáveis necessárias para o streamlit_app.py
__all__ = ['CALENDAR_TOOLS', 'get_system_message', 'handle_tool_call', 'get_calendar_service']

if __name__ == "__main__":
    main()