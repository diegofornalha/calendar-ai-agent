from typing import List, Dict, Any, Optional
from datetime import datetime
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
import pytz
import logging
import streamlit as st
from utils import calendar_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache to store event details for quick lookup
event_cache = {}

def _cache_event(event: Dict[str, Any]):
    """Cache event details for quick lookup."""
    event_id = event['id']
    event_cache[event_id] = {
        'id': event_id,
        'summary': event['summary'],
        'start': event['start'].get('dateTime', event['start'].get('date')),
        'end': event['end'].get('dateTime', event['end'].get('date')),
        'attendees': [attendee['email'] for attendee in event.get('attendees', [])]
    }
    # Also cache by summary for fuzzy lookup
    event_cache[event['summary'].lower()] = event_cache[event_id]
    return event_cache[event_id]

def _get_selected_calendar_id():
    """Obtém o ID do calendário selecionado ou padrão"""
    if 'selected_calendar_id' in st.session_state:
        return st.session_state.selected_calendar_id
    return 'primary'  # Usado como fallback

def _find_event_id(service: Resource, event_identifier: str) -> Optional[str]:
    """Find event ID by exact ID or event summary."""
    # First check cache
    if event_identifier in event_cache:
        return event_cache[event_identifier]['id']
    
    calendar_id = _get_selected_calendar_id()
    
    # If not in cache, try as exact ID
    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_identifier).execute()
        _cache_event(event)
        return event['id']
    except HttpError as e:
        if e.resp.status != 404:  # If error is not "Not Found", propagate it
            raise
    
    # If not found, try searching by title
    try:
        # Search in recent events
        now = datetime.now(pytz.UTC)
        three_months = datetime.now(pytz.UTC).replace(month=now.month + 3)
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=now.isoformat(),
            timeMax=three_months.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        # Find by exact title (case insensitive)
        for event in events:
            if event.get('summary', '').lower() == event_identifier.lower():
                _cache_event(event)
                return event['id']
    except HttpError:
        pass  # Ignore errors in search
    
    return None

def ensure_rfc3339_format(date_str: str) -> str:
    """Ensure the date string is in RFC3339 format with timezone."""
    try:
        # If the string already has timezone info, parse it directly
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        # If no timezone info, assume UTC
        dt = datetime.fromisoformat(date_str).replace(tzinfo=pytz.UTC)
    
    return dt.isoformat()

def create_event(service: Resource, summary: str, start_time: str, end_time: str,
                 description: str = '', location: str = '', attendees: List[str] = None) -> Dict[str, Any]:
    """Create a new calendar event."""
    try:
        # Create event body
        event_body = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC'
            }
        }
        
        # Add attendees if provided
        if attendees:
            event_body['attendees'] = [{'email': email} for email in attendees]
            
        calendar_id = _get_selected_calendar_id()
            
        # Call the Calendar API
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            sendUpdates='all' if attendees else 'none'
        ).execute()
        
        # Cache the new event
        _cache_event(event)
        
        return {
            'success': True,
            'event': {
                'id': event['id'],
                'summary': event.get('summary', 'No title'),
                'start': event['start'].get('dateTime'),
                'end': event['end'].get('dateTime'),
                'location': event.get('location', ''),
                'description': event.get('description', ''),
                'attendees': [attendee.get('email') for attendee in event.get('attendees', [])]
            },
            'message': 'Event created successfully'
        }
    except ValueError as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Invalid input. Please check the format of your dates and inputs.'
        }
    except HttpError as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Error creating event in Google Calendar.'
        }

def list_events(service: Resource, start_date: str, end_date: str, max_results: int = 10) -> Dict[str, Any]:
    """List calendar events between start_date and end_date."""
    try:
        # Parse dates and convert to ISO format
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        calendar_id = _get_selected_calendar_id()
        
        # Call the Calendar API
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        # Cache events for quick lookup
        for event in events:
            _cache_event(event)
        
        # Format events for display
        formatted_events = []
        for event in events:
            start_time = event['start'].get('dateTime', event['start'].get('date'))
            end_time = event['end'].get('dateTime', event['end'].get('date'))
            
            formatted_event = {
                'id': event['id'],
                'summary': event.get('summary', 'No title'),
                'start': start_time,
                'end': end_time,
                'location': event.get('location', ''),
                'description': event.get('description', ''),
                'attendees': [attendee.get('email') for attendee in event.get('attendees', [])]
            }
            formatted_events.append(formatted_event)
            
        return {
            'success': True,
            'events': formatted_events,
            'count': len(formatted_events)
        }
    except ValueError as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Invalid date format. Please use ISO format (YYYY-MM-DD or YYYY-MM-DDThh:mm:ss).'
        }
    except HttpError as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Error listing events from Google Calendar.'
        }

def add_attendee(service: Resource, event_id: str, email: str) -> Dict[str, Any]:
    """Add an attendee to an existing event."""
    try:
        # Find the actual event ID if a summary was provided
        actual_event_id = _find_event_id(service, event_id)
        if not actual_event_id:
            return {
                'success': False,
                'error': 'Event not found',
                'message': f'Could not find event with ID or title: {event_id}'
            }
            
        calendar_id = _get_selected_calendar_id()
            
        # Get the current event
        event = service.events().get(calendarId=calendar_id, eventId=actual_event_id).execute()
        
        # Add the new attendee
        attendees = event.get('attendees', [])
        
        # Check if already an attendee
        if any(attendee.get('email') == email for attendee in attendees):
            return {
                'success': False,
                'error': 'Attendee already exists',
                'message': f'{email} is already an attendee of this event.'
            }
            
        attendees.append({'email': email})
        event['attendees'] = attendees
        
        # Update the event
        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=actual_event_id,
            body=event,
            sendUpdates='all'
        ).execute()
        
        # Update cache
        _cache_event(updated_event)
        
        return {
            'success': True,
            'event': {
                'id': updated_event['id'],
                'summary': updated_event.get('summary', 'No title'),
                'attendees': [attendee.get('email') for attendee in updated_event.get('attendees', [])]
            },
            'message': f'Added {email} to the event successfully'
        }
    except HttpError as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Error adding attendee to event in Google Calendar.'
        }

def delete_event(service: Resource, event_id: str) -> Dict[str, Any]:
    """Delete a calendar event."""
    try:
        # Find the actual event ID if a summary was provided
        actual_event_id = _find_event_id(service, event_id)
        if not actual_event_id:
            return {
                'success': False,
                'error': 'Event not found',
                'message': f'Could not find event with ID or title: {event_id}'
            }
            
        calendar_id = _get_selected_calendar_id()
            
        # Call the Calendar API
        service.events().delete(
            calendarId=calendar_id,
            eventId=actual_event_id
        ).execute()
        
        # Remove from cache
        if actual_event_id in event_cache:
            del event_cache[actual_event_id]
        
        return {
            'success': True,
            'message': 'Event deleted successfully'
        }
    except HttpError as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Error deleting event from Google Calendar.'
        }
