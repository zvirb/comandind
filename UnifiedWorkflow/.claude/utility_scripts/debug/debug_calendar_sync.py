#!/usr/bin/env python3
"""
Debug Calendar Sync 500 Error
Try to identify the exact source of the 500 error
"""
import sys
import traceback
import asyncio
from datetime import datetime, timezone
import os

# Add app to path
sys.path.insert(0, '/home/marku/ai_workflow_engine/app')

async def debug_calendar_sync():
    """Debug the calendar sync endpoint to find the 500 error source"""
    
    print("="*60)
    print("🔍 DEBUGGING CALENDAR SYNC 500 ERROR")
    print("="*60)
    
    try:
        # Test import of key components
        print("📦 Testing imports...")
        
        try:
            from api.routers.calendar_router import router, trigger_auto_sync
            print("✅ Calendar router imported successfully")
        except Exception as e:
            print(f"❌ Calendar router import failed: {e}")
            traceback.print_exc()
            return
        
        try:
            from api.services.google_calendar_service import GoogleCalendarService
            print("✅ Google Calendar service imported successfully")
        except Exception as e:
            print(f"❌ Google Calendar service import failed: {e}")
            traceback.print_exc()
            
        try:
            from api.services.oauth_token_manager import get_oauth_token_manager
            print("✅ OAuth token manager imported successfully")
        except Exception as e:
            print(f"❌ OAuth token manager import failed: {e}")
            traceback.print_exc()
            
        try:
            from shared.monitoring.calendar_sync_monitoring import (
                start_calendar_sync_monitoring, finish_calendar_sync_monitoring
            )
            print("✅ Calendar sync monitoring imported successfully")
        except Exception as e:
            print(f"❌ Calendar sync monitoring import failed: {e}")
            traceback.print_exc()
            
        try:
            from shared.utils.database_setup import get_async_session
            print("✅ Database setup imported successfully")
        except Exception as e:
            print(f"❌ Database setup import failed: {e}")
            traceback.print_exc()
            
        # Test database connection
        print("\n🗄️ Testing database connection...")
        try:
            from shared.utils.database_setup import get_async_session
            async with get_async_session() as db:
                from sqlalchemy import text
                result = await db.execute(text("SELECT 1"))
                print("✅ Database connection successful")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            traceback.print_exc()
            
        # Test specific monitoring function that might be causing issues
        print("\n📊 Testing calendar sync monitoring...")
        try:
            from shared.monitoring.calendar_sync_monitoring import start_calendar_sync_monitoring
            metrics = start_calendar_sync_monitoring(
                user_id=999999,  # Test user ID
                endpoint="/api/v1/calendar/sync/auto"
            )
            print(f"✅ Monitoring started successfully: {metrics}")
        except Exception as e:
            print(f"❌ Calendar sync monitoring failed: {e}")
            traceback.print_exc()
            
        print("\n🎯 Testing the actual trigger_auto_sync function...")
        
        # Create mock user and session
        try:
            from shared.database.models import User
            from unittest.mock import MagicMock
            
            # Create mock user
            mock_user = MagicMock(spec=User)
            mock_user.id = 999999
            
            # Create mock database session
            mock_db = MagicMock()
            
            print("✅ Mock objects created")
            
            # Try to understand what happens in the function
            from api.routers.calendar_router import start_calendar_sync_monitoring
            
            print("🔍 Starting monitoring for test...")
            test_metrics = start_calendar_sync_monitoring(
                user_id=999999,
                endpoint="/api/v1/calendar/sync/auto"
            )
            print(f"✅ Test monitoring successful: {test_metrics}")
            
        except Exception as e:
            print(f"❌ Function testing failed: {e}")
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Debug script failed: {e}")
        traceback.print_exc()
        
    print("="*60)
    print("🏁 DEBUG COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(debug_calendar_sync())