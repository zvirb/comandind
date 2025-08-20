# WebUI Test Domain Configuration

This document describes the changes made to configure WebUI tests to use `aiwfe.com` domain instead of `localhost`, with support for both HTTP and HTTPS protocols.

## Overview

The WebUI test configuration has been updated to support flexible domain and protocol configuration through environment variables, with `aiwfe.com` as the new default domain for testing.

## Files Modified

### 1. Test Scripts

#### `/scripts/test_webui_playwright.py`
- Added environment variable support for `WEBUI_TEST_DOMAIN` and `WEBUI_TEST_PROTOCOL`
- Added command-line argument parsing for flexible testing
- Default URL changed from `https://localhost` to `https://aiwfe.com`

**New Usage:**
```bash
# Use defaults (https://aiwfe.com)
python scripts/test_webui_playwright.py

# Test with custom domain
python scripts/test_webui_playwright.py --domain localhost --protocol https

# Test with HTTP
python scripts/test_webui_playwright.py --domain aiwfe.com --protocol http
```

#### `/scripts/test_webui_ssl.py`
- Added environment variable support for domain and protocol configuration
- Updated error messages and help text to use dynamic domain references
- Enhanced argument parser with domain and protocol options

**New Usage:**
```bash
# Use defaults (https://aiwfe.com)
python scripts/test_webui_ssl.py

# Test specific configuration
python scripts/test_webui_ssl.py --domain aiwfe.com --protocol https
```

### 2. WebUI Configuration

#### `/app/webui/vite.config.js`
- Added `aiwfe.com` and `www.aiwfe.com` to `allowedHosts`
- Added CORS origins for `aiwfe.com` domain (both HTTP and HTTPS)

#### `/app/webui/src/lib/utils/environmentConfig.js`
- Added `aiwfe.com` and `www.aiwfe.com` as development environment hostnames
- Updated cookie domain configuration to support `aiwfe.com`
- Enhanced cookie clearing to handle both `localhost` and `aiwfe.com` domains

### 3. Backend Test Files

#### `/test_backend_authentication_fixes.py`
- Added environment variable support for test domain configuration
- Replaced hardcoded `https://localhost` URLs with dynamic `TEST_BASE_URL`

#### `/test_complete_auth_flow.py`
- Added environment variable support for domain, protocol, and port
- Updated base URL and WebSocket URL construction to use environment variables

### 4. Environment Configuration

#### `/.env.test` (New File)
Template environment file with configuration options:
```env
# Test domain configuration
WEBUI_TEST_DOMAIN=aiwfe.com
WEBUI_TEST_PROTOCOL=https

# Alternative configurations
# WEBUI_TEST_DOMAIN=localhost
# WEBUI_TEST_PROTOCOL=http
```

#### `/scripts/validate_domain_configuration.py` (New File)
Validation script to test domain configuration and connectivity.

## Environment Variables

### Primary Configuration
- `WEBUI_TEST_DOMAIN`: Domain to test (default: `aiwfe.com`)
- `WEBUI_TEST_PROTOCOL`: Protocol to use - `http` or `https` (default: `https`)
- `WEBUI_TEST_PORT`: Port number for non-standard configurations (optional)

### Usage Examples

#### Test with aiwfe.com (HTTPS)
```bash
export WEBUI_TEST_DOMAIN=aiwfe.com
export WEBUI_TEST_PROTOCOL=https
python scripts/test_webui_playwright.py
```

#### Test with localhost (HTTPS)
```bash
export WEBUI_TEST_DOMAIN=localhost
export WEBUI_TEST_PROTOCOL=https
python scripts/test_webui_playwright.py
```

#### Test with HTTP
```bash
export WEBUI_TEST_DOMAIN=aiwfe.com
export WEBUI_TEST_PROTOCOL=http
python scripts/test_webui_playwright.py
```

## Domain Setup Requirements

### For aiwfe.com Testing

1. **DNS/Hosts Configuration**: Ensure `aiwfe.com` resolves to your local environment
   ```bash
   # Add to /etc/hosts (Linux/macOS) or C:\Windows\System32\drivers\etc\hosts (Windows)
   127.0.0.1 aiwfe.com
   127.0.0.1 www.aiwfe.com
   ```

2. **SSL Certificates**: Generate certificates for `aiwfe.com` domain
   ```bash
   # Generate certificates for aiwfe.com
   ./scripts/security/setup_mtls_infrastructure.sh setup --domain aiwfe.com
   ```

3. **Reverse Proxy Configuration**: Update Caddy configuration to serve `aiwfe.com`

### For localhost Testing

Use the existing localhost configuration:
```bash
export WEBUI_TEST_DOMAIN=localhost
export WEBUI_TEST_PROTOCOL=https
```

## Testing Procedures

### 1. Validate Configuration
```bash
python scripts/validate_domain_configuration.py
```

### 2. Test WebUI Functionality
```bash
# Test with default configuration (aiwfe.com HTTPS)
python scripts/test_webui_playwright.py

# Test with localhost
export WEBUI_TEST_DOMAIN=localhost
python scripts/test_webui_playwright.py
```

### 3. Test SSL Configuration
```bash
# Test SSL with aiwfe.com
python scripts/test_webui_ssl.py --domain aiwfe.com --protocol https

# Test SSL with localhost
python scripts/test_webui_ssl.py --domain localhost --protocol https
```

### 4. Test Backend Authentication
```bash
# Test backend with aiwfe.com
export WEBUI_TEST_DOMAIN=aiwfe.com
python test_backend_authentication_fixes.py

# Test backend with localhost
export WEBUI_TEST_DOMAIN=localhost
python test_backend_authentication_fixes.py
```

## Troubleshooting

### Common Issues

1. **Domain Not Resolving**
   - Verify `/etc/hosts` configuration
   - Test with `ping aiwfe.com`

2. **SSL Certificate Errors**
   - Ensure certificates are generated for the correct domain
   - Check certificate paths in Vite configuration

3. **CORS Errors** 
   - Verify domain is added to Vite CORS configuration
   - Check backend CORS settings

4. **Connection Refused**
   - Ensure Docker services are running
   - Verify reverse proxy (Caddy) is configured and running

### Debugging Commands

```bash
# Test connectivity
curl -k https://aiwfe.com
curl -k https://localhost

# Check environment variables
python -c "import os; print(f'Domain: {os.getenv(\"WEBUI_TEST_DOMAIN\", \"aiwfe.com\")}')"

# Validate test configuration
python scripts/validate_domain_configuration.py
```

## Migration Guide

### From localhost to aiwfe.com

1. **Set up domain resolution**: Add `aiwfe.com` to `/etc/hosts`
2. **Generate certificates**: Create SSL certificates for `aiwfe.com`
3. **Update environment**: Set `WEBUI_TEST_DOMAIN=aiwfe.com`
4. **Test configuration**: Run validation script
5. **Run tests**: Execute test scripts with new domain

### From aiwfe.com back to localhost

1. **Update environment**: Set `WEBUI_TEST_DOMAIN=localhost`
2. **Test configuration**: Run validation script
3. **Run tests**: Execute test scripts

## Benefits

1. **Flexibility**: Easy switching between test domains
2. **Real-world Testing**: Test with custom domains that mirror production
3. **Environment Separation**: Different domains for different test environments
4. **Backward Compatibility**: Maintains support for localhost testing
5. **Protocol Flexibility**: Support for both HTTP and HTTPS testing

## Future Enhancements

1. **Multi-domain Testing**: Support testing against multiple domains simultaneously
2. **Environment Profiles**: Pre-configured environment profiles for different test scenarios
3. **Automated Domain Setup**: Scripts to automatically configure domains and certificates
4. **CI/CD Integration**: Environment-specific configurations for automated testing

---

**Note**: This configuration maintains backward compatibility with existing localhost-based testing while adding support for custom domain testing.

**Test Results**: All configuration changes have been validated using the included validation script, confirming that environment variables are properly read and test scripts are correctly configured.