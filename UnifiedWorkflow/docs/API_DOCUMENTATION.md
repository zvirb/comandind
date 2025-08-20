# AI Workflow Engine - Comprehensive API Documentation

## 🚀 API Overview

The AI Workflow Engine provides a robust FastAPI-based REST API serving as the central communication hub for all system interactions. The API manages authentication, data processing, AI model integration, and service orchestration across the multi-container architecture.

**Base URL**: `https://localhost/api/v1/`  
**API Version**: 1.0.0  
**Authentication**: JWT Bearer Token  
**Content-Type**: `application/json`

---

## 🔐 Authentication & Security

### Authentication Flow

The API uses JWT (JSON Web Tokens) with custom authentication middleware for secure access control.

#### Login Endpoint
```http
POST /api/v1/auth/jwt/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "secure_password"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user_id": "uuid-string",
  "role": "user"
}
```

#### Authentication Header
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### CSRF Protection
All state-changing operations require CSRF tokens:

```http
GET /api/v1/auth/csrf-token
```

**Response**:
```json
{
  "csrf_token": "csrf-token-string"
}
```

Include in requests:
```http
X-CSRF-TOKEN: csrf-token-string
```

---

## 📊 Complete Router Documentation

### Authentication & Security Routers (10 endpoints)

#### 1. **Custom Auth Router** (`/api/v1/auth/`)
- `POST /jwt/login` - JWT authentication with enhanced security
- `POST /jwt/login-debug` - Debug login with detailed error information
- `POST /refresh` - Token refresh for continued session
- `POST /logout` - Secure logout with token invalidation
- `GET /csrf-token` - CSRF token generation

#### 2. **OAuth Router** (`/api/v1/oauth/`)
- `GET /google/authorize` - Google OAuth authorization
- `POST /google/callback` - Handle Google OAuth callback
- `GET /status` - OAuth connection status

#### 3. **Two-Factor Authentication** (`/api/v1/2fa/`)
- `POST /setup` - Initialize 2FA setup
- `POST /verify` - Verify 2FA token
- `POST /disable` - Disable 2FA for account
- `GET /backup-codes` - Generate backup codes

#### 4. **Enhanced Auth Router** (`/api/v1/enhanced-auth/`)
- `POST /advanced/login` - Advanced login with risk assessment
- `POST /session/validate` - Session validation and renewal
- `GET /security/status` - Account security status

#### 5. **WebAuthn Router** (`/api/v1/webauthn/`)
- `POST /register/begin` - Start WebAuthn registration
- `POST /register/complete` - Complete WebAuthn registration  
- `POST /authenticate/begin` - Start WebAuthn authentication
- `POST /authenticate/complete` - Complete WebAuthn authentication

#### 6. **Password Management** (`/api/v1/auth/`)
- `POST /change-password` - Change user password
- `POST /reset-password` - Reset password with token
- `POST /forgot-password` - Request password reset

#### 7. **Security Tier Router** (`/api/v1/security-tier/`)
- `GET /current` - Current security tier status
- `POST /upgrade` - Request security tier upgrade
- `GET /requirements` - Security tier requirements

#### 8. **Enterprise Security** (`/api/enterprise-security/`)
- `GET /policies` - Security policies for enterprise users
- `POST /audit/log` - Security audit logging
- `GET /compliance/status` - Compliance status check

#### 9. **Security Metrics** (`/api/v1/security-metrics/`)
- `GET /dashboard` - Security metrics dashboard
- `GET /incidents` - Security incident reports
- `POST /alerts/configure` - Configure security alerts

#### 10. **Native Auth Router** (`/native/auth/`)
- `POST /device/register` - Register native device
- `POST /device/authenticate` - Authenticate native device
- `GET /device/status` - Device authentication status

### Core Application Routers (12 endpoints)

#### 11. **Chat Router** (`/api/v1/chat/`)
- `POST /send` - Send chat message to AI models
- `GET /history` - Retrieve chat history
- `POST /stream` - Streaming chat responses
- `DELETE /clear` - Clear chat history

#### 12. **Conversation Router** (`/api/v1/conversation/`)
- `POST /create` - Create new conversation thread
- `GET /{conversation_id}` - Get conversation details
- `PUT /{conversation_id}` - Update conversation
- `DELETE /{conversation_id}` - Delete conversation

#### 13. **Tasks Router** (`/api/v1/tasks/`)
- `POST /create` - Create background task
- `GET /{task_id}/status` - Get task status
- `GET /list` - List user tasks
- `DELETE /{task_id}` - Cancel task

#### 14. **Profile Router** (`/api/v1/profile/`)
- `GET /` - Get user profile
- `PUT /` - Update user profile
- `POST /avatar` - Upload profile avatar
- `GET /preferences` - Get user preferences

#### 15. **Settings Router** (`/api/v1/settings/`)
- `GET /` - Get application settings
- `PUT /` - Update settings
- `POST /export` - Export user data
- `POST /import` - Import user data

#### 16. **Categories Router** (`/api/v1/categories/`)
- `GET /` - List categories
- `POST /` - Create category
- `PUT /{category_id}` - Update category
- `DELETE /{category_id}` - Delete category

#### 17. **Interview Router** (`/api/v1/interviews/`)
- `POST /create` - Create interview session
- `GET /{interview_id}` - Get interview details
- `POST /{interview_id}/question` - Ask interview question
- `POST /{interview_id}/complete` - Complete interview

#### 18. **Assessment Scheduler** (`/api/v1/assessments/`)
- `POST /schedule` - Schedule assessment
- `GET /{assessment_id}` - Get assessment details
- `PUT /{assessment_id}` - Update assessment
- `DELETE /{assessment_id}` - Cancel assessment

#### 19. **User History Router** (`/api/v1/user-history/`)
- `GET /activities` - Get user activity history
- `GET /analytics` - User behavior analytics
- `DELETE /clear` - Clear history data

#### 20. **Bug Report Router** (`/api/v1/bug-reports/`)
- `POST /submit` - Submit bug report
- `GET /` - List user bug reports
- `GET /{report_id}` - Get bug report details

#### 21. **Focus Nudge Router** (`/api/v1/focus-nudge/`)
- `GET /suggestions` - Get focus suggestions
- `POST /track` - Track focus metrics
- `GET /analytics` - Focus analytics

#### 22. **Mission Suggestions** (`/api/v1/mission-suggestions/`)
- `GET /` - Get mission suggestions
- `POST /complete` - Mark mission complete
- `GET /progress` - Mission progress tracking

### AI & Integration Routers (8 endpoints)

#### 23. **Ollama Router** (`/api/v1/ollama/`)
- `GET /models` - List available models
- `POST /generate` - Generate with Ollama model
- `POST /embeddings` - Generate embeddings
- `GET /status` - Ollama service status

#### 24. **Semantic Router** (`/api/v1/semantic/`)
- `POST /analyze` - Semantic content analysis
- `POST /similarity` - Calculate semantic similarity
- `POST /search` - Semantic search functionality

#### 25. **LLM Router** (`/api/v1/llm/`)
- `POST /completion` - Text completion requests
- `POST /chat` - Chat completion requests
- `GET /models` - Available LLM models

#### 26. **Smart Router API** (`/api/v1/smart-router/`)
- `POST /route` - Smart routing decisions
- `GET /analytics` - Routing analytics
- `POST /configure` - Configure routing rules

#### 27. **System Prompts Router** (`/api/v1/system-prompts/`)
- `GET /` - List system prompts
- `POST /` - Create system prompt
- `PUT /{prompt_id}` - Update prompt
- `DELETE /{prompt_id}` - Delete prompt

#### 28. **Protocol Router** (`/api/v1/protocol/`)
- `GET /stack` - Protocol stack status
- `POST /configure` - Configure protocols
- `GET /metrics` - Protocol metrics

#### 29. **Calendar Router** (`/api/v1/calendar/`)
- `GET /events` - Get calendar events
- `POST /events` - Create calendar event
- `PUT /events/{event_id}` - Update event
- `DELETE /events/{event_id}` - Delete event

#### 30. **Drive Router** (`/api/v1/drive/`)
- `GET /files` - List Google Drive files
- `POST /upload` - Upload to Google Drive
- `GET /{file_id}` - Download from Drive
- `DELETE /{file_id}` - Delete Drive file

### WebSocket & Real-time Communication (4 endpoints)

#### 31. **WebSocket Router** (`/api/v1/ws/`)
- `WS /connect` - Basic WebSocket connection
- `WS /chat` - Chat WebSocket endpoint

#### 32. **Enhanced Secure WebSocket** (`/api/v1/secure-ws/`)
- `WS /connect` - Secure WebSocket with authentication
- `WS /stream` - Streaming data WebSocket

#### 33. **Chat WebSocket** (`/ws/chat/`)
- `WS /` - Real-time chat WebSocket
- `WS /room/{room_id}` - Chat room WebSocket

#### 34. **Secure WebSocket Router** (`/api/v1/websocket/`)
- `WS /secure` - Enterprise-grade secure WebSocket
- `WS /admin` - Administrative WebSocket

### Administrative & Monitoring (6 endpoints)

#### 35. **Admin Router** (`/api/v1/admin/`)
- `GET /users` - List all users
- `POST /users/{user_id}/activate` - Activate user
- `POST /users/{user_id}/deactivate` - Deactivate user
- `GET /system/stats` - System statistics

#### 36. **Performance Dashboard** (`/api/v1/performance-dashboard/`)
- `GET /health-overview` - System health overview
- `GET /metrics/realtime` - Real-time performance metrics
- `GET /metrics/historical` - Historical performance data
- `GET /bottlenecks/analysis` - Bottleneck analysis

#### 37. **Security Metrics Router** (`/api/v1/security-metrics/`)
- `GET /dashboard` - Security dashboard
- `GET /threats` - Threat detection data
- `POST /incidents` - Report security incident

#### 38. **Monitoring Router** (`/api/v1/monitoring/`)
- `GET /health` - Service health checks
- `GET /metrics` - System metrics
- `POST /alerts` - Configure monitoring alerts

#### 39. **Public Router** (`/public/`)
- `GET /status` - Public system status
- `GET /version` - API version information
- `GET /documentation` - API documentation

### Native Client Support (3 endpoints)

#### 40. **Native Router** (`/native/`)
- `GET /config` - Native client configuration
- `POST /sync` - Sync native client data
- `GET /updates` - Check for updates

#### 41. **Native API Router** (`/native/api/`)
- `POST /authenticate` - Native client authentication
- `GET /data` - Native client data access
- `POST /upload` - Native client uploads

#### 42. **Native Auth Router** (`/native/auth/`)
- `POST /register` - Register native client
- `POST /login` - Native client login
- `POST /refresh` - Refresh native token

### Additional Specialized Routers (2 endpoints)

#### 43. **Scoring Router** (`/api/v1/scoring/`)
- `POST /calculate` - Calculate scores
- `GET /leaderboard` - User leaderboard
- `GET /analytics` - Scoring analytics

#### 44. **Enhanced Auth Router** (`/api/v1/enhanced/`)
- `POST /multi-factor` - Multi-factor authentication
- `GET /session/info` - Session information
- `POST /security/check` - Security verification

---

## 📋 Standard Response Formats

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERR_400_VALIDATION",
    "message": "Validation error",
    "details": {
      "field": "email",
      "issue": "Invalid format"
    }
  }
}
```

### Pagination Response
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8
  }
}
```

---

## 🔒 Security Headers

All API responses include security headers:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

---

## 📊 Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **General API**: 100 requests per minute
- **Authentication**: 5 login attempts per minute
- **WebSocket**: 1000 messages per minute
- **File Upload**: 10 uploads per minute

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

---

## 🚨 Error Codes

| Code Range | Category | Description |
|------------|----------|-------------|
| 400-499 | Client Error | Invalid request, authentication, or authorization |
| 500-599 | Server Error | Internal server errors, service unavailable |
| ERR_400_* | Validation | Input validation failures |
| ERR_401_* | Authentication | Authentication failures |
| ERR_403_* | Authorization | Permission denied |
| ERR_429_* | Rate Limiting | Too many requests |
| ERR_500_* | Internal | Internal server errors |

---

## 📡 WebSocket API

### Connection
```javascript
const ws = new WebSocket('wss://localhost/api/v1/secure-ws/connect');
ws.addEventListener('open', (event) => {
  // Send authentication
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your-jwt-token'
  }));
});
```

### Message Format
```json
{
  "type": "message_type",
  "data": { ... },
  "timestamp": "2025-08-06T14:30:22Z"
}
```

---

## 🔧 Development & Testing

### Health Check Endpoints
```http
GET /health
GET /api/v1/health
GET /api/health
```

**Response**:
```json
{
  "status": "ok",
  "redis_connection": "ok",
  "database_connection": "ok",
  "timestamp": "2025-08-06T14:30:22Z"
}
```

### API Documentation
- **Interactive Documentation**: `https://localhost/docs`
- **OpenAPI Schema**: `https://localhost/openapi.json`
- **ReDoc**: `https://localhost/redoc`

---

## 📚 SDK Examples

### Python Client
```python
import requests

class AIWorkflowClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {'Authorization': f'Bearer {token}'}
    
    def login(self, username, password):
        response = requests.post(
            f"{self.base_url}/api/v1/auth/jwt/login",
            json={"username": username, "password": password}
        )
        return response.json()
    
    def chat(self, message):
        response = requests.post(
            f"{self.base_url}/api/v1/chat/send",
            json={"message": message},
            headers=self.headers
        )
        return response.json()
```

### JavaScript Client
```javascript
class AIWorkflowAPI {
  constructor(baseURL, token) {
    this.baseURL = baseURL;
    this.token = token;
  }
  
  async login(username, password) {
    const response = await fetch(`${this.baseURL}/api/v1/auth/jwt/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    return response.json();
  }
  
  async chat(message) {
    const response = await fetch(`${this.baseURL}/api/v1/chat/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify({ message })
    });
    return response.json();
  }
}
```

---

## 📈 Performance Specifications

### Response Time Targets
- **Health endpoints**: < 50ms
- **Authentication**: < 300ms
- **Data retrieval**: < 500ms
- **AI processing**: < 5000ms

### Throughput Capacity
- **Concurrent users**: 100+
- **Requests per second**: 500+
- **WebSocket connections**: 1000+

---

This comprehensive API documentation covers all 44 routers with authentication examples, error handling, and complete endpoint specifications for the AI Workflow Engine.