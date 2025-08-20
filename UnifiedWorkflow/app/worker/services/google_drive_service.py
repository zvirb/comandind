"""
Google Drive service for handling Drive API interactions with user OAuth credentials.
"""

import logging
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from shared.database.models._models import UserOAuthToken, GoogleService
from shared.utils.database_setup import get_db
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)

# Google Drive API scopes
DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file"
]

# Supported file types for document extraction
SUPPORTED_DOC_TYPES = {
    'application/vnd.google-apps.document': 'text/plain',
    'application/vnd.google-apps.spreadsheet': 'text/csv',
    'application/vnd.google-apps.presentation': 'text/plain',
    'application/pdf': 'application/pdf',
    'text/plain': 'text/plain',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword': 'application/msword'
}


def get_drive_service(user_id: int) -> Optional[Resource]:
    """
    Builds and returns a Google Drive service object authenticated
    with the user's OAuth credentials.
    """
    logger.info("Building Google Drive service for user_id: %s", user_id)
    try:
        # Get the user's OAuth token for Google Drive
        with get_db() as db:
            oauth_token = db.query(UserOAuthToken).filter(
                UserOAuthToken.user_id == user_id,
                UserOAuthToken.service == GoogleService.DRIVE
            ).first()
            
            if not oauth_token:
                logger.error(
                    "No Google Drive OAuth token found for user_id: %s. "
                    "User needs to connect their Google Drive first.",
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
                        "User needs to reconnect their Google Drive.",
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
            
            service: Resource = build("drive", "v3", credentials=creds)
            logger.info("Successfully built Google Drive service with OAuth credentials.")
            return service
            
    except Exception as e:
        logger.error("Failed to build Google Drive service: %s", e, exc_info=True)
    return None


async def list_drive_files(service: Resource, query: str = "", max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Lists files from Google Drive based on a query.
    """
    logger.info("Listing Drive files with query: %s", query)
    try:
        # Build the query - only show files the user owns and that are not trashed
        full_query = "trashed=false"
        if query:
            full_query += f" and (name contains '{query}' or fullText contains '{query}')"
        
        # Only include document types we can process
        mime_types = list(SUPPORTED_DOC_TYPES.keys())
        mime_query = " or ".join([f"mimeType='{mime}'" for mime in mime_types])
        full_query += f" and ({mime_query})"
        
        results = service.files().list(
            q=full_query,
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink, parents)"
        ).execute()
        
        files = results.get('files', [])
        
        logger.info("Found %d files matching query", len(files))
        return files
        
    except HttpError as e:
        logger.error("Google Drive API error while listing files: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error while listing files: %s", e, exc_info=True)
        raise


async def download_file_content(service: Resource, file_id: str, mime_type: str) -> Optional[str]:
    """
    Downloads the content of a file from Google Drive.
    """
    logger.info("Downloading content for file_id: %s, mime_type: %s", file_id, mime_type)
    try:
        # Determine export format based on file type
        if mime_type in SUPPORTED_DOC_TYPES:
            export_mime_type = SUPPORTED_DOC_TYPES[mime_type]
            
            if mime_type.startswith('application/vnd.google-apps'):
                # Google Workspace files need to be exported
                request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
            else:
                # Regular files can be downloaded directly
                request = service.files().get_media(fileId=file_id)
            
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                logger.debug("Download progress: %d%%", int(status.progress() * 100))
            
            file_io.seek(0)
            
            # Convert bytes to string based on export format
            if export_mime_type in ['text/plain', 'text/csv']:
                content = file_io.read().decode('utf-8')
            else:
                # For other formats, we might need additional processing
                # For now, return the first 1000 characters as a preview
                try:
                    content = file_io.read().decode('utf-8')[:1000]
                except UnicodeDecodeError:
                    content = "Binary file content - cannot display as text"
            
            logger.info("Successfully downloaded file content (%d characters)", len(content))
            return content
        else:
            logger.warning("Unsupported file type for content extraction: %s", mime_type)
            return None
            
    except HttpError as e:
        logger.error("Google Drive API error while downloading file: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error while downloading file: %s", e, exc_info=True)
        raise


async def get_file_metadata(service: Resource, file_id: str) -> Optional[Dict[str, Any]]:
    """
    Gets metadata for a specific file.
    """
    logger.info("Getting metadata for file_id: %s", file_id)
    try:
        file_metadata = service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, size, modifiedTime, webViewLink, description, parents"
        ).execute()
        
        logger.info("Successfully retrieved metadata for file: %s", file_metadata.get('name'))
        return file_metadata
        
    except HttpError as e:
        logger.error("Google Drive API error while getting file metadata: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error while getting file metadata: %s", e, exc_info=True)
        raise


async def search_files_by_content(service: Resource, search_term: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Searches for files by content within supported document types.
    """
    logger.info("Searching files by content: %s", search_term)
    try:
        # Search for files that contain the search term in their content
        query = f"trashed=false and fullText contains '{search_term}'"
        
        # Only include document types we can process
        mime_types = list(SUPPORTED_DOC_TYPES.keys())
        mime_query = " or ".join([f"mimeType='{mime}'" for mime in mime_types])
        query += f" and ({mime_query})"
        
        results = service.files().list(
            q=query,
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink)"
        ).execute()
        
        files = results.get('files', [])
        
        logger.info("Found %d files containing the search term", len(files))
        return files
        
    except HttpError as e:
        logger.error("Google Drive API error while searching files: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error while searching files: %s", e, exc_info=True)
        raise