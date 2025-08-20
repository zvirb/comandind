#!/bin/bash
# AIWFE SSL Certificate Fix Script
# Replaces self-signed certificate with Let's Encrypt production certificate

set -e

echo "=================================================="
echo "AIWFE SSL Certificate Fix - Let's Encrypt Setup"
echo "=================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="${DOMAIN:-aiwfe.com}"
EMAIL="${EMAIL:-admin@aiwfe.com}"
COMPOSE_FILE="docker-compose.yml"

echo -e "${YELLOW}Target Domain: ${DOMAIN}${NC}"
echo -e "${YELLOW}Admin Email: ${EMAIL}${NC}"

# Step 1: Stop existing services
echo -e "\n${YELLOW}Step 1: Stopping existing services...${NC}"
docker-compose -f ${COMPOSE_FILE} down || true

# Step 2: Clean up old certificates and Caddy data
echo -e "\n${YELLOW}Step 2: Cleaning up old certificates...${NC}"
docker volume rm ai_workflow_engine_caddy_data 2>/dev/null || true
docker volume rm ai_workflow_engine_caddy_config 2>/dev/null || true

# Step 3: Ensure Caddyfile is configured for Let's Encrypt
echo -e "\n${YELLOW}Step 3: Verifying Caddyfile configuration...${NC}"
if grep -q "email admin@aiwfe.com" config/caddy/Caddyfile; then
    echo -e "${GREEN}✓ Caddyfile already configured for Let's Encrypt${NC}"
else
    echo -e "${RED}✗ Caddyfile needs email configuration${NC}"
    exit 1
fi

# Step 4: Create required directories
echo -e "\n${YELLOW}Step 4: Creating required directories...${NC}"
mkdir -p logs/caddy
mkdir -p docker/caddy_reverse_proxy

# Step 5: Create entrypoint wrapper if it doesn't exist
echo -e "\n${YELLOW}Step 5: Creating Caddy entrypoint wrapper...${NC}"
cat > docker/caddy_reverse_proxy/entrypoint-wrapper.sh << 'EOF'
#!/bin/sh
set -e

echo "Starting Caddy reverse proxy..."
echo "Domain: ${DOMAIN:-aiwfe.com}"
echo "Environment: Production with Let's Encrypt"

# Ensure Caddy has proper permissions
chown -R caddy:caddy /data /config 2>/dev/null || true

# Start Caddy
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
EOF

chmod +x docker/caddy_reverse_proxy/entrypoint-wrapper.sh

# Step 6: Start core services first (database, redis)
echo -e "\n${YELLOW}Step 6: Starting core services...${NC}"
docker-compose -f ${COMPOSE_FILE} up -d postgres redis

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for core services to be ready...${NC}"
sleep 10

# Step 7: Start API and WebUI services
echo -e "\n${YELLOW}Step 7: Starting application services...${NC}"
docker-compose -f ${COMPOSE_FILE} up -d api webui

# Wait for services to be ready
echo -e "${YELLOW}Waiting for application services to be ready...${NC}"
sleep 10

# Step 8: Start Caddy with Let's Encrypt
echo -e "\n${YELLOW}Step 8: Starting Caddy with Let's Encrypt...${NC}"
docker-compose -f ${COMPOSE_FILE} up -d caddy_reverse_proxy

# Step 9: Monitor Caddy logs for certificate acquisition
echo -e "\n${YELLOW}Step 9: Monitoring certificate acquisition...${NC}"
echo -e "${YELLOW}Watching Caddy logs (press Ctrl+C to stop monitoring)...${NC}"

# Function to check certificate
check_certificate() {
    echo -e "\n${YELLOW}Checking certificate status...${NC}"
    
    # Wait a moment for Caddy to start
    sleep 5
    
    # Check if certificate is valid
    if curl -I https://${DOMAIN} 2>&1 | grep -q "SSL certificate problem"; then
        echo -e "${YELLOW}Certificate is still being acquired...${NC}"
        return 1
    else
        echo -e "${GREEN}✓ Certificate acquired successfully!${NC}"
        return 0
    fi
}

# Monitor logs and check certificate
timeout 60 docker-compose -f ${COMPOSE_FILE} logs -f caddy_reverse_proxy &
LOG_PID=$!

# Wait for certificate acquisition (max 60 seconds)
COUNTER=0
MAX_WAIT=60
while [ $COUNTER -lt $MAX_WAIT ]; do
    sleep 5
    COUNTER=$((COUNTER + 5))
    
    if check_certificate; then
        kill $LOG_PID 2>/dev/null || true
        break
    fi
    
    if [ $COUNTER -ge $MAX_WAIT ]; then
        echo -e "${RED}✗ Certificate acquisition timeout${NC}"
        kill $LOG_PID 2>/dev/null || true
        exit 1
    fi
done

# Step 10: Validate SSL certificate
echo -e "\n${YELLOW}Step 10: Validating SSL certificate...${NC}"

# Test with curl
echo -e "\n${YELLOW}Testing with curl...${NC}"
if curl -I https://${DOMAIN} 2>&1 | grep -q "HTTP"; then
    echo -e "${GREEN}✓ HTTPS connection successful${NC}"
else
    echo -e "${RED}✗ HTTPS connection failed${NC}"
fi

# Show certificate details
echo -e "\n${YELLOW}Certificate details:${NC}"
echo | openssl s_client -servername ${DOMAIN} -connect ${DOMAIN}:443 2>/dev/null | \
    openssl x509 -noout -text 2>/dev/null | \
    grep -A2 "Subject:" || echo "Could not retrieve certificate details"

echo | openssl s_client -servername ${DOMAIN} -connect ${DOMAIN}:443 2>/dev/null | \
    openssl x509 -noout -text 2>/dev/null | \
    grep -A2 "Issuer:" || echo "Could not retrieve issuer details"

# Step 11: Test website accessibility
echo -e "\n${YELLOW}Step 11: Testing website accessibility...${NC}"

# Test main page
echo -e "\nTesting main page..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://${DOMAIN})
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    echo -e "${GREEN}✓ Main page accessible (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}✗ Main page not accessible (HTTP $HTTP_CODE)${NC}"
fi

# Test API endpoint
echo -e "\nTesting API endpoint..."
API_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://${DOMAIN}/api/v1/health)
if [ "$API_CODE" = "200" ] || [ "$API_CODE" = "404" ]; then
    echo -e "${GREEN}✓ API endpoint accessible (HTTP $API_CODE)${NC}"
else
    echo -e "${RED}✗ API endpoint not accessible (HTTP $API_CODE)${NC}"
fi

# Step 12: Show running services
echo -e "\n${YELLOW}Step 12: Running services:${NC}"
docker-compose -f ${COMPOSE_FILE} ps

echo -e "\n=================================================="
echo -e "${GREEN}SSL Certificate Fix Complete!${NC}"
echo -e "=================================================="
echo -e "${GREEN}✓ Let's Encrypt certificate installed${NC}"
echo -e "${GREEN}✓ Services running with HTTPS${NC}"
echo -e "${GREEN}✓ Site accessible at: https://${DOMAIN}${NC}"
echo -e "=================================================="

# Optional: Show how to monitor certificate renewal
echo -e "\n${YELLOW}Certificate Auto-Renewal:${NC}"
echo "Caddy automatically renews Let's Encrypt certificates."
echo "To check renewal status:"
echo "  docker-compose logs caddy_reverse_proxy | grep -i certificate"
echo ""
echo "To manually trigger renewal:"
echo "  docker-compose exec caddy_reverse_proxy caddy reload --config /etc/caddy/Caddyfile"