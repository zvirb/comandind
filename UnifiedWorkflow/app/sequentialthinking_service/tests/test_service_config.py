#!/usr/bin/env python3
"""
Basic tests for Sequential Thinking Service configuration
"""

import os
import sys
import json
from pathlib import Path

# Add service to path
service_path = Path(__file__).parent.parent
sys.path.insert(0, str(service_path))

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        # Test basic imports
        from config import get_settings
        print("✓ Config import successful")
        
        from models import ReasoningRequest, ReasoningResponse
        print("✓ Models import successful")
        
        # Test service imports (these might fail without dependencies)
        try:
            from services import (
                LangGraphReasoningService,
                RedisCheckpointService,
                OllamaClientService,
                MemoryIntegrationService,
                AuthenticationService
            )
            print("✓ Services import successful")
        except ImportError as e:
            print(f"⚠️ Services import failed (expected without dependencies): {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    print("\n🔧 Testing configuration...")
    
    try:
        from config import get_settings
        settings = get_settings()
        
        print(f"✓ Service name: {settings.SERVICE_NAME}")
        print(f"✓ Port: {settings.PORT}")
        print(f"✓ Redis URL: {settings.REDIS_URL}")
        print(f"✓ Ollama URL: {settings.OLLAMA_URL}")
        print(f"✓ Memory Service URL: {settings.MEMORY_SERVICE_URL}")
        print(f"✓ Max thinking steps: {settings.MAX_THINKING_STEPS}")
        print(f"✓ mTLS enabled: {settings.MTLS_ENABLED}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_models():
    """Test Pydantic model creation"""
    print("\n📋 Testing data models...")
    
    try:
        from models import ReasoningRequest, ReasoningResponse, ThoughtStep, ReasoningState
        
        # Test request model
        request = ReasoningRequest(
            query="What is 2 + 2?",
            max_steps=5,
            enable_memory_integration=True,
            enable_self_correction=True
        )
        print(f"✓ ReasoningRequest created: {request.session_id[:8]}...")
        
        # Test response model  
        response = ReasoningResponse(
            session_id=request.session_id,
            query=request.query,
            state=ReasoningState.INITIALIZED,
            confidence_score=0.8
        )
        print(f"✓ ReasoningResponse created: {response.state}")
        
        # Test step model
        step = ThoughtStep(
            step_number=1,
            thought="This is a test thought",
            confidence=0.9
        )
        print(f"✓ ThoughtStep created: step {step.step_number}")
        
        return True
        
    except Exception as e:
        print(f"❌ Models test failed: {e}")
        return False

def test_docker_structure():
    """Test Docker-related files exist"""
    print("\n🐳 Testing Docker structure...")
    
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Check Dockerfile
        dockerfile = project_root / "docker" / "sequentialthinking-service" / "Dockerfile"
        if dockerfile.exists():
            print("✓ Dockerfile exists")
        else:
            print("❌ Dockerfile missing")
            return False
            
        # Check entrypoint
        entrypoint = project_root / "docker" / "sequentialthinking-service" / "entrypoint-wrapper.sh"
        if entrypoint.exists():
            print("✓ Entrypoint script exists")
            if os.access(entrypoint, os.X_OK):
                print("✓ Entrypoint script is executable")
            else:
                print("⚠️ Entrypoint script not executable")
        else:
            print("❌ Entrypoint script missing")
            return False
            
        # Check requirements
        requirements = service_path / "requirements.txt"
        if requirements.exists():
            print("✓ Requirements file exists")
            with open(requirements) as f:
                deps = f.read()
                if "langgraph" in deps and "redis" in deps and "fastapi" in deps:
                    print("✓ Key dependencies listed")
                else:
                    print("⚠️ Some key dependencies may be missing")
        else:
            print("❌ Requirements file missing")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Docker structure test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧠 Sequential Thinking Service - Configuration Tests")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_config,
        test_models, 
        test_docker_structure
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! Service configuration looks good.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())