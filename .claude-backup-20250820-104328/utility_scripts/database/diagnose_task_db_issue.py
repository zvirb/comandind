#!/usr/bin/env python3
"""
Diagnose the exact database issue causing task endpoint 500 errors.
This script tests the database queries directly without going through the API.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, '/home/marku/ai_workflow_engine/app')

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from shared.database.models import Task, User
from shared.utils.database_setup import get_async_session, get_db
from api import crud

async def test_async_database_connection():
    """Test if we can establish an async database connection."""
    print("🗄️  Testing async database connection...")
    
    try:
        # Get an async session
        async for session in get_async_session():
            print("✅ Async database connection successful")
            await session.close()
            return True
    except Exception as e:
        print(f"❌ Async database connection failed: {e}")
        return False

def test_sync_database_connection():
    """Test if we can establish a sync database connection."""
    print("🗄️  Testing sync database connection...")
    
    try:
        # Get a sync session
        for session in get_db():
            print("✅ Sync database connection successful") 
            session.close()
            return True
    except Exception as e:
        print(f"❌ Sync database connection failed: {e}")
        return False

def test_task_query_directly():
    """Test the exact task query that the API endpoint uses."""
    print("📋 Testing direct task query...")
    
    try:
        # Use sync database for direct testing
        for db in get_db():
            # Test with a real user ID
            # First, find any user to test with
            test_user = db.query(User).first()
            if not test_user:
                print("❌ No users found in database")
                return False
            
            print(f"🧪 Testing with user ID: {test_user.id} ({test_user.email})")
            
            # Now test the exact query from crud.get_tasks_by_user
            tasks = crud.get_tasks_by_user(db=db, user_id=test_user.id)
            print(f"✅ Direct task query successful: found {len(tasks)} tasks")
            
            # Show sample task data
            if tasks:
                sample_task = tasks[0]
                print(f"📝 Sample task: {sample_task.title} (ID: {sample_task.id})")
                print(f"    Status: {sample_task.status}")
                print(f"    Semantic tags: {sample_task.semantic_tags}")
            
            db.close()
            return True
            
    except Exception as e:
        print(f"❌ Direct task query failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def test_task_table_schema():
    """Test if the task table has the expected schema."""
    print("🏗️  Testing task table schema...")
    
    try:
        for db in get_db():
            # Try to query the table structure
            result = db.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'tasks' ORDER BY ordinal_position")
            columns = result.fetchall()
            
            print("📋 Task table columns:")
            for column_name, data_type in columns:
                print(f"   {column_name}: {data_type}")
            
            # Check for critical columns
            column_names = [col[0] for col in columns]
            critical_columns = ['id', 'user_id', 'title', 'description', 'status', 'semantic_tags']
            
            missing_columns = [col for col in critical_columns if col not in column_names]
            if missing_columns:
                print(f"❌ Missing critical columns: {missing_columns}")
                return False
            else:
                print("✅ All critical columns present")
            
            db.close()
            return True
            
    except Exception as e:
        print(f"❌ Schema check failed: {e}")
        return False

def test_user_lookup():
    """Test user lookup that happens in the auth dependency."""
    print("👤 Testing user lookup for auth...")
    
    try:
        for db in get_db():
            # Test finding the admin user we used in our test
            admin_user = db.query(User).filter(User.email == "admin@aiwfe.com").first()
            if admin_user:
                print(f"✅ Found admin user: ID {admin_user.id}")
                return admin_user
            else:
                print("❌ Admin user not found")
                # List some users
                users = db.query(User).limit(5).all()
                print(f"📋 Available users: {[f'{u.email} (ID: {u.id})' for u in users]}")
                return users[0] if users else None
            
    except Exception as e:
        print(f"❌ User lookup failed: {e}")
        return None

async def main():
    """Run all diagnostic tests."""
    print("🚨 DATABASE TASK ENDPOINT DIAGNOSIS")
    print("=" * 60)
    
    # Test 1: Basic connection
    print("\n1. Testing Database Connections...")
    sync_ok = test_sync_database_connection()
    async_ok = await test_async_database_connection()
    
    if not sync_ok and not async_ok:
        print("❌ No database connection possible, aborting")
        return
    
    # Test 2: Schema check
    print("\n2. Testing Table Schema...")
    schema_ok = test_task_table_schema()
    
    # Test 3: User lookup
    print("\n3. Testing User Lookup...")
    test_user = test_user_lookup()
    
    # Test 4: Direct task query
    print("\n4. Testing Direct Task Query...")
    if test_user:
        query_ok = test_task_query_directly()
    else:
        print("❌ Cannot test task query without a valid user")
        query_ok = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DIAGNOSIS SUMMARY")
    print("=" * 60)
    
    print(f"Database Connection (Sync): {'✅' if sync_ok else '❌'}")
    print(f"Database Connection (Async): {'✅' if async_ok else '❌'}")  
    print(f"Table Schema: {'✅' if schema_ok else '❌'}")
    print(f"User Lookup: {'✅' if test_user else '❌'}")
    print(f"Task Query: {'✅' if query_ok else '❌'}")
    
    if query_ok:
        print("\n✅ DIAGNOSIS: Database queries work fine directly")
        print("   The issue might be in:")
        print("   - Async session handling in FastAPI")
        print("   - Authentication dependency failures") 
        print("   - Request processing middleware")
    else:
        print("\n❌ DIAGNOSIS: Database query issues found")
        print("   Fix the database connection or schema issues")

if __name__ == "__main__":
    asyncio.run(main())