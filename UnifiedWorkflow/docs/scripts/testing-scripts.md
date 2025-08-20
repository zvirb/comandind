# Testing Scripts Documentation

Testing scripts provide validation, health checks, and testing utilities for the AI Workflow Engine. These scripts ensure system reliability, security compliance, and performance standards.

## Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `validate_ssl_configuration.sh` | SSL/TLS configuration validation | `./scripts/validate_ssl_configuration.sh` |
| `validate_ssl_fix.py` | Python-based SSL validation | `python ./scripts/validate_ssl_fix.py` |
| `validate_domain_configuration.py` | Domain configuration testing | `python ./scripts/validate_domain_configuration.py` |
| `validate_security_monitoring.sh` | Security monitoring validation | `./scripts/validate_security_monitoring.sh` |
| `test_webui_ssl.py` | Web UI SSL testing | `python ./scripts/test_webui_ssl.py` |
| `test_webui_playwright.py` | Web UI automated testing | `python ./scripts/test_webui_playwright.py` |
| `setup_playwright_user.py` | Playwright test user setup | `python ./scripts/setup_playwright_user.py` |
| `create_playwright_user.py` | Create test user for Playwright | `python ./scripts/create_playwright_user.py` |

---

## scripts/validate_ssl_configuration.sh

**Location:** `/scripts/validate_ssl_configuration.sh`  
**Purpose:** Comprehensive SSL/TLS configuration validation for all services.

### Description
Validates SSL/TLS configuration across all services, including certificate validity, cipher suites, protocol versions, and security compliance.

### Usage
```bash
./scripts/validate_ssl_configuration.sh [OPTIONS]
```

### Options
- `--service <name>` - Validate specific service only
- `--verbose` - Detailed output with debugging information
- `--fix` - Attempt to fix detected issues automatically

### Validation Checks
```bash
# Certificate Validation
- Certificate chain integrity
- Certificate expiration dates  
- Subject Alternative Name (SAN) validation
- Key usage and extended key usage
- Certificate revocation status

# Protocol Validation
- Supported TLS versions (minimum TLS 1.2)
- Cipher suite security
- Perfect Forward Secrecy (PFS) support
- HSTS header presence
- Certificate transparency compliance

# Configuration Validation
- SSL/TLS endpoint accessibility
- mTLS client authentication
- Certificate pinning validation
- OCSP stapling functionality
```

### Services Tested
- **API Service** - REST API endpoints with mTLS
- **Web UI** - HTTPS frontend with proper headers
- **Database** - PostgreSQL SSL connections
- **Redis** - TLS-enabled cache connections
- **Qdrant** - Vector database SSL configuration
- **Caddy** - Reverse proxy SSL termination
- **Monitoring** - Prometheus/Grafana HTTPS

### Output Format
```
🔐 SSL/TLS Configuration Validation
===================================

Testing API Service (api.ai-workflow-engine.local:443)...
✅ Certificate chain valid
✅ Certificate expires in 364 days
✅ TLS 1.3 supported
✅ Strong cipher suites only
✅ HSTS header present
✅ mTLS client authentication working

Testing Web UI (localhost:8080)...
✅ HTTPS redirect working
✅ Security headers present
✅ Certificate valid for domain
⚠️  Certificate expires in 29 days (consider renewal)

Testing Database (postgres:5432)...
✅ SSL connection established
✅ Client certificate authentication
✅ Strong encryption algorithms

Overall Status: ✅ PASS (1 warning)
Recommendations:
- Renew Web UI certificate within 30 days
- Consider enabling OCSP stapling for improved performance
```

### Common Issues Fixed
- **Certificate Chain Issues:** Incomplete certificate chains
- **Weak Ciphers:** Outdated or insecure cipher suites
- **Protocol Issues:** Insecure TLS versions enabled
- **Header Issues:** Missing security headers
- **Certificate Issues:** Invalid or expired certificates

---

## scripts/validate_ssl_fix.py

**Location:** `/scripts/validate_ssl_fix.py`  
**Purpose:** Python-based SSL validation with detailed diagnostics and automated fixes.

### Description
Comprehensive SSL validation tool written in Python that provides detailed certificate analysis, security assessment, and automated remediation capabilities.

### Usage
```bash
python ./scripts/validate_ssl_fix.py [OPTIONS]
```

### Options
- `--host <hostname>` - Validate specific host
- `--port <port>` - Custom port (default: 443)
- `--cert-path <path>` - Validate local certificate file
- `--fix-issues` - Automatically fix detected issues
- `--report <format>` - Generate report (json, html, text)

### Features
```python
# Certificate Analysis
- X.509 certificate parsing and validation
- Certificate chain verification
- Expiration date monitoring
- Key strength analysis
- Certificate transparency log verification

# Security Assessment
- TLS version support analysis
- Cipher suite security evaluation
- HSTS policy validation
- Certificate pinning verification
- OCSP response validation

# Automated Fixes
- Certificate chain repair
- Weak cipher suite disabling
- Security header injection
- Certificate renewal scheduling
- Configuration optimization
```

### Diagnostic Capabilities
```python
# SSL Connection Analysis
def analyze_ssl_connection(hostname, port):
    context = ssl.create_default_context()
    with socket.create_connection((hostname, port)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()
            cipher = ssock.cipher()
            version = ssock.version()
            
            return {
                'certificate': analyze_certificate(cert),
                'cipher_suite': analyze_cipher(cipher),
                'tls_version': version,
                'security_score': calculate_security_score(cert, cipher, version)
            }

# Certificate Validation
def validate_certificate(cert):
    issues = []
    
    # Check expiration
    expiry = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
    days_until_expiry = (expiry - datetime.now()).days
    
    if days_until_expiry < 30:
        issues.append(f"Certificate expires in {days_until_expiry} days")
    
    # Check key size
    public_key = cert['subject']
    if 'RSA' in str(public_key) and get_key_size(cert) < 2048:
        issues.append("Key size less than 2048 bits")
    
    return issues
```

### Report Generation
```json
{
  "validation_results": {
    "timestamp": "2025-08-04T10:30:00Z",
    "host": "api.ai-workflow-engine.local",
    "overall_status": "PASS",
    "security_score": 95,
    "issues": [
      {
        "severity": "warning",
        "category": "certificate_expiry",
        "message": "Certificate expires in 29 days",
        "recommendation": "Schedule certificate renewal"
      }
    ],
    "certificates": [
      {
        "subject": "CN=api.ai-workflow-engine.local",
        "issuer": "CN=AI Workflow Engine Root CA",
        "serial_number": "1234567890",
        "valid_from": "2024-08-04T00:00:00Z",
        "valid_until": "2025-08-04T00:00:00Z",
        "key_algorithm": "RSA",
        "key_size": 4096,
        "signature_algorithm": "SHA256withRSA"
      }
    ],
    "tls_configuration": {
      "supported_versions": ["TLSv1.2", "TLSv1.3"],
      "cipher_suites": [
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "ECDHE-RSA-AES256-GCM-SHA384"
      ],
      "perfect_forward_secrecy": true,
      "hsts_enabled": true
    }
  }
}
```

---

## scripts/validate_domain_configuration.py

**Location:** `/scripts/validate_domain_configuration.py`  
**Purpose:** Domain configuration and DNS validation for the application.

### Description
Validates domain configuration, DNS resolution, and network accessibility for all application endpoints.

### Usage
```bash
python ./scripts/validate_domain_configuration.py [OPTIONS]
```

### Validation Areas
```python
# DNS Resolution
- A/AAAA record validation
- CNAME record verification  
- MX record validation (if applicable)
- DNS propagation checking
- Reverse DNS lookup validation

# Network Accessibility
- Port accessibility testing
- Firewall rule validation
- Load balancer configuration
- CDN configuration (if applicable)
- Geographic accessibility testing

# Domain Security
- Domain certificate validation
- HSTS preload status
- CAA record verification
- DMARC/SPF configuration (if applicable)
- Domain reputation checking
```

### Configuration Tests
```python
# Test domain resolution
def test_domain_resolution(domain):
    try:
        ip_addresses = socket.gethostbyname_ex(domain)[2]
        return {
            'status': 'success',
            'addresses': ip_addresses,
            'resolution_time': measure_resolution_time(domain)
        }
    except socket.gaierror as e:
        return {
            'status': 'failed',
            'error': str(e),
            'recommendation': 'Check DNS configuration'
        }

# Test port accessibility
def test_port_accessibility(host, port, timeout=10):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    
    try:
        result = sock.connect_ex((host, port))
        return result == 0
    finally:
        sock.close()
```

---

## Web UI Testing Scripts

### scripts/test_webui_ssl.py
**Purpose:** Specialized SSL testing for the Web UI component.

### Description
Tests Web UI SSL configuration including HTTPS redirects, security headers, and certificate validation.

### Test Cases
```python
# HTTPS Redirect Testing
def test_https_redirect():
    response = requests.get('http://localhost:8080', allow_redirects=False)
    assert response.status_code == 301
    assert response.headers['Location'].startswith('https://')

# Security Headers Testing  
def test_security_headers():
    response = requests.get('https://localhost:8080')
    required_headers = [
        'Strict-Transport-Security',
        'Content-Security-Policy',
        'X-Frame-Options',
        'X-Content-Type-Options'
    ]
    
    for header in required_headers:
        assert header in response.headers

# Certificate Validation
def test_certificate_validity():
    context = ssl.create_default_context()
    with socket.create_connection(('localhost', 8080)) as sock:
        with context.wrap_socket(sock, server_hostname='localhost') as ssock:
            cert = ssock.getpeercert()
            # Validate certificate properties
            assert cert['subject'][0][0][1] == 'localhost'
            assert not is_certificate_expired(cert)
```

### scripts/test_webui_playwright.py
**Purpose:** Automated browser testing using Playwright framework.

### Description
Comprehensive browser-based testing including user interactions, authentication flows, and UI functionality validation.

### Test Scenarios
```python
# Authentication Flow Testing
async def test_login_flow(page):
    await page.goto('https://localhost:8080')
    await page.fill('#email', 'admin@example.com')
    await page.fill('#password', 'admin_password')
    await page.click('#login-button')
    
    # Verify successful login
    await expect(page.locator('#dashboard')).to_be_visible()

# SSL Certificate Warning Testing
async def test_ssl_certificate_handling(page):
    # Navigate with self-signed certificate
    await page.goto('https://localhost:8080')
    
    # Check if certificate warning is handled properly
    certificate_error = page.locator('.certificate-warning')
    if await certificate_error.is_visible():
        await page.click('#accept-certificate')
    
    # Verify page loads correctly
    await expect(page.locator('#app')).to_be_visible()

# Performance Testing
async def test_page_load_performance(page):
    start_time = time.time()
    await page.goto('https://localhost:8080')
    await page.wait_for_load_state('networkidle')
    load_time = time.time() - start_time
    
    assert load_time < 5.0, f"Page load time {load_time}s exceeds 5s threshold"

# Responsive Design Testing
async def test_responsive_design(page):
    # Test mobile viewport
    await page.set_viewport_size({'width': 375, 'height': 667})
    await page.goto('https://localhost:8080')
    
    # Verify mobile menu is visible
    await expect(page.locator('#mobile-menu')).to_be_visible()
    
    # Test desktop viewport
    await page.set_viewport_size({'width': 1920, 'height': 1080})
    await page.reload()
    
    # Verify desktop layout
    await expect(page.locator('#desktop-sidebar')).to_be_visible()
```

---

## Test User Management Scripts

### scripts/setup_playwright_user.py
**Purpose:** Sets up dedicated test user accounts for Playwright testing.

### Description
Creates and configures test user accounts with appropriate permissions for automated testing scenarios.

### Features
```python
# Test User Creation
def create_test_user(email, password, role='test_user'):
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
        status='active',
        tfa_enabled=False,  # Disable 2FA for testing
        email_verified=True  # Pre-verify for testing
    )
    
    db.add(user)
    db.commit()
    return user

# Test Data Setup
def setup_test_data(user_id):
    # Create test conversations
    test_conversation = Conversation(
        user_id=user_id,
        title="Test Conversation",
        created_at=datetime.utcnow()
    )
    
    # Create test messages
    test_message = Message(
        conversation_id=test_conversation.id,
        content="Test message",
        role="user",
        created_at=datetime.utcnow()
    )
    
    db.add_all([test_conversation, test_message])
    db.commit()
```

### scripts/create_playwright_user.py
**Purpose:** Simplified test user creation for Playwright automation.

### Usage
```bash
python ./scripts/create_playwright_user.py --email test@example.com --password testpass123
```

### Integration
```python
# Playwright test integration
@pytest.fixture
async def authenticated_page(browser):
    page = await browser.new_page()
    
    # Use test user credentials
    await page.goto('https://localhost:8080/login')
    await page.fill('#email', 'test@example.com')
    await page.fill('#password', 'testpass123')
    await page.click('#login-button')
    
    # Wait for authentication
    await page.wait_for_url('**/dashboard')
    
    return page
```

---

## Security Validation Scripts

### scripts/validate_security_monitoring.sh
**Purpose:** Validates security monitoring and alerting systems.

### Description
Tests security monitoring capabilities including intrusion detection, audit logging, and alerting mechanisms.

### Validation Areas
```bash
# Security Event Detection
- Failed authentication attempts
- Suspicious request patterns
- Certificate validation failures
- Unauthorized access attempts

# Audit Logging
- Log completeness and accuracy
- Log integrity and tamper detection
- Log retention and archiving
- Compliance with security standards

# Alerting Systems
- Alert generation for security events
- Alert delivery mechanisms
- Alert escalation procedures
- False positive management
```

### Test Scenarios
```bash
# Test failed authentication detection
test_failed_auth_detection() {
    # Attempt login with invalid credentials
    curl -k -X POST https://localhost:8080/api/auth/login \
        -H "Content-Type: application/json" \
        -d '{"email":"invalid@example.com","password":"wrongpass"}'
    
    # Verify security event was logged
    if grep -q "SECURITY_EVENT.*FAILED_AUTH" logs/security_audit.log; then
        log_success "Failed authentication detection working"
    else
        log_error "Failed authentication not detected"
    fi
}

# Test certificate validation
test_certificate_validation() {
    # Test with invalid certificate
    if ! openssl s_client -connect localhost:8080 -verify_return_error; then
        log_success "Certificate validation working correctly"
    else
        log_error "Certificate validation issue detected"
    fi
}
```

---

## Testing Workflows

### SSL/TLS Validation Workflow
```bash
# 1. Validate SSL configuration
./scripts/validate_ssl_configuration.sh --verbose

# 2. Python-based detailed analysis
python ./scripts/validate_ssl_fix.py --fix-issues

# 3. Domain configuration validation
python ./scripts/validate_domain_configuration.py

# 4. Web UI specific SSL tests
python ./scripts/test_webui_ssl.py
```

### Automated Testing Workflow
```bash
# 1. Setup test environment
python ./scripts/setup_playwright_user.py

# 2. Run automated browser tests
python ./scripts/test_webui_playwright.py

# 3. Validate security monitoring
./scripts/validate_security_monitoring.sh

# 4. Generate test reports
python -m pytest --html=reports/test_report.html
```

### Continuous Integration Testing
```bash
# CI pipeline testing sequence
1. Environment validation
2. SSL/TLS configuration tests
3. Security validation
4. Automated browser tests
5. Performance benchmarks
6. Security monitoring validation
7. Report generation and analysis
```

---

## Test Configuration

### Playwright Configuration
```python
# playwright.config.py
from playwright.sync_api import Playwright

def pytest_configure(config):
    config.playwright = {
        'browser': 'chromium',
        'headless': True,
        'viewport': {'width': 1280, 'height': 720},
        'ignore_https_errors': True,  # For self-signed certificates
        'timeout': 30000
    }
```

### SSL Test Configuration
```python
# ssl_test_config.py
SSL_TEST_CONFIG = {
    'endpoints': [
        {'host': 'localhost', 'port': 8080, 'name': 'WebUI'},
        {'host': 'api.ai-workflow-engine.local', 'port': 443, 'name': 'API'},
        {'host': 'postgres', 'port': 5432, 'name': 'Database'}
    ],
    'security_requirements': {
        'min_tls_version': 'TLSv1.2',
        'required_headers': ['HSTS', 'CSP', 'X-Frame-Options'],
        'cipher_suite_strength': 'HIGH',
        'certificate_key_size': 2048
    }
}
```

---

## Best Practices

### Testing Strategy
1. **Layered Testing:** Multiple levels of validation
2. **Automated Testing:** Integrate with CI/CD pipelines
3. **Security Focus:** Prioritize security testing
4. **Performance Testing:** Include performance benchmarks
5. **Cross-Browser Testing:** Test on multiple browsers

### SSL/TLS Testing
1. **Certificate Validation:** Verify complete certificate chains
2. **Protocol Testing:** Ensure secure protocols only
3. **Cipher Suite Testing:** Validate strong encryption
4. **Header Validation:** Check security headers
5. **Regular Testing:** Automate regular SSL validation

### Security Testing
1. **Threat Modeling:** Test based on threat models
2. **Penetration Testing:** Include security penetration tests
3. **Compliance Testing:** Validate compliance requirements
4. **Monitoring Testing:** Test security monitoring systems
5. **Incident Response:** Test incident response procedures

---

*For advanced testing scenarios and troubleshooting, see the [Testing Guide](../testing.md).*