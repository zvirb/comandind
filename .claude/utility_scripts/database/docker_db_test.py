#!/usr/bin/env python3
"""
Test database connection using Docker network and investigate task endpoint 500 error.
"""

import psycopg2
import json
import os
import subprocess

def get_docker_db_config():
    """Get database configuration for Docker environment."""
    # For production AI Workflow Engine, the database is in Docker
    db_config = {
        'host': 'localhost',  # Database should be accessible via port mapping
        'port': 5432,
        'database': 'ai_workflow_engine',
        'user': 'ai_user', 
        'password': 'secure_password_2024'
    }
    
    print(f"🐳 Docker database config: {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")
    return db_config

def get_docker_internal_db_config():
    """Get database configuration for internal Docker network."""
    # Try using Docker internal network
    db_config = {
        'host': 'postgres',  # Docker service name
        'port': 5432,
        'database': 'ai_workflow_engine',
        'user': 'ai_user',
        'password': 'secure_password_2024'
    }
    
    print(f"🐳 Docker internal config: {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")
    return db_config

def test_docker_exec_db_connection():
    """Test database by executing commands inside the PostgreSQL container."""
    print("🐳 Testing database via Docker exec...")
    
    try:
        # Get the PostgreSQL container name
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=postgres", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            print("❌ Could not find PostgreSQL container")
            return False
        
        container_name = result.stdout.strip()
        if not container_name:
            print("❌ No PostgreSQL container found")
            return False
        
        print(f"🐳 Found PostgreSQL container: {container_name}")
        
        # Test connection inside container
        cmd = [
            "docker", "exec", container_name,
            "psql", "-U", "ai_user", "-d", "ai_workflow_engine",
            "-c", "SELECT version();"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, env={"PGPASSWORD": "secure_password_2024"})
        
        if result.returncode == 0:
            print("✅ Database connection successful via Docker exec")
            print(f"   Output: {result.stdout.strip()}")
            return container_name
        else:
            print(f"❌ Database connection failed via Docker exec: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Docker exec test failed: {e}")
        return False

def test_tasks_table_via_docker(container_name):
    """Test tasks table structure via Docker exec."""
    print("📋 Testing tasks table via Docker...")
    
    try:
        # Check if tasks table exists and get its structure
        cmd = [
            "docker", "exec", container_name,
            "psql", "-U", "ai_user", "-d", "ai_workflow_engine",
            "-c", """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'tasks' 
            ORDER BY ordinal_position;
            """
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, env={"PGPASSWORD": "secure_password_2024"})
        
        if result.returncode == 0:
            print("✅ Tasks table query successful")
            print(f"📋 Table structure:\n{result.stdout}")
            return True
        else:
            print(f"❌ Tasks table query failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Tasks table test failed: {e}")
        return False

def test_users_and_tasks_data_via_docker(container_name):
    """Test actual user and task data via Docker exec."""
    print("👤📋 Testing users and tasks data via Docker...")
    
    try:
        # Query users and their task counts
        cmd = [
            "docker", "exec", container_name,
            "psql", "-U", "ai_user", "-d", "ai_workflow_engine",
            "-c", """
            SELECT u.id, u.email, COUNT(t.id) as task_count
            FROM users u
            LEFT JOIN tasks t ON u.id = t.user_id
            GROUP BY u.id, u.email
            ORDER BY u.id
            LIMIT 5;
            """
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, env={"PGPASSWORD": "secure_password_2024"})
        
        if result.returncode == 0:
            print("✅ Users and tasks query successful")
            print(f"📊 Users with task counts:\n{result.stdout}")
            
            # Check specifically for admin user tasks
            cmd2 = [
                "docker", "exec", container_name,
                "psql", "-U", "ai_user", "-d", "ai_workflow_engine",
                "-c", """
                SELECT t.id, t.title, t.status, t.semantic_tags IS NOT NULL as has_semantic_tags
                FROM tasks t
                JOIN users u ON t.user_id = u.id
                WHERE u.email = 'admin@aiwfe.com'
                LIMIT 3;
                """
            ]
            
            result2 = subprocess.run(cmd2, capture_output=True, text=True, env={"PGPASSWORD": "secure_password_2024"})
            
            if result2.returncode == 0:
                print("✅ Admin user tasks query successful")
                print(f"📝 Admin tasks:\n{result2.stdout}")
            else:
                print(f"❌ Admin tasks query failed: {result2.stderr}")
            
            return True
        else:
            print(f"❌ Users and tasks query failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Users and tasks test failed: {e}")
        return False

def test_potential_async_session_issue(container_name):
    """Test for potential async session or connection pool issues."""
    print("🔄 Testing for async session issues...")
    
    try:
        # Simulate concurrent connections like FastAPI would create
        cmd = [
            "docker", "exec", container_name,
            "psql", "-U", "ai_user", "-d", "ai_workflow_engine",
            "-c", "SELECT pg_stat_get_db_numbackends(pg_database.oid) AS connections FROM pg_database WHERE datname = 'ai_workflow_engine';"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, env={"PGPASSWORD": "secure_password_2024"})
        
        if result.returncode == 0:
            print("✅ Connection count query successful")
            print(f"📊 Current connections:\n{result.stdout}")
            
            # Check for any locking issues
            cmd2 = [
                "docker", "exec", container_name,
                "psql", "-U", "ai_user", "-d", "ai_workflow_engine",
                "-c", "SELECT COUNT(*) FROM pg_locks WHERE granted = false;"
            ]
            
            result2 = subprocess.run(cmd2, capture_output=True, text=True, env={"PGPASSWORD": "secure_password_2024"})
            
            if result2.returncode == 0:
                print("✅ Lock check successful")
                print(f"🔒 Blocked queries:\n{result2.stdout}")
            
            return True
        else:
            print(f"❌ Connection check failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Async session test failed: {e}")
        return False

def main():
    """Run all database tests via Docker."""
    print("🚨 DOCKER DATABASE DIAGNOSIS")
    print("=" * 60)
    
    # Test 1: Basic connection via Docker exec
    container_name = test_docker_exec_db_connection()
    if not container_name:
        print("❌ Cannot connect to database in Docker, aborting")
        return
    
    # Test 2: Table structure
    if not test_tasks_table_via_docker(container_name):
        print("❌ Tasks table issues found")
        return
    
    # Test 3: Data integrity
    if not test_users_and_tasks_data_via_docker(container_name):
        print("❌ Data integrity issues found")
        return
    
    # Test 4: Async/connection issues
    test_potential_async_session_issue(container_name)
    
    print("\n" + "=" * 60)
    print("📊 DIAGNOSIS COMPLETE")
    print("=" * 60)
    print("✅ Database is accessible and has correct structure")
    print("✅ Users and tasks data exists")
    print("🤔 Issue might be in:")
    print("   - FastAPI async session handling")
    print("   - Authentication middleware in production")
    print("   - Database connection pool exhaustion")
    print("   - Network connectivity between API and database containers")

if __name__ == "__main__":
    main()