# 📋 Step-by-Step Cloudflare Migration Instructions

**Goal**: Migrate aiwfe.com from Dynu DNS to Cloudflare for free SSL certificates and better performance.

**Time**: 15 minutes setup + 1-24 hours DNS propagation

---

## 🔧 PART 1: Setup Cloudflare (10 minutes)

### Step 1: Create Cloudflare Account
1. **Open browser** and go to: https://cloudflare.com/sign-up
2. **Enter your email** and create a password
3. **Click "Create Account"**
4. **Verify your email** (check your inbox)

### Step 2: Add Your Domain
1. **Click "Add a site"** (big blue button)
2. **Type**: `aiwfe.com`
3. **Click "Add site"**

### Step 3: Choose Free Plan
1. **Select "Free"** plan (it's perfect for your needs)
2. **Click "Continue"**

### Step 4: Review DNS Records
Cloudflare will scan and import your existing DNS records from Dynu:

1. **Check the list** - you should see:
   - **A record**: `aiwfe.com` pointing to `220.253.17.93`
   - **Maybe other records** like `www` or `*`

2. **If the A record is missing or wrong**:
   - Click "Add record"
   - Type: A
   - Name: aiwfe.com (or just @)
   - IPv4 address: 220.253.17.93
   - Click "Save"

3. **Add WWW record** (if not present):
   - Click "Add record"
   - Type: CNAME
   - Name: www
   - Target: aiwfe.com
   - Click "Save"

4. **Click "Continue"**

### Step 5: Get Your Nameservers
Cloudflare will show you **two nameservers** like:
```
alice.ns.cloudflare.com
bob.ns.cloudflare.com
```

**📝 WRITE THESE DOWN** - you'll need them in the next part!

**⚠️ DON'T CLICK "Done" YET** - leave this tab open!

---

## 🌐 PART 2: Update Domain Nameservers (5 minutes)

You need to update the nameservers where you **bought** your domain (not at Dynu).

### Find Your Domain Registrar
The domain registrar is where you originally purchased `aiwfe.com`. Common ones:
- GoDaddy
- Namecheap  
- Google Domains
- Porkbun
- Domain.com
- Gandi
- Hover

### Update Nameservers at Your Registrar

**For GoDaddy:**
1. Log into your GoDaddy account
2. Go to "My Products" → "All Products and Services" 
3. Find aiwfe.com → Click "DNS"
4. Scroll down to "Nameservers"
5. Click "Change"
6. Select "I'll use my own nameservers"
7. Enter the two Cloudflare nameservers
8. Click "Save"

**For Namecheap:**
1. Log into Namecheap account
2. Go to "Domain List"
3. Find aiwfe.com → Click "Manage"
4. Go to "Nameservers" section
5. Select "Custom DNS"
6. Enter the two Cloudflare nameservers
7. Click "Save"

**For Google Domains:**
1. Log into domains.google.com
2. Find aiwfe.com → Click "Manage"
3. Go to "DNS" tab
4. Scroll to "Name servers"
5. Select "Use custom name servers"
6. Enter the two Cloudflare nameservers
7. Click "Save"

**For Other Registrars:**
Look for sections called:
- "DNS Management"
- "Nameservers" 
- "DNS Settings"
- "Name Servers"

### After Updating Nameservers
1. **Go back to Cloudflare tab**
2. **Click "Done"**
3. **Wait for confirmation** (Cloudflare will check periodically)

---

## 🔑 PART 3: Get Cloudflare API Token (3 minutes)

### Step 1: Go to API Tokens Page
1. **In Cloudflare dashboard**, click your profile icon (top right)
2. **Click "My Profile"**
3. **Click "API Tokens" tab**
4. **Click "Create Token"**

### Step 2: Create DNS Edit Token
1. **Click "Use template"** next to "Edit zone DNS"
2. **Configure the token**:
   - Zone Resources: Include → Specific zone → Select `aiwfe.com`
   - Leave other settings as default
3. **Click "Continue to summary"**
4. **Click "Create Token"**

### Step 3: Save Your Token
1. **Copy the token** (long string starting with something like `1234abcd...`)
2. **Save it somewhere safe** - you won't see it again!
3. **Click "I have copied the token"**

---

## ⏱️ PART 4: Wait for DNS Propagation (1-24 hours)

### Check Migration Status
Run this command to see if migration is complete:

```bash
dig NS aiwfe.com
```

**When it shows Cloudflare nameservers** (instead of Dynu), the migration is complete!

**Before migration** (shows Dynu):
```
aiwfe.com. IN NS ns1.dynu.com.
aiwfe.com. IN NS ns2.dynu.com.
```

**After migration** (shows Cloudflare):
```
aiwfe.com. IN NS alice.ns.cloudflare.com.
aiwfe.com. IN NS bob.ns.cloudflare.com.
```

### Timeline Expectations:
- **1-4 hours**: Most common (migration complete)
- **4-12 hours**: Sometimes takes longer
- **24 hours**: Maximum time (very rare)

---

## 🚀 PART 5: Deploy SSL Certificates (Once DNS Migration Complete)

### Step 1: Configure Environment File
```bash
# Edit the environment file:
nano /home/marku/ai_workflow_engine/config/secrets/.env.production
```

**Replace this line**:
```
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token_here
```

**With your actual token**:
```
CLOUDFLARE_API_TOKEN=1234abcd_your_actual_token_from_part_3
```

**Save and exit**: Press `Ctrl+X`, then `Y`, then `Enter`

### Step 2: Run Deployment Script
```bash
# Navigate to project directory:
cd /home/marku/ai_workflow_engine

# Run the deployment script:
./scripts/deploy_authentication_flow.sh
```

This script will:
1. ✅ Fix backend authentication issues
2. ✅ Deploy Let's Encrypt certificates via Cloudflare
3. ✅ Test the complete authentication flow
4. ✅ Generate a success report

### Step 3: Test Success
1. **Open browser** and go to: https://aiwfe.com
2. **Look for**:
   - ✅ **No certificate warnings**
   - ✅ **Green padlock** in address bar
   - ✅ **Login form loads** without errors
   - ✅ **Can submit login form**

---

## 🆘 Troubleshooting

### "DNS hasn't propagated yet"
**Symptoms**: `dig NS aiwfe.com` still shows Dynu nameservers
**Solution**: Wait longer, propagation can take up to 24 hours

### "Can't find where to update nameservers"
**Solution**: 
1. Check your email for domain purchase receipts
2. Look for the company name (that's your registrar)
3. Log into that company's website
4. Look for "DNS", "Nameservers", or "Domain Management"

### "Cloudflare API token doesn't work"
**Symptoms**: Deployment script fails with API errors
**Solutions**:
1. Double-check the token is copied correctly (no extra spaces)
2. Verify the token has permissions for aiwfe.com zone
3. Make sure you selected "Edit zone DNS" template

### "Site still shows certificate errors"
**Symptoms**: Browser still shows "Not secure"
**Solutions**:
1. Wait 15 minutes after deployment script completes
2. Clear browser cache (Ctrl+Shift+R)
3. Try in incognito/private browsing mode
4. Check deployment script logs for errors

---

## 📞 Need Help?

### Quick Status Checks:
```bash
# Check if DNS migration is complete:
dig NS aiwfe.com

# Check current certificate status:
curl -I https://aiwfe.com

# Check deployment logs:
docker-compose logs -f
```

### Common Questions:

**Q: Will my site go down during migration?**
A: No! Cloudflare imports your existing DNS records, so there's no downtime.

**Q: How long until I get SSL certificates?**
A: About 15 minutes after DNS propagation completes.

**Q: What if I made a mistake?**
A: You can always change nameservers back to Dynu if needed.

**Q: Can I test before the migration is complete?**
A: You should wait until DNS propagation is complete before running the deployment script.

---

## 🎯 Summary Checklist

- [ ] Created Cloudflare account
- [ ] Added aiwfe.com domain  
- [ ] Chose Free plan
- [ ] Verified DNS records (A record pointing to 220.253.17.93)
- [ ] Got Cloudflare nameservers
- [ ] Updated nameservers at domain registrar
- [ ] Created Cloudflare API token
- [ ] Waited for DNS propagation (`dig NS aiwfe.com` shows Cloudflare)
- [ ] Updated environment file with API token
- [ ] Ran deployment script (`./scripts/deploy_authentication_flow.sh`)
- [ ] Tested https://aiwfe.com - no certificate warnings!

**Result**: Free SSL certificates forever + better performance! 🎉