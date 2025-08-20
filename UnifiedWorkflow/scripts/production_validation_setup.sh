#!/bin/bash

# Production Validation Preparation Script
# Version: 1.0
# Date: 2025-08-14

set -euo pipefail

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PRODUCTION_SITES=("http://aiwfe.com" "https://aiwfe.com")
PLAYWRIGHT_DIR="/home/marku/ai_workflow_engine/tests/playwright"
EVIDENCE_DIR="/home/marku/ai_workflow_engine/.claude/evidence/production_validation"

# Create directories
mkdir -p "${PLAYWRIGHT_DIR}/scenarios"
mkdir -p "${EVIDENCE_DIR}/screenshots"
mkdir -p "${EVIDENCE_DIR}/logs"

# SSL Certificate Validation Function
validate_ssl() {
    local site="$1"
    local cert_info
    cert_info=$(echo | openssl s_client -showcerts -servername "$(echo "$site" | cut -d/ -f3)" -connect "$(echo "$site" | cut -d/ -f3)":443 2>/dev/null | openssl x509 -noout -dates)
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}SSL Certificate Valid for $site${NC}"
        echo "$cert_info"
        return 0
    else
        echo -e "${RED}SSL Certificate Invalid for $site${NC}"
        return 1
    fi
}

# Endpoint Availability Check
check_endpoint() {
    local site="$1"
    local response_code
    response_code=$(curl -o /dev/null -s -w "%{http_code}" "$site")
    
    if [[ "$response_code" -ge 200 && "$response_code" -lt 400 ]]; then
        echo -e "${GREEN}Endpoint $site is AVAILABLE (Response: $response_code)${NC}"
        return 0
    else
        echo -e "${RED}Endpoint $site is UNAVAILABLE (Response: $response_code)${NC}"
        return 1
    fi
}

# Playwright Test Scenario Templates
create_playwright_scenarios() {
    cat > "${PLAYWRIGHT_DIR}/scenarios/authentication_flow.js" << 'EOF'
const { test, expect } = require('@playwright/test');

test('Authentication Flow', async ({ page }) => {
    // Login Test Scenario Template
    await page.goto('https://aiwfe.com/login');
    // TODO: Replace with actual login credentials handling
    await page.fill('#username', 'test_user');
    await page.fill('#password', 'test_password');
    await page.click('button[type="submit"]');
    
    // Validate login success
    await expect(page).toHaveURL(/dashboard/);
});
EOF

    cat > "${PLAYWRIGHT_DIR}/scenarios/responsive_design.js" << 'EOF'
const { test, expect } = require('@playwright/test');

test('Responsive Design Check', async ({ page }) => {
    const viewports = [
        { width: 375, height: 812 },   // iPhone X
        { width: 1024, height: 768 },  // iPad
        { width: 1920, height: 1080 }  // Desktop
    ];

    for (const viewport of viewports) {
        await page.setViewportSize(viewport);
        await page.goto('https://aiwfe.com');
        
        // Basic responsive checks
        const mainContent = await page.$('main');
        expect(mainContent).not.toBeNull();
    }
});
EOF
}

# Evidence Collection Template
create_evidence_template() {
    cat > "${EVIDENCE_DIR}/validation_report_template.md" << 'EOF'
# Production Validation Report

## Site Availability
- [ ] http://aiwfe.com Endpoint Status
- [ ] https://aiwfe.com Endpoint Status

## SSL Validation
- [ ] SSL Certificate Validity

## Authentication Flow
- [ ] Login Workflow
- [ ] Registration Workflow
- [ ] OAuth Integration

## Responsive Design
- [ ] Mobile Viewport
- [ ] Tablet Viewport
- [ ] Desktop Viewport

## Performance Metrics
- [ ] Initial Load Time
- [ ] Time to Interactive
- [ ] Resource Loading Performance

## Evidence Collected
- Screenshots: 📂 `.claude/evidence/production_validation/screenshots/`
- Logs: 📂 `.claude/evidence/production_validation/logs/`
EOF
}

# Main Execution
main() {
    echo -e "${YELLOW}Starting Production Validation Preparation...${NC}"
    
    # SSL Validation
    for site in "${PRODUCTION_SITES[@]}"; do
        validate_ssl "$site"
        check_endpoint "$site"
    done
    
    # Create Playwright Scenarios
    create_playwright_scenarios
    
    # Create Evidence Template
    create_evidence_template
    
    echo -e "${GREEN}Production Validation Preparation Complete!${NC}"
}

# Run Main
main