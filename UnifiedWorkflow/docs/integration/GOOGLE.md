# Google Services Integration Documentation

**AI Workflow Engine - Google APIs Integration Guide**

*Last Updated: August 2, 2025*

## Overview

The AI Workflow Engine provides comprehensive integration with Google services, enabling users to seamlessly interact with their Google Calendar, Gmail, and Google Drive accounts through an intelligent AI interface. This document outlines the architecture, implementation patterns, security considerations, and development guidelines for Google services integration.

## Supported Google Services

### 1. Google Calendar API Integration
- **Full calendar synchronization** with local database
- **Event creation, modification, and deletion** 
- **AI-powered event categorization** using LLM models
- **Movability scoring** for smart scheduling
- **Timezone handling** with comprehensive error tracking
- **Bidirectional sync** with conflict resolution

### 2. Gmail API Integration  
- **Email reading and searching** capabilities
- **Recent email retrieval** with content parsing
- **Query-based email search** functionality
- **Email content extraction** with proper encoding handling
- **Read-only access** for security

### 3. Google Drive API Integration
- **Document search and retrieval**
- **Content extraction** from Google Workspace files
- **File metadata access**
- **Support for multiple document types** (Docs, Sheets, PDFs, etc.)
- **Full-text search** within documents

## Architecture Overview

### Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend UI   │    │   API Service   │    │ Worker Service  │
│   (SvelteKit)   │───▶│   (FastAPI)     │───▶│   (Celery)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   PostgreSQL    │    │ Google APIs     │
                       │   (OAuth Tokens)│    │ (Calendar/Gmail │
                       │                 │    │  /Drive)        │
                       └─────────────────┘    └─────────────────┘
```

### Container Distribution

- **API Service**: OAuth flow management, token storage, user authentication
- **Worker Service**: Heavy API operations, data processing, AI categorization
- **Database**: OAuth token persistence, event synchronization state
- **Frontend**: User interface for Google service connections

## Authentication Architecture

### OAuth 2.0 Implementation

The system implements Google OAuth 2.0 with the following flow:

1. **Authorization Request**: User initiates connection from settings UI
2. **OAuth Redirect**: System redirects to Google's authorization server
3. **Authorization Grant**: User consents to requested permissions
4. **Token Exchange**: System exchanges authorization code for access/refresh tokens
5. **Token Storage**: Encrypted token storage in PostgreSQL database
6. **Token Refresh**: Automatic token renewal using refresh tokens

### Security Model

```python
# Token Storage Schema
class UserOAuthToken(Base):
    user_id: int                    # Foreign key to user
    service: GoogleService          # Enum: CALENDAR, DRIVE, GMAIL
    access_token: str              # Encrypted access token
    refresh_token: Optional[str]   # Encrypted refresh token
    token_expiry: datetime         # Token expiration timestamp
    scope: str                     # Comma-separated OAuth scopes
    service_email: str             # Connected Google account email
```

### Service Account vs User Authentication

- **User Authentication**: OAuth 2.0 for personal account access
- **No Service Accounts**: All access is user-delegated for privacy
- **Scope Minimization**: Least-privilege access patterns

## Configuration Management

### OAuth Credentials Setup

OAuth credentials are managed through Docker secrets for production security:

```bash
# Production Setup (Docker Secrets)
echo "your-google-client-id" | docker secret create google_client_id -
echo "your-google-client-secret" | docker secret create google_client_secret -
```

### Environment Configuration

```python
# Configuration Loading (config.py)
class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[SecretStr] = None
    
    @model_validator(mode='after')
    def load_google_oauth_from_secrets(self) -> 'Settings':
        # Automatic loading from Docker secrets
        if not self.GOOGLE_CLIENT_ID:
            self.GOOGLE_CLIENT_ID = read_secret_file('google_client_id')
        if not self.GOOGLE_CLIENT_SECRET:
            self.GOOGLE_CLIENT_SECRET = SecretStr(read_secret_file('google_client_secret'))
        return self
```

### Required API Scopes

```python
# Service-specific OAuth scopes
SCOPES = {
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "drive": ["https://www.googleapis.com/auth/drive.readonly"], 
    "gmail": ["https://www.googleapis.com/auth/gmail.readonly"]
}
```

## Google Calendar Integration

### Synchronization Strategy

The calendar service implements sophisticated bidirectional synchronization:

```python
async def sync_events(self, user_id: int, force_sync: bool = False):
    # Incremental sync: 1 month past to 3 months future
    # Full sync: 1 year past to 1 year future
    time_min = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    time_max = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
    
    # Fetch, process, and cleanup events
    google_events = await self._fetch_google_events(time_min, time_max)
    await self._process_events_batch(google_events)
    await self._cleanup_deleted_events(google_event_ids)
```

### AI-Powered Event Processing

Events undergo intelligent processing for enhanced functionality:

1. **Categorization**: LLM-based event categorization
2. **Movability Scoring**: AI assessment of scheduling flexibility
3. **Timezone Normalization**: Robust timezone handling with error tracking
4. **Conflict Detection**: Smart scheduling conflict identification

```python
async def _categorize_event(self, summary: str, description: str) -> EventCategory:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_CATEGORIZE},
        {"role": "user", "content": f"Event Summary: {summary}\nDescription: {description}"}
    ]
    category = await invoke_llm(messages, model_name=selected_model)
    return category.strip().title()
```

### Timezone Handling

Comprehensive timezone support with error tracking:

```python
def _parse_event_time(self, time_data: Dict[str, Any]) -> Optional[datetime]:
    try:
        if 'timeZone' in time_data:
            tz = ZoneInfo(time_data['timeZone'])
            return dt.replace(tzinfo=tz)
    except ZoneInfoNotFoundError as e:
        self._track_timezone_error(time_data['timeZone'], 'timed_event')
        return dt.replace(tzinfo=timezone.utc)  # Fallback to UTC
```

## Gmail Integration

### Email Access Patterns

Gmail integration focuses on read-only operations for privacy and security:

```python
async def get_recent_emails(service: Resource, max_results: int = 10):
    # Retrieve recent inbox messages
    messages_result = service.users().messages().list(
        userId="me", 
        maxResults=max_results,
        labelIds=['INBOX']
    ).execute()
    
    # Process email content with proper encoding
    for message in messages:
        content = await self._extract_email_content(message)
        yield processed_email
```

### Search Capabilities

Advanced email search with Gmail query syntax support:

```python
async def search_emails(service: Resource, query: str, max_results: int = 10):
    # Support Gmail search operators
    search_result = service.users().messages().list(
        userId="me",
        q=query,  # Supports: from:, subject:, has:attachment, etc.
        maxResults=max_results
    ).execute()
```

## Google Drive Integration

### Document Processing Pipeline

Drive integration supports comprehensive document access:

```python
# Supported document types
SUPPORTED_DOC_TYPES = {
    'application/vnd.google-apps.document': 'text/plain',
    'application/vnd.google-apps.spreadsheet': 'text/csv',
    'application/vnd.google-apps.presentation': 'text/plain',
    'application/pdf': 'application/pdf',
    'text/plain': 'text/plain'
}

async def download_file_content(service: Resource, file_id: str, mime_type: str):
    if mime_type.startswith('application/vnd.google-apps'):
        # Export Google Workspace files
        request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
    else:
        # Download regular files
        request = service.files().get_media(fileId=file_id)
```

### Search and Discovery

Multi-modal file search capabilities:

```python
async def search_files_by_content(service: Resource, search_term: str):
    # Full-text search within documents
    query = f"trashed=false and fullText contains '{search_term}'"
    
    # Filter by supported document types
    mime_types = list(SUPPORTED_DOC_TYPES.keys())
    mime_query = " or ".join([f"mimeType='{mime}'" for mime in mime_types])
    query += f" and ({mime_query})"
```

## Error Handling & Resilience

### Retry Logic Implementation

Robust error handling with exponential backoff:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(HttpError)
)
async def api_call_with_retry():
    # Google API calls with automatic retry
    pass
```

### Token Management

Automatic token refresh with error recovery:

```python
async def refresh_expired_token(oauth_token: UserOAuthToken):
    if oauth_token.token_expiry <= datetime.now(timezone.utc):
        creds = Credentials(
            token=oauth_token.access_token,
            refresh_token=oauth_token.refresh_token,
            # ... other credentials
        )
        await asyncio.to_thread(creds.refresh, Request())
        
        # Update stored tokens
        oauth_token.access_token = creds.token
        oauth_token.token_expiry = creds.expiry
        db.commit()
```

### API Rate Limiting

Google API quota management strategies:

- **Request batching** for bulk operations
- **Exponential backoff** for rate limit errors
- **Request prioritization** for time-sensitive operations
- **Quota monitoring** and alerting

## Tool Integration Architecture

### Worker Service Integration

Google services are exposed through the worker's tool system:

```python
# Tool handler mapping
TOOL_HANDLER_MAP = {
    constants.CALENDAR_TOOL_ID: handle_calendar_interaction,
    constants.EMAIL_TOOL_ID: handle_email_interaction,
    constants.DRIVE_TOOL_ID: handle_drive_interaction,
}

async def handle_calendar_interaction(state: GraphState) -> Dict[str, Any]:
    # Intelligent routing based on user intent
    if "check" in user_input:
        return await check_calendar_events(state)
    elif "create" in user_input:
        return await create_calendar_event_tool(state)
    # ... other actions
```

### AI Service Integration

LLM-powered analysis and categorization:

```python
# Event categorization with fallback
async def _categorize_event(summary: str, description: str) -> str:
    try:
        llm_response = await invoke_llm(categorization_messages)
        if llm_response in Event.get_available_categories():
            return llm_response
    except Exception as e:
        logger.warning(f"LLM categorization failed: {e}")
    return "Default"  # Safe fallback
```

## Development Guidelines

### Adding New Google Service Integrations

1. **Define OAuth Scopes**: Add required scopes to configuration
2. **Create Service Module**: Follow existing service patterns
3. **Implement Authentication**: Use shared OAuth token management
4. **Add API Methods**: Implement with retry logic and error handling
5. **Create Tool Handler**: Expose through worker tool system
6. **Update Frontend**: Add UI for service connection/management

### Service Implementation Pattern

```python
# Standard service implementation pattern
class GoogleServiceClient:
    def __init__(self, oauth_token: UserOAuthToken, db: Session):
        self.oauth_token = oauth_token
        self.db = db
        self.service = None
    
    def _get_google_service(self) -> Resource:
        # Standard service initialization with token refresh
        pass
    
    @retry(stop=stop_after_attempt(3))
    async def api_method(self, params):
        # API method with retry logic
        pass
```

### Testing Google API Integrations

```python
# Testing patterns for Google service integrations
@pytest.fixture
def mock_google_service():
    with patch('googleapiclient.discovery.build') as mock_build:
        yield mock_build.return_value

async def test_calendar_sync(mock_google_service):
    # Mock API responses
    mock_google_service.events().list().execute.return_value = {
        'items': [sample_event_data]
    }
    
    # Test synchronization
    service = GoogleCalendarService(oauth_token, db)
    result = await service.sync_events(user_id=1)
    
    assert result['events_synced'] == 1
```

## Monitoring and Observability

### Performance Metrics

Key metrics for Google services monitoring:

- **API Response Times**: Track latency for each Google service
- **Token Refresh Rates**: Monitor OAuth token refresh frequency
- **Error Rates**: Track API failures and categorize error types
- **Sync Success Rates**: Monitor calendar/drive synchronization success
- **User Adoption**: Track service connection and usage patterns

### Error Tracking

Comprehensive error logging and alerting:

```python
def _track_timezone_error(self, invalid_timezone: str, event_type: str):
    logger.error(f"TIMEZONE ERROR: Invalid timezone '{invalid_timezone}' "
                f"in {event_type}. Consider adding timezone validation.")
    # TODO: Store metrics in Redis for dashboard display
    # TODO: Send alerts for repeated timezone errors
```

### Health Checks

Service health monitoring endpoints:

- **OAuth Token Validity**: Check token expiration status
- **API Connectivity**: Verify Google service reachability
- **Sync Status**: Monitor last successful synchronization times
- **Quota Usage**: Track API quota consumption

## Security Best Practices

### Token Security

- **Encryption at Rest**: OAuth tokens encrypted in database
- **Secure Transmission**: TLS for all API communications
- **Token Rotation**: Regular refresh token rotation
- **Scope Limitation**: Minimal required permissions only

### Access Control

- **User Isolation**: Strict user-based access controls
- **Service Segregation**: Isolated credentials per Google service
- **Audit Logging**: Comprehensive access and operation logging
- **Session Management**: Secure session handling for OAuth flows

### Privacy Protection

- **Data Minimization**: Store only essential synchronization data
- **Local Processing**: AI processing occurs locally, not on Google
- **User Control**: Users can disconnect services at any time
- **Transparent Permissions**: Clear explanation of required access

## Troubleshooting Guide

### Common Issues

#### OAuth Configuration Problems

**Symptom**: "OAuth is not configured" error
**Solutions**:
- Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
- Check Docker secrets file permissions (600)
- Confirm secrets are properly mounted in containers
- Review application logs for configuration loading errors

#### Authentication Failures

**Symptom**: "Token expired" or "Invalid credentials" errors
**Solutions**:
- Check token expiry timestamps in database
- Verify refresh token availability
- Re-authenticate user if refresh token is missing
- Validate OAuth redirect URIs in Google Console

#### API Rate Limiting

**Symptom**: "Quota exceeded" or "Rate limit exceeded" errors
**Solutions**:
- Implement exponential backoff in retry logic
- Reduce API call frequency for bulk operations
- Monitor quota usage in Google Cloud Console
- Consider API request batching for efficiency

#### Timezone Issues

**Symptom**: Events appear at wrong times
**Solutions**:
- Check timezone validation in `_parse_event_time`
- Review timezone error logs for invalid zones
- Verify system timezone configuration
- Consider fallback to UTC for invalid timezones

### Debugging Tools

#### Database Queries

```sql
-- Check OAuth token status
SELECT user_id, service, token_expiry, created_at 
FROM user_oauth_tokens 
WHERE service IN ('calendar', 'drive', 'gmail');

-- View recent sync activity
SELECT user_id, google_event_id, updated_at 
FROM events 
WHERE google_event_id IS NOT NULL 
ORDER BY updated_at DESC LIMIT 10;
```

#### Log Analysis

```bash
# View Google service logs
docker-compose logs -f worker | grep -i google

# Check OAuth flow logs  
docker-compose logs -f api | grep -i oauth

# Monitor API errors
docker-compose logs -f worker | grep -i "HttpError\|GoogleAPI"
```

#### Configuration Validation

```python
# Validate Google OAuth configuration
from shared.utils.config import get_settings

settings = get_settings()
settings.load_google_oauth_from_secrets()

print(f"Client ID configured: {bool(settings.GOOGLE_CLIENT_ID)}")
print(f"Client Secret configured: {bool(settings.GOOGLE_CLIENT_SECRET)}")
```

## API Reference

### OAuth Management Endpoints

```http
GET /api/v1/oauth/google/status
# Returns connection status for all Google services

GET /api/v1/oauth/google/connect/{service}
# Initiates OAuth flow for specified service (calendar|drive|gmail)

GET /api/v1/oauth/google/callback
# Handles OAuth callback and token exchange

DELETE /api/v1/oauth/google/disconnect/{service}
# Disconnects specified Google service
```

### Calendar API Methods

```python
# Core calendar service methods
async def sync_events(user_id: int, force_sync: bool = False)
async def create_calendar_event(service: Resource, calendar_id: str, event_data: Dict)
async def update_calendar_event(service: Resource, calendar_id: str, event_id: str, event_data: Dict)
async def list_calendar_events(service: Resource, calendar_id: str, time_min: str, time_max: str)
```

### Gmail API Methods  

```python
# Gmail service methods
async def get_recent_emails(service: Resource, max_results: int = 10)
async def search_emails(service: Resource, query: str, max_results: int = 10)
def get_gmail_service(user_id: int) -> Optional[Resource]
```

### Drive API Methods

```python
# Google Drive service methods
async def list_drive_files(service: Resource, query: str = "", max_results: int = 20)
async def download_file_content(service: Resource, file_id: str, mime_type: str)
async def search_files_by_content(service: Resource, search_term: str, max_results: int = 10)
async def get_file_metadata(service: Resource, file_id: str)
```

## Future Enhancements

### Planned Features

1. **Google Sheets Integration**: Spreadsheet reading and manipulation
2. **Google Photos API**: Photo management and AI-powered organization
3. **Google Tasks API**: Task synchronization with local task management
4. **Google Meet Integration**: Meeting scheduling and management
5. **Advanced Calendar AI**: Smart scheduling suggestions and conflict resolution

### Technical Improvements

1. **Webhook Support**: Real-time event synchronization using Google webhooks
2. **Batch Operations**: Improved efficiency for bulk data operations
3. **Caching Layer**: Redis-based caching for frequently accessed data
4. **Multi-Account Support**: Support for multiple Google accounts per user
5. **Advanced Analytics**: Detailed usage analytics and performance insights

### Security Enhancements

1. **Certificate Pinning**: Enhanced TLS security for API communications
2. **Token Encryption**: Advanced encryption for stored OAuth tokens
3. **Audit Trail**: Comprehensive audit logging for compliance
4. **Privacy Controls**: Enhanced user privacy controls and data retention policies

---

## Support

For issues with Google services integration:

1. **Check Configuration**: Verify OAuth setup in Google Cloud Console
2. **Review Logs**: Examine application logs for detailed error messages  
3. **Test Connectivity**: Use Google API Explorer to test service connectivity
4. **Documentation**: Refer to Google API documentation for service-specific issues
5. **Community**: Engage with the AI Workflow Engine community for support

For development assistance, see the main project documentation and development guidelines in `AIASSIST.md`.