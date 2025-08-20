# Infrastructure & Deployment

Comprehensive infrastructure documentation covering deployment, containerization, database setup, and operational procedures.

## 🏢 Infrastructure Overview

The AI Workflow Engine infrastructure is designed for:
- **Containerized Deployment**: Docker-based microservices architecture
- **Security-First**: mTLS encryption and comprehensive security
- **Scalability**: Horizontal scaling and load balancing
- **Reliability**: High availability and fault tolerance
- **Monitoring**: Comprehensive monitoring and alerting

## 📋 Infrastructure Documentation

### [🚀 Deployment Guide](deployment.md)
Complete deployment procedures for all environments:
- Production deployment steps
- Staging environment setup
- Development environment configuration
- Rollback procedures
- Zero-downtime deployment strategies

### [🐳 Docker Configuration](docker.md)
Docker and containerization setup:
- Docker compose configurations
- Container orchestration
- Image management and optimization
- Multi-stage build processes
- Container security hardening

### [🗄️ Database Setup](database.md)
Database infrastructure and configuration:
- PostgreSQL setup and optimization
- Connection pooling configuration
- Backup and recovery procedures
- Performance tuning
- High availability setup

### [🔒 SSL/TLS Configuration](ssl-setup.md)
SSL/TLS and certificate management:
- Certificate generation and management
- mTLS configuration for all services
- SSL termination and proxy setup
- Certificate rotation procedures
- Security validation

## 🐳 Container Architecture

### Docker Compose Configurations

#### Development (mTLS Required)
```bash
# MANDATORY for development
docker-compose -f docker-compose-mtls.yml up
```

#### Production
```bash
# Production deployment
docker-compose -f docker-compose.yml up -d
```

#### Specialized Configurations
- `docker-compose-certs.yaml`: Certificate management
- `docker-compose-mcp.yml`: MCP server integration
- `docker-compose.override-nossl.yml`: Non-SSL override (testing only)

### Service Architecture
- **API Service**: FastAPI application server
- **WebUI Service**: Svelte frontend application
- **Database**: PostgreSQL with pgbouncer connection pooling
- **Cache**: Redis for session and data caching
- **Reverse Proxy**: Caddy for SSL termination and routing
- **Monitoring**: Prometheus for metrics collection

## 🔧 Infrastructure Setup

### Prerequisites
```bash
# System requirements
- Docker 20.x+
- Docker Compose 2.x+
- Linux/macOS/Windows with WSL2
- 4GB+ RAM
- 20GB+ disk space
```

### Initial Setup
```bash
# 1. Security infrastructure (MANDATORY)
./scripts/security/setup_mtls_infrastructure.sh setup

# 2. Start infrastructure
docker-compose -f docker-compose-mtls.yml up

# 3. Validate setup
./scripts/validate_ssl_configuration.sh
```

## 🗄️ Database Infrastructure

### PostgreSQL Configuration
```yaml
# Database service configuration
services:
  database:
    image: postgres:15
    environment:
      POSTGRES_DB: ai_workflow_engine
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./config/postgresql:/etc/postgresql/conf.d
```

### Connection Pooling (pgbouncer)
```ini
# pgbouncer configuration
[databases]
ai_workflow_engine = host=database port=5432 dbname=ai_workflow_engine

[pgbouncer]
pool_mode = transaction
max_client_conn = 100
default_pool_size = 10
```

### Backup Strategy
```bash
# Automated database backups
pg_dump -h localhost -U postgres ai_workflow_engine > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup automation
./scripts/database/backup_database.sh
```

## 🔒 Security Infrastructure

### mTLS Configuration
All services communicate using mutual TLS:
- **Certificate Authority**: Self-signed CA for development
- **Service Certificates**: Individual certificates per service
- **Client Certificates**: Client authentication certificates
- **Certificate Rotation**: Automated certificate renewal

### Security Services
```yaml
# Security service configuration
security:
  ca_certificate: /certs/ca/ca.crt
  server_certificate: /certs/server/server.crt
  server_key: /certs/server/server.key
  client_certificate: /certs/client/client.crt
  client_key: /certs/client/client.key
```

## 📊 Monitoring & Observability

### Prometheus Metrics
- API request rates and response times
- Database connection pool metrics
- System resource utilization
- Security event monitoring
- Custom application metrics

### Health Checks
```yaml
# Service health checks
healthcheck:
  test: ["CMD", "curl", "-f", "https://localhost:8443/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Logging Strategy
- **Structured Logging**: JSON format for all services
- **Centralized Logging**: Log aggregation and analysis
- **Security Logging**: Comprehensive security event logging
- **Performance Logging**: Request timing and performance metrics

## 🚀 Deployment Procedures

### Development Deployment
```bash
# 1. Setup security infrastructure
./scripts/security/setup_mtls_infrastructure.sh setup

# 2. Start development environment
docker-compose -f docker-compose-mtls.yml up

# 3. Run migrations
alembic upgrade head

# 4. Validate deployment
./scripts/validate_deployment.sh
```

### Production Deployment
```bash
# 1. Deploy security enhancements
./scripts/deploy_security_enhancements.sh

# 2. Deploy application
docker-compose -f docker-compose.yml up -d

# 3. Run database migrations
docker-compose exec api alembic upgrade head

# 4. Validate production deployment
./scripts/validate_production_deployment.sh
```

### Rollback Procedures
```bash
# Database rollback
alembic downgrade -1

# Application rollback
docker-compose down
docker-compose -f docker-compose.yml up -d --scale api=0
# Deploy previous version
docker-compose -f docker-compose.yml up -d
```

## 🔧 Configuration Management

### Environment Variables
```bash
# Core configuration
DATABASE_URL=postgresql://user:pass@database:5432/ai_workflow_engine
REDIS_URL=redis://redis:6379/0
JWT_SECRET=your-jwt-secret
ENVIRONMENT=production

# Security configuration
SSL_CERT_PATH=/certs/server/server.crt
SSL_KEY_PATH=/certs/server/server.key
CA_CERT_PATH=/certs/ca/ca.crt
```

### Configuration Files
- `/config/caddy/`: Reverse proxy configuration
- `/config/postgresql/`: Database configuration
- `/config/pgbouncer/`: Connection pooling configuration
- `/config/redis/`: Cache configuration
- `/config/prometheus/`: Monitoring configuration

## 🛠️ Operational Procedures

### Routine Maintenance
```bash
# Database maintenance
./scripts/database/maintenance.sh

# Certificate rotation
./scripts/security/rotate_certificates.sh

# Log rotation
./scripts/maintenance/rotate_logs.sh

# System cleanup
./scripts/maintenance/cleanup.sh
```

### Scaling Procedures
```bash
# Scale API services
docker-compose -f docker-compose.yml up -d --scale api=3

# Scale database connections
# Update pgbouncer configuration and restart
```

## 🔗 Related Documentation

- [Security Implementation](../security/overview.md)
- [Development Environment](../development/environment-setup.md)
- [Database Architecture](../architecture/database.md)
- [Troubleshooting Infrastructure](../troubleshooting/common-issues.md)

---

**⚠️ Security Note**: Always use mTLS configuration for development as mandated in [CLAUDE.md](../../CLAUDE.md).