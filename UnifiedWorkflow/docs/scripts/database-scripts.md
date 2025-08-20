# Database Scripts Documentation

Database scripts handle migrations, user management, and data operations for the AI Workflow Engine's PostgreSQL database with security context integration.

## Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `_generate_migration.sh` | Generate Alembic migrations | `./scripts/_generate_migration.sh "message"` |
| `_generate_migration_with_password.sh` | Migration with password | `./scripts/_generate_migration_with_password.sh "message"` |
| `run_migrations.py` | Apply database migrations | `python ./scripts/run_migrations.py` |
| `migrate_check.py` | Check migration status | `python ./scripts/migrate_check.py` |
| `create_admin.sh` | Create admin user | `./scripts/create_admin.sh` |
| `create_admin_clean.sh` | Clean admin creation | `./scripts/create_admin_clean.sh` |
| `seed_initial_data.py` | Seed database with data | `python ./scripts/seed_initial_data.py` |
| `populate_system_prompts.py` | Load system prompts | `python ./scripts/populate_system_prompts.py` |
| `convert_user_passwords.py` | Convert password hashes | `python ./scripts/convert_user_passwords.py` |
| `migrate_user_passwords.py` | Migrate user passwords | `python ./scripts/migrate_user_passwords.py` |
| `migrate_user_passwords.sh` | Password migration wrapper | `./scripts/migrate_user_passwords.sh` |
| `fix_database_users.sh` | Fix user database issues | `./scripts/fix_database_users.sh` |

---

## scripts/_generate_migration.sh

**Location:** `/scripts/_generate_migration.sh`  
**Purpose:** Generate new Alembic database migration files for schema changes.

### Description
The primary script for creating database migrations. It ensures the API service is healthy before generating migrations and uses proper database credentials from secrets.

### Usage
```bash
./scripts/_generate_migration.sh "Migration message"
```

### Examples
```bash
# Add new table
./scripts/_generate_migration.sh "Add user_sessions table"

# Modify existing table
./scripts/_generate_migration.sh "Add email_verified column to users"

# Index optimization
./scripts/_generate_migration.sh "Add index on users.email"

# Security enhancement
./scripts/_generate_migration.sh "Add audit_log table"
```

### What It Does
1. **Service Health Check:** Ensures API service is running and healthy
2. **Database Connection:** Establishes secure connection to PostgreSQL
3. **Migration Generation:** Runs `alembic revision --autogenerate`
4. **Validation:** Verifies migration file was created successfully

### Prerequisites
- API service must be running and healthy
- Database must be accessible
- Alembic configuration must be valid
- Model changes must be present in the codebase

### Process Flow
```bash
# 1. Start required services
docker compose up -d --no-deps api pgbouncer postgres redis qdrant

# 2. Wait for API service health check
# Timeout: 120 seconds, Check interval: 5 seconds

# 3. Generate migration
docker compose exec -e DATABASE_URL=$DB_URL api alembic revision --autogenerate -m "message"

# 4. Validate success
```

### Output
```
INFO: Ensuring api and database services are running...
INFO: Waiting for the 'api' service to be healthy...
SUCCESS: ✅ Service 'api' is healthy.
INFO: Generating Alembic migration: "Add new feature"
SUCCESS: ✅ Successfully created new migration file.
```

### Troubleshooting
- **"Service unhealthy"**: Check API service logs with `docker compose logs api`
- **"Database connection failed"**: Verify database credentials in secrets
- **"No changes detected"**: Ensure model changes are imported properly
- **"Migration failed"**: Check Alembic configuration and database schema

---

## scripts/_generate_migration_with_password.sh

**Location:** `/scripts/_generate_migration_with_password.sh`  
**Purpose:** Alternative migration generation with explicit password handling.

### Description
Similar to the main migration script but with additional password validation and security checks.

### Usage
```bash
./scripts/_generate_migration_with_password.sh "Migration message"
```

### Features
- Enhanced password validation
- Additional security checks
- Alternative credential handling
- Backup generation before migration

---

## scripts/run_migrations.py

**Location:** `/scripts/run_migrations.py`  
**Purpose:** Python script for applying database migrations programmatically.

### Description
Runs Alembic migrations directly from Python with proper error handling and logging.

### Usage
```bash
python ./scripts/run_migrations.py
```

### Features
```python
# Key functionality
- Automatic database connection management
- Transaction safety
- Migration rollback on failure
- Detailed logging and error reporting
- Integration with application settings
```

### When to Use
- Automated deployment scripts
- Container initialization
- CI/CD pipelines
- Programmatic migration control

---

## scripts/migrate_check.py

**Location:** `/scripts/migrate_check.py`  
**Purpose:** Check the current migration status and identify pending migrations.

### Description
Provides detailed information about database schema version, pending migrations, and migration history.

### Usage
```bash
python ./scripts/migrate_check.py
```

### Output
```
Current database revision: abc123def456
Pending migrations: 2
- revision_1: Add user preferences table
- revision_2: Update user roles enum

Migration history:
✅ initial_migration (2024-01-01)
✅ add_user_table (2024-01-15)
✅ add_auth_system (2024-02-01)
⏳ add_preferences (pending)
⏳ update_roles (pending)
```

---

## scripts/create_admin.sh

**Location:** `/scripts/create_admin.sh`  
**Purpose:** Create the initial admin user account with modern password hashing.

### Description
Creates or updates the admin user account using modern pwdlib password hashing (Argon2id) and ensures proper role assignment.

### Usage
```bash
./scripts/create_admin.sh
```

### What It Does
1. **Secret Loading:** Loads admin credentials from secrets
2. **Database Connection:** Establishes secure PostgreSQL connection
3. **User Check:** Determines if admin user exists
4. **Password Migration:** Updates old bcrypt hashes to pwdlib format
5. **Role Assignment:** Ensures admin role is properly set
6. **Validation:** Confirms successful creation/update

### Password Security
- **Modern Hashing:** Uses pwdlib with Argon2id algorithm
- **Migration Support:** Automatically migrates from old bcrypt hashes  
- **Security Standards:** Follows OWASP password storage guidelines
- **Validation:** Comprehensive password strength validation

### Configuration
Admin credentials are loaded from:
- `secrets/admin_email.txt` - Admin email address
- `secrets/admin_password.txt` - Admin password

### Process
```bash
# 1. Wait for PostgreSQL availability
until PGPASSWORD=$POSTGRES_PASSWORD psql ... -c '\q'; do
  sleep 1
done

# 2. Run Python admin creation script with modern password hashing
python -c "
# Modern password hashing implementation
from pwdlib import PasswordHash
pwd_hasher = PasswordHash.recommended()  # Uses Argon2id

# User creation/update logic with security context
create_admin_user(session, email, password)
"
```

### Output
```
--- create_admin.sh: Script starting ---
--- create_admin.sh: Exporting secrets ---
--- create_admin.sh: Waiting for PostgreSQL ---
--- create_admin.sh: PostgreSQL is available ---
INFO: Creating new admin user: admin@example.com
INFO: Admin user created successfully: admin@example.com
--- create_admin.sh: Script finished ---
```

---

## scripts/create_admin_clean.sh

**Location:** `/scripts/create_admin_clean.sh`  
**Purpose:** Clean admin user creation without legacy compatibility.

### Description
Streamlined admin creation script for fresh installations without backward compatibility concerns.

### Usage
```bash
./scripts/create_admin_clean.sh
```

### Features
- No legacy password migration
- Simplified logic flow
- Faster execution
- Clean database assumptions

---

## scripts/seed_initial_data.py

**Location:** `/scripts/seed_initial_data.py`  
**Purpose:** Populate database with initial data and default configurations.

### Description
Seeds the database with essential data including default roles, permissions, system settings, and sample content.

### Usage
```bash
python ./scripts/seed_initial_data.py
```

### Data Seeded
- **User Roles:** admin, user, moderator
- **Permissions:** CRUD operations, system access
- **System Settings:** Default configurations
- **Sample Data:** Example conversations, templates
- **Security Policies:** Default security rules

### Features
```python
# Example seeding logic
def seed_roles():
    roles = ['admin', 'user', 'moderator']
    for role_name in roles:
        if not session.query(Role).filter_by(name=role_name).first():
            role = Role(name=role_name, description=f"{role_name} role")
            session.add(role)

def seed_permissions():
    permissions = [
        ('users.create', 'Create users'),
        ('users.read', 'Read user data'),
        ('users.update', 'Update users'),
        ('users.delete', 'Delete users')
    ]
    # Implementation...
```

---

## Password Migration Scripts

### convert_user_passwords.py
**Purpose:** Convert user passwords from old format to new pwdlib format.

### migrate_user_passwords.py
**Purpose:** Batch migration of user passwords with validation.

### migrate_user_passwords.sh
**Purpose:** Shell wrapper for password migration with proper service coordination.

### Migration Process
1. **Backup:** Create database backup before migration
2. **Validation:** Verify old password hashes
3. **Conversion:** Convert to new pwdlib format
4. **Testing:** Validate new hashes work correctly
5. **Cleanup:** Remove old hash data if successful

---

## Database Management Workflows

### Development Workflow
```bash
# 1. Make model changes in code
# Edit app/shared/database/models/*.py

# 2. Generate migration
./scripts/_generate_migration.sh "Add new feature"

# 3. Review generated migration
# Check migrations/versions/latest_migration.py

# 4. Apply migration (handled by container startup)
./run.sh --soft-reset
```

### Production Deployment
```bash
# 1. Generate migration in development
./scripts/_generate_migration.sh "Production feature"

# 2. Test migration
python ./scripts/migrate_check.py

# 3. Apply in production
python ./scripts/run_migrations.py

# 4. Verify success
python ./scripts/migrate_check.py
```

### User Management
```bash
# Create initial admin
./scripts/create_admin.sh

# Migrate password hashes
./scripts/migrate_user_passwords.sh

# Seed initial data
python ./scripts/seed_initial_data.py

# Populate system prompts
python ./scripts/populate_system_prompts.py
```

---

## Database Security Integration

### Security Context
All database operations use the security audit service:
```python
from shared.services.security_audit_service import security_audit_service

# Set security context before database operations
await security_audit_service.set_security_context(
    session=session, 
    user_id=user_id, 
    service_name="migration"
)
```

### Secure Connections
- **mTLS:** Mutual TLS authentication for database connections
- **Certificate Validation:** Full certificate chain validation
- **Connection Pooling:** Secure connection pooling via PgBouncer
- **Credential Management:** Secrets-based credential storage

### Audit Logging
All database changes are audited:
- Migration execution logs
- User creation/modification logs
- Password change audits
- Schema change tracking

---

## Common Issues and Solutions

### Migration Generation Issues
```bash
# No changes detected
# Solution: Ensure model imports are correct
python -c "from shared.database.models import *"

# Service unhealthy
# Solution: Check service logs and restart
docker compose logs api
docker compose restart api
```

### Database Connection Issues
```bash
# Connection refused
# Solution: Verify database is running
docker compose ps postgres

# Authentication failed
# Solution: Check secrets
cat secrets/postgres_password.txt
```

### Migration Application Issues
```bash
# Migration conflict
# Solution: Resolve manually or regenerate
alembic merge <revision1> <revision2>

# Schema mismatch
# Solution: Reset database schema
./run.sh --reset
```

### User Creation Issues
```bash
# Admin user exists but wrong role
# Solution: Run create_admin.sh again (handles updates)
./scripts/create_admin.sh

# Password hash migration needed
# Solution: Run password migration
./scripts/migrate_user_passwords.sh
```

---

## Best Practices

### Migration Best Practices
1. **Descriptive Messages:** Use clear, descriptive migration messages
2. **Review Generated Code:** Always review auto-generated migrations
3. **Test Migrations:** Test migrations in development first
4. **Backup Strategy:** Backup database before major migrations
5. **Rollback Plan:** Have rollback strategy for failed migrations

### Security Best Practices
1. **Secure Connections:** Always use mTLS for database connections
2. **Secret Management:** Store credentials in secrets, not code
3. **Audit Logging:** Log all database changes for security
4. **Access Control:** Use principle of least privilege
5. **Password Security:** Use modern password hashing algorithms

### Development Best Practices
1. **Model Changes:** Make incremental, logical model changes
2. **Testing:** Test database operations thoroughly
3. **Documentation:** Document complex migrations
4. **Validation:** Validate data integrity after migrations
5. **Monitoring:** Monitor migration performance and success

---

*For database schema details and advanced operations, see the [Database Guide](../database.md).*