#!/usr/bin/env python3
"""
Bug Submission Service - Independent Container
Handles bug report submissions and GitHub integration
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
import httpx
import json
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables and secrets
def read_secret_file(file_path: str, fallback: str = '') -> str:
    """Read secret from file if it exists, otherwise return fallback"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return f.read().strip()
    except Exception as e:
        logger.warning(f"Failed to read secret file {file_path}: {e}")
    return fallback

GITHUB_TOKEN = read_secret_file(os.getenv('GITHUB_TOKEN_FILE', ''), os.getenv('GITHUB_TOKEN', ''))
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER', 'zvirb')
GITHUB_REPO_NAME = os.getenv('GITHUB_REPO_NAME', 'TheArtificialIntelligenceWorkflowEngine')
SERVICE_PORT = int(os.getenv('BUG_SERVICE_PORT', 8080))
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://api:8000')
ANTHROPIC_API_KEY = read_secret_file(os.getenv('ANTHROPIC_API_KEY_FILE', ''), os.getenv('ANTHROPIC_API_KEY', ''))

# Security
security = HTTPBearer()

app = FastAPI(
    title="Bug Submission Service",
    description="Independent bug submission and GitHub integration service",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class BugSubmissionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=10)
    labels: List[str] = Field(default_factory=list)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    autoAssign: bool = Field(default=True)
    createPR: bool = Field(default=True)
    runTests: bool = Field(default=True)

class BugSubmissionResponse(BaseModel):
    success: bool
    issueNumber: Optional[int] = None
    issueUrl: Optional[str] = None
    message: str

class ServiceHealthResponse(BaseModel):
    status: str
    timestamp: str
    github_connected: bool
    auth_service_connected: bool

# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify authentication token with main auth service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/api/auth/verify",
                headers={"Authorization": f"Bearer {credentials.credentials}"},
                timeout=5.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token"
                )
    except httpx.RequestError:
        # If auth service is down, we can still allow submissions with a warning
        logger.warning("Auth service unavailable, allowing submission with limited verification")
        return {"user_id": "unknown", "username": "anonymous"}

# GitHub integration functions
async def create_github_issue(submission: BugSubmissionRequest, user_info: Dict[str, Any]) -> Dict[str, Any]:
    """Create a GitHub issue from the bug submission"""
    
    if not GITHUB_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub integration not configured"
        )
    
    # Prepare issue body with template
    issue_body = f"""## Bug Submission from AI Workflow Engine

**Submitted by:** {user_info.get('username', 'Anonymous')}
**Priority:** {submission.priority.upper()}
**Submission Time:** {datetime.utcnow().isoformat()}Z

---

{submission.body}

---

## Automation Settings
- **Auto-assign Claude:** {'✅ Yes' if submission.autoAssign else '❌ No'}
- **Create PR automatically:** {'✅ Yes' if submission.createPR else '❌ No'}  
- **Run tests:** {'✅ Yes' if submission.runTests else '❌ No'}

## Processing Instructions
This issue was submitted via the AI Workflow Engine Bug Submission Service and should be automatically processed by Claude AI.

**Internal Tracking:**
- Service: bug-submission-service
- User ID: {user_info.get('user_id', 'unknown')}
- Timestamp: {datetime.utcnow().isoformat()}Z
"""

    # Prepare labels
    labels = ['user-submitted', 'bug-submission-service'] + submission.labels
    if submission.priority in ['high', 'critical']:
        labels.append(f'priority-{submission.priority}')
    if submission.autoAssign:
        labels.append('claude-auto-develop')

    # Create GitHub issue
    github_data = {
        "title": submission.title,
        "body": issue_body,
        "labels": labels
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/issues",
                headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json"
                },
                json=github_data,
                timeout=30.0
            )
            
            if response.status_code == 201:
                issue_data = response.json()
                return {
                    "success": True,
                    "issue_number": issue_data["number"],
                    "issue_url": issue_data["html_url"],
                    "issue_data": issue_data
                }
            else:
                logger.error(f"GitHub API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"GitHub API error: {response.status_code}"
                )
                
        except httpx.RequestError as e:
            logger.error(f"GitHub request failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GitHub service unavailable"
            )

async def trigger_claude_processing(issue_data: Dict[str, Any], submission: BugSubmissionRequest) -> None:
    """Trigger Claude AI processing for the created issue"""
    
    if not submission.autoAssign:
        return
    
    # This would integrate with Claude API or webhook
    # For now, we'll log the trigger
    logger.info(f"Claude processing triggered for issue #{issue_data['issue_number']}")
    
    # Future: Integrate with Claude Code CLI or Anthropic API
    # if ANTHROPIC_API_KEY:
    #     # Trigger Claude analysis
    #     pass

# API Routes
@app.get("/health", response_model=ServiceHealthResponse)
async def health_check():
    """Health check endpoint"""
    
    # Check GitHub connectivity
    github_connected = False
    if GITHUB_TOKEN:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}",
                    headers={"Authorization": f"token {GITHUB_TOKEN}"},
                    timeout=5.0
                )
                github_connected = response.status_code == 200
        except:
            github_connected = False
    
    # Check auth service connectivity
    auth_connected = False
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AUTH_SERVICE_URL}/health", timeout=5.0)
            auth_connected = response.status_code == 200
    except:
        auth_connected = False
    
    return ServiceHealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        github_connected=github_connected,
        auth_service_connected=auth_connected
    )

@app.post("/api/bugs/submit", response_model=BugSubmissionResponse)
async def submit_bug(
    submission: BugSubmissionRequest,
    user_info: Dict[str, Any] = Depends(verify_token)
):
    """Submit a bug report and create GitHub issue"""
    
    try:
        logger.info(f"Bug submission from user {user_info.get('username', 'unknown')}: {submission.title}")
        
        # Create GitHub issue
        github_result = await create_github_issue(submission, user_info)
        
        # Trigger Claude processing if requested
        if submission.autoAssign:
            asyncio.create_task(
                trigger_claude_processing(github_result["issue_data"], submission)
            )
        
        return BugSubmissionResponse(
            success=True,
            issueNumber=github_result["issue_number"],
            issueUrl=github_result["issue_url"],
            message=f"Bug report successfully submitted as issue #{github_result['issue_number']}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bug submission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bug submission failed due to internal error"
        )

@app.get("/api/bugs/status/{issue_number}")
async def get_bug_status(issue_number: int, user_info: Dict[str, Any] = Depends(verify_token)):
    """Get status of a submitted bug report"""
    
    if not GITHUB_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub integration not configured"
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/issues/{issue_number}",
                headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                issue_data = response.json()
                return {
                    "issue_number": issue_data["number"],
                    "title": issue_data["title"],
                    "state": issue_data["state"],
                    "created_at": issue_data["created_at"],
                    "updated_at": issue_data["updated_at"],
                    "html_url": issue_data["html_url"],
                    "labels": [label["name"] for label in issue_data["labels"]],
                    "comments": issue_data["comments"]
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bug report not found"
                )
                
    except httpx.RequestError as e:
        logger.error(f"GitHub status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub service unavailable"
        )

@app.get("/api/bugs/templates")
async def get_bug_templates():
    """Get bug report templates"""
    
    templates = {
        "bug_report": {
            "name": "Bug Report",
            "template": """## Bug Description
[Clear description of the bug]

## Steps to Reproduce
1. Step 1
2. Step 2  
3. Step 3

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- OS: 
- Browser/Version: 
- Other relevant info: 
"""
        },
        "feature_request": {
            "name": "Feature Request",
            "template": """## Feature Description
[Clear description of the requested feature]

## Use Case
[Why this feature is needed]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Additional Context
[Any additional information]
"""
        },
        "improvement": {
            "name": "Improvement",
            "template": """## Current Behavior
[How things work now]

## Proposed Improvement
[What should be improved]

## Benefits
[Why this improvement is valuable]

## Implementation Notes
[Any technical considerations]
"""
        }
    }
    
    return templates

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level="info",
        reload=False
    )