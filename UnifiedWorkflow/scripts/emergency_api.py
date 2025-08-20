#!/usr/bin/env python3
"""Emergency minimal API to restore production access"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

app = FastAPI(title="AI Workflow Engine Emergency API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    # Serve the emergency HTML page
    if os.path.exists("emergency_index.html"):
        with open("emergency_index.html", "r") as f:
            return HTMLResponse(content=f.read())
    return {"message": "AI Workflow Engine - Emergency API Running", "status": "operational"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "emergency-api"}

@app.get("/api/auth/me")
async def auth_me():
    """Minimal auth endpoint for frontend"""
    return {
        "user": {
            "id": "emergency-user",
            "email": "admin@aiwfe.com",
            "username": "admin"
        }
    }

@app.post("/api/auth/login")
async def login():
    """Minimal login endpoint"""
    return {
        "access_token": "emergency-token",
        "token_type": "bearer",
        "user": {
            "id": "emergency-user",
            "email": "admin@aiwfe.com",
            "username": "admin"
        }
    }

@app.get("/api/chat/history")
async def chat_history():
    """Minimal chat history endpoint"""
    return {"conversations": [], "message": "Emergency mode - chat history unavailable"}

@app.post("/api/chat/send")
async def chat_send():
    """Minimal chat send endpoint"""
    return {
        "response": "System is in emergency recovery mode. Full chat functionality will be restored soon.",
        "status": "emergency"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)