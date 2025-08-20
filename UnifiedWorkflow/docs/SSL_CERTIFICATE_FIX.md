# SSL Certificate Infrastructure Fix

## Problem Summary

The AI Workflow Engine application was experiencing SSL certificate issues that prevented users from accessing the login form. The main problems were:

1. **ServiceWorker Registration Failure**: "Failed to register a ServiceWorker for scope ('https://localhost/') with script ('https://localhost/service-worker.js'): An SSL certificate error occurred when fetching the script"
2. **Browser Certificate Warnings**: Users couldn't access the application due to SSL certificate validation errors
3. **Client Certificate Requirements**: The localhost development configuration required client certificates, which browsers don't have
4. **Missing Subject Alternative Names**: Certificates didn't include localhost and 127.0.0.1 as valid hostnames

## Root Cause Analysis

1. **Incomplete Subject Alternative Names (SAN)**: The original Caddy certificates were missing proper SAN entries for localhost development
2. **Client Certificate Enforcement**: The Caddy configuration required client certificates for localhost, which is incompatible with browser access
3. **Certificate Loading Issues**: Caddy was auto-generating local certificates instead of using the custom mTLS certificates
4. **Volume Synchronization**: Updated certificates weren't being properly propagated to Docker containers

## Solution Implementation

### 1. Certificate Regeneration with Proper SAN

**Problem**: Original certificates lacked proper Subject Alternative Names for localhost development.

**Solution**: Regenerated Caddy certificates with correct SAN entries:

```bash
# Revoke old certificate
cd /home/marku/ai_workflow_engine/certs/ca
openssl ca -config openssl.cnf -revoke newcerts/1007.pem

# Generate new CSR with proper SAN configuration
cd /home/marku/ai_workflow_engine/certs/caddy_reverse_proxy
openssl req -new -key caddy_reverse_proxy-key.pem -out caddy_reverse_proxy-csr.pem -config caddy_reverse_proxy-ext.cnf

# Sign with CA including SAN extensions
cd /home/marku/ai_workflow_engine/certs/ca
openssl ca -config openssl.cnf -extensions v3_req -extfile ../caddy_reverse_proxy/caddy_reverse_proxy-ext.cnf -in ../caddy_reverse_proxy/caddy_reverse_proxy-csr.pem -out ../caddy_reverse_proxy/caddy_reverse_proxy-cert.pem -batch
```

**Verification**: The new certificate includes proper SAN entries:
```
X509v3 Subject Alternative Name: 
    DNS:caddy, DNS:localhost, IP Address:127.0.0.1, DNS:*.ai-workflow-engine.local
```

### 2. Caddy Configuration Updates

**Problem**: Caddy configuration required client certificates for localhost development.

**Solution**: Updated `/home/marku/ai_workflow_engine/config/caddy/Caddyfile-mtls`:

```caddyfile
# Before (problematic)
localhost, 127.0.0.1, *.local, :443 {
    tls /etc/certs/caddy_reverse_proxy/unified-cert.pem /etc/certs/caddy_reverse_proxy/unified-key.pem {
        client_auth {
            mode request
            trusted_ca_cert_file /etc/certs/caddy_reverse_proxy/rootCA.pem
        }
    }
}

# After (fixed)
localhost, 127.0.0.1, *.local, :443 {
    # Enable HTTPS with our certificates but no client certificate requirement for development
    tls /etc/certs/caddy_reverse_proxy/unified-cert.pem /etc/certs/caddy_reverse_proxy/unified-key.pem {
        protocols tls1.2 tls1.3
    }
}
```

### 3. Certificate Bundle Updates

**Problem**: Docker secrets contained outdated certificate bundles.

**Solution**: Updated certificate bundle files in secrets directory:

```bash
# Update certificate bundle with CA chain
cat caddy_reverse_proxy-cert.pem rootCA.pem > unified-cert.pem

# Update secrets directory
cp unified-cert.pem /home/marku/ai_workflow_engine/secrets/caddy_reverse_proxy_cert_bundle.pem
cp caddy_reverse_proxy-key.pem /home/marku/ai_workflow_engine/secrets/caddy_reverse_proxy_private_key.pem
```

### 4. Docker Volume Certificate Updates

**Problem**: Docker containers were using cached certificates from the `certs` volume.

**Solution**: Updated certificates in the Docker volume using a temporary container:

```bash
docker run --rm -v ai_workflow_engine_certs:/tmp/certs-volume -v /home/marku/ai_workflow_engine/certs:/host-certs alpine sh -c "
cp -v /host-certs/caddy_reverse_proxy/unified-cert.pem /tmp/certs-volume/caddy_reverse_proxy/unified-cert.pem &&
cp -v /host-certs/caddy_reverse_proxy/unified-key.pem /tmp/certs-volume/caddy_reverse_proxy/unified-key.pem &&
chmod 644 /tmp/certs-volume/caddy_reverse_proxy/*.pem &&
chmod 600 /tmp/certs-volume/caddy_reverse_proxy/*-key.pem
"
```

## Verification Steps

### 1. Certificate Validation
```bash
# Verify certificate chain
openssl verify -CAfile /home/marku/ai_workflow_engine/certs/ca/certs/ca-cert.pem /home/marku/ai_workflow_engine/certs/caddy_reverse_proxy/unified-cert.pem

# Check SAN entries
openssl x509 -in /home/marku/ai_workflow_engine/certs/caddy_reverse_proxy/unified-cert.pem -text -noout | grep -A 5 "Subject Alternative Name"
```

### 2. HTTPS Connection Test
```bash
# Test HTTPS connectivity
curl -I -k --max-time 10 https://localhost:443

# Verify certificate in browser
# Navigate to https://localhost and check certificate details
```

### 3. ServiceWorker Registration
- Navigate to https://localhost in browser
- Open Developer Tools > Application > Service Workers
- Verify ServiceWorker registers successfully without SSL errors

## Results

✅ **SSL Certificate Errors Resolved**: Certificates now include proper SAN for localhost and 127.0.0.1  
✅ **Client Certificate Requirement Removed**: Browsers can access localhost without client certificates  
✅ **ServiceWorker Registration Fixed**: ServiceWorkers can now register successfully  
✅ **Certificate Chain Valid**: Complete certificate chain with proper CA validation  
✅ **Docker Container Updates**: Certificates properly propagated to running containers  

## Troubleshooting

### Common Issues

1. **Caddy Still Using Auto-Generated Certificates**
   - Verify certificates are properly mounted in container
   - Check Caddy logs for certificate loading issues
   - Ensure Docker volume contains updated certificates

2. **Certificate Permission Errors** 
   - Private keys should have 600 permissions
   - Certificate files should have 644 permissions
   - Container user must have read access to certificate files

3. **SAN Validation Failures**
   - Verify certificate includes localhost and 127.0.0.1 in SAN
   - Check browser certificate details for proper SAN entries
   - Ensure certificate is not expired

### Recovery Commands

```bash
# Restart Caddy with updated certificates
docker compose -f docker-compose-mtls.yml restart caddy_reverse_proxy

# Check certificate loading in container
docker exec ai_workflow_engine-caddy_reverse_proxy-1 ls -la /etc/certs/caddy_reverse_proxy/

# View Caddy logs for certificate issues
docker logs ai_workflow_engine-caddy_reverse_proxy-1
```

## Security Considerations

- **Development vs Production**: This fix is designed for localhost development. Production environments should use proper CA-signed certificates
- **Client Certificate Security**: Removed client certificate requirements only for localhost. Production mTLS endpoints (port 8443) still require client certificates
- **Certificate Rotation**: Updated certificates are valid for 1 year and will need rotation before expiration

## Files Modified

1. `/home/marku/ai_workflow_engine/config/caddy/Caddyfile-mtls` - Removed client certificate requirement for localhost
2. `/home/marku/ai_workflow_engine/certs/caddy_reverse_proxy/caddy_reverse_proxy-cert.pem` - New certificate with proper SAN
3. `/home/marku/ai_workflow_engine/certs/caddy_reverse_proxy/unified-cert.pem` - Updated certificate bundle
4. `/home/marku/ai_workflow_engine/secrets/caddy_reverse_proxy_cert_bundle.pem` - Updated Docker secret
5. `/home/marku/ai_workflow_engine/secrets/caddy_reverse_proxy_private_key.pem` - Updated private key

---

**Implementation Date**: August 4, 2025  
**Status**: ✅ Resolved  
**Impact**: Critical - Enables browser access to application  