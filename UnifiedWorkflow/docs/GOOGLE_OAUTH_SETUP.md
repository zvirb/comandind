# Google OAuth Setup Guide

This guide explains how to set up Google OAuth credentials for the AI Workflow Engine to enable Google services integration (Calendar, Drive, Gmail).

## Prerequisites

1. A Google Cloud Console account
2. Admin access to your AI Workflow Engine deployment

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note down your Project ID

## Step 2: Enable Required APIs

In the Google Cloud Console, enable the following APIs for your project:

1. **Google Calendar API** - for calendar synchronization
2. **Google Drive API** - for document access
3. **Gmail API** - for email integration

To enable APIs:
1. Go to "APIs & Services" > "Library"
2. Search for and enable each API listed above
3. Wait for activation to complete

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. If prompted, configure the OAuth consent screen first:
   - Choose "Internal" if for organization use only, or "External" for public use
   - Fill in required fields (app name, user support email, developer contact)
   - Add your domain to authorized domains
   - Save and continue through the scopes and test users sections

4. For the OAuth client:
   - Application type: "Web application"
   - Name: "AI Workflow Engine" (or your preferred name)
   - Authorized redirect URIs: Add these URLs (replace `your-domain.com` with your actual domain):
     ```
     https://your-domain.com/api/v1/oauth/google/callback
     http://localhost:8000/api/v1/oauth/google/callback  (for local development)
     ```

5. Click "Create"
6. Save the generated **Client ID** and **Client Secret**

## Step 4: Configure AI Workflow Engine

### Option A: Docker Secrets (Recommended for Production)

1. Create secret files:
   ```bash
   echo "your-client-id-here" | docker secret create google_client_id -
   echo "your-client-secret-here" | docker secret create google_client_secret -
   ```

2. Update your `docker-compose.yml` to include the secrets:
   ```yaml
   services:
     api:
       secrets:
         - google_client_id
         - google_client_secret
   
   secrets:
     google_client_id:
       external: true
     google_client_secret:
       external: true
   ```

### Option B: Environment Variables (Development)

Set these environment variables:
```bash
export GOOGLE_CLIENT_ID="your-client-id-here"
export GOOGLE_CLIENT_SECRET="your-client-secret-here"
```

### Option C: Docker Secrets Files (Alternative)

Create files in your secrets directory:
```bash
# Create secrets directory if it doesn't exist
mkdir -p /path/to/secrets

# Create secret files
echo "your-client-id-here" > /path/to/secrets/google_client_id.txt
echo "your-client-secret-here" > /path/to/secrets/google_client_secret.txt

# Secure the files
chmod 600 /path/to/secrets/google_client_*.txt
```

## Step 5: Restart Services

After configuring credentials, restart your AI Workflow Engine:

```bash
docker-compose down
docker-compose up -d
```

## Step 6: Test the Connection

1. Log into your AI Workflow Engine
2. Go to Settings
3. In the Google Services section, click "Connect" for any service
4. You should be redirected to Google's authorization page
5. Grant the requested permissions
6. You should be redirected back with a success message

## Troubleshooting

### "OAuth is not configured" Error

- Check that both `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are properly set
- Verify the secrets files exist and have correct permissions
- Check the application logs for more details

### "Invalid redirect URI" Error

- Ensure your redirect URI in Google Cloud Console exactly matches your domain
- For local development, make sure you added the localhost URL
- Check that you're using the correct protocol (http vs https)

### "Access blocked" Error

- Make sure your OAuth consent screen is properly configured
- If using "Internal" consent screen, ensure the user's email domain matches your organization
- For "External" consent screen, add test users during development

### API Not Enabled Error

- Go back to Google Cloud Console and verify all required APIs are enabled
- Wait a few minutes after enabling APIs for them to become fully active

## Security Notes

1. **Never commit credentials to version control**
2. **Use Docker secrets in production**
3. **Regularly rotate your OAuth credentials**
4. **Monitor OAuth usage in Google Cloud Console**
5. **Use principle of least privilege for API scopes**

## API Scopes Used

The AI Workflow Engine uses these OAuth scopes:

- **Calendar**: `https://www.googleapis.com/auth/calendar` - Full calendar access
- **Drive**: `https://www.googleapis.com/auth/drive.readonly` - Read-only Drive access  
- **Gmail**: `https://www.googleapis.com/auth/gmail.readonly` - Read-only Gmail access

## Support

If you encounter issues:

1. Check the application logs for detailed error messages
2. Verify your Google Cloud Console configuration
3. Test with a simple OAuth flow outside the application
4. Contact your system administrator

For development questions, refer to the main project documentation.