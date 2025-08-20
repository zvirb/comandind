"""
Custom exceptions for Google Calendar integration.

These exceptions provide granular error handling and diagnostic information
for different failure scenarios in the Google Calendar synchronization process.
"""

class GoogleCalendarSyncError(Exception):
    """Base exception for Google Calendar synchronization errors."""
    pass

class AuthenticationError(GoogleCalendarSyncError):
    """Raised when authentication or authorization fails."""
    pass

class TokenRefreshError(AuthenticationError):
    """Raised when token refresh encounters an issue."""
    pass

class CalendarAPIError(GoogleCalendarSyncError):
    """Raised for general Google Calendar API interaction errors."""
    def __init__(self, message, error_code=None):
        super().__init__(message)
        self.error_code = error_code

class RateLimitExceededError(CalendarAPIError):
    """Raised when API rate limits are exceeded."""
    pass

class EventCreationError(CalendarAPIError):
    """Raised when event creation fails."""
    pass

class InsufficientPermissionsError(AuthenticationError):
    """Raised when the current OAuth credentials lack required permissions."""
    pass