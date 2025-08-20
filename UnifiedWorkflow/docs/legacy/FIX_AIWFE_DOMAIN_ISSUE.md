# AIWFE.COM Domain Connectivity Fix

## Root Cause Identified
The domain `aiwfe.com` resolves to external IP `220.253.17.93` instead of localhost, causing API calls to fail with "net::ERR_FAILED".

## Critical Fix Required

### Step 1: Add DNS Override
Add the following entries to `/etc/hosts` (requires sudo access):

```bash
sudo nano /etc/hosts
```

Add these lines:
```
# Local development override for aiwfe.com
127.0.0.1 aiwfe.com
127.0.0.1 www.aiwfe.com
```

### Step 2: Verify DNS Resolution
After editing `/etc/hosts`, verify the fix:

```bash
nslookup aiwfe.com
# Should now show 127.0.0.1
```

### Step 3: Test API Connectivity
```bash
curl -k https://aiwfe.com/api/v1/health
# Should return: {"status":"ok","redis_connection":"ok"}
```

### Step 4: Restart Browser
Clear browser DNS cache by restarting the browser or opening in incognito mode.

## Technical Details

**Current DNS Resolution:**
- aiwfe.com → 220.253.17.93 (external server)
- API calls go to wrong destination

**After Fix:**
- aiwfe.com → 127.0.0.1 (local Docker containers)
- API calls route through Caddy to API container

**Docker Network Configuration:**
- Network: ai_workflow_engine_secure_net (172.20.0.0/16)
- Caddy: Ports 80, 443, 8443 exposed
- API: Internal port 8000
- All containers healthy and communicating

**SSL Certificate Status:**
- ✅ Certificate includes aiwfe.com in SAN list
- ✅ Valid for both localhost and aiwfe.com
- ✅ Caddy serving correct certificate

## Alternative Solutions

### Option 1: Use localhost for development
Access the application via `https://localhost` instead of `https://aiwfe.com`

### Option 2: Browser DNS override
Use browser extensions or developer tools to override DNS for aiwfe.com

### Option 3: Local DNS server
Set up dnsmasq or similar local DNS server with custom overrides

## Validation Commands

```bash
# Check current DNS resolution
nslookup aiwfe.com

# Test localhost access (should work)
curl -k https://localhost/api/v1/health

# Test aiwfe.com access (after fix)
curl -k https://aiwfe.com/api/v1/health

# Check Docker containers
docker ps --format "table {{.Names}}\t{{.Status}}"

# Check Caddy logs
docker logs ai_workflow_engine-caddy_reverse_proxy-1 --tail 10
```

## Expected Result
After applying the DNS override fix, the frontend at `https://aiwfe.com` will successfully connect to the API endpoints, resolving the login failure issue.