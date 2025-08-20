# Architecture Context Package (Compressed)
**Target Agents**: backend-gateway-expert, python-refactoring-architect, webui-architect  
**Token Limit**: 4000 | **Estimated Size**: 3,900 tokens | **Compression Ratio**: 68%

## 🏗️ CURRENT SYSTEM ARCHITECTURE

### Service Layer Architecture
```python
# Current Architecture Pattern: Layered Monolith
app/
├── api/                    # FastAPI REST endpoints
│   ├── auth/              # Authentication & OAuth
│   ├── calendar/          # Calendar operations
│   ├── tasks/             # Task management
│   ├── user/              # User profile management
│   └── middleware/        # Cross-cutting concerns
├── worker/                # Celery background tasks
│   ├── calendar/          # Google Calendar sync
│   ├── notifications/     # Email, push notifications
│   └── tasks/             # Task processing
└── shared/                # Common utilities
    ├── models/            # SQLAlchemy ORM models
    ├── schemas/           # Pydantic validation schemas
    └── utils/             # Shared business logic

# Data Flow: Request → Middleware → Router → Service → Repository → Database
```

### Database Schema Analysis
```sql
-- Core Tables Architecture
Users Table:
  - Primary entity for authentication
  - Google OAuth integration fields
  - Profile and preferences storage

Tasks Table:
  - User-owned task management
  - Status workflow: pending → in_progress → completed
  - Due dates, priorities, categories

Calendar_Events Table:  
  - Google Calendar sync integration
  - Bidirectional sync (local ↔ Google)
  - Event metadata and attendees

User_Sessions Table:
  - Redis-backed session management
  - JWT token storage and validation
  - Session security tracking
```

## 🔧 ARCHITECTURAL REFACTORING REQUIREMENTS

### Service Decomposition Strategy
```python
# Target: Domain-Driven Design with Clear Boundaries

# 1. Authentication Service (Standalone)
class AuthenticationService:
    async def authenticate_user(self, token: str) -> User
    async def refresh_token(self, refresh_token: str) -> TokenPair
    async def logout_user(self, session_id: str) -> None

# 2. Calendar Service (External Integration)
class CalendarService:
    async def sync_google_calendar(self, user_id: int) -> SyncResult
    async def create_event(self, event: EventCreate) -> Event
    async def get_user_events(self, user_id: int, date_range: DateRange) -> List[Event]

# 3. Task Management Service (Core Business Logic)  
class TaskService:
    async def create_task(self, task: TaskCreate) -> Task
    async def update_task_status(self, task_id: int, status: TaskStatus) -> Task
    async def get_user_tasks(self, user_id: int, filters: TaskFilters) -> List[Task]

# 4. Notification Service (Cross-cutting)
class NotificationService:
    async def send_email(self, user_id: int, template: str, data: dict) -> None
    async def send_push_notification(self, user_id: int, message: str) -> None
```

### Repository Pattern Implementation
```python
# Current: Direct SQLAlchemy in endpoints (tight coupling)
# Target: Repository abstraction for testability and maintainability

from abc import ABC, abstractmethod

class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]
    @abstractmethod
    async def create(self, user_data: UserCreate) -> User
    @abstractmethod
    async def update(self, user_id: int, user_data: UserUpdate) -> User

class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

# Dependency Injection
async def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return SQLAlchemyUserRepository(db)
```

### API Gateway Pattern
```python
# Current: Monolithic FastAPI application
# Target: API Gateway with service routing

from fastapi import FastAPI, Request
from httpx import AsyncClient

class APIGateway:
    def __init__(self):
        self.services = {
            'auth': 'http://auth-service:8001',
            'calendar': 'http://calendar-service:8002', 
            'tasks': 'http://task-service:8003',
            'notifications': 'http://notification-service:8004'
        }
    
    async def route_request(self, service: str, path: str, request: Request):
        service_url = self.services[service]
        async with AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=f"{service_url}{path}",
                headers=dict(request.headers),
                content=await request.body()
            )
            return response

# Middleware for Authentication
class AuthenticationMiddleware:
    async def __call__(self, request: Request, call_next):
        if request.url.path.startswith('/api/auth'):
            return await call_next(request)
        
        token = request.headers.get('Authorization')
        if not token:
            return JSONResponse({'error': 'Authentication required'}, 401)
        
        user = await verify_jwt_token(token)
        request.state.user = user
        return await call_next(request)
```

## 🎯 FRONTEND ARCHITECTURE MODERNIZATION

### Component Architecture Refactoring
```typescript
// Current: Page-based components with mixed concerns
// Target: Atomic Design with clear separation

// 1. Atomic Components (Pure UI)
interface ButtonProps {
    variant: 'primary' | 'secondary' | 'danger';
    size: 'sm' | 'md' | 'lg';
    onClick: () => void;
    children: React.ReactNode;
}

// 2. Molecule Components (UI + Minor Logic)
interface TaskItemProps {
    task: Task;
    onStatusChange: (id: number, status: TaskStatus) => void;
    onEdit: (task: Task) => void;
}

// 3. Organism Components (Complex Logic)
interface TaskListProps {
    userId: number;
    filters: TaskFilters;
    onTaskCreate: (task: TaskCreate) => void;
}

// 4. Template Components (Layout)
interface DashboardTemplateProps {
    sidebar: React.ReactNode;
    main: React.ReactNode;
    notifications: React.ReactNode;
}
```

### State Management Architecture
```typescript
// Current: Component-local state with prop drilling
// Target: Centralized state with context/stores

// Svelte Store Pattern
import { writable, derived } from 'svelte/store';

// User State
export const user = writable<User | null>(null);
export const isAuthenticated = derived(user, $user => !!$user);

// Tasks State  
export const tasks = writable<Task[]>([]);
export const pendingTasks = derived(tasks, $tasks => 
    $tasks.filter(task => task.status === 'pending')
);

// Calendar State
export const calendarEvents = writable<CalendarEvent[]>([]);
export const currentMonth = writable<Date>(new Date());
export const monthlyEvents = derived(
    [calendarEvents, currentMonth],
    ([$events, $month]) => filterEventsByMonth($events, $month)
);

// API State Management
class ApiStore {
    private cache = new Map<string, { data: any; timestamp: number }>();
    
    async fetchWithCache<T>(url: string, ttl = 300000): Promise<T> {
        const cached = this.cache.get(url);
        if (cached && Date.now() - cached.timestamp < ttl) {
            return cached.data;
        }
        
        const data = await fetch(url).then(r => r.json());
        this.cache.set(url, { data, timestamp: Date.now() });
        return data;
    }
}
```

## 🔄 MICROSERVICES MIGRATION PLAN

### Decomposition Strategy
```yaml
Phase 1: Extract Authentication Service
  Services: auth-service (standalone)
  Database: Shared (users, sessions tables)
  Communication: HTTP API
  Timeline: 2 weeks
  
Phase 2: Extract Calendar Service
  Services: calendar-service (Google API integration)
  Database: Dedicated (calendar_events table)
  Communication: HTTP + Message Queue
  Timeline: 3 weeks
  
Phase 3: Extract Task Service
  Services: task-service (core business logic)
  Database: Dedicated (tasks table)
  Communication: HTTP + Events
  Timeline: 2 weeks
  
Phase 4: Extract Notification Service
  Services: notification-service (cross-cutting)
  Database: Dedicated (notifications table)  
  Communication: Message Queue only
  Timeline: 1 week
```

### Inter-Service Communication
```python
# Event-Driven Architecture with Message Queues
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class DomainEvent:
    event_type: str
    aggregate_id: str
    event_data: Dict[str, Any]
    timestamp: datetime
    version: int

class EventBus:
    def __init__(self, broker_url: str):
        self.producer = create_producer(broker_url)
        self.consumers = {}
    
    async def publish(self, event: DomainEvent):
        await self.producer.send(event.event_type, event.dict())
    
    async def subscribe(self, event_type: str, handler: Callable):
        self.consumers[event_type] = handler

# Example Events
USER_CREATED = DomainEvent(
    event_type='user.created',
    aggregate_id='user-123',
    event_data={'email': 'user@example.com', 'name': 'John Doe'},
    timestamp=datetime.utcnow(),
    version=1
)

TASK_COMPLETED = DomainEvent(
    event_type='task.completed',
    aggregate_id='task-456',
    event_data={'user_id': 123, 'task_id': 456, 'completed_at': '2025-08-13T10:00:00Z'},
    timestamp=datetime.utcnow(),
    version=1
)
```

## 📦 DEPLOYMENT ARCHITECTURE

### Container Orchestration Strategy
```yaml
# Current: Docker Compose (Development/Staging)
# Target: Kubernetes (Production)

Kubernetes Architecture:
  Namespaces:
    - aiwfe-auth: Authentication service
    - aiwfe-calendar: Calendar service
    - aiwfe-tasks: Task management service
    - aiwfe-notifications: Notification service
    - aiwfe-gateway: API Gateway
    - aiwfe-frontend: WebUI service
    
  Service Mesh (Istio):
    - mTLS between services
    - Circuit breakers and retries
    - Distributed tracing
    - Rate limiting and load balancing
    
  Data Layer:
    - PostgreSQL cluster (primary/replica)
    - Redis cluster (session + cache)
    - Message queue (RabbitMQ/Kafka)
```

### Infrastructure as Code
```python
# Terraform Configuration Example
resource "kubernetes_deployment" "auth_service" {
  metadata {
    name      = "auth-service"
    namespace = "aiwfe-auth"
    labels = {
      app = "auth-service"
      version = "v1.0.0"
    }
  }
  
  spec {
    replicas = 3
    
    selector {
      match_labels = {
        app = "auth-service"
      }
    }
    
    template {
      metadata {
        labels = {
          app = "auth-service"
        }
      }
      
      spec {
        container {
          name  = "auth-service"
          image = "aiwfe/auth-service:v1.0.0"
          
          resources {
            requests = {
              cpu    = "100m"
              memory = "256Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "512Mi"
            }
          }
          
          env {
            name = "DATABASE_URL"
            value_from {
              secret_key_ref {
                name = "auth-db-secret"
                key  = "url"
              }
            }
          }
        }
      }
    }
  }
}
```

## ⚡ PHASE 5 ARCHITECTURE ACTIONS

### Immediate Refactoring Tasks
1. **Service Layer Extraction**: Create clear service boundaries for auth, calendar, tasks
2. **Repository Pattern**: Abstract data access behind repository interfaces
3. **Dependency Injection**: Implement proper DI container for testability
4. **API Versioning**: Add v1 prefix and versioning strategy
5. **Event-Driven Communication**: Implement domain events for service communication

### Code Quality Improvements
```python
# 1. Type Hints and Validation
from typing import Optional, List, Union
from pydantic import BaseModel, validator

class TaskService:
    def __init__(self, task_repo: TaskRepository, event_bus: EventBus):
        self.task_repo = task_repo
        self.event_bus = event_bus
    
    async def create_task(self, user_id: int, task_data: TaskCreate) -> Task:
        task = await self.task_repo.create(user_id, task_data)
        await self.event_bus.publish(TaskCreatedEvent(task.id, user_id))
        return task

# 2. Error Handling Strategy
class ApplicationError(Exception):
    def __init__(self, message: str, error_code: str, status_code: int = 400):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

class TaskNotFoundError(ApplicationError):
    def __init__(self, task_id: int):
        super().__init__(
            f"Task {task_id} not found",
            "TASK_NOT_FOUND", 
            404
        )
```

### Critical Files for Architecture Refactoring
- `app/api/main.py`: API Gateway and routing configuration
- `app/services/`: Service layer implementation
- `app/repositories/`: Data access abstraction
- `app/shared/events.py`: Domain event system
- `app/shared/dependencies.py`: Dependency injection setup
- `k8s/services/`: Kubernetes service manifests

**CRITICAL**: All architectural changes require integration testing validation with concrete evidence (service communication logs, API contract compliance, data consistency verification) before Step 6 approval.