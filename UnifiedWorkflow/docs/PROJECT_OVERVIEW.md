# 🤖 AI Workflow Engine - Project Overview

## 📁 High-Level Project Structure

**Purpose**: Comprehensive AI-powered workflow engine with agent orchestration, web interface, and containerized deployment.

### 🏗️ Core Architecture Directories

```
/home/marku/ai_workflow_engine/
├── 📂 .claude/                    # Agent orchestration system
├── 📂 app/                        # Application layer
│   ├── 📂 api/                   # FastAPI backend services
│   └── 📂 webui-next/            # Next.js frontend interface
├── 📂 docker/                     # Container configurations
├── 📂 docs/                       # Comprehensive documentation
├── 📂 servers/                    # MCP server implementations
└── 📂 [config & deployment files] # Root-level configurations
```

## 🎯 Key Architectural Patterns

### Agent Orchestration System
- **Location**: `.claude/` directory
- **Purpose**: 48-agent ecosystem with 10-phase orchestration workflow
- **Key Feature**: Prevents recursion with evidence-based validation

### Full-Stack Application
- **Backend**: FastAPI with async/await patterns in `app/api/`
- **Frontend**: Next.js React application in `app/webui-next/`
- **Integration**: RESTful APIs with WebSocket real-time communication

### Containerized Deployment
- **Technology**: Docker Compose orchestration
- **Architecture**: Multi-service container deployment with health monitoring
- **Production**: Traefik reverse proxy with SSL/TLS termination

## 🚀 Entry Points & Main Components

### Primary Application Entry Points
- **API Server**: `/app/api/main.py` - FastAPI application root
- **WebUI**: `/app/webui-next/src/App.jsx` - React application entry
- **Docker**: `/docker-compose.yml` - Container orchestration

### Agent System Entry Points
- **Orchestration**: `.claude/PHASE_1_AGENT_ECOSYSTEM_VALIDATION_*.md` - Agent ecosystem reports
- **Agent Registry**: Distributed across `.claude/agents/` directory
- **Workflow Config**: `.claude/unified-orchestration-config.yaml` (referenced but not visible)

## 📋 Cross-References to Detailed Documentation

For comprehensive details on each directory and component:

- **API Details**: See `FOLDER_DETAILS/api_directory.md`
- **Frontend Structure**: See `FOLDER_DETAILS/frontend_directory.md`
- **Agent System**: See `FOLDER_DETAILS/claude_directory.md`
- **Container Architecture**: See `FOLDER_DETAILS/docker_directory.md`
- **Documentation Organization**: See `FOLDER_DETAILS/docs_directory.md`
- **MCP Servers**: See `FOLDER_DETAILS/servers_directory.md`

## ⚡ Recent Major Changes

### Infrastructure Improvements (Aug 14, 2025)
- ✅ Container health check fixes resolved (wget instead of curl)
- ✅ WebUI container health monitoring restored
- ✅ Production deployment validated at https://aiwfe.com

### Security & Authentication
- 🔴 WebSocket authentication failures identified (403 errors)
- 🔴 Settings authentication bypass vulnerability confirmed
- 🟡 Registration UX improvements needed

### Agent Ecosystem
- ✅ 48 agents validated and operational
- ✅ Orchestration workflow enhanced with evidence-based validation
- ✅ Deployment orchestration success documented

---

**Token Count**: ~750 tokens (within PROJECT_OVERVIEW.md limits)
**Last Updated**: August 14, 2025
**Maintenance**: Auto-updated by documentation-specialist agent