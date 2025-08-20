# AI Workflow Engine Database Documentation

**Last Updated:** August 2, 2025  
**Database System:** PostgreSQL  
**Connection Pooling:** PgBouncer  
**Migration Tool:** Alembic  

## Overview

This document provides comprehensive documentation of all database schemas, relationships, and data persistence patterns in the AI Workflow Engine. The system uses PostgreSQL as the primary database with PgBouncer for connection pooling.

## Database Architecture

### Core Services
- **postgres**: Primary PostgreSQL database
- **pgbouncer**: Connection pooling service
- **api-migrate**: Alembic migration service (startup only)
- **api**: FastAPI application (connects via pgbouncer)
- **worker**: Celery background service (connects via pgbouncer)

### Database Access Patterns
- **Application Services**: Connect via pgbouncer (port 6432)
- **Migrations**: Connect directly to postgres (port 5432)
- **Connection Details**: Username: `app_user`, Database: `ai_workflow_db`

## Database Schema

### User Management Tables

#### users
**Primary Key:** `id` (Integer, Auto-increment)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, AUTOINCREMENT | Unique user identifier |
| email | String | UNIQUE, NOT NULL, INDEXED | User email address |
| hashed_password | String | NOT NULL | Bcrypt hashed password |
| is_active | Boolean | NOT NULL, DEFAULT TRUE | User account status |
| is_superuser | Boolean | NOT NULL, DEFAULT FALSE | Admin privileges |
| is_verified | Boolean | NOT NULL, DEFAULT FALSE | Email verification status |
| role | UserRole | NOT NULL, DEFAULT 'user' | User role (admin/user) |
| status | UserStatus | NOT NULL, DEFAULT 'pending_approval' | Account status |
| tfa_enabled | Boolean | DEFAULT FALSE | Two-factor authentication enabled |
| tfa_secret | String | NULLABLE | TOTP secret for 2FA |
| created_at | DateTime | NOT NULL, DEFAULT NOW() | Account creation timestamp |
| updated_at | DateTime | NULLABLE, ON UPDATE NOW() | Last update timestamp |

**User Settings Columns:**
| Column | Type | Default | Description |
|--------|------|---------|-------------|
| theme | String | 'dark' | UI theme preference |
| notifications_enabled | Boolean | TRUE | Notification settings |
| selected_model | String | 'llama3.2:3b' | Default AI model |
| timezone | String | 'UTC' | User timezone |
| chat_model | String | 'llama3.2:3b' | Chat model preference |
| initial_assessment_model | String | 'llama3.2:3b' | Assessment model |
| tool_selection_model | String | 'llama3.2:3b' | Tool selection model |
| embeddings_model | String | 'llama3.2:3b' | Embeddings model |
| coding_model | String | 'llama3.2:3b' | Coding assistance model |

**Granular Node-Specific Models:**
| Column | Type | Default | Description |
|--------|------|---------|-------------|
| executive_assessment_model | String | 'llama3.2:3b' | Executive assessment |
| confidence_assessment_model | String | 'llama3.2:3b' | Confidence scoring |
| tool_routing_model | String | 'llama3.2:3b' | Tool routing decisions |
| simple_planning_model | String | 'llama3.2:3b' | Simple planning tasks |
| wave_function_specialist_model | String | 'llama3.2:1b' | Wave function analysis |
| wave_function_refinement_model | String | 'llama3.1:8b' | Wave function refinement |
| plan_validation_model | String | 'llama3.2:3b' | Plan validation |
| plan_comparison_model | String | 'llama3.2:3b' | Plan comparison |
| reflection_model | String | 'llama3.2:3b' | Reflection and analysis |
| final_response_model | String | 'llama3.2:3b' | Final response generation |
| fast_conversational_model | String | 'llama3.2:1b' | Fast conversational responses |

**Enhanced Profile Columns (JSONB):**
| Column | Type | Description |
|--------|------|-------------|
| calendar_event_weights | JSONB | Event category weights |
| agent_settings | JSONB | Agent configuration |
| personal_goals | JSONB | User's personal goals |
| work_style_preferences | JSONB | Work style settings |
| productivity_patterns | JSONB | Productivity insights |
| interview_insights | JSONB | AI interview results |
| project_preferences | JSONB | Project preferences |
| default_code_style | JSONB | Coding style preferences |
| git_integrations | JSONB | Git integration settings |

**Web Search Configuration:**
| Column | Type | Description |
|--------|------|-------------|
| web_search_provider | String | Search provider (tavily/serpapi/disabled) |
| web_search_api_key | String | Encrypted API key |

#### user_profiles
**Primary Key:** `id` (Integer)  
**Foreign Key:** `user_id` → `users.id`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PRIMARY KEY | Profile identifier |
| user_id | Integer | FK users.id, UNIQUE | User reference |
| first_name | String | NULLABLE | First name |
| last_name | String | NULLABLE | Last name |
| display_name | String | NULLABLE | Display name |
| date_of_birth | String | NULLABLE | Birth date |
| phone_number | String | NULLABLE | Primary phone |
| alternate_phone | String | NULLABLE | Secondary phone |
| personal_address | JSONB | NULLABLE | Address information |
| job_title | String | NULLABLE | Job title |
| company | String | NULLABLE | Company name |
| department | String | NULLABLE | Department |
| work_phone | String | NULLABLE | Work phone |
| work_email | String | NULLABLE | Work email |
| work_address | JSONB | NULLABLE | Work address |
| preferred_contact_method | String | NULLABLE | Contact preference |
| emergency_contact | JSONB | NULLABLE | Emergency contact |
| bio | Text | NULLABLE | Biography |
| website | String | NULLABLE | Personal website |
| linkedin | String | NULLABLE | LinkedIn profile |
| twitter | String | NULLABLE | Twitter handle |
| github | String | NULLABLE | GitHub username |
| timezone | String | NULLABLE | Timezone preference |
| language | String | NULLABLE | Language preference |
| created_at | DateTime | NOT NULL | Creation timestamp |
| updated_at | DateTime | NOT NULL | Update timestamp |

### Authentication & Security Tables

#### registered_devices
**Primary Key:** `id` (UUID)  
**Foreign Key:** `user_id` → `users.id`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Device identifier |
| user_id | Integer | FK users.id, INDEXED | User reference |
| device_name | String | NOT NULL | Device name |
| device_type | String | NOT NULL | Device type |
| user_agent | String | NULLABLE | Browser user agent |
| ip_address | String | NULLABLE | IP address |
| last_used_at | DateTime | NULLABLE | Last access time |
| is_trusted | Boolean | DEFAULT FALSE | Trusted device flag |
| created_at | DateTime | NOT NULL | Registration timestamp |

#### user_two_factor_auth
**Primary Key:** `id` (UUID)  
**Foreign Key:** `user_id` → `users.id`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | 2FA identifier |
| user_id | Integer | FK users.id, UNIQUE | User reference |
| is_enabled | Boolean | DEFAULT FALSE | 2FA enabled status |
| secret_key | String | NULLABLE | TOTP secret key |
| backup_codes | JSONB | NULLABLE | Backup codes array |
| last_used_at | DateTime | NULLABLE | Last TOTP use |
| created_at | DateTime | NOT NULL | Setup timestamp |
| updated_at | DateTime | NOT NULL | Update timestamp |

#### passkey_credentials
**Primary Key:** `id` (UUID)  
**Foreign Key:** `user_id` → `users.id`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Credential identifier |
| user_id | Integer | FK users.id, INDEXED | User reference |
| credential_id | String | UNIQUE, NOT NULL | WebAuthn credential ID |
| public_key | String | NOT NULL | Public key data |
| credential_name | String | NULLABLE | User-defined name |
| last_used_at | DateTime | NULLABLE | Last use timestamp |
| created_at | DateTime | NOT NULL | Registration timestamp |

### Chat & Conversation Tables

#### chat_history
**Primary Key:** `id` (Integer)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PRIMARY KEY | Message identifier |
| session_id | String | INDEXED, NOT NULL | Session identifier |
| message | JSONB | NOT NULL | Message data |
| created_at | DateTime | NOT NULL | Message timestamp |

**Message JSONB Structure:**
```json
{
  "role": "user|assistant|system",
  "content": "message text",
  "metadata": {
    "mode": "simple|expert-group|smart-router|socratic",
    "agent_name": "agent name",
    "agent_type": "type",
    "tools_used": ["tool1", "tool2"],
    "confidence_score": 0.95
  }
}
```

#### session_state
**Primary Key:** `session_id` (String)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| session_id | String | PRIMARY KEY | Session identifier |
| state | JSONB | NOT NULL | Session state data |
| updated_at | DateTime | NOT NULL, ON UPDATE | Last update |

**State JSONB Structure:**
```json
{
  "mode": "chat_mode",
  "context": {},
  "expert_selections": ["expert1", "expert2"],
  "interview_type": "assessment_type",
  "workflow_state": {},
  "todo_list": [],
  "meeting_state": {}
}
```

#### chat_messages
**Primary Key:** `id` (UUID)  
**Foreign Key:** `user_id` → `users.id`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Message identifier |
| session_id | String | INDEXED, NOT NULL | Session reference |
| user_id | Integer | FK users.id, INDEXED | User reference |
| message_type | String | NOT NULL | Message type (human/ai/system) |
| content | Text | NOT NULL | Message content |
| message_order | Integer | NOT NULL | Order within session |
| conversation_domain | String | NULLABLE | Domain classification |
| tool_used | String | NULLABLE | Tool used |
| plan_step | Integer | NULLABLE | Plan step number |
| confidence_score | Float | NULLABLE | AI confidence |
| qdrant_point_id | String | NULLABLE, INDEXED | Vector DB reference |
| embedding_model_used | String | NULLABLE | Embedding model |
| created_at | DateTime | NOT NULL | Creation timestamp |

#### chat_session_summaries
**Primary Key:** `id` (UUID)  
**Foreign Key:** `user_id` → `users.id`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Summary identifier |
| session_id | String | UNIQUE, INDEXED | Session reference |
| user_id | Integer | FK users.id, INDEXED | User reference |
| started_at | DateTime | NOT NULL | Session start time |
| ended_at | DateTime | NOT NULL | Session end time |
| message_count | Integer | NOT NULL | Total messages |
| total_tokens_used | Integer | NULLABLE | Token usage |
| conversation_domain | String | NULLABLE | Domain classification |
| summary | Text | NOT NULL | Session summary |
| key_topics | JSONB | NOT NULL | Topic list |
| decisions_made | JSONB | NOT NULL | Decision list |
| user_preferences | JSONB | NOT NULL | Extracted preferences |
| tools_used | JSONB | NOT NULL | Tools used list |
| plans_created | Integer | DEFAULT 0 | Number of plans |
| expert_questions_asked | Integer | DEFAULT 0 | Expert questions count |
| session_rating | Float | NULLABLE | User rating |
| complexity_level | String | DEFAULT 'medium' | Complexity level |
| resolution_status | String | DEFAULT 'completed' | Resolution status |
| search_keywords | JSONB | NOT NULL | Search keywords |
| follow_up_suggested | Boolean | DEFAULT FALSE | Follow-up needed |
| follow_up_tasks | JSONB | NOT NULL | Follow-up tasks |
| created_at | DateTime | NOT NULL | Creation timestamp |
| updated_at | DateTime | NOT NULL | Update timestamp |

### Expert Group Data Persistence

#### Expert Selection Storage
Expert selections are stored in multiple ways:

1. **Client-side (localStorage)**: Browser storage for immediate UI state
2. **Session State**: Database persistence via `session_state` table
3. **Chat History**: Message metadata includes expert selections

**Expert Selection Flow:**
```javascript
// Frontend storage
localStorage.setItem('expertSelections', JSON.stringify(selectedExperts));

// API request context
context: {
  selected_agents: ["technical_expert", "business_analyst"],
  enabled_experts: ["expert1", "expert2"] // Legacy format
}

// Database persistence in session_state
{
  "expert_selections": ["technical_expert", "business_analyst"],
  "meeting_state": {
    "pm_question": "...",
    "experts": {},
    "todo_list": [],
    "summary": null,
    "is_complete": false
  }
}
```

#### Expert Group Message Structure
Expert group conversations are stored with specific metadata:

```json
{
  "role": "assistant",
  "content": "expert response",
  "metadata": {
    "type": "expert_response|pm_question|meeting_start|meeting_summary",
    "expert_name": "Technical Expert",
    "agent_type": "expert_group",
    "phase": "questioning|expert_input|planning|execution|summary",
    "confidence": 0.85,
    "todo_list": [],
    "workflow_type": "langgraph_expert_group"
  }
}
```

### OAuth & External Services

#### user_oauth_tokens
**Primary Key:** `id` (Integer)  
**Foreign Key:** `user_id` → `users.id`  
**Unique Constraint:** `(user_id, service)`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PRIMARY KEY | Token identifier |
| user_id | Integer | FK users.id, INDEXED | User reference |
| service | GoogleService | NOT NULL | Service type |
| access_token | Text | NOT NULL | OAuth access token |
| refresh_token | Text | NULLABLE | OAuth refresh token |
| token_expiry | DateTime | NULLABLE | Token expiration |
| scope | Text | NULLABLE | OAuth scopes |
| service_user_id | String | NULLABLE | Google user ID |
| service_email | String | NULLABLE | Connected email |
| created_at | DateTime | NOT NULL | Creation timestamp |
| updated_at | DateTime | NOT NULL | Update timestamp |

### Document Management

#### documents
**Primary Key:** `id` (UUID)  
**Foreign Key:** `user_id` → `users.id`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Document identifier |
| filename | String | NOT NULL | Original filename |
| user_id | Integer | FK users.id, INDEXED | Owner reference |
| created_at | DateTime | NOT NULL | Upload timestamp |
| status | DocumentStatus | NOT NULL | Processing status |

#### document_chunks
**Primary Key:** `id` (UUID)  
**Foreign Key:** `document_id` → `documents.id`  
**Unique Constraint:** `(document_id, chunk_index)`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Chunk identifier |
| document_id | UUID | FK documents.id, INDEXED | Document reference |
| chunk_index | Integer | NOT NULL | Chunk order |
| content | Text | NOT NULL | Chunk text |
| vector_id | String | NULLABLE | Qdrant vector ID |
| semantic_keywords | JSONB | NULLABLE | Extracted keywords |
| semantic_category | String | NULLABLE | Category classification |
| semantic_summary | Text | NULLABLE | Chunk summary |
| extracted_entities | JSONB | NULLABLE | Named entities |

### Calendar & Events

#### calendars
**Primary Key:** `id` (Integer)  
**Foreign Key:** `user_id` → `users.id`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PRIMARY KEY | Calendar identifier |
| user_id | Integer | FK users.id, INDEXED | User reference |
| name | String | DEFAULT 'Default Calendar' | Calendar name |
| description | Text | NULLABLE | Calendar description |

#### events
**Primary Key:** `id` (Integer)  
**Foreign Key:** `calendar_id` → `calendars.id`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PRIMARY KEY | Event identifier |
| google_event_id | String | UNIQUE, INDEXED | Google Calendar ID |
| calendar_id | Integer | FK calendars.id, INDEXED | Calendar reference |
| summary | String | NOT NULL | Event title |
| description | Text | NULLABLE | Event description |
| start_time | DateTime | NOT NULL, INDEXED | Start time |
| end_time | DateTime | NOT NULL, INDEXED | End time |
| category | EventCategory | NOT NULL | Event category |
| movability_score | Float | NOT NULL | Flexibility score |
| is_movable | Boolean | NOT NULL | Can be rescheduled |
| semantic_keywords | JSONB | NULLABLE | Keywords |
| semantic_embedding_id | String | NULLABLE | Vector ID |
| semantic_category | String | NULLABLE | AI category |
| semantic_tags | JSONB | NULLABLE | Semantic tags |
| event_type | String | DEFAULT 'meeting' | Event type |
| attendees | JSONB | NULLABLE | Attendee list |
| location | String | NULLABLE | Event location |
| recurrence_rule | String | NULLABLE | Recurrence pattern |
| reminder_minutes | Integer | DEFAULT 15 | Reminder time |
| importance_weight | Float | DEFAULT 1.0 | Importance weight |
| created_at | DateTime | NOT NULL | Creation timestamp |
| updated_at | DateTime | NOT NULL | Update timestamp |

### Task & Project Management

#### projects
**Primary Key:** `id` (UUID)  
**Foreign Key:** `user_id` → `users.id`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Project identifier |
| user_id | Integer | FK users.id, INDEXED | User reference |
| name | String | NOT NULL | Project name |
| description | Text | NULLABLE | Project description |
| project_type | String | NULLABLE | Project type |
| programming_language | String | NULLABLE | Primary language |
| framework | String | NULLABLE | Framework used |
| repository_url | String | NULLABLE | Git repository |
| local_path | String | NULLABLE | Local path |
| status | String | DEFAULT 'active' | Project status |
| project_metadata | JSONB | NULLABLE | Additional metadata |
| created_at | DateTime | NOT NULL | Creation timestamp |
| updated_at | DateTime | NOT NULL | Update timestamp |

#### tasks
**Primary Key:** `id` (UUID)  
**Foreign Keys:** `user_id` → `users.id`, `project_id` → `projects.id`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Task identifier |
| user_id | Integer | FK users.id, INDEXED | User reference |
| project_id | UUID | FK projects.id, INDEXED | Project reference |
| title | String | NOT NULL | Task title |
| description | Text | NULLABLE | Task description |
| status | TaskStatus | NOT NULL | Task status |
| priority | TaskPriority | NOT NULL | Task priority |
| category | String | NULLABLE | Task category |
| due_date | DateTime | NULLABLE | Due date |
| estimated_hours | Float | NULLABLE | Time estimate |
| actual_hours | Float | NULLABLE | Actual time |
| completion_percentage | Integer | DEFAULT 0 | Progress percentage |
| semantic_keywords | JSONB | NULLABLE | Keywords |
| semantic_embedding_id | String | NULLABLE | Vector ID |
| semantic_category | String | NULLABLE | AI category |
| semantic_tags | JSONB | NULLABLE | Semantic tags |
| semantic_summary | Text | NULLABLE | Task summary |
| importance_weight | Float | DEFAULT 1.0 | Importance weight |
| urgency_weight | Float | DEFAULT 1.0 | Urgency weight |
| complexity_weight | Float | DEFAULT 1.0 | Complexity weight |
| user_priority_weight | Float | DEFAULT 1.0 | User priority |
| calculated_score | Float | NULLABLE | Calculated score |
| task_type | TaskType | NOT NULL | Task type |
| programming_language | String | NULLABLE | Language |
| difficulty_level | String | NULLABLE | Difficulty |
| code_context | JSONB | NULLABLE | Code context |
| repository_branch | String | NULLABLE | Git branch |
| created_at | DateTime | NOT NULL | Creation timestamp |
| updated_at | DateTime | NOT NULL | Update timestamp |

**Semantic Tags Structure for Expert Group Tasks:**
```json
{
  "subtasks": [
    {
      "task": "Analyze requirements",
      "assigned_to": "Business Analyst",
      "priority": "High",
      "status": "completed"
    }
  ],
  "expert_assignments": {
    "Technical Expert": ["task1", "task2"],
    "Business Analyst": ["task3"]
  },
  "workflow_metadata": {
    "pm_managed": true,
    "coordination_method": "langgraph"
  }
}
```

### System Configuration

#### system_settings
**Primary Key:** `id` (Integer)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PRIMARY KEY | Setting identifier |
| key | String | UNIQUE, INDEXED | Setting key |
| value | Text | NOT NULL | Setting value |
| description | Text | NULLABLE | Setting description |
| created_at | DateTime | NOT NULL | Creation timestamp |
| updated_at | DateTime | NOT NULL | Update timestamp |

#### system_prompts
**Primary Key:** `id` (UUID)  
**Foreign Key:** `user_id` → `users.id`  
**Unique Constraint:** `(user_id, prompt_key)`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Prompt identifier |
| user_id | Integer | FK users.id, NULLABLE | User override |
| prompt_key | String | INDEXED, NOT NULL | Prompt key |
| prompt_category | String | INDEXED, NOT NULL | Category |
| prompt_name | String | NOT NULL | Human-readable name |
| description | Text | NULLABLE | Prompt description |
| prompt_text | Text | NOT NULL | Prompt content |
| variables | JSONB | NULLABLE | Variable definitions |
| is_factory_default | Boolean | DEFAULT FALSE | Factory default |
| is_active | Boolean | DEFAULT TRUE | Active status |
| version | Integer | DEFAULT 1 | Version number |
| usage_count | Integer | DEFAULT 0 | Usage counter |
| last_used_at | DateTime | NULLABLE | Last use time |
| average_satisfaction | Float | NULLABLE | Satisfaction rating |
| success_rate | Float | NULLABLE | Success rate |
| created_at | DateTime | NOT NULL | Creation timestamp |
| updated_at | DateTime | NOT NULL | Update timestamp |

## Expert Group Chat Data Flow

### 1. Expert Selection Persistence
Expert selections are handled through multiple storage layers:

**Frontend State Management:**
- Component state in `ExpertGroupChat.svelte`
- Parent component manages expert selections
- Real-time UI updates during expert meetings

**Session Persistence:**
- `session_state` table stores active selections
- Chat context includes expert selections
- Session continuity across page refreshes

**Message Metadata:**
- Each expert group message includes expert context
- Workflow type identification
- Phase tracking (questioning → expert_input → planning → execution → summary)

### 2. Streaming Expert Responses
Expert group conversations use real-time streaming:

**Stream Types:**
- `meeting_start`: Initialize expert group session
- `pm_question`: Project Manager questions
- `expert_response`: Individual expert responses
- `todo_update`: Action plan updates
- `meeting_summary`: Final meeting summary
- `stream_complete`: Session completion

**Database Storage:**
- Each stream chunk is stored in `chat_history`
- Metadata includes expert names and phases
- Full conversation reconstructable from database

### 3. State Management Across Requests
Expert group state persistence ensures continuity:

**LangGraph State (ExpertGroupState):**
```python
{
  "session_id": "unique_session_id",
  "user_request": "original request",
  "selected_agents": ["technical_expert", "business_analyst"],
  "pm_questions": {"expert": "question"},
  "expert_inputs": {"expert": {"input": "response"}},
  "todo_list": [{"task": "...", "assigned_to": "..."}],
  "completed_tasks": [{"task": "...", "result": "..."}],
  "final_summary": "summary text",
  "current_phase": "summary",
  "discussion_context": [...]
}
```

**Frontend Meeting State:**
```javascript
{
  pm_question: "PM question text",
  experts: {
    "Technical Expert": { response: "expert response" },
    "Business Analyst": { response: "analyst response" }
  },
  todo_list: ["task1", "task2"],
  summary: "meeting summary",
  is_complete: false
}
```

## Data Integrity & Performance

### Primary Key Strategy
- **Integer PKs**: User-related tables for performance
- **UUID PKs**: Content tables for global uniqueness
- **String PKs**: Session-based tables for external compatibility

### Foreign Key Relationships
All foreign keys maintain referential integrity with CASCADE options where appropriate.

### Indexing Strategy
- **Primary Keys**: Automatic clustered indexes
- **Foreign Keys**: Non-clustered indexes for joins
- **Search Fields**: Composite indexes for chat search
- **Time-based**: DateTime columns for chronological queries

### JSONB Performance
- **GIN Indexes**: On frequently queried JSONB columns
- **Specific Path Queries**: Optimized for semantic_tags searches
- **Expert Metadata**: Fast lookups for expert assignments

### Expert Group Performance Considerations

**Database Queries:**
- Session state retrieval: Single query by session_id
- Expert selection loading: JSONB field access
- Message history: Indexed by session_id and timestamp
- Workflow state: Efficient JSONB operations

**Potential Bottlenecks:**
- Large expert group conversations in single session
- Frequent JSONB updates during streaming
- Complex semantic_tags queries

**Optimization Recommendations:**
1. **Message Pagination**: Implement pagination for long conversations
2. **State Caching**: Cache active expert group states in Redis
3. **Batch Updates**: Batch multiple stream updates
4. **Index Optimization**: Monitor JSONB query patterns

## Migration Management

### Alembic Configuration
- **Auto-generation**: `alembic revision --autogenerate -m "description"`
- **Review Required**: Always manually review generated migrations
- **Startup Application**: `api-migrate` service applies migrations

### Schema Changes
- **Never Direct**: Use Alembic for all schema changes
- **Backward Compatibility**: Consider rollback scenarios
- **Data Migration**: Include data transformation in migrations

## Security Considerations

### Data Protection
- **Password Hashing**: Bcrypt with appropriate rounds
- **Token Encryption**: OAuth tokens encrypted at rest
- **API Key Storage**: Web search keys encrypted
- **Audit Trail**: Creation and update timestamps

### Access Control
- **Row-Level Security**: User-based data isolation
- **Connection Pooling**: Limited database connections
- **Least Privilege**: Application user has minimal permissions

### Expert Group Security
- **Session Isolation**: Expert selections scoped to sessions
- **User Data Separation**: All data tied to user_id
- **Conversation Privacy**: Session data not shared between users

This comprehensive database documentation serves as the authoritative reference for all database operations, relationships, and data persistence patterns in the AI Workflow Engine.