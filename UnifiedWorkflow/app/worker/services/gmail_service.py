"""
Gmail service for handling Gmail API interactions with user OAuth credentials.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import base64
import email

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

from shared.database.models._models import UserOAuthToken, GoogleService
from shared.utils.database_setup import get_db
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)

# Gmail API scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


def get_gmail_service(user_id: int) -> Optional[Resource]:
    """
    Builds and returns a Gmail service object authenticated
    with the user's OAuth credentials.
    """
    logger.info("Building Gmail service for user_id: %s", user_id)
    try:
        # Get the user's OAuth token for Gmail
        with get_db() as db:
            oauth_token = db.query(UserOAuthToken).filter(
                UserOAuthToken.user_id == user_id,
                UserOAuthToken.service == GoogleService.GMAIL
            ).first()
            
            if not oauth_token:
                logger.error(
                    "No Gmail OAuth token found for user_id: %s. "
                    "User needs to connect their Gmail first.",
                    user_id
                )
                return None
            
            # Check if token is expired and needs refresh
            now = datetime.now(timezone.utc)
            if oauth_token.token_expiry and oauth_token.token_expiry <= now:
                if oauth_token.refresh_token:
                    logger.info("OAuth token expired, attempting refresh for user_id: %s", user_id)
                    # Refresh the token
                    creds = Credentials(
                        token=oauth_token.access_token,
                        refresh_token=oauth_token.refresh_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=get_settings().GOOGLE_CLIENT_ID,
                        client_secret=get_settings().GOOGLE_CLIENT_SECRET.get_secret_value()
                    )
                    creds.refresh(Request())
                    
                    # Update the stored token
                    oauth_token.access_token = creds.token
                    oauth_token.token_expiry = creds.expiry
                    db.commit()
                    
                    logger.info("Successfully refreshed OAuth token for user_id: %s", user_id)
                else:
                    logger.error(
                        "OAuth token expired and no refresh token available for user_id: %s. "
                        "User needs to reconnect their Gmail.",
                        user_id
                    )
                    return None
            else:
                # Token is still valid
                creds = Credentials(
                    token=oauth_token.access_token,
                    refresh_token=oauth_token.refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=get_settings().GOOGLE_CLIENT_ID,
                    client_secret=get_settings().GOOGLE_CLIENT_SECRET.get_secret_value()
                )
            
            service: Resource = build("gmail", "v1", credentials=creds)
            logger.info("Successfully built Gmail service with OAuth credentials.")
            return service
            
    except Exception as e:
        logger.error("Failed to build Gmail service: %s", e, exc_info=True)
    return None


async def get_recent_emails(service: Resource, user_id: str = "me", max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves recent emails from the user's Gmail inbox.
    """
    logger.info("Fetching %d recent emails for user", max_results)
    try:
        # Get list of messages
        messages_result = service.users().messages().list(
            userId=user_id, 
            maxResults=max_results,
            labelIds=['INBOX']
        ).execute()
        
        messages = messages_result.get('messages', [])
        
        email_list = []
        for message in messages:
            # Get detailed message info
            msg = service.users().messages().get(
                userId=user_id, 
                id=message['id'],
                format='full'
            ).execute()
            
            # Extract email details
            payload = msg.get('payload', {})
            headers = payload.get('headers', [])
            
            # Get subject, sender, date
            subject = ""
            sender = ""
            date = ""
            
            for header in headers:
                name = header.get('name', '').lower()
                value = header.get('value', '')
                
                if name == 'subject':
                    subject = value
                elif name == 'from':
                    sender = value
                elif name == 'date':
                    date = value
            
            # Get email body
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                            break
            elif payload.get('mimeType') == 'text/plain':
                data = payload.get('body', {}).get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
            
            email_list.append({
                'id': message['id'],
                'subject': subject,
                'sender': sender,
                'date': date,
                'snippet': msg.get('snippet', ''),
                'body': body[:500] if body else msg.get('snippet', '')  # Limit body to 500 chars
            })
        
        logger.info("Successfully retrieved %d emails", len(email_list))
        return email_list
        
    except HttpError as e:
        logger.error("Gmail API error while fetching emails: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error while fetching emails: %s", e, exc_info=True)
        raise


async def search_emails(service: Resource, query: str, user_id: str = "me", max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Searches emails based on a query string.
    """
    logger.info("Searching emails with query: %s", query)
    try:
        # Search messages
        search_result = service.users().messages().list(
            userId=user_id,
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = search_result.get('messages', [])
        
        email_list = []
        for message in messages:
            # Get detailed message info
            msg = service.users().messages().get(
                userId=user_id,
                id=message['id'],
                format='full'
            ).execute()
            
            # Extract email details (same as get_recent_emails)
            payload = msg.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = ""
            sender = ""
            date = ""
            
            for header in headers:
                name = header.get('name', '').lower()
                value = header.get('value', '')
                
                if name == 'subject':
                    subject = value
                elif name == 'from':
                    sender = value
                elif name == 'date':
                    date = value
            
            email_list.append({
                'id': message['id'],
                'subject': subject,
                'sender': sender,
                'date': date,
                'snippet': msg.get('snippet', '')
            })
        
        logger.info("Found %d emails matching query", len(email_list))
        return email_list
        
    except HttpError as e:
        logger.error("Gmail API error while searching emails: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error while searching emails: %s", e, exc_info=True)
        raise