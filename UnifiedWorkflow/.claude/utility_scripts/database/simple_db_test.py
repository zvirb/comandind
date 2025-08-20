#!/usr/bin/env python3
"""
Simple database connection test to check if the database is accessible
and if the task table has the right schema.
"""

import psycopg2
import json
import os
from urllib.parse import urlparse

def get_db_config():
    """Get database configuration from environment or defaults."""
    # Try to read from the environment file if it exists
    env_file = ".env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")
    
    # Default configuration for production
    db_config = {
        'host': os.getenv('DATABASE_HOST', 'localhost'),
        'port': int(os.getenv('DATABASE_PORT', 5432)),
        'database': os.getenv('DATABASE_NAME', 'ai_workflow_engine'),
        'user': os.getenv('DATABASE_USER', 'ai_user'),
        'password': os.getenv('DATABASE_PASSWORD', 'secure_password_2024')
    }
    
    print(f"🔧 Database config: {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")
    return db_config

def test_database_connection():
    """Test basic database connection."""
    print("🗄️  Testing database connection...")
    
    try:
        db_config = get_db_config()
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Database connection successful")
        print(f"   PostgreSQL version: {version}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_task_table_exists():
    """Test if the tasks table exists and check its structure."""
    print("📋 Testing tasks table...")
    
    try:
        db_config = get_db_config()
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'tasks'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        if not table_exists:
            print("❌ Tasks table does not exist")
            return False
        
        print("✅ Tasks table exists")
        
        # Check table schema
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'tasks' 
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print("📋 Task table columns:")
        for column_name, data_type, is_nullable in columns:
            print(f"   {column_name}: {data_type} ({'nullable' if is_nullable == 'YES' else 'not null'})")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Tasks table check failed: {e}")
        return False

def test_user_table_and_data():
    """Test users table and check for test data."""
    print("👤 Testing users table...")
    
    try:
        db_config = get_db_config()
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        if not table_exists:
            print("❌ Users table does not exist")
            return False
        
        print("✅ Users table exists")
        
        # Count users
        cursor.execute("SELECT COUNT(*) FROM users;")
        user_count = cursor.fetchone()[0]
        print(f"📊 Total users: {user_count}")
        
        # Check for admin user
        cursor.execute("SELECT id, email FROM users WHERE email = 'admin@aiwfe.com';")
        admin_user = cursor.fetchone()
        if admin_user:
            print(f"✅ Admin user found: ID {admin_user[0]}, Email {admin_user[1]}")
            return admin_user[0]  # Return user ID
        else:
            print("❌ Admin user not found")
            # Show some sample users
            cursor.execute("SELECT id, email FROM users LIMIT 3;")
            sample_users = cursor.fetchall()
            print("📋 Sample users:")
            for user_id, email in sample_users:
                print(f"   ID {user_id}: {email}")
            return sample_users[0][0] if sample_users else None
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Users table check failed: {e}")
        return None

def test_tasks_query(user_id):
    """Test the actual query that would be used by the API."""
    print(f"📋 Testing tasks query for user {user_id}...")
    
    try:
        db_config = get_db_config()
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Execute the same query as get_tasks_by_user
        cursor.execute("SELECT * FROM tasks WHERE user_id = %s;", (user_id,))
        tasks = cursor.fetchall()
        
        print(f"✅ Tasks query successful: found {len(tasks)} tasks")
        
        if tasks:
            # Get column names
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'tasks' 
                ORDER BY ordinal_position;
            """)
            columns = [row[0] for row in cursor.fetchall()]
            
            # Show first task
            first_task = dict(zip(columns, tasks[0]))
            print(f"📝 Sample task:")
            print(f"   ID: {first_task.get('id')}")
            print(f"   Title: {first_task.get('title')}")
            print(f"   Status: {first_task.get('status')}")
            print(f"   Semantic tags: {first_task.get('semantic_tags')}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Tasks query failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all database tests."""
    print("🚨 SIMPLE DATABASE DIAGNOSIS")
    print("=" * 50)
    
    # Test 1: Connection
    if not test_database_connection():
        print("❌ Cannot connect to database, aborting")
        return
    
    # Test 2: Table structure
    if not test_task_table_exists():
        print("❌ Tasks table issues, aborting")
        return
    
    # Test 3: User data
    user_id = test_user_table_and_data()
    if not user_id:
        print("❌ No users available for testing")
        return
    
    # Test 4: Task query
    test_tasks_query(user_id)
    
    print("\n" + "=" * 50)
    print("✅ Database diagnosis complete")

if __name__ == "__main__":
    main()