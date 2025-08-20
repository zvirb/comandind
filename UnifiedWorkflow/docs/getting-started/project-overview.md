# AI Workflow Engine

## 🤖 A Self-Hosted, Privacy-First Intelligent Assistant

The AI Workflow Engine is a powerful, self-hosted AI assistant designed with data sovereignty and privacy as its guiding principles. It empowers users to run a sophisticated AI on their own hardware, ensuring that personal and sensitive information remains securely under their control. By leveraging Docker and a single GPU, this project makes advanced, customizable AI accessible to technical users without the need for enterprise-level infrastructure.

At its core, this project solves the critical privacy and control issues found in mainstream cloud-based AI assistants. Unlike commercial services that require sending your data to third-party servers, this engine runs entirely on your personal Ubuntu system, giving you complete ownership of your data and the AI's operational logic.

---

## Features

The AI Workflow Engine is a feature-rich platform that is continuously evolving. Here’s a look at what’s complete and what’s on the horizon:

### ✅ Implemented Features

*   **Hardened Security:** The application's foundation is built on robust security principles. This includes a hardened Docker environment with isolated services, the complete removal of hardcoded credentials from the repository's history, and the implementation of a production-grade Gunicorn/Uvicorn web server stack.
*   **Comprehensive API Security:** The backend API is protected with multiple layers of security, including mandatory API Key authentication, strict CORS policies, rate limiting to prevent abuse, and secure error handling to prevent information leakage.
*   **Two-Factor Authentication (2FA):** Complete TOTP-based 2FA implementation with Google Authenticator support, QR code generation, backup codes, device management, and trusted device tracking.
*   **Robust Frontend Security:** The SvelteKit web UI is fortified with a strict Content Security Policy (CSP) and has been fully migrated to Svelte 5 for improved performance and security.
*   **Resilient Database Architecture:** The system uses a dual-path database connection strategy. Application services connect through a high-performance PgBouncer connection pool, while state-sensitive database migrations connect directly to PostgreSQL to ensure transactional integrity.
*   **Intelligent Tool Router & Specialized Models:** The LangGraph-based tool router now uses specialized LLM models for different tasks (e.g., chat, tool selection, coding), selecting the optimal model for each step to enhance accuracy and efficiency.
*   **Semantic Memory:** The assistant leverages the power of a Qdrant vector database to manage and retrieve personalized context through vector embeddings. This enables the assistant to remember past interactions and provide more relevant, context-aware responses.
*   **Retrieval-Augmented Generation (RAG):** A fully functional RAG pipeline allows the assistant to answer questions based on documents you provide. This involves processing and chunking documents, generating embeddings, and using the retrieved context to deliver accurate and well-supported answers.
*   **Modern Calendar System:** A complete calendar overhaul featuring the `vkurko/calendar` library. It's fully integrated with the new theme system and allows for interactive, drag-and-drop event creation.
*   **Enhanced User Experience & Theming:** A professional UI overhaul with a dual theme system (light/dark modes) and engaging animations, such as a new "thinking brain" loading indicator, for a more polished and intuitive user experience.
*   **Robust Error Handling:** System-wide improvements to error handling, including fixes for document uploads and chat connection issues, provide clearer user feedback and more graceful fallback behavior.
*   **Profile Data Persistence:** Complete implementation of user profile data storage with a dedicated database table, supporting both manual profile updates and AI-extracted profile information from chat conversations.
*   **Advanced Categorization System:** Intelligent event and task categorization with user-customizable categories, flexibility scoring for scheduling optimization, and dynamic AI categorization that learns from user preferences.

#### 🚀 Key Benefits Achieved

*   **Specialized AI Models:** Different models optimized for different task types for better performance and accuracy.
*   **Professional Theming:** Consistent dark/light themes with proper color schemes for a polished look and feel.
*   **Modern Framework:** Upgraded to the latest Svelte 5 for better performance and developer experience.
*   **Enhanced UX:** Engaging loading animations and better error handling improve user interaction.
*   **Functional Calendar:** A working, modern calendar system with interactive features.
*   **Robust Error Handling:** Graceful degradation when issues occur, leading to a more stable application.
*   **Persistent User Profiles:** Complete user profile management with database storage for personal and professional information.
*   **Intelligent Categorization:** Advanced categorization with flexibility scoring enables smart scheduling and personalized organization.

#### 👤 User Profile System

The AI Workflow Engine includes a comprehensive user profile system that allows users to store and manage their personal and professional information:

**Profile Features:**
- **Personal Information:** Name, date of birth, phone numbers, personal address
- **Professional Details:** Job title, company, department, work contact information
- **Contact Preferences:** Preferred communication methods and emergency contacts
- **Social Profiles:** LinkedIn, Twitter, GitHub, and personal website links
- **Localization:** Timezone and language preferences
- **Rich Data Support:** JSON-based storage for complex address and contact structures

**Data Management:**
- **Database Persistence:** All profile data is stored in a dedicated `user_profiles` table with full CRUD operations
- **RESTful API:** Complete REST endpoints for profile management (`GET`, `PUT` operations)
- **AI Integration:** Conversational profile collection where AI can extract structured data from natural language
- **Data Validation:** Strict field validation and sanitization for security
- **Incremental Updates:** Support for partial profile updates without overwriting existing data

**Security & Privacy:**
- **User-Scoped Access:** Each user can only access and modify their own profile data
- **Secure Storage:** All sensitive information is stored with proper database constraints
- **Input Validation:** Comprehensive validation to prevent injection attacks
- **Audit Trail:** Created/updated timestamps for all profile changes

#### 🏷️ Advanced Categorization System

The AI Workflow Engine features a sophisticated categorization system that intelligently organizes events and tasks based on user-defined categories with advanced weighting and flexibility controls:

**Smart Categorization Features:**
- **User-Customizable Categories:** Create and manage personal categories with custom names, colors, emojis, and descriptions
- **Multi-Weight System:** Each category includes importance, urgency, complexity, and flexibility weights for intelligent scheduling
- **Flexibility Scoring:** Categories have flexibility scores (0-1) that determine how "moveable" events are:
  - **0.0 (Fixed):** Booked appointments, classes, meetings that cannot be rescheduled
  - **0.5 (Moderate):** Work tasks, project deadlines with some flexibility
  - **1.0 (Highly Flexible):** Study time, exercise, personal tasks that can be easily moved
- **AI-Powered Categorization:** LLM-based event categorization using dynamic prompts that include user's actual categories
- **Weighted Scoring Integration:** Categories feed into the intelligent task/event scoring system for optimal scheduling

**Technical Implementation:**
- **Dynamic Category Management:** Real-time fetching of user categories from database with fallback to defaults
- **Flexible Data Model:** JSON-based category weights allow for complex, user-specific configurations
- **Calendar Integration:** Categories automatically map to Google Calendar colors for visual consistency
- **Cross-Service Integration:** Both events and tasks use the same categorization framework
- **Performance Optimized:** Efficient database queries with proper indexing and caching

**User Benefits:**
- **Personalized Organization:** Categories reflect individual work styles and life patterns
- **Intelligent Scheduling:** AI considers category flexibility when suggesting optimal timing
- **Visual Consistency:** Color-coded categories provide immediate visual context
- **Adaptive Learning:** System learns from user categorization patterns over time
- **Seamless Integration:** Works across calendar, tasks, and planning tools

#### 🧠 Adaptive Socratic Interview System

The AI Workflow Engine features a sophisticated interview system based on the Socratic method, designed to facilitate deep self-reflection and personal development through AI-guided conversations:

**Core Interview Types:**
- **🎯 Mission Statement Development:** Discover core values and life purpose through guided exploration
- **📈 Work Style Assessment:** Understand personal productivity patterns and optimal working conditions  
- **🔄 Productivity Pattern Analysis:** Identify strengths, challenges, and improvement opportunities
- **🌟 Personal Life Reflection:** Explore goals, relationships, and life satisfaction

**Adaptive Intelligence Features:**
- **Dynamic Question Generation:** AI adapts questions in real-time based on user responses and conversation context
- **Contextual Memory:** System remembers past interview sessions and builds on previous insights
- **Multi-Phase Structure:** Each interview follows a structured progression (Exploration → Analysis → Synthesis → Action)
- **Progress Tracking:** Visual indicators show interview completion and confidence levels
- **Personalized Insights:** AI generates tailored recommendations based on interview responses

**Technical Implementation:**
- **Vector-Based Context:** Uses Qdrant vector database for semantic understanding of responses
- **Smart Token Management:** Efficient LLM usage with specialized models for different interview phases
- **Session Persistence:** Interviews can be paused and resumed across multiple sessions
- **Data Privacy:** All interview data remains locally stored with full user control

#### 📱 Android Focus Nudge System (In Development)

The AI Workflow Engine includes plans for a native Android application that extends the AI assistant's capabilities to mobile productivity enhancement:

**Core Mobile Features:**
- **📊 Usage Tracking:** Monitor app usage patterns, screen time, and digital behavior via Android's UsageStatsManager
- **🧠 AI-Powered Analysis:** Server-side analysis of mobile usage patterns to identify productivity opportunities  
- **💡 Contextual Nudges:** Smart notifications and suggestions delivered at optimal moments
- **🔄 Feedback Loop:** Touch-optimized feedback collection to improve nudge effectiveness over time
- **🔒 Privacy-First:** All data processing occurs on your self-hosted infrastructure

**Technical Architecture:**
- **Hybrid Delivery System:** WebSocket connections for active app, intelligent polling for background updates
- **No External Dependencies:** Designed to work entirely with your existing infrastructure (no Firebase/external push services)
- **Battery Optimized:** Smart connection management and efficient background processing within Android's limitations
- **Permission Conscious:** Minimal required permissions with graceful degradation for denied access

**Current Development Status:**
- ✅ **Backend API Complete:** Full REST API and WebSocket infrastructure ready
- ✅ **Technical Specifications:** Detailed Android implementation documents available
- 🚧 **Frontend Development:** Native Android UI and integration layer in progress
- 🚧 **Testing & Optimization:** Performance optimization and real-world testing phase

**Documentation Available:**
- Complete Android API specifications (`docs/FOCUS_NUDGE_ANDROID_API_SPEC.md`)
- No-Firebase implementation guide (`docs/FOCUS_NUDGE_ANDROID_NO_FIREBASE_SPEC.md`)
- Technical architecture and integration patterns

### 🎯 Roadmap & Current Status

> **📍 Major Update (July 28, 2025)**: Core productivity platform is now **95% complete**! All major systems including Email Management, Task Management, and Reflective Coach Tools are fully operational.

#### ✅ **COMPLETED MAJOR SYSTEMS**
*   **✅ Google OAuth Integration:** Full per-user OAuth implemented for Calendar, Drive, and Gmail with secure token management
*   **✅ User Profile System:** Comprehensive profile management with 20+ fields, database persistence, and AI-enhanced tools  
*   **✅ Calendar System:** Complete integration with Google Calendar, Australian timezone support, AI-assisted event creation
*   **✅ Authentication & Security:** Robust authentication system with role-based access control and comprehensive 2FA support
*   **✅ Database Architecture:** All major models implemented with proper relationships and migrations
*   **✅ Email Management Tools:** Gmail service fully implemented with email fetching, parsing, and OAuth integration
*   **✅ Task Management System:** Enhanced task tools with intelligent parsing, CRUD operations, calendar integration, and subtask generation
*   **✅ Advanced Categorization System:** User-customizable categories with flexibility scoring, AI-powered categorization, and weighted scoring integration
*   **✅ Reflective Coach Tools:** Complete assessment system with Work Style, Productivity Patterns, and Mission Statement tools
*   **✅ Adaptive Socratic Interviews:** AI-powered interview system using Socratic methodology for personal development, mission statement creation, and productivity pattern analysis
*   **✅ Server Health Monitoring:** Comprehensive connectivity monitoring with automatic retry and user notifications
*   **✅ Enhanced Subtask Generation:** AI-powered task breakdown with intelligent failure case handling and contextual help
*   **✅ Native Client Backend:** Initial backend support for a native desktop client, including certificate-based access control and dedicated API endpoints.

#### 🚧 **REMAINING DEVELOPMENT WORK**
*   **Native Desktop Client (Frontend & Packaging):** Development of the cross-platform desktop application, including UI, screen awareness, and text modification features.
*   **Android Focus Nudge App:** Native Android application for mobile productivity enhancement with usage tracking and AI-powered focus nudges
*   **Project Management System:** Advanced multi-phase project management for complex, long-term goals
*   **Advanced AI Integration:** Cross-service data correlation and intelligent workflow automation

#### 🔮 **FUTURE ENHANCEMENTS** 
*   **Integration Expansion:** Microsoft 365 OAuth, Slack/GitHub/Notion integrations following established OAuth patterns
*   **Mobile Experience:** Android client development (Focus Nudge system in active development), progressive web app enhancements
*   **Enterprise Features:** Advanced analytics, team collaboration tools, enterprise SSO integration

**Current Status:** Core productivity platform complete - ready for advanced features and integrations


## Technology Stack

The AI Workflow Engine is built on a modern, robust technology stack designed for performance, security, and scalability:

| Category                       | Technology / Library                                                                                                                            |
| :----------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Backend**                    | [FastAPI](https://fastapi.tiangolo.com/), [Gunicorn](https://gunicorn.org/) / [Uvicorn](https://www.uvicorn.org/)                                    |
| **Frontend**                   | SvelteKit, Tailwind CSS, vkurko/calendar         || **Databases & Caching**        | [PostgreSQL](https://www.postgresql.org/), [Alembic](https://alembic.sqlalchemy.org/), [Redis](https://redis.io/)                                    |
| **AI / ML**                    | [LangChain](https://www.langchain.com/) & [LangGraph](https://langchain-ai.github.io/langgraph/), [Ollama](https://ollama.com/), [Qdrant](https://qdrant.tech/) |
| **Containerization**           | [Docker](https://www.docker.com/), [Docker Compose](https://docs.docker.com/compose/)                                                             |
| **Monitoring & Reverse Proxy** | [Prometheus](https://prometheus.io/), [Grafana](https://grafana.com/), [Caddy](https://caddyserver.com/)                                            |

## Project Structure

### Storage and Persistence

The project uses Docker named volumes for all stateful services to ensure data persistence and avoid common permission issues associated with host-based bind mounts.

*   **Data Volumes:** Services like PostgreSQL (`postgres_data`), Redis (`redis_data`), and Qdrant (`qdrant_data`) each have their own dedicated named volume. When a container starts with a new, empty volume, the official entrypoint script for that service (e.g., `postgres`) automatically initializes the directory with the correct ownership. This robust, built-in behavior prevents permission errors without needing custom `chown` commands in wrapper scripts.

*   **Secure Certificate Handling:** A shared named volume (`certs`) is used to manage TLS certificates through a secure, multi-stage process:
    1.  A one-time `certs-init` service generates certificates and places them into service-specific subdirectories within the `certs` volume.
    2.  Each service then mounts the entire `certs` volume to a temporary, read-only location.
    3.  A lightweight entrypoint wrapper script inside each container copies **only its own certificates** to a private, secure location. This enforces the principle of least privilege, ensuring no service can access another service's certificates.

---

The project is organized as a monorepo, with the backend, frontend, and all supporting services in a single repository to facilitate code sharing and streamlined development. Here is a high-level overview of the key directories and files:

| File/Directory                | Description                                                                                                                                              |
| :---------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`docker-compose.yml`**      | The master file for defining and running the multi-container Docker application. It orchestrates all services, networks, and volumes.                    |
| **`app/`**                    | Contains the source code for the backend services (`api`, `worker`), the frontend (`webui`), and a `shared` directory containing common logic, schemas, and utilities. |
| **`docker/`**                 | Holds the `Dockerfile` for each service, defining how its image is built, along with any necessary entrypoint wrapper scripts for initialization.        |
| **`config/`**                 | Contains configuration files for services like Caddy, PostgreSQL, and PgBouncer.                                                                         |
| **`scripts/`**                | A collection of shell scripts for managing the application lifecycle (setup, start, migrations, etc.).                                                   |
| **`docs/`**                   | Contains all project documentation, including the roadmap, system architecture, and detailed team reports.                                                 |
| **`certs/`**                  | Stores locally generated SSL certificates for secure communication. This directory is created by the setup script and is ignored by Git.                   |
| **`secrets/`**                | Stores sensitive information like API keys and passwords. This directory is created by the setup script and is ignored by Git.                             |
| **`logs/`**                   | Contains runtime logs, including a detailed `error_log.txt` that is automatically generated when a container fails. This directory is ignored by Git.      |

## Getting Started

Follow these steps to get the AI Workflow Engine up and running on your local system.

### Prerequisites

* **Docker and Docker Compose:** Essential for running the containerized application stack.
* **Python ~3.11:** Required for local development and running setup scripts. Must match the version in `pyproject.toml`.
* **Git:** For cloning the repository.
* **An NVIDIA GPU with CUDA drivers:** Required for running in GPU mode.
* **NVIDIA Container Toolkit:** Required for Docker to access the GPU.

### Installation

The recommended way to run the AI Workflow Engine is using Docker. A comprehensive setup script automates the entire process, including secure SSL certificate generation.

#### 🔐 Local Development Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/zvirb/ai_workflow_engine.git
    cd ai_workflow_engine
    ```

2.  **Run the One-Time Setup Script:**
    This script prepares your environment by generating secrets, creating browser-trusted SSL certificates using [mkcert](https://github.com/FiloSottile/mkcert), building Docker images, and configuring the database.

    ```bash
    ./scripts/_setup.sh
    ```
    
    **What the setup script does:**
    - ✅ **Generates secure secrets** for database, JWT tokens, and API keys
    - ✅ **Creates SSL certificates** using mkcert for trusted HTTPS
    - ✅ **Installs root CA** system-wide for seamless browser trust
    - ✅ **Initializes database** with proper schema and migrations
    - ✅ **Sets up user accounts** (prompts for admin credentials)
    - ✅ **Builds Docker images** with caching for speed

    **Setup options:**
    - `--no-cache`: Force rebuild without cache
    - `--full-teardown`: Reset environment and rebuild everything

3.  **Start the Application:**
    ```bash
    ./run.sh
    ```
    
    **Run options:**
    - `--build`: Rebuild images before starting
    - `--reset`: Reset all data and restart fresh
    - `--no-watch`: Skip the monitoring dashboard

#### 🌐 Remote Access Setup

For accessing the web UI from other computers on your network:

1.  **Setup the server for remote access:**
    ```bash
    # For hostname-based access
    ./scripts/_setup_remote_access.sh --hostname myserver.local
    
    # For IP-based access
    ./scripts/_setup_remote_access.sh --ip 192.168.1.100
    
    # For custom ports
    ./scripts/_setup_remote_access.sh --hostname myserver.local --https-port 8443
    
    # Install CA on server for local browser trust
    ./scripts/_setup_remote_access.sh --hostname myserver.local --install-ca
    ```

2.  **Setup client computers:**
    On each computer that needs to access the web UI securely:
    ```bash
    # Copy rootCA.pem from the server to the client, then:
    ./scripts/_setup_client_access.sh --ca-file rootCA.pem --url https://myserver.local
    
    # Auto-install without prompts
    ./scripts/_setup_client_access.sh --ca-file rootCA.pem --yes
    ```

#### 🔧 Fresh Installation Requirements

The setup scripts automatically handle all dependencies, but for manual setup you need:
- **Docker & Docker Compose** - For containerization
- **mkcert** - Automatically installed by setup script for SSL certificates
- **Python 3.11** - For development (matches `pyproject.toml`)
- **NVIDIA GPU + CUDA drivers** - For AI model inference
- **NVIDIA Container Toolkit** - For Docker GPU access

### Usage

#### 🖥️ Accessing the Application

**Local Development:**
- **Web UI:** `https://localhost` (🔒 Secure with trusted certificate)
- **API Documentation:** `https://localhost/api/v1/docs`

**Remote Access:**
- **Web UI:** `https://your-server-hostname` or `https://server-ip`
- **Custom Ports:** `https://your-server:8443` (if configured)

#### 🔐 Security Features

- **Automatic HTTPS:** All connections use SSL with trusted certificates
- **CSRF Protection:** Prevents cross-site request forgery attacks
- **Secure Cookies:** Authentication tokens use secure, HTTP-only cookies
- **Database Encryption:** All data stored securely with proper access controls
- **API Authentication:** JWT tokens with configurable expiration
- **Two-Factor Authentication (2FA):** Complete TOTP implementation supporting:
  - **Google Authenticator Integration:** Standard TOTP with QR code setup
  - **Backup Codes:** Emergency access codes for device loss scenarios
  - **Device Management:** Track and manage trusted devices
  - **Manual Entry:** Alternative setup method for authenticator apps
  - **Security Settings:** User-configurable 2FA preferences and device trust levels

#### 🛡️ Setting Up Two-Factor Authentication

After accessing the web UI, enhance your account security with 2FA:

1. **Navigate to Security Settings:**
   - Click your profile menu → "Security"
   - Or visit: `https://localhost/security`

2. **Enable 2FA:**
   - Click "Enable Two-Factor Authentication"
   - Scan the QR code with Google Authenticator, Authy, or similar TOTP app
   - Enter the 6-digit verification code to complete setup
   - **Important:** Save the backup codes in a secure location

3. **Device Management:**
   - Mark frequently used devices as "trusted" to reduce 2FA prompts
   - Monitor and revoke access for unfamiliar devices
   - Configure device security levels (Secure, Standard, Basic)

#### 📊 Monitoring & Logs

The setup script launches an interactive dashboard showing live service status. You can also:
```bash
# View logs for a specific service
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f webui

# Check overall system health
docker compose ps
```

---
## Troubleshooting

The project is designed to be resilient, but if you encounter issues during setup or runtime, here are the recommended steps.

### Automatic Error Logging

When a container fails to build or start correctly, the setup script automatically captures detailed diagnostic information and saves it to `logs/error_log.txt`. This log is your first stop for debugging. It includes:
*   The command that was running when the failure occurred.
*   The container's status, exit code, and health check output.
*   Configuration details like environment variables and volume mounts.
*   The last 50 lines of the container's logs.
*   A state snapshot of its critical dependencies.

### Getting AI-Powered Help

This project includes a unique helper script to assist with debugging. After a failure, you can run this script to generate a detailed prompt for an AI assistant like Gemini Code Assist.

1.  **Generate the Prompt:**
    After a failure, run the following script:
    ```bash
    ./scripts/_ask_gemini.sh
    ```
2.  **Copy and Paste:**
    The script will analyze the `logs/error_log.txt`, prepare a comprehensive prompt, and automatically copy it to your clipboard.
3.  **Get a Solution:**
    Paste the prompt into your AI assistant to receive a detailed analysis and a suggested fix.

### Common Issues

#### PostgreSQL SSL Certificate Configuration Issue

If PostgreSQL is repeatedly restarting with SSL certificate errors like `FATAL: could not load server certificate file`, this indicates a mismatch between the certificate file paths in the docker-compose configuration and the actual certificate filenames created by the entrypoint wrapper.

**Symptoms:**
- PostgreSQL service shows status "Restarting" 
- Log shows: `FATAL: could not load server certificate file "/etc/certs/postgres/unified-cert.pem": No such file or directory`

**Solution:**
The postgres entrypoint wrapper copies certificates to specific filenames (`server.crt`, `server.key`, `root.crt`) but the docker-compose.yml may reference the original filenames. To fix:

1. Check the postgres configuration in docker-compose.yml:
```yaml
command:
  - "postgres"
  - "-c"
  - "ssl_cert_file=/etc/certs/postgres/server.crt"  # Not unified-cert.pem
  - "-c" 
  - "ssl_key_file=/etc/certs/postgres/server.key"   # Not unified-key.pem
```

2. Run a soft reset to apply the fix:
```bash
./run.sh --soft-reset
```

#### Worker Service `su-exec` or `gosu` Issues

If the worker service is restarting with errors like `exec: su-exec: not found` or similar privilege dropping errors:

**Symptoms:**
- Worker service shows status "Restarting" or "Unhealthy"
- Log shows: `/usr/local/bin/run.sh: exec: su-exec: not found`

**Solution:**
The worker uses `gosu` for privilege dropping (Debian-based), while other services may use `su-exec` (Alpine-based). Ensure the worker Dockerfile installs the correct utility:

1. Check worker Dockerfile includes `gosu`:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends curl gosu && rm -rf /var/lib/apt/lists/*
```

2. Update worker run.sh to use `gosu`:
```bash
exec gosu app:app env \
```

3. Run soft reset to apply changes:
```bash
./run.sh --soft-reset
```

#### pgbouncer SSL Configuration Issues

If the API returns 500 errors and pgbouncer logs show "SSL required" errors, this indicates SSL configuration problems between services and pgbouncer.

**Symptoms:**
- API authentication endpoints return 500 Internal Server Error
- pgbouncer logs: `WARNING: (nodb)/(nouser)@IP:PORT pooler error: SSL required`
- Database connectivity fails for API and worker services

**Root Cause:**
pgbouncer requires SSL encryption for client connections but the SSL configuration may be incorrectly set up for client certificate authentication.

**Solution:**
Configure pgbouncer for SSL encryption without requiring client certificate authentication:

1. Update `config/pgbouncer/pgbouncer.ini`:
```ini
; --- Client-Facing SSL Configuration ---
client_tls_sslmode = require
client_tls_cert_file = /etc/pgbouncer/certs/unified-cert.pem
client_tls_key_file = /etc/pgbouncer/certs/unified-key.pem
```

2. Ensure API and worker database connections include SSL parameters:
```bash
DATABASE_URL="postgresql+psycopg://app_user:${POSTGRES_PASSWORD}@pgbouncer:6432/app_tx?sslmode=require&sslrootcert=/etc/certs/api/rootCA.pem&sslcert=/etc/certs/api/unified-cert.pem&sslkey=/etc/certs/api/unified-key.pem"
```

3. Run soft reset to apply changes:
```bash
./run.sh --soft-reset
```

#### `ERROR: UtilAcceptVsock:271: accept4 failed 110` on Windows (WSL)

This is a known, often transient error related to the communication layer between Docker Desktop and the Windows Subsystem for Linux (WSL). It indicates a timeout or connection issue. The setup scripts have built-in retries to handle this, but if the problem persists, you can try the following steps to stabilize your environment:

1.  **Restart Docker Desktop:** This is often the quickest fix. Right-click the Docker icon in your system tray and select "Restart".
2.  **Restart WSL:** Open a PowerShell or Command Prompt terminal and run the following command to completely shut down all WSL instances. Then, restart Docker Desktop.
    ```powershell
    wsl --shutdown
    ```
3.  **Check for Updates:** Ensure you are running the latest version of Docker Desktop, as updates often include bug fixes for WSL integration.

---
## Contributing

We welcome contributions to the AI Workflow Engine! If you're interested in helping improve the project, please review our [Contributing Guidelines](CONTRIBUTING.md) for details on how to get started, our code of conduct, and the process for submitting pull requests.
## License and Acknowledgements

This project is open-source and available under the MIT License.

We extend our heartfelt thanks to the creators and maintainers of the incredible open-source software that makes this project possible, including:

* **FastAPI, Uvicorn, and Gunicorn** for providing a high-performance web framework and server stack.
* **LangChain and LangGraph** for their powerful libraries that make it possible to build sophisticated AI agents.
* **Ollama** for democratizing access to powerful large language models.
* **Qdrant** for their high-performance vector database, which is essential for the assistant's memory.
* **Svelte and SvelteKit** for the tools to build a fast, modern, and user-friendly web interface.
* **Docker and Docker Compose** for revolutionizing how we build, ship, and run applications.
* **PostgreSQL** for providing a reliable and feature-rich open-source database.

And a special thanks to the countless other open-source libraries and tools that have been instrumental in the development of this project. A full list of dependencies can be found in the `requirements.txt` and `webui/package.json` files.