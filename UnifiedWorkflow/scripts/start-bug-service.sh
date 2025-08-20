#!/bin/bash

# Start Bug Submission Service
# Independent container for bug reporting with GitHub integration

set -e

echo "🐛 Starting Bug Submission Service..."

# Load environment variables
if [ -f .env.bug-service ]; then
    export $(cat .env.bug-service | grep -v '^#' | xargs)
    echo "✅ Environment variables loaded"
else
    echo "⚠️  .env.bug-service file not found, using defaults"
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Build and start the bug submission service
echo "🔨 Building bug submission service..."
cd app/bug_submission_service

# Build the container
docker build -t ai_workflow_engine/bug-submission-service .

# Stop existing container if running
docker stop bug-submission-service 2>/dev/null || true
docker rm bug-submission-service 2>/dev/null || true

# Start the container
echo "🚀 Starting bug submission service container..."
docker run -d \
    --name bug-submission-service \
    --network ai_workflow_engine_shared-network \
    -p 8080:8080 \
    -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
    -e GITHUB_REPO_OWNER="${GITHUB_REPO_OWNER:-zvirb}" \
    -e GITHUB_REPO_NAME="${GITHUB_REPO_NAME:-TheArtificialIntelligenceWorkflowEngine}" \
    -e AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-http://api:8000}" \
    -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
    -e BUG_SERVICE_PORT="${BUG_SERVICE_PORT:-8080}" \
    --restart unless-stopped \
    ai_workflow_engine/bug-submission-service

# Wait for service to be ready
echo "⏳ Waiting for service to be ready..."
for i in {1..30}; do
    if curl -f http://localhost:8080/health >/dev/null 2>&1; then
        echo "✅ Bug submission service is ready!"
        break
    fi
    sleep 2
    echo "   Attempt $i/30..."
done

# Show service status
echo ""
echo "📊 Service Status:"
docker ps --filter name=bug-submission-service --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🔗 Service Endpoints:"
echo "   Health Check: http://localhost:8080/health"
echo "   Bug Submission: http://localhost:8080/api/bugs/submit"
echo "   Templates: http://localhost:8080/api/bugs/templates"

echo ""
echo "📱 Frontend Integration:"
echo "   The FloatingUserNav now includes a 'Submit Bug Report' button"
echo "   Bug reports are automatically submitted to GitHub as issues"
echo "   Claude AI integration will process issues automatically"

echo ""
echo "🎉 Bug submission service is now running independently!"
echo "   Even if the main API goes down, users can still submit bug reports."