# Focus Nudge API Specification

This document provides the complete API specification for the Focus Nudge system, enabling the AI feedback loop between the desktop client and server.

## Overview

The Focus Nudge system consists of:
1. **Data Collection**: Desktop client sends usage/notification data to server
2. **AI Analysis**: Server analyzes patterns and generates personalized nudges  
3. **Real-time Delivery**: Server pushes nudges to client via WebSocket
4. **Feedback Loop**: Client provides feedback to improve AI recommendations

## Authentication

All endpoints require authentication via JWT token:
```
Authorization: Bearer <your-jwt-token>
```

## REST API Endpoints

### 1. Submit Usage Data

**Endpoint**: `POST /api/v1/focus-nudge/usage-data`

**Purpose**: Primary data ingestion endpoint for desktop client to submit collected usage data and notification interactions.

**Request Body**:
```json
{
  "client_id": "desktop_client_uuid",
  "report_timestamp": "2024-01-15T10:30:00Z",
  "usage_data": [
    {
      "timestamp": "2024-01-15T10:25:00Z",
      "active_application": "Visual Studio Code",
      "window_title": "main.py - MyProject",
      "session_duration_ms": 1800000,
      "idle_time_ms": 0,
      "focus_score": 0.85,
      "context": {
        "productivity_apps": ["vscode", "terminal"],
        "distraction_apps": []
      }
    }
  ],
  "notification_interactions": [
    {
      "notification_id": "nudge_123",
      "action": "acted_upon",
      "timestamp": "2024-01-15T10:20:00Z",
      "response_time_ms": 5000,
      "context": {
        "effectiveness_rating": 4
      }
    }
  ],
  "system_info": {
    "platform": "Windows",
    "client_version": "1.0.0"
  }
}
```

**Response**:
```json
{
  "status": "received",
  "message": "Usage data received successfully",
  "report_id": "report_uuid",
  "processed_usage_points": 1,
  "processed_notifications": 1,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Call Frequency**: Every 5-10 minutes from desktop client

---

### 2. Get Nudge History

**Endpoint**: `GET /api/v1/focus-nudge/nudge-history?limit=50`

**Purpose**: Retrieve recent focus nudges for sync after reconnection.

**Response**:
```json
[
  {
    "nudge_id": "nudge_123",
    "type": "reminder",
    "message": "You've been away for a while. Ready to dive back into your work?",
    "priority": "medium",
    "action_required": false,
    "suggested_actions": [
      "Review your current task",
      "Take a 5-minute planning break"
    ],
    "sent_at": "2024-01-15T10:20:00Z",
    "expires_at": "2024-01-15T10:35:00Z"
  }
]
```

---

### 3. Submit Nudge Feedback

**Endpoint**: `POST /api/v1/focus-nudge/nudge-feedback`

**Purpose**: Provide feedback on nudge effectiveness for AI learning.

**Request Body**:
```json
{
  "nudge_id": "nudge_123",
  "action": "acted_upon",
  "effectiveness_rating": 4,
  "feedback_text": "This helped me refocus on my task"
}
```

**Response**:
```json
{
  "status": "received",
  "message": "Feedback recorded successfully"
}
```

**Actions**: `acknowledged`, `dismissed`, `acted_upon`, `ignored`

---

### 4. Get Focus Analytics

**Endpoint**: `GET /api/v1/focus-nudge/focus-analytics?timeframe_hours=24`

**Purpose**: Retrieve focus analytics and insights.

**Response**:
```json
{
  "timeframe_hours": 24,
  "focus_score_average": 0.75,
  "productive_hours": 6.5,
  "distraction_incidents": 12,
  "top_distracting_apps": [
    {"app": "Social Media", "time_spent_minutes": 45}
  ],
  "focus_trends": {
    "morning": 0.85,
    "afternoon": 0.70,
    "evening": 0.60
  },
  "nudge_effectiveness": {
    "total_nudges_sent": 8,
    "acknowledged": 6,
    "acted_upon": 4,
    "average_rating": 4.2
  }
}
```

---

### 5. Health Check

**Endpoint**: `GET /api/v1/focus-nudge/health`

**Response**:
```json
{
  "status": "healthy",
  "service": "focus_nudge_api",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## WebSocket Connection

### Focus Nudge WebSocket

**Endpoint**: `ws://localhost:8000/api/v1/ws/focus-nudge/{client_id}?token={jwt_token}`

**Purpose**: Real-time delivery of focus nudges from server to desktop client.

#### Connection Flow

1. **Connect**: Client connects with JWT token and client_id
2. **Authentication**: Server validates token and establishes session
3. **Confirmation**: Server sends connection confirmation
4. **Listen**: Client listens for focus nudge events
5. **Respond**: Client can send acknowledgments back

#### Connection Confirmation
```json
{
  "type": "connection_established",
  "client_id": "desktop_client_uuid",
  "user_id": 123,
  "timestamp": "2024-01-15T10:30:00Z",
  "message": "Focus Nudge WebSocket connected successfully"
}
```

#### Focus Nudge Event
```json
{
  "type": "focus_nudge",
  "client_id": "desktop_client_uuid",
  "nudge": {
    "nudge_id": "nudge_456",
    "type": "suggestion",
    "message": "Your focus seems scattered. Consider trying a focus technique.",
    "priority": "high",
    "action_required": false,
    "suggested_actions": [
      "Try the Pomodoro Technique (25min focused work)",
      "Close unnecessary applications",
      "Take a short mindfulness break"
    ],
    "expires_at": "2024-01-15T10:45:00Z",
    "metadata": {
      "trigger_reason": "low_focus_score",
      "confidence": 0.85
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Client Response (Optional)
```json
{
  "type": "nudge_acknowledgment",
  "nudge_id": "nudge_456",
  "action": "acknowledged",
  "timestamp": "2024-01-15T10:30:15Z"
}
```

## Data Models

### UsageData
```json
{
  "timestamp": "ISO 8601 datetime",
  "active_application": "string (optional)",
  "window_title": "string (optional)", 
  "session_duration_ms": "integer",
  "idle_time_ms": "integer (default: 0)",
  "focus_score": "float 0.0-1.0 (optional)",
  "context": "object (optional)"
}
```

### NotificationInteraction
```json
{
  "notification_id": "string",
  "action": "clicked|dismissed|ignored|actioned",
  "timestamp": "ISO 8601 datetime",
  "response_time_ms": "integer (optional)",
  "context": "object (optional)"
}
```

### FocusNudgeEvent
```json
{
  "nudge_id": "string (UUID)",
  "type": "reminder|suggestion|warning|celebration",
  "message": "string",
  "priority": "low|medium|high|urgent",
  "action_required": "boolean",
  "suggested_actions": "array of strings",
  "expires_at": "ISO 8601 datetime (optional)",
  "metadata": "object (optional)"
}
```

## Integration Guide

### Desktop Client Integration

1. **Initialize**: Connect to WebSocket on application start
2. **Collect Data**: Track user activity and focus metrics
3. **Submit Batches**: Send usage data every 5-10 minutes
4. **Listen for Nudges**: Handle incoming focus nudge events
5. **Provide Feedback**: Send nudge effectiveness feedback

### WebSocket Client Example (Python)
```python
import websockets
import json
import asyncio

async def focus_nudge_client():
    uri = "ws://localhost:8000/api/v1/ws/focus-nudge/my_client_id?token=jwt_token"
    
    async with websockets.connect(uri) as websocket:
        # Listen for messages
        async for message in websocket:
            data = json.loads(message)
            
            if data["type"] == "focus_nudge":
                nudge = data["nudge"]
                # Display nudge to user
                print(f"Focus Nudge: {nudge['message']}")
                
                # Send acknowledgment
                response = {
                    "type": "nudge_acknowledgment",
                    "nudge_id": nudge["nudge_id"],
                    "action": "acknowledged"
                }
                await websocket.send(json.dumps(response))
```

### Usage Data Collection Example
```python
import requests
import time

def collect_and_send_usage_data():
    usage_data = {
        "client_id": "desktop_client_uuid",
        "usage_data": [
            {
                "timestamp": time.time(),
                "active_application": get_active_app(),
                "session_duration_ms": get_session_duration(),
                "focus_score": calculate_focus_score()
            }
        ],
        "notification_interactions": get_notification_history()
    }
    
    response = requests.post(
        "http://localhost:8000/api/v1/focus-nudge/usage-data",
        json=usage_data,
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    
    return response.json()
```

## AI Analysis Pipeline

The system uses the following AI analysis pipeline:

1. **Pattern Detection**: Identify focus issues from usage data
   - Extended idle time
   - Low focus scores
   - Frequent app switching
   - Distraction patterns

2. **Nudge Generation**: Create personalized interventions
   - Context-aware messaging
   - Appropriate timing
   - Actionable suggestions
   - Respect user preferences

3. **Learning Loop**: Improve based on feedback
   - Track nudge effectiveness
   - Adjust timing and content
   - Personalize to user patterns
   - Reduce notification fatigue

## Error Handling

### HTTP Error Codes
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid JWT token  
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### WebSocket Error Codes
- `1008 Policy Violation`: Authentication failed
- `1011 Internal Error`: Server error
- `1012 Service Restart`: Server restarting

### Client Error Handling
```python
try:
    response = requests.post("/api/v1/focus-nudge/usage-data", json=data)
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        # Refresh JWT token
        refresh_auth_token()
    elif e.response.status_code == 429:
        # Back off and retry
        time.sleep(60)
```

## Rate Limits

- **Usage Data Submission**: 12 requests per hour (every 5 minutes)
- **Nudge History**: 60 requests per hour  
- **Analytics**: 24 requests per hour
- **Feedback**: 120 requests per hour

## Security Considerations

1. **Authentication**: All endpoints require valid JWT tokens
2. **Data Privacy**: Usage data is associated only with authenticated user
3. **Rate Limiting**: Prevents abuse and ensures fair usage
4. **Input Validation**: All inputs are validated and sanitized
5. **Transport Security**: Use HTTPS/WSS in production

## Testing

### Health Check
```bash
curl -X GET "http://localhost:8000/api/v1/focus-nudge/health"
```

### Submit Test Data
```bash
curl -X POST "http://localhost:8000/api/v1/focus-nudge/usage-data" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "test_client",
    "usage_data": [{
      "timestamp": "2024-01-15T10:30:00Z",
      "session_duration_ms": 1800000,
      "focus_score": 0.75
    }]
  }'
```

This completes the Focus Nudge API specification. The system provides a comprehensive feedback loop for AI-powered focus management with real-time nudge delivery and continuous learning from user interactions.