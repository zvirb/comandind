# Backend API Error Investigation - Research Phase Analysis

**Date**: 2025-08-10  
**Scope**: HTTP 500 errors in business logic API endpoints  
**Status**: CRITICAL SCHEMA MISMATCHES IDENTIFIED  

## Critical Issues Discovered

### 1. Missing Database Tables
The following tables referenced in the application code do not exist in the database:

- **`calendars` table**: CRITICAL - Should exist per initial migration `c1f348491f8` but missing
- **`events` table**: CRITICAL - Should exist per initial migration `c1f348491f8` but missing  
- **`audit.security_violations` table**: Missing from audit schema

**Evidence from Logs**:
```
[2025-08-10 21:28:26 UTC] [ERROR] [api] asyncpg.exceptions.UndefinedTableError: relation "calendars" does not exist
[2025-08-10 21:28:26 UTC] [ERROR] [api] relation "audit.security_violations" does not exist at character 13
```

**Impact**: 
- `/api/v1/calendar/events` returns HTTP 500 
- `/api/v1/calendar/sync/auto` fails
- Security audit logging fails across all endpoints

### 2. Enum Value Case Mismatches

#### GoogleService Enum Mismatch
**Database Values**: `calendar`, `drive`, `gmail` (lowercase)  
**Application Code**: `CALENDAR`, `DRIVE`, `GMAIL` (uppercase)  

**Error Pattern**:
```
[2025-08-10 21:27:34 UTC] [ERROR] invalid input value for enum googleservice: "CALENDAR"
```

**Location**: `/home/marku/ai_workflow_engine/app/shared/database/models/_models.py:224`
```python
service: Mapped[GoogleService] = mapped_column(
    SQLAlchemyEnum(GoogleService, native_enum=True, name="googleservice"), 
    nullable=False
)
```

#### TaskStatus Enum Mismatch
**Database Values**: `pending`, `in_progress`, `completed`, `cancelled`, `on_hold` (lowercase)  
**Application Code**: `PENDING`, `IN_PROGRESS`, etc. (attempts to use uppercase)

**Error Pattern**:
```
[2025-08-10 21:28:42 UTC] [ERROR] invalid input value for enum task_status: "PENDING"
```

**Impact**: 
- POST `/api/v1/tasks` returns HTTP 500
- Task creation completely broken

## Database Schema Analysis

### Current Database State
**Migration Version**: `d4e5f6a7b8c9`

**Existing Tables**: ✅
- `users`, `tasks`, `projects`, `user_oauth_tokens`, `user_profiles`, `user_categories`
- `task_feedback`, `system_prompts`, `user_history_summaries`
- `memory_records`, `graph_nodes`, `graph_edges`, `processing_jobs`

**Missing Tables**: ❌
- `calendars` 
- `events`
- `calendars` → `events` relationship broken
- `audit.security_violations` (audit schema exists but table missing)

### Enum Types in Database
```sql
-- Current database enum values (all lowercase)
googleservice: calendar, drive, gmail
task_status: pending, in_progress, completed, cancelled, on_hold  
task_priority: low, medium, high, urgent
task_type: general, coding, review, testing, deployment, meeting, research, opportunity
userrole: admin, user
userstatus: pending_approval, active, disabled
```

## Root Cause Analysis

### 1. Migration State Issues
- Current migration `d4e5f6a7b8c9` is missing critical table definitions
- Calendar-related tables were never created in the database
- Security audit table creation was incomplete

### 2. Enum Value Inconsistency  
- Python enum definitions use UPPERCASE values
- Database enum types use lowercase values
- SQLAlchemy mapping not configured correctly for case sensitivity

### 3. Code vs Schema Drift
**Model Definition** (`_models.py:211-216`):
```python
class GoogleService(str, enum.Enum):
    """Enumeration for Google services that can be connected via OAuth."""
    CALENDAR = "calendar"  # ← Value is lowercase
    DRIVE = "drive"
    GMAIL = "gmail"
```

**But Usage** attempts to pass `"CALENDAR"` instead of `"calendar"`

## API Endpoint Failures

### Calendar API (`/api/v1/calendar/*`)
- **GET `/api/v1/calendar/events`**: HTTP 500 - `UndefinedTableError: relation "calendars" does not exist`
- **POST `/api/v1/calendar/sync/auto`**: HTTP 500 - GoogleService enum mismatch

**Router Location**: `/home/marku/ai_workflow_engine/app/api/routers/calendar_router.py`

### Tasks API (`/api/v1/tasks`)  
- **POST `/api/v1/tasks`**: HTTP 500 - `invalid input value for enum task_status: "PENDING"`
- **PUT `/api/v1/tasks/{task_id}`**: Same enum mismatch issue

**Router Location**: `/home/marku/ai_workflow_engine/app/api/routers/tasks_router.py`

### Security Audit Logging
- **All endpoints**: Security violation logging fails due to missing `audit.security_violations` table
- **Error propagation**: API errors compound because security logging also fails

## Request Flow Analysis

### Failing Request Lifecycle

1. **Request arrives** at API endpoint (e.g., POST `/api/v1/tasks`)
2. **CSRF verification** passes ✅
3. **Authentication** passes ✅  
4. **CRUD operation** begins
5. **Database query** attempts to use enum value
6. **Enum validation fails** ❌ - Case mismatch
7. **Exception thrown** - `InvalidTextRepresentation`
8. **Security logging fails** ❌ - Missing audit table
9. **HTTP 500 returned** to client

### Infrastructure vs Application Layer
- **Infrastructure health**: ✅ All containers running
- **Database connectivity**: ✅ Connection established
- **Authentication**: ✅ JWT validation working
- **Business logic**: ❌ Schema mismatches cause failures

## Impact Assessment

### Broken Functionality
1. **Task Management**: Task creation, updates completely broken
2. **Calendar Integration**: All calendar operations fail
3. **Security Auditing**: No security events being logged
4. **Google OAuth**: Service integration fails on enum mismatch

### User Experience
- **Frontend loads** but cannot create/edit tasks  
- **Calendar view** empty due to API failures
- **No error visibility** to users (generic 500 responses)

## Next Steps Required

### Immediate Actions Needed
1. **Database Migration**: Create missing `calendars` and `events` tables
2. **Audit Schema**: Create missing `audit.security_violations` table  
3. **Enum Consistency**: Fix case mismatches in enum usage
4. **Schema Validation**: Ensure all model definitions match database

### Migration Requirements
```sql
-- Required table creation
CREATE TABLE calendars (...);
CREATE TABLE events (...);  
CREATE TABLE audit.security_violations (...);
```

### Code Fixes Required
1. Fix enum value case handling in CRUD operations
2. Update SQLAlchemy enum mappings to handle case properly  
3. Verify all model-to-database mappings

## Evidence Files
- **Error Logs**: `/home/marku/ai_workflow_engine/logs/runtime_errors.log*`
- **Models**: `/home/marku/ai_workflow_engine/app/shared/database/models/_models.py`
- **API Routers**: `/home/marku/ai_workflow_engine/app/api/routers/tasks_router.py`, `calendar_router.py`
- **Database State**: Migration version `d4e5f6a7b8c9`

## Summary
Infrastructure is healthy but **application layer has critical schema mismatches** causing all business logic APIs to fail with HTTP 500 errors. Immediate database migration and enum consistency fixes required to restore functionality.