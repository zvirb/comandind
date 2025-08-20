# 🚀 Cloudflare API Token Setup Guide

**Goal:** Deploy Let's Encrypt certificates to fix login issues and eliminate browser certificate warnings.

## Quick 5-Minute Setup

### Step 1: Create Cloudflare API Token
1. **Go to:** https://dash.cloudflare.com/profile/api-tokens
2. **Click:** "Create Token"
3. **Use template:** "Edit zone DNS" 
4. **Configure permissions:**
   - Zone > DNS > Edit ✅
   - Zone > Zone > Read ✅
5. **Zone Resources:** Include > Specific zone > `aiwfe.com`
6. **Click:** "Continue to summary" → "Create Token"
7. **Copy the token** (you won't see it again!)

### Step 2: Get Zone ID
1. **Go to:** https://dash.cloudflare.com
2. **Select:** "aiwfe.com" domain
3. **Copy Zone ID** from the right sidebar (looks like: `1234567890abcdef1234567890abcdef`)

### Step 3: Configure Environment File
```bash
# Edit the production environment file:
nano /home/marku/ai_workflow_engine/config/secrets/.env.production

# Replace these values with your actual credentials:
CLOUDFLARE_API_TOKEN=your_actual_cloudflare_api_token_here
DOMAIN=aiwfe.com
EMAIL=admin@aiwfe.com
```

### Step 4: Deploy Let's Encrypt Certificates
```bash
# Run the deployment script (this will fix the login issue):
cd /home/marku/ai_workflow_engine
./scripts/deploy_ssl_certificate_production.sh
```

## What This Fixes

**Current Problem:**
- Browser shows "Your connection is not private"
- Certificate error: `net::ERR_CERT_AUTHORITY_INVALID`
- Users cannot log in due to certificate trust issues

**After Deployment:**
- ✅ Valid Let's Encrypt certificate (trusted by all browsers)
- ✅ No certificate warnings
- ✅ Users can log in successfully
- ✅ Automatic certificate renewal (60 days)

## Deployment Process

The deployment script will:
1. **Validate** your DNS and API token
2. **Stop** current services with self-signed certificates
3. **Start** production services with Let's Encrypt
4. **Wait** for certificate acquisition (2-5 minutes)
5. **Validate** certificate installation
6. **Test** browser compatibility

## Verification Steps

After deployment, test in your browser:
1. Visit https://aiwfe.com
2. ✅ No certificate warnings
3. ✅ Green padlock in address bar
4. ✅ Login form works correctly

## Troubleshooting

**If certificate acquisition fails:**
```bash
# Check logs:
docker-compose -f docker-compose-production.yml logs caddy_reverse_proxy

# Verify API token:
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.cloudflare.com/client/v4/user/tokens/verify
```

**Common issues:**
- **Wrong API token:** Must have Zone:DNS:Edit permission
- **Wrong Zone ID:** Must match your aiwfe.com domain
- **DNS propagation:** May take 5-15 minutes

## Support

If you encounter issues:
1. Check the deployment logs
2. Verify your Cloudflare API token permissions
3. Ensure DNS is pointing to your server IP
4. Run the SSL validation script: `./scripts/validate_ssl_certificate.sh`

---

**Ready to deploy?** Run the deployment script after configuring your API token!