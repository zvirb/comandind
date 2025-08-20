"""
Google Drive service for browsing and accessing files.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from shared.database.models import UserOAuthToken, GoogleService
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)

class GoogleDriveService:
    """Service for managing Google Drive file access."""
    
    def __init__(self, oauth_token: UserOAuthToken, db: Session):
        self.oauth_token = oauth_token
        self.db = db
        self.service = None
        
    def _get_google_service(self):
        """Initialize Google Drive service with OAuth credentials."""
        if self.service:
            return self.service
        
        # Get settings for OAuth credentials
        settings = get_settings()
        
        credentials = Credentials(
            token=self.oauth_token.access_token,
            refresh_token=self.oauth_token.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET.get_secret_value(),
            scopes=self.oauth_token.scope.split(',') if self.oauth_token.scope else []
        )
        
        try:
            self.service = build('drive', 'v3', credentials=credentials)
            
            # Check if credentials were refreshed and update database
            if credentials.token != self.oauth_token.access_token:
                logger.info("OAuth token was refreshed, updating database")
                self.oauth_token.access_token = credentials.token
                if credentials.refresh_token:
                    self.oauth_token.refresh_token = credentials.refresh_token
                if credentials.expiry:
                    self.oauth_token.token_expiry = credentials.expiry
                self.oauth_token.updated_at = datetime.now(timezone.utc)
                self.db.commit()
            
            return self.service
        except Exception as e:
            logger.error(f"Failed to create Google Drive service: {e}")
            raise
    
    async def list_files(self, folder_id: str = None, page_size: int = 20, page_token: str = None) -> Dict[str, Any]:
        """
        List files from Google Drive.
        
        Args:
            folder_id: ID of the folder to list files from (None for root)
            page_size: Number of files to return per page
            page_token: Token for pagination
            
        Returns:
            Dictionary with files list and pagination info
        """
        try:
            service = self._get_google_service()
            
            # Build query
            query_parts = []
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            else:
                # Show files in root or files shared with user
                query_parts.append("('root' in parents) or (sharedWithMe=true)")
            
            # Exclude trashed files
            query_parts.append("trashed=false")
            
            query = " and ".join(query_parts)
            
            # Request files
            request = service.files().list(
                q=query,
                pageSize=page_size,
                pageToken=page_token,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, thumbnailLink, webViewLink, iconLink, parents)"
            )
            
            result = request.execute()
            files = result.get('files', [])
            
            # Process files to add display information
            processed_files = []
            for file in files:
                processed_file = {
                    'id': file['id'],
                    'name': file['name'],
                    'mimeType': file['mimeType'],
                    'size': file.get('size'),
                    'modifiedTime': file.get('modifiedTime'),
                    'thumbnailLink': file.get('thumbnailLink'),
                    'webViewLink': file.get('webViewLink'),
                    'iconLink': file.get('iconLink'),
                    'isFolder': file['mimeType'] == 'application/vnd.google-apps.folder',
                    'fileExtension': self._get_file_extension(file['name'], file['mimeType']),
                    'displaySize': self._format_file_size(file.get('size'))
                }
                processed_files.append(processed_file)
            
            return {
                'files': processed_files,
                'nextPageToken': result.get('nextPageToken'),
                'hasMore': 'nextPageToken' in result
            }
            
        except HttpError as e:
            if e.resp.status == 401:
                logger.error("Google Drive access token expired")
                raise Exception("Google Drive access token expired. Please reconnect your account.")
            else:
                logger.error(f"Google Drive API error: {e}")
                raise Exception(f"Google Drive API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during Drive file listing: {e}")
            raise
    
    async def get_file_content(self, file_id: str) -> bytes:
        """
        Download file content from Google Drive.
        Handles both regular files and Google Workspace files (Docs, Sheets, Slides).
        
        Args:
            file_id: ID of the file to download
            
        Returns:
            Tuple of (file_content as bytes, file_metadata dict)
        """
        try:
            service = self._get_google_service()
            
            # Get file metadata first
            file_metadata = service.files().get(fileId=file_id).execute()
            mime_type = file_metadata.get('mimeType', '')
            
            # Check if it's a Google Workspace file that needs export
            if self._is_google_workspace_file(mime_type):
                # Export the file in an appropriate format
                export_mime_type = self._get_export_mime_type(mime_type)
                request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
                file_content = request.execute()
                
                # Update metadata to reflect the exported format
                file_metadata['mimeType'] = export_mime_type
                file_metadata['name'] = self._update_filename_for_export(
                    file_metadata.get('name', 'document'), 
                    export_mime_type
                )
            else:
                # Regular file download
                request = service.files().get_media(fileId=file_id)
                file_content = request.execute()
            
            return file_content, file_metadata
            
        except HttpError as e:
            if e.resp.status == 401:
                logger.error("Google Drive access token expired")
                raise Exception("Google Drive access token expired. Please reconnect your account.")
            elif e.resp.status == 403 and "fileNotDownloadable" in str(e):
                logger.error(f"File {file_id} is not downloadable: {e}")
                raise Exception("This file type cannot be downloaded. Please try exporting it manually from Google Drive.")
            else:
                logger.error(f"Google Drive API error: {e}")
                raise Exception(f"Google Drive API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during Drive file download: {e}")
            raise
    
    def _is_google_workspace_file(self, mime_type: str) -> bool:
        """Check if the file is a Google Workspace file that needs export."""
        google_workspace_types = [
            'application/vnd.google-apps.document',      # Google Docs
            'application/vnd.google-apps.spreadsheet',   # Google Sheets
            'application/vnd.google-apps.presentation',  # Google Slides
            'application/vnd.google-apps.drawing',       # Google Drawings
            'application/vnd.google-apps.form',          # Google Forms
        ]
        return mime_type in google_workspace_types
    
    def _get_export_mime_type(self, google_mime_type: str) -> str:
        """Get the appropriate export MIME type for Google Workspace files."""
        export_mapping = {
            'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
            'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',    # .xlsx
            'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
            'application/vnd.google-apps.drawing': 'image/png',  # .png
            'application/vnd.google-apps.form': 'application/pdf',  # .pdf
        }
        return export_mapping.get(google_mime_type, 'application/pdf')  # Default to PDF
    
    def _update_filename_for_export(self, original_name: str, export_mime_type: str) -> str:
        """Update filename to match the export format."""
        # Remove any existing extension
        name_without_ext = original_name.rsplit('.', 1)[0] if '.' in original_name else original_name
        
        # Add appropriate extension based on export MIME type
        extension_mapping = {
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
            'image/png': '.png',
            'application/pdf': '.pdf',
        }
        
        extension = extension_mapping.get(export_mime_type, '.pdf')
        return f"{name_without_ext}{extension}"
    
    def _get_file_extension(self, filename: str, mime_type: str) -> str:
        """Get file extension from filename or mime type."""
        if '.' in filename:
            return filename.split('.')[-1].lower()
        
        # Common mime type to extension mapping
        mime_extensions = {
            'application/pdf': 'pdf',
            'application/msword': 'doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/vnd.ms-excel': 'xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'application/vnd.ms-powerpoint': 'ppt',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
            'text/plain': 'txt',
            'text/csv': 'csv',
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'application/vnd.google-apps.document': 'gdoc',
            'application/vnd.google-apps.spreadsheet': 'gsheet',
            'application/vnd.google-apps.presentation': 'gslides',
        }
        
        return mime_extensions.get(mime_type, 'file')
    
    def _format_file_size(self, size_bytes: str) -> str:
        """Format file size in human readable format."""
        if not size_bytes:
            return ""
        
        try:
            size = int(size_bytes)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        except (ValueError, TypeError):
            return ""