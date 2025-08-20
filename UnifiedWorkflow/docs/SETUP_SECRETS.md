# AI Workflow Engine - Secrets Setup Guide

This guide explains how to set up the AI Workflow Engine with proper Docker secrets management.

## Overview

The AI Workflow Engine uses Docker secrets to securely manage sensitive configuration data. This approach:
- Keeps secrets out of environment files
- Provides better security for production deployments
- Allows for easier credential rotation
- Follows Docker security best practices

## Quick Setup

Run the setup script to generate all required secrets and certificates:

```bash
./scripts/_setup_secrets_and_certs.sh
```

This script will:
1. Generate all required passwords and keys
2. Create SSL certificates for HTTPS
3. Prompt for admin credentials
4. Prompt for Google OAuth credentials (optional)
5. Set up proper file permissions

## Manual Setup (Advanced)

If you need to set up secrets manually, create the following files in the `secrets/` directory:

### Required Secrets

- `postgres_password.txt` - Database password
- `jwt_secret_key.txt` - JWT signing key
- `api_key.txt` - Internal API key
- `redis_password.txt` - Redis password
- `qdrant_api_key.txt` - Qdrant API key
- `admin_email.txt` - Admin user email
- `admin_password.txt` - Admin user password

### Optional Secrets (for Google Services)

- `google_client_id.txt` - Google OAuth Client ID
- `google_client_secret.txt` - Google OAuth Client Secret

### Google OAuth Setup

To enable Google services integration:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the following APIs:
   - Google Calendar API
   - Google Drive API
   - Gmail API
4. Go to 'Credentials' and create OAuth 2.0 Client ID
5. Set authorized redirect URIs to: `https://your-domain.com/api/v1/oauth/google/callback`
6. Copy the Client ID and Client Secret to the respective secret files

## File Permissions

The setup script automatically sets correct permissions:
- Secret files: `600` (owner read/write only)
- Redis ACL file: `644` (readable by containers)

## Environment Variables

The `.env` file should only contain non-sensitive configuration:
- Service hostnames and ports
- Feature flags
- CORS origins
- Ollama model names

**Never put passwords or secrets in the `.env` file!**

## Docker Compose Integration

The Docker Compose configuration automatically:
- Mounts secrets from the `secrets/` directory
- Makes them available at `/run/secrets/` inside containers
- Loads them via the application's configuration system

## Troubleshooting

### Secrets Not Loading

If secrets are not being loaded:
1. Check file permissions: `ls -la secrets/`
2. Verify Docker secrets are mounted: `docker compose exec api ls -la /run/secrets/`
3. Check application logs: `docker compose logs api`

### Permission Errors

If you get permission denied errors:
1. Ensure files are owned by the correct user
2. Check that secret files have 600 permissions
3. Restart the affected containers

### Google OAuth Issues

If Google OAuth is not working:
1. Verify the redirect URI in Google Cloud Console matches your domain
2. Check that both `google_client_id.txt` and `google_client_secret.txt` exist
3. Restart the API container after adding OAuth credentials

## Security Notes

- Never commit secret files to version control
- Use different secrets for different environments
- Rotate secrets regularly
- Consider using external secret management systems for production

## Support

If you need help with the setup process, check the logs and ensure all required secrets are present and have correct permissions.