# API Documentation

Complete API reference and integration guides for the AI Workflow Engine. This section covers REST APIs, WebSocket APIs, and all integration endpoints.

## 🔌 API Overview

The AI Workflow Engine provides comprehensive APIs for:
- **Authentication & Authorization**: User and service authentication
- **Agent Management**: AI agent orchestration and control
- **Data Processing**: Data ingestion, processing, and retrieval
- **Real-time Communication**: WebSocket-based real-time features
- **Integration Services**: External service integrations

## 📋 API Documentation

### [📖 API Reference](reference.md)
Complete API reference documentation:
- Endpoint documentation with examples
- Request/response schemas
- Authentication requirements
- Rate limiting information
- Error codes and handling

### [🔐 Authentication & Authorization](auth.md)
Authentication and authorization APIs:
- Login and logout endpoints
- Token management (JWT)
- Session handling
- Permission checking
- User management APIs

### [🔄 WebSocket API](websocket.md)
Real-time communication via WebSockets:
- Connection establishment
- Message protocols
- Event streaming
- Authentication over WebSocket
- Error handling and reconnection

### [📱 Focus Nudge API](focus-nudge.md)
Mobile application integration APIs:
- Focus tracking endpoints
- Nudge delivery system
- User preference management
- Analytics and reporting
- Offline synchronization

## 🚀 Quick Start

### Authentication Flow
```bash
# 1. Login to get JWT token
curl -X POST "https://api.example.com/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# 2. Use token for authenticated requests
curl -X GET "https://api.example.com/api/v1/user/profile" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### WebSocket Connection
```javascript
// Connect to WebSocket with authentication
const ws = new WebSocket('wss://api.example.com/ws?token=YOUR_JWT_TOKEN');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

## 🔧 API Configuration

### Base URLs
- **Development**: `https://localhost:8443`
- **Production**: `https://api.yourdomain.com`
- **WebSocket**: `wss://api.yourdomain.com/ws`

### Required Headers
```http
Content-Type: application/json
Authorization: Bearer YOUR_JWT_TOKEN
X-API-Version: v1
```

### Rate Limiting
- **Default**: 100 requests per minute per user
- **Authenticated**: 1000 requests per minute per user
- **WebSocket**: 100 connections per user

## 📊 API Schemas

### Common Response Format
```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully",
  "timestamp": "2025-01-04T10:30:00Z",
  "version": "1.0"
}
```

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {}
  },
  "timestamp": "2025-01-04T10:30:00Z"
}
```

## 🔐 Authentication

### JWT Token Structure
```json
{
  "user_id": "123",
  "username": "user@example.com",
  "roles": ["user", "admin"],
  "exp": 1672531200,
  "iat": 1672444800
}
```

### Required Security Headers
- `Authorization: Bearer <token>`
- `X-Requested-With: XMLHttpRequest`
- `Content-Type: application/json`

## 📱 Client Libraries

### JavaScript/TypeScript
```javascript
import { APIClient } from './lib/api_client';

const client = new APIClient({
  baseURL: 'https://api.example.com',
  token: 'your-jwt-token'
});

const user = await client.get('/user/profile');
```

### Python
```python
from shared.services.api_client import APIClient

client = APIClient(
    base_url='https://api.example.com',
    token='your-jwt-token'
)

user = await client.get('/user/profile')
```

## 🧪 Testing

### API Testing Tools
- **Postman Collection**: Available in `/docs/api/postman/`
- **OpenAPI Spec**: Available at `/api/docs`
- **Test Suite**: Run with `pytest tests/api/`

### Test Authentication
```bash
# Get test token
export TEST_TOKEN=$(curl -s -X POST "https://localhost:8443/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test"}' | jq -r '.access_token')

# Test API endpoint
curl -H "Authorization: Bearer $TEST_TOKEN" \
  "https://localhost:8443/api/v1/user/profile"
```

## 📈 API Monitoring

### Health Checks
- **Health Endpoint**: `GET /health`
- **Readiness Check**: `GET /ready`
- **Metrics**: `GET /metrics`

### Monitoring Metrics
- Request rate and response times
- Error rates by endpoint
- Authentication success/failure rates
- WebSocket connection counts

## 🔗 Integration Examples

### React Integration
```jsx
import { useEffect, useState } from 'react';
import { apiClient } from '../services/api';

function UserProfile() {
    const [user, setUser] = useState(null);
    
    useEffect(() => {
        apiClient.get('/user/profile').then(setUser);
    }, []);
    
    return <div>{user?.name}</div>;
}
```

### Mobile App Integration
```dart
// Flutter/Dart example
import 'package:http/http.dart' as http;

class ApiService {
  final String baseUrl = 'https://api.example.com';
  
  Future<Map<String, dynamic>> getUserProfile(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/user/profile'),
      headers: {'Authorization': 'Bearer $token'},
    );
    return json.decode(response.body);
  }
}
```

## 🚨 Common Issues

### Authentication Problems
- **Invalid Token**: Check token expiration and format
- **Missing Headers**: Ensure required headers are included
- **CORS Issues**: Verify CORS configuration for web clients

### Rate Limiting
- **429 Too Many Requests**: Implement exponential backoff
- **Rate Limit Headers**: Check `X-RateLimit-*` headers
- **Token Bucket**: Understand rate limiting algorithm

## 📚 Related Documentation

- [Authentication System](../security/authentication.md)
- [WebSocket Security](../security/overview.md#websocket-security)
- [API Testing Guide](../testing/integration.md)
- [Troubleshooting API Issues](../troubleshooting/common-issues.md)

---

**For Implementation Details**: See the [Development Guides](../development/README.md) for implementing API integrations.