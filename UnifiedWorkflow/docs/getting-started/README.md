# Getting Started

Welcome to the AI Workflow Engine! This section provides everything you need to get up and running quickly.

## 📋 Prerequisites

Before you begin, ensure you have:
- Python 3.9+ installed
- Docker and Docker Compose
- Git for version control
- Basic knowledge of Python and web development

## 🚀 Quick Start Options

### Option 1: Standard Setup
For most users and development environments:
```bash
git clone https://github.com/your-org/ai_workflow_engine.git
cd ai_workflow_engine
./install.sh
```

### Option 2: mTLS Development Setup (Recommended for Security Development)
For working with security features and mTLS:
```bash
git clone https://github.com/your-org/ai_workflow_engine.git
cd ai_workflow_engine
./scripts/security/setup_mtls_infrastructure.sh setup
docker-compose -f docker-compose-mtls.yml up
```

## 📚 Getting Started Guides

### [🔧 Project Setup](setup.md)
Complete installation and configuration guide including:
- System requirements
- Dependency installation
- Database setup
- Environment configuration

### [⚡ Quick Start Guide](quickstart.md)
Get the system running in 5 minutes:
- Minimal setup steps
- First API call
- Basic authentication
- Simple examples

### [🌍 Environment Configuration](environment.md)
Configure your development environment:
- Environment variables
- Database connections
- API keys and secrets
- Development vs. production settings

### [👨‍💻 First Time Developer Guide](first-time-developer.md)
Comprehensive guide for new developers:
- Codebase overview
- Development workflow
- Coding standards
- Making your first contribution

## 🔗 What's Next?

After completing the getting started guides:

1. **Explore the Architecture**: Understand the [system architecture](../architecture/README.md)
2. **Try the APIs**: Check out the [API documentation](../api/README.md)
3. **Set up Development**: Follow the [development guides](../development/README.md)
4. **Learn about Security**: Review [security documentation](../security/README.md)

## 🆘 Need Help?

If you encounter issues during setup:
- Check the [Troubleshooting Guide](../troubleshooting/README.md)
- Review [Common Setup Issues](../troubleshooting/common-issues.md)
- See the [Contributing Guidelines](../development/contributing.md) for support

## 📖 Key Resources

- [Main README](../../README.md) - Project overview
- [User Guide](../../USER_GUIDE.md) - End-user documentation
- [Development Environment Setup](../development/environment-setup.md)
- [Security Setup Guide](../security/overview.md)

---

**Next Steps**: Choose your setup option above and follow the corresponding guide!