# AI Workflow Engine - Developer Knowledge Base

## 🚀 Getting Started

Welcome to the AI Workflow Engine development environment! This comprehensive guide will get you up and running quickly while ensuring you follow our development standards and best practices.

### 🎯 Quick Start Summary

1. **Clone Repository** → Set up local development environment
2. **Configure Environment** → Set environment variables and secrets
3. **Start Services** → Launch development stack with Docker Compose
4. **Run Tests** → Verify everything works
5. **Start Coding** → Follow our development patterns and guidelines

---

## 🛠️ Development Environment Setup

### Prerequisites

**Required Software**:
- **Git** 2.30+
- **Docker** 20.10+ with Docker Compose V2
- **Python** 3.11+ (for IDE support and local testing)
- **Node.js** 18+ and npm (for frontend development)
- **VS Code** (recommended) with Python and Svelte extensions

**Hardware Requirements**:
- **CPU**: 4+ cores recommended
- **Memory**: 16GB+ recommended (8GB minimum)
- **Storage**: 20GB+ free space for Docker images and data

### Initial Setup

**1. Clone and Setup Repository**:
```bash
# Clone repository
git clone https://github.com/your-org/ai-workflow-engine.git
cd ai-workflow-engine

# Create development branch
git checkout -b feature/your-feature-name

# Set up environment
cp .env.example .env.development
```

**2. Configure Development Environment**:
```bash
# .env.development
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Database
POSTGRES_DB=ai_workflow_engine_dev
POSTGRES_USER=devuser
POSTGRES_PASSWORD=devpass123
DATABASE_URL=postgresql://devuser:devpass123@localhost:5432/ai_workflow_engine_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT (development only - not for production!)
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# WebUI Settings
WEBUI_HOST=0.0.0.0
WEBUI_PORT=3000

# CORS for development
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://localhost

# Google Services (optional for development)
GOOGLE_CLIENT_ID=your_dev_google_client_id
GOOGLE_CLIENT_SECRET=your_dev_google_client_secret

# Ollama (if running locally)
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

**3. Start Development Stack**:
```bash
# Start infrastructure services first
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis qdrant

# Wait for services to be ready
sleep 30

# Run database migrations
docker-compose -f docker-compose.yml -f docker-compose.dev.yml run --rm api python -m alembic upgrade head

# Start all services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Verify everything is running
docker-compose ps
curl http://localhost:8000/api/v1/health
```

**4. Setup Pre-commit Hooks**:
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Test hooks
pre-commit run --all-files
```

### Development vs Production Differences

| Aspect | Development | Production |
|--------|-------------|------------|
| **Environment** | Hot reloading, debug mode | Optimized, minified |
| **Database** | Local PostgreSQL | Managed/clustered DB |
| **Secrets** | Plain text in .env | Docker secrets |
| **Logging** | DEBUG level | WARNING/ERROR level |
| **SSL/TLS** | Self-signed or HTTP | Valid certificates |
| **Error Handling** | Detailed stack traces | User-friendly messages |
| **Performance** | Development tools enabled | Production optimizations |

---

## 🏗️ Project Structure & Architecture

### Repository Organization

```
ai_workflow_engine/
├── .claude/                    # Claude AI agent definitions
│   ├── agents/                # Specialist agent configurations
│   └── AGENT_REGISTRY.md      # Agent documentation
├── app/                       # Main application code
│   ├── api/                   # FastAPI backend service
│   │   ├── routers/          # API route handlers (44 routers)
│   │   ├── middleware/       # Custom middleware
│   │   ├── dependencies/     # Dependency injection
│   │   └── main.py          # FastAPI application entry
│   ├── shared/               # Shared modules across services
│   │   ├── database/        # Database models and setup
│   │   ├── services/        # Business logic services
│   │   ├── schemas/         # Pydantic schemas
│   │   └── utils/           # Utility functions
│   ├── webui/               # SvelteKit frontend
│   │   ├── src/            # Svelte source code
│   │   │   ├── routes/     # SvelteKit routes
│   │   │   ├── lib/        # Shared components and utilities
│   │   │   └── app.html    # App template
│   │   └── package.json    # Frontend dependencies
│   └── worker/             # Celery worker service
│       ├── tasks/          # Background task definitions
│       └── celery_app.py   # Celery configuration
├── config/                 # Service configurations
│   ├── caddy/             # Reverse proxy config
│   ├── postgres/          # Database config
│   └── redis/             # Cache config
├── docs/                  # Documentation
├── scripts/               # Automation scripts
├── tests/                 # Test suites
├── docker-compose.yml     # Main compose file
├── docker-compose.dev.yml # Development overrides
└── requirements.txt       # Python dependencies
```

### Key Architecture Patterns

**1. Import Patterns - CRITICAL REQUIREMENT**:
```python
# ✅ CORRECT - All imports use 'from shared.' prefix
from shared.database.models import User
from shared.services.auth_service import AuthService
from shared.schemas.user_schemas import UserCreate
from shared.utils.config import get_settings

# ❌ INCORRECT - Direct imports will fail in containers
from database.models import User
from services.auth_service import AuthService
```

**2. Service Layer Pattern**:
```python
# Business logic in services
from shared.services.user_service import UserService

async def create_user_endpoint(user_data: UserCreate):
    user_service = UserService()
    return await user_service.create_user(user_data)
```

**3. Dependency Injection**:
```python
from api.dependencies import get_current_user, get_db

@router.post("/protected")
async def protected_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {"user_id": current_user.id}
```

**4. Error Handling Pattern**:
```python
from shared.utils.error_handler import handle_api_error

try:
    result = await some_operation()
    return {"success": True, "data": result}
except Exception as e:
    return handle_api_error(e)
```

---

## 🎨 Frontend Development Guide

### SvelteKit Development

**Project Structure**:
```
app/webui/src/
├── app.html              # HTML template
├── app.css              # Global styles
├── routes/              # File-based routing
│   ├── +layout.svelte   # Root layout
│   ├── +page.svelte     # Home page
│   ├── login/          # Auth pages
│   ├── dashboard/      # Main app
│   └── admin/          # Admin interface
├── lib/                # Reusable code
│   ├── components/     # Svelte components
│   ├── stores/         # State management
│   ├── api_client/     # API integration
│   └── utils/          # Helper functions
└── service-worker.js   # PWA service worker
```

**Component Development Standards**:
```svelte
<!-- ComponentExample.svelte -->
<script>
  import { onMount } from 'svelte';
  import { authStore } from '$lib/stores/auth.js';
  import ApiClient from '$lib/api_client/index.js';
  
  export let title = 'Default Title';
  
  let loading = false;
  let data = null;
  let error = null;
  
  onMount(async () => {
    await loadData();
  });
  
  async function loadData() {
    loading = true;
    error = null;
    
    try {
      const apiClient = new ApiClient();
      data = await apiClient.getData();
    } catch (err) {
      error = err.message;
      console.error('Failed to load data:', err);
    } finally {
      loading = false;
    }
  }
</script>

<div class="component">
  <h2>{title}</h2>
  
  {#if loading}
    <div class="loading">Loading...</div>
  {:else if error}
    <div class="error">Error: {error}</div>
  {:else if data}
    <div class="content">
      <!-- Content here -->
    </div>
  {/if}
</div>

<style>
  .component {
    padding: 1rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
  }
  
  .loading, .error {
    padding: 1rem;
    text-align: center;
  }
  
  .error {
    color: var(--error-color);
    background: var(--error-bg);
  }
</style>
```

**State Management**:
```javascript
// lib/stores/auth.js
import { writable } from 'svelte/store';

function createAuthStore() {
  const { subscribe, set, update } = writable({
    user: null,
    token: null,
    isAuthenticated: false
  });

  return {
    subscribe,
    login: (user, token) => {
      set({ user, token, isAuthenticated: true });
      localStorage.setItem('auth_token', token);
    },
    logout: () => {
      set({ user: null, token: null, isAuthenticated: false });
      localStorage.removeItem('auth_token');
    },
    checkAuth: () => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        // Verify token with API
        return true;
      }
      return false;
    }
  };
}

export const authStore = createAuthStore();
```

**API Client Pattern**:
```javascript
// lib/api_client/index.js
class ApiClient {
  constructor() {
    this.baseURL = 'http://localhost:8000/api/v1';
    this.token = localStorage.getItem('auth_token');
  }

  async request(method, endpoint, data = null) {
    const headers = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const config = {
      method,
      headers,
    };

    if (data && method !== 'GET') {
      config.body = JSON.stringify(data);
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, config);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP ${response.status}`);
    }

    return await response.json();
  }

  async get(endpoint) {
    return this.request('GET', endpoint);
  }

  async post(endpoint, data) {
    return this.request('POST', endpoint, data);
  }

  async put(endpoint, data) {
    return this.request('PUT', endpoint, data);
  }

  async delete(endpoint) {
    return this.request('DELETE', endpoint);
  }
}

export default ApiClient;
```

### Frontend Development Workflow

**1. Start Development Server**:
```bash
# Start backend services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d api postgres redis

# Start frontend development server
cd app/webui
npm run dev

# Open browser to http://localhost:5173
```

**2. Hot Reloading**:
The development server automatically reloads when you make changes to:
- Svelte components
- JavaScript modules
- CSS styles
- Route files

**3. Building for Production**:
```bash
cd app/webui
npm run build

# Test production build
npm run preview
```

---

## 🐍 Backend Development Guide

### FastAPI Development

**Router Pattern**:
```python
# api/routers/example_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from shared.database.models import User
from shared.schemas.user_schemas import UserResponse, UserCreate
from shared.services.user_service import UserService
from api.dependencies import get_current_user, get_db, verify_csrf_token

router = APIRouter()

@router.get("/users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of users with pagination."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    user_service = UserService(db)
    return await user_service.get_users(skip=skip, limit=limit)

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _csrf_token: str = Depends(verify_csrf_token)  # CSRF protection
):
    """Create a new user."""
    user_service = UserService(db)
    try:
        return await user_service.create_user(user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

**Service Layer Pattern**:
```python
# shared/services/user_service.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

from shared.database.models import User
from shared.schemas.user_schemas import UserCreate, UserUpdate
from shared.utils.security import get_password_hash, verify_password

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return self.db.query(User).filter(User.email == email).first()
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create new user with validation."""
        # Check if user already exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user
        db_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            role=user_data.role or "user",
            is_active=True
        )
        
        try:
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Failed to create user due to data conflict")
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user credentials."""
        user = await self.get_user_by_email(email)
        if not user or not user.is_active:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user
```

**Database Model Pattern**:
```python
# shared/database/models.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="user")
    documents = relationship("Document", back_populates="user")
    
    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}')>"
```

**Schema Pattern (Pydantic)**:
```python
# shared/schemas/user_schemas.py
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
from shared.database.models import UserRole, UserStatus

class UserBase(BaseModel):
    email: EmailStr
    role: Optional[UserRole] = UserRole.USER

class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: str
    status: UserStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: EmailStr  # Using username for compatibility
    password: str
```

### Backend Development Workflow

**1. Database Changes**:
```bash
# Create migration after model changes
docker-compose run --rm api python -m alembic revision --autogenerate -m "Add user table"

# Apply migration
docker-compose run --rm api python -m alembic upgrade head

# Downgrade if needed
docker-compose run --rm api python -m alembic downgrade -1
```

**2. Adding New Router**:
```bash
# 1. Create router file
touch app/api/routers/new_feature_router.py

# 2. Implement router following patterns above

# 3. Register router in main.py
# Add: from api.routers.new_feature_router import router as new_feature_router
# Add: app.include_router(new_feature_router, prefix="/api/v1/new-feature", tags=["New Feature"])

# 4. Test router
curl http://localhost:8000/api/v1/new-feature/test
```

**3. Running Tests**:
```bash
# Run all tests
docker-compose run --rm api pytest

# Run specific test file
docker-compose run --rm api pytest tests/test_user_service.py

# Run with coverage
docker-compose run --rm api pytest --cov=shared --cov-report=html

# Run integration tests
docker-compose run --rm api pytest tests/integration/
```

---

## 🔄 Worker Development Guide

### Celery Task Development

**Task Pattern**:
```python
# app/worker/tasks/example_tasks.py
from celery import current_app
from shared.services.document_service import DocumentService
from shared.database.models import Document
from shared.utils.database_setup import get_db
import logging

logger = logging.getLogger(__name__)

@current_app.task(bind=True, max_retries=3)
def process_document(self, document_id: str, user_id: str, file_path: str):
    """Process uploaded document with retry logic."""
    try:
        db = next(get_db())
        doc_service = DocumentService(db)
        
        # Update document status
        document = doc_service.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        document.status = "processing"
        db.commit()
        
        # Process document (example)
        result = process_file_content(file_path)
        
        # Store results
        document.metadata = result
        document.status = "completed"
        db.commit()
        
        logger.info(f"Successfully processed document {document_id}")
        return {"status": "success", "document_id": document_id}
        
    except Exception as exc:
        logger.error(f"Error processing document {document_id}: {exc}")
        
        # Update status to failed
        try:
            db = next(get_db())
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = "failed"
                db.commit()
        except Exception as db_exc:
            logger.error(f"Failed to update document status: {db_exc}")
        
        # Retry with exponential backoff
        retry_delay = 60 * (2 ** self.request.retries)  # 60, 120, 240 seconds
        raise self.retry(exc=exc, countdown=retry_delay)

@current_app.task
def cleanup_old_files():
    """Scheduled task for cleanup."""
    import os
    from datetime import datetime, timedelta
    
    # Clean files older than 30 days
    cutoff_date = datetime.now() - timedelta(days=30)
    cleanup_count = 0
    
    for root, dirs, files in os.walk('/app/documents'):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.getmtime(file_path) < cutoff_date.timestamp():
                os.remove(file_path)
                cleanup_count += 1
    
    logger.info(f"Cleaned up {cleanup_count} old files")
    return {"cleaned_files": cleanup_count}

def process_file_content(file_path: str) -> dict:
    """Helper function for file processing."""
    # Implement file processing logic
    return {"processed_at": datetime.now().isoformat(), "size": os.path.getsize(file_path)}
```

**Task Registration**:
```python
# app/worker/celery_app.py
from celery import Celery
from shared.utils.config import get_settings

settings = get_settings()

app = Celery(
    'ai_workflow_worker',
    broker=str(settings.REDIS_URL),
    backend=str(settings.REDIS_URL),
    include=['worker.tasks.document_tasks', 'worker.tasks.ai_tasks']
)

# Configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'worker.tasks.document_tasks.*': {'queue': 'documents'},
        'worker.tasks.ai_tasks.*': {'queue': 'ai_processing'},
    }
)

# Periodic tasks
from celery.schedules import crontab
app.conf.beat_schedule = {
    'cleanup-files': {
        'task': 'worker.tasks.document_tasks.cleanup_old_files',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```

### Worker Development Workflow

**1. Adding New Tasks**:
```bash
# 1. Create task file
touch app/worker/tasks/new_feature_tasks.py

# 2. Implement tasks following patterns above

# 3. Register in celery_app.py
# Add to include list: 'worker.tasks.new_feature_tasks'

# 4. Test task
docker-compose run --rm worker celery -A celery_app.app call worker.tasks.new_feature_tasks.test_task
```

**2. Testing Workers**:
```bash
# Start worker in foreground for debugging
docker-compose run --rm worker celery -A celery_app.app worker --loglevel=debug

# Monitor task execution
docker-compose run --rm worker celery -A celery_app.app events

# Check task status
docker-compose exec redis redis-cli llen celery  # Queue length
```

---

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── unit/                  # Unit tests
│   ├── test_services/    # Service layer tests
│   ├── test_models/      # Model tests
│   └── test_utils/       # Utility tests
├── integration/          # Integration tests
│   ├── test_api/        # API endpoint tests
│   ├── test_database/   # Database integration
│   └── test_auth/       # Authentication flow tests
├── e2e/                 # End-to-end tests
│   ├── test_user_flow/  # Complete user workflows
│   └── test_admin_flow/ # Admin workflows
├── fixtures/            # Test data and fixtures
└── conftest.py         # Pytest configuration
```

### Writing Tests

**Unit Test Example**:
```python
# tests/unit/test_services/test_user_service.py
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from shared.services.user_service import UserService
from shared.schemas.user_schemas import UserCreate
from shared.database.models import User

class TestUserService:
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def user_service(self, mock_db):
        return UserService(mock_db)
    
    @pytest.fixture
    def sample_user_data(self):
        return UserCreate(
            email="test@example.com",
            password="testpass123",
            role="user"
        )
    
    async def test_create_user_success(self, user_service, mock_db, sample_user_data):
        # Mock existing user check
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock password hashing
        with patch('shared.services.user_service.get_password_hash') as mock_hash:
            mock_hash.return_value = "hashed_password"
            
            # Execute
            result = await user_service.create_user(sample_user_data)
            
            # Verify
            assert mock_db.add.called
            assert mock_db.commit.called
            mock_hash.assert_called_once_with("testpass123")
    
    async def test_create_user_duplicate_email(self, user_service, mock_db, sample_user_data):
        # Mock existing user
        existing_user = User(email="test@example.com")
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="User with this email already exists"):
            await user_service.create_user(sample_user_data)
```

**Integration Test Example**:
```python
# tests/integration/test_api/test_user_endpoints.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.main import app
from shared.utils.database_setup import get_db, get_test_db
from shared.database.models import User

# Override dependency
app.dependency_overrides[get_db] = get_test_db

client = TestClient(app)

class TestUserEndpoints:
    def test_create_user_success(self, test_db: Session):
        user_data = {
            "email": "newuser@example.com",
            "password": "testpass123",
            "role": "user"
        }
        
        response = client.post("/api/v1/users", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "user"
        assert "id" in data
        
        # Verify in database
        user = test_db.query(User).filter(User.email == "newuser@example.com").first()
        assert user is not None
        assert user.is_active is True
    
    def test_get_users_requires_auth(self):
        response = client.get("/api/v1/users")
        assert response.status_code == 401
    
    def test_get_users_with_auth(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/api/v1/users", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
```

**End-to-End Test Example**:
```python
# tests/e2e/test_user_flow/test_registration_login.py
import pytest
from playwright.sync_api import Page

class TestUserRegistrationFlow:
    def test_complete_user_registration_and_login(self, page: Page):
        # Navigate to registration
        page.goto("http://localhost:3000/register")
        
        # Fill registration form
        page.fill('[data-testid="email"]', 'newuser@example.com')
        page.fill('[data-testid="password"]', 'testpass123')
        page.fill('[data-testid="confirm-password"]', 'testpass123')
        
        # Submit registration
        page.click('[data-testid="register-button"]')
        
        # Verify success message
        assert page.locator('[data-testid="success-message"]').is_visible()
        
        # Navigate to login
        page.goto("http://localhost:3000/login")
        
        # Fill login form
        page.fill('[data-testid="email"]', 'newuser@example.com')
        page.fill('[data-testid="password"]', 'testpass123')
        
        # Submit login
        page.click('[data-testid="login-button"]')
        
        # Verify dashboard access
        page.wait_for_url("**/dashboard")
        assert page.locator('[data-testid="user-menu"]').is_visible()
```

### Test Configuration

**pytest.ini**:
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
python_classes = Test*
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=shared
    --cov=api
    --cov-report=term-missing
    --cov-report=html:htmlcov
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    auth: Authentication related tests
```

**conftest.py**:
```python
# tests/conftest.py
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from shared.database.models import Base
from shared.utils.database_setup import get_settings
from api.main import app

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def admin_token():
    # Create admin user and return token
    return "admin_jwt_token_here"

@pytest.fixture
def user_token():
    # Create regular user and return token
    return "user_jwt_token_here"

# Event loop for async tests
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

### Running Tests

```bash
# Run all tests
docker-compose run --rm api pytest

# Run specific test categories
docker-compose run --rm api pytest -m unit
docker-compose run --rm api pytest -m integration
docker-compose run --rm api pytest -m e2e

# Run with coverage
docker-compose run --rm api pytest --cov=shared --cov=api

# Run specific test file
docker-compose run --rm api pytest tests/unit/test_services/test_user_service.py

# Run and stop on first failure
docker-compose run --rm api pytest -x

# Run tests in parallel
docker-compose run --rm api pytest -n auto
```

---

## 📝 Code Style and Standards

### Python Code Style

**Use Black for formatting**:
```bash
# Format code
docker-compose run --rm api black shared/ api/

# Check formatting
docker-compose run --rm api black --check shared/ api/
```

**Use isort for import sorting**:
```bash
# Sort imports
docker-compose run --rm api isort shared/ api/

# Check import sorting
docker-compose run --rm api isort --check-only shared/ api/
```

**Use flake8 for linting**:
```bash
# Lint code
docker-compose run --rm api flake8 shared/ api/
```

**Pre-commit configuration** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3.11
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]
```

### JavaScript/Svelte Code Style

**Use Prettier for formatting**:
```bash
cd app/webui
npm run format        # Format code
npm run format:check  # Check formatting
```

**Use ESLint for linting**:
```bash
cd app/webui
npm run lint         # Lint code
npm run lint:fix     # Fix linting issues
```

**Configuration files**:

**.prettierrc**:
```json
{
  "useTabs": false,
  "singleQuote": true,
  "trailingComma": "es5",
  "printWidth": 100,
  "plugins": ["prettier-plugin-svelte"],
  "overrides": [
    {
      "files": "*.svelte",
      "options": {
        "parser": "svelte"
      }
    }
  ]
}
```

**.eslintrc.cjs**:
```javascript
module.exports = {
  root: true,
  extends: [
    'eslint:recommended',
    '@typescript-eslint/recommended',
    'prettier'
  ],
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint'],
  parserOptions: {
    sourceType: 'module',
    ecmaVersion: 2020
  },
  env: {
    browser: true,
    es2017: true,
    node: true
  },
  overrides: [
    {
      files: ['*.svelte'],
      processor: 'svelte3/svelte3'
    }
  ]
};
```

### Documentation Standards

**Python Docstrings**:
```python
def example_function(param1: str, param2: int = 0) -> dict:
    """
    Brief description of the function.
    
    Longer description if needed. This function does something important
    and here's how it works.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter with default value
    
    Returns:
        Dictionary containing the result with keys:
        - success: Boolean indicating success
        - data: The actual data returned
        - message: Status message
    
    Raises:
        ValueError: If param1 is empty
        TypeError: If param2 is not an integer
        
    Example:
        >>> result = example_function("test", 42)
        >>> print(result["success"])
        True
    """
    if not param1:
        raise ValueError("param1 cannot be empty")
    
    return {"success": True, "data": f"{param1}_{param2}", "message": "OK"}
```

**JavaScript Documentation**:
```javascript
/**
 * API client for communicating with the backend.
 * 
 * @class ApiClient
 * @example
 * const client = new ApiClient();
 * const users = await client.get('/users');
 */
class ApiClient {
  /**
   * Make an authenticated HTTP request.
   * 
   * @param {string} method - HTTP method (GET, POST, etc.)
   * @param {string} endpoint - API endpoint path
   * @param {Object} [data=null] - Request data for POST/PUT requests
   * @returns {Promise<Object>} Response data from API
   * @throws {Error} When request fails or returns error status
   */
  async request(method, endpoint, data = null) {
    // Implementation here
  }
}
```

---

## 🔧 Development Tools and Scripts

### Useful Development Scripts

**Database Reset Script** (`scripts/dev-reset-db.sh`):
```bash
#!/bin/bash
echo "Resetting development database..."

# Stop services
docker-compose down

# Remove database volume
docker volume rm ai-workflow-engine_postgres_data || true

# Start database
docker-compose up -d postgres
sleep 10

# Run migrations
docker-compose run --rm api python -m alembic upgrade head

# Seed development data
docker-compose run --rm api python scripts/seed_dev_data.py

echo "Database reset complete!"
```

**Development Data Seeder** (`scripts/seed_dev_data.py`):
```python
#!/usr/bin/env python
"""Seed development database with test data."""

import asyncio
from shared.utils.database_setup import get_db
from shared.services.user_service import UserService
from shared.schemas.user_schemas import UserCreate

async def seed_data():
    """Create development test data."""
    db = next(get_db())
    user_service = UserService(db)
    
    # Create admin user
    admin_data = UserCreate(
        email="admin@example.com",
        password="admin123",
        role="admin"
    )
    
    admin_user = await user_service.create_user(admin_data)
    print(f"Created admin user: {admin_user.email}")
    
    # Create test users
    for i in range(5):
        user_data = UserCreate(
            email=f"user{i}@example.com",
            password="user123",
            role="user"
        )
        
        user = await user_service.create_user(user_data)
        print(f"Created test user: {user.email}")
    
    print("Development data seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_data())
```

**Code Quality Check Script** (`scripts/check-code-quality.sh`):
```bash
#!/bin/bash
echo "Running code quality checks..."

# Python checks
echo "Checking Python code formatting..."
docker-compose run --rm api black --check shared/ api/ || exit 1

echo "Checking Python import sorting..."
docker-compose run --rm api isort --check-only shared/ api/ || exit 1

echo "Running Python linting..."
docker-compose run --rm api flake8 shared/ api/ || exit 1

echo "Running Python type checking..."
docker-compose run --rm api mypy shared/ api/ || exit 1

# JavaScript checks
echo "Checking JavaScript/Svelte formatting..."
cd app/webui && npm run format:check || exit 1

echo "Running JavaScript/Svelte linting..."
cd app/webui && npm run lint || exit 1

# Test checks
echo "Running unit tests..."
docker-compose run --rm api pytest tests/unit/ || exit 1

echo "All code quality checks passed!"
```

### IDE Configuration

**VS Code Settings** (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "files.associations": {
    "*.svelte": "svelte"
  },
  "svelte.enable-ts-plugin": true
}
```

**VS Code Extensions** (`.vscode/extensions.json`):
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.flake8",
    "ms-python.black-formatter",
    "ms-python.isort",
    "ms-python.mypy-type-checker",
    "svelte.svelte-vscode",
    "bradlc.vscode-tailwindcss",
    "ms-vscode.vscode-json",
    "redhat.vscode-yaml",
    "ms-vscode-remote.remote-containers"
  ]
}
```

---

## 🚀 Contributing Guidelines

### Branch Strategy

**Main Branches**:
- `main` - Production-ready code
- `develop` - Integration branch for features

**Feature Branches**:
- `feature/feature-name` - New features
- `bugfix/bug-description` - Bug fixes
- `hotfix/critical-fix` - Critical production fixes

### Contribution Workflow

**1. Fork and Clone**:
```bash
# Fork repository on GitHub
# Clone your fork
git clone https://github.com/yourusername/ai-workflow-engine.git
cd ai-workflow-engine

# Add upstream remote
git remote add upstream https://github.com/original-org/ai-workflow-engine.git
```

**2. Create Feature Branch**:
```bash
# Update local main
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

**3. Develop and Test**:
```bash
# Make your changes
# Add tests for new functionality
# Run tests to ensure nothing breaks
docker-compose run --rm api pytest

# Check code quality
./scripts/check-code-quality.sh
```

**4. Commit and Push**:
```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add user profile management

- Add user profile update endpoint
- Implement profile image upload
- Add profile validation tests
- Update API documentation"

# Push to your fork
git push origin feature/your-feature-name
```

**5. Create Pull Request**:
- Open PR from your feature branch to upstream `develop`
- Fill out PR template completely
- Request review from maintainers
- Address feedback and update PR

### Commit Message Format

Use conventional commits:
```
type(scope): description

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding/fixing tests
- `chore`: Maintenance tasks

**Examples**:
```bash
feat(api): add user authentication endpoints
fix(webui): resolve login form validation issues
docs(readme): update setup instructions
test(auth): add integration tests for JWT flow
```

### Pull Request Guidelines

**PR Title**: Use conventional commit format

**PR Description Template**:
```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No breaking changes (or marked as such)

## Screenshots (if applicable)
Add screenshots for UI changes.
```

**Review Process**:
1. Automated checks must pass (CI/CD)
2. Code review by at least one maintainer
3. All feedback addressed
4. Approved and merged by maintainer

---

## 🔍 Debugging and Troubleshooting

### Common Development Issues

**1. Import Errors**:
```bash
# Problem: ModuleNotFoundError
# Solution: Ensure using 'from shared.' pattern
# ❌ Wrong: from database.models import User
# ✅ Correct: from shared.database.models import User
```

**2. Database Connection Issues**:
```bash
# Check database container
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U aiworkflow -d ai_workflow_engine

# Reset database if needed
./scripts/dev-reset-db.sh
```

**3. WebUI Not Loading**:
```bash
# Check WebUI container
docker-compose ps webui

# Check WebUI logs
docker-compose logs webui

# Restart frontend development server
cd app/webui && npm run dev
```

**4. Worker Tasks Not Processing**:
```bash
# Check worker container
docker-compose ps worker

# Check worker logs
docker-compose logs worker

# Check Redis connection
docker-compose exec redis redis-cli ping

# Monitor task queue
docker-compose exec redis redis-cli monitor
```

### Debugging Tools

**Python Debugging**:
```python
# Add to code for debugging
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()

# Debug with Docker
docker-compose run --rm -p 5678:5678 api python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**JavaScript Debugging**:
```javascript
// Browser debugging
console.log('Debug info:', variable);
debugger;  // Browser will pause here

// VS Code debugging for Node.js
// Add to .vscode/launch.json
{
  "type": "node",
  "request": "launch",
  "name": "Debug SvelteKit",
  "program": "${workspaceFolder}/app/webui/node_modules/@sveltejs/kit/src/cli.js",
  "args": ["dev"],
  "cwd": "${workspaceFolder}/app/webui"
}
```

**Database Debugging**:
```bash
# Connect to database
docker-compose exec postgres psql -U aiworkflow -d ai_workflow_engine

# Common queries
\dt                              # List tables
\d users                         # Describe users table
SELECT * FROM users LIMIT 5;    # Sample data

# Query performance
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';
```

### Performance Debugging

**Python Profiling**:
```python
# Add profiling decorator
import cProfile
import io
import pstats

def profile_function(func):
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        result = func(*args, **kwargs)
        pr.disable()
        
        # Print stats
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        print(s.getvalue())
        
        return result
    return wrapper

@profile_function
def slow_function():
    # Your code here
    pass
```

**Database Performance**:
```sql
-- Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- 1 second
SELECT pg_reload_conf();

-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
WHERE mean_time > 1000 
ORDER BY mean_time DESC;
```

**Frontend Performance**:
```javascript
// Performance monitoring
const start = performance.now();
await someAsyncOperation();
const end = performance.now();
console.log(`Operation took ${end - start} milliseconds`);

// Bundle analysis
npm run build
npm run analyze  // If configured
```

---

## 🎓 Learning Resources

### Required Reading

**Before Contributing**:
1. **AIASSIST.md** - System architecture and patterns
2. **API_DOCUMENTATION.md** - Complete API reference
3. **SYSTEM_ARCHITECTURE.md** - Service interactions

**Python/FastAPI Resources**:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
- [Celery Documentation](https://docs.celeryproject.org/)

**Frontend Resources**:
- [SvelteKit Documentation](https://kit.svelte.dev/)
- [Svelte Tutorial](https://svelte.dev/tutorial)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

**Docker Resources**:
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

### Internal Documentation

**Architecture Guides**:
- `docs/SYSTEM_ARCHITECTURE.md` - Complete system overview
- `docs/API_DOCUMENTATION.md` - API reference
- `docs/USER_AUTHENTICATION_GUIDE.md` - Authentication flows

**Operational Guides**:
- `docs/OPERATIONAL_RUNBOOKS.md` - Deployment and maintenance
- `docs/TESTING_ISSUES_COMPILATION.md` - Known issues and fixes

### Community Resources

**Getting Help**:
1. Check existing documentation first
2. Search GitHub issues
3. Ask in development chat/forum
4. Create GitHub issue with details

**Best Practices**:
1. Write tests for new code
2. Follow existing code patterns
3. Document complex logic
4. Keep commits atomic and descriptive
5. Review your own PRs before submitting

---

This comprehensive developer knowledge base provides everything needed to contribute effectively to the AI Workflow Engine project. Remember to always check the latest documentation and follow the established patterns for consistency and maintainability.