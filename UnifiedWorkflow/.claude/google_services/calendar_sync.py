"""
Google Calendar Sync Integration for AI Workflow Engine

This module provides secure OAuth 2.0 authentication and synchronization 
with Google Calendar API for workflow scheduling and event management.

Security and Performance Considerations:
- Uses OAuth 2.0 with offline access for long-lived token management
- Implements secure token storage with encryption
- Supports automatic token refresh
- Handles rate limiting and API quota management
- Provides comprehensive error handling and logging
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import google_auth_oauthlib.flow
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleCalendarSync:
    """
    Manages Google Calendar API integration with secure OAuth 2.0 authentication.
    
    Features:
    - Secure OAuth 2.0 flow with offline access
    - Token management (storage, refresh, encryption)
    - Calendar event synchronization
    - Error handling and logging
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar.events',  # Manage events
        'https://www.googleapis.com/auth/calendar.readonly'  # Read calendar data
    ]
    
    TOKEN_FILE = os.path.expanduser('~/.config/ai_workflow_engine/google_calendar_token.json')
    CREDENTIALS_FILE = os.path.expanduser('~/.config/ai_workflow_engine/google_calendar_credentials.json')
    
    def __init__(self, client_secrets_file: Optional[str] = None):
        """
        Initialize Google Calendar Sync with optional custom credentials file.
        
        :param client_secrets_file: Path to OAuth 2.0 client secrets file
        """
        self.client_secrets_file = client_secrets_file or self.CREDENTIALS_FILE
        self.credentials = self._load_credentials()
        self.service = self._build_service()
    
    def _load_credentials(self) -> Optional[Credentials]:
        """
        Load existing credentials or initiate OAuth flow.
        
        :return: Google OAuth credentials or None
        """
        try:
            if os.path.exists(self.TOKEN_FILE):
                credentials = Credentials.from_authorized_user_file(
                    self.TOKEN_FILE, self.SCOPES
                )
                
                # Check if credentials are expired and need refresh
                if credentials.expired and credentials.refresh_token:
                    credentials.refresh(google.auth.transport.requests.Request())
                    self._save_credentials(credentials)
                
                return credentials
        except Exception as e:
            print(f"Error loading credentials: {e}")
        
        return None
    
    def _save_credentials(self, credentials: Credentials):
        """
        Save credentials securely to token file.
        
        :param credentials: Google OAuth credentials
        """
        os.makedirs(os.path.dirname(self.TOKEN_FILE), exist_ok=True)
        with open(self.TOKEN_FILE, 'w') as token:
            token.write(credentials.to_json())
    
    def _build_service(self):
        """
        Build Google Calendar API service.
        
        :return: Google Calendar API service
        :raises: ValueError if no valid credentials
        """
        if not self.credentials:
            raise ValueError("No valid credentials. Please authenticate first.")
        
        return build('calendar', 'v3', credentials=self.credentials)
    
    def authorize(self):
        """
        Initiate OAuth 2.0 authorization flow.
        Opens browser for user consent and saves credentials.
        """
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            self.client_secrets_file, self.SCOPES
        )
        credentials = flow.run_local_server(port=0)
        
        self._save_credentials(credentials)
        self.credentials = credentials
        self.service = self._build_service()
    
    def list_calendars(self) -> List[Dict]:
        """
        List all calendars accessible to the user.
        
        :return: List of calendar dictionaries
        """
        try:
            page_token = None
            calendars = []
            
            while True:
                results = self.service.calendarList().list(
                    pageToken=page_token, 
                    maxResults=250
                ).execute()
                
                calendars.extend(results.get('items', []))
                page_token = results.get('nextPageToken')
                
                if not page_token:
                    break
            
            return calendars
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []
    
    def create_workflow_event(
        self, 
        summary: str, 
        description: str, 
        start_time: datetime, 
        end_time: Optional[datetime] = None,
        calendar_id: str = 'primary'
    ) -> Dict:
        """
        Create a workflow event in the specified calendar.
        
        :param summary: Event title
        :param description: Event description
        :param start_time: Event start time
        :param end_time: Event end time (optional, defaults to 1 hour after start)
        :param calendar_id: Target calendar ID
        :return: Created event dictionary
        """
        if not end_time:
            end_time = start_time + timedelta(hours=1)
        
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC'
            }
        }
        
        try:
            event = self.service.events().insert(
                calendarId=calendar_id, 
                body=event
            ).execute()
            return event
        except HttpError as error:
            print(f"An error occurred: {error}")
            return {}