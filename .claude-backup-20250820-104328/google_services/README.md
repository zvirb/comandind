# Google Services Integration for AI Workflow Engine

## Google Calendar Sync

### Overview
This package provides secure Google Calendar API integration for scheduling and managing workflow events.

### Features
- Secure OAuth 2.0 authentication
- Token management with automatic refresh
- Calendar event creation and synchronization
- Comprehensive error handling
- Configurable synchronization parameters

### Prerequisites
- Python 3.8+
- Google Cloud Platform project with Calendar API enabled
- OAuth 2.0 client credentials

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
1. Create a Google Cloud Platform project
2. Enable the Google Calendar API
3. Create OAuth 2.0 credentials (client ID and client secret)
4. Download the credentials JSON file
5. Configure `config.yaml` with your settings

### Usage Example
```python
from datetime import datetime
from .calendar_sync import GoogleCalendarSync

# Initialize the sync service
calendar_sync = GoogleCalendarSync()

# First-time authorization (opens browser)
calendar_sync.authorize()

# Create a workflow event
event = calendar_sync.create_workflow_event(
    summary='AI Workflow Execution',
    description='Automated workflow run',
    start_time=datetime.now(),
    end_time=datetime.now() + timedelta(hours=1)
)
```

### Security Considerations
- Store credentials securely
- Use environment variables for sensitive information
- Implement token rotation and revocation strategies

### Error Handling
```python
from .exceptions import GoogleCalendarSyncError

try:
    # Perform calendar operations
    pass
except GoogleCalendarSyncError as e:
    # Handle specific Google Calendar sync errors
    log_error(e)
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Submit a pull request

### License
[Insert appropriate license]