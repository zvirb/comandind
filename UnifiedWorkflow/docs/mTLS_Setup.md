# mTLS Setup for WebUI Access

This document explains how to configure and use Mutual TLS (mTLS) authentication for accessing the AI Workflow Engine WebUI.

## Overview

mTLS provides enhanced security by requiring both server and client certificates for authentication. This ensures that only authorized users with valid client certificates can access the WebUI.

## Features

- **Server Authentication**: WebUI verifies client certificates against the trusted CA
- **Client Authentication**: Browsers present client certificates to authenticate users
- **Enhanced Security**: Prevents unauthorized access even if passwords are compromised
- **Browser Integration**: Works with all major browsers (Chrome, Firefox, Safari, Edge)

## Setup Process

### 1. Generate Certificates

Run the certificate generation script to create both server and client certificates:

```bash
./scripts/_setup_secrets_and_certs.sh
```

This script will:
- Generate server certificates for all services
- Generate client certificates for WebUI access
- Create a trusted CA root certificate
- Distribute certificates to Docker volumes

### 2. Configure Client Certificates

Run the client configuration script to prepare certificates for browser import:

```bash
./scripts/configure_mtls_client.sh
```

This script will:
- Extract client certificates from Docker volumes
- Create a PKCS#12 file for browser import
- Provide detailed instructions for browser configuration

### 3. Import Client Certificate into Browser

#### Chrome/Edge:
1. Go to Settings → Privacy and Security → Manage certificates
2. Click "Personal" tab → "Import"
3. Select the `webui-client.p12` file
4. Leave password empty (no password set)
5. Complete the import process

#### Firefox:
1. Go to Settings → Privacy & Security → Certificates
2. Click "View Certificates" → "Your Certificates" → "Import"
3. Select the `webui-client.p12` file
4. Leave password empty
5. Complete the import process

#### Safari:
1. Double-click the `webui-client.p12` file
2. It will automatically import into Keychain
3. Enter your system password when prompted

### 4. Access the WebUI

#### Production Environment (mTLS Always Required)
- **URL**: https://aiwfe.com
- **Authentication**: Requires client certificate
- **Setup**: Complete steps 1-3 above

#### Local Development Environment (mTLS Optional)
- **URL**: https://localhost
- **Default**: No client certificate required (convenient for development)
- **With mTLS**: Use `./scripts/toggle_mtls.sh on` to enable client certificate requirement

**Toggle mTLS for Local Development:**
```bash
# Check current status
./scripts/toggle_mtls.sh status

# Enable mTLS for localhost (requires client certificates)
./scripts/toggle_mtls.sh on

# Disable mTLS for localhost (no client certificates needed)
./scripts/toggle_mtls.sh off
```

Your browser will prompt you to select the client certificate when connecting to environments with mTLS enabled.

## Configuration Details

### Server Configuration

The mTLS configuration is handled by Caddy reverse proxy in `/config/caddy/Caddyfile`:

```caddyfile
# Production domain with mTLS (always enabled)
aiwfe.com {
    tls /etc/certs/caddy_reverse_proxy/unified-cert.pem /etc/certs/caddy_reverse_proxy/unified-key.pem {
        client_auth {
            mode require_and_verify
            trusted_ca_cert_file /etc/certs/caddy_reverse_proxy/rootCA.pem
        }
    }
    
    handle {
        reverse_proxy webui:3000
    }
}

# Local development (mTLS optional - controlled by toggle script)
localhost, 127.0.0.1, *.local, :443 {
    # Default: TLS without client certificate requirement
    tls /etc/certs/caddy_reverse_proxy/unified-cert.pem /etc/certs/caddy_reverse_proxy/unified-key.pem
    
    # When mTLS is enabled via toggle script:
    # tls /etc/certs/caddy_reverse_proxy/unified-cert.pem /etc/certs/caddy_reverse_proxy/unified-key.pem {
    #     client_auth {
    #         mode require_and_verify
    #         trusted_ca_cert_file /etc/certs/caddy_reverse_proxy/rootCA.pem
    #     }
    # }
    
    handle {
        reverse_proxy webui:3000
    }
}
```

### mTLS Toggle Script

The `scripts/toggle_mtls.sh` script provides easy management of mTLS for local development:

- **Purpose**: Enable/disable client certificate requirement for localhost
- **Production**: Always requires mTLS (not affected by toggle)
- **Local**: Can be toggled on/off for development convenience

### Certificate Management

Certificates are managed through Docker volumes:
- **Volume**: `ai_workflow_engine_certs`
- **Server certificates**: `unified-cert.pem`, `unified-key.pem`
- **Client certificates**: `client-cert.pem`, `client-key.pem`
- **Root CA**: `rootCA.pem`

## Security Considerations

### Certificate Protection
- Client certificates are generated per environment
- Private keys are never transmitted over the network
- PKCS#12 files should be stored securely
- Consider password-protecting PKCS#12 files for additional security

### Access Control
- Only users with valid client certificates can access the WebUI
- Certificates are tied to the specific CA root
- Regular certificate rotation is recommended

### Troubleshooting

#### Common Issues:

1. **Browser not prompting for certificate**:
   - Ensure the certificate is properly imported
   - Check browser certificate settings
   - Verify certificate is not expired

2. **Certificate selection not working**:
   - Clear browser cache and cookies
   - Re-import the certificate
   - Check certificate validity dates

3. **Connection refused**:
   - Verify Caddy is running with updated configuration
   - Check certificate file permissions
   - Ensure Docker volume has all certificate files

#### Verification Commands:

```bash
# Check certificate files in Docker volume
docker run --rm -v "ai_workflow_engine_certs:/certs" alpine:latest ls -la /certs/

# Test certificate validity
openssl x509 -in client-cert.pem -text -noout

# Verify certificate chain
openssl verify -CAfile rootCA.pem client-cert.pem
```

## Maintenance

### Certificate Renewal
- Certificates are automatically renewed when running `_setup_secrets_and_certs.sh`
- Users need to re-import updated certificates into browsers
- Consider automating certificate distribution for multiple users

### Backup and Recovery
- Backup the `secrets/` directory and certificate files
- Store the root CA certificate securely
- Document certificate distribution procedures

## Migration Notes

### From Basic TLS to mTLS
- Existing server certificates remain valid
- Client certificates are additional security layer
- Users must import client certificates to continue access
- API endpoints can be configured separately if needed

### Multi-User Environments
- Consider generating individual client certificates per user
- Implement certificate revocation procedures
- Use certificate serial numbers for user identification
- Integrate with existing user management systems

## Integration with CI/CD

For automated testing and deployment:

```bash
# Generate certificates for CI/CD
./scripts/_setup_secrets_and_certs.sh

# Configure test client certificates
./scripts/configure_mtls_client.sh

# Use certificates in automated tests
curl --cert client-cert.pem --key client-key.pem --cacert rootCA.pem https://localhost/
```

## Support

For issues with mTLS configuration:
1. Check the troubleshooting section above
2. Verify all certificates are properly generated
3. Ensure browser supports client certificate authentication
4. Review Caddy logs for TLS handshake errors

Remember: mTLS provides strong authentication but requires proper certificate management and user training for effective deployment.