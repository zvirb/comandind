#!/usr/bin/env python3
"""
Apply Phase 2 Database Migration

This script applies the critical database fixes migration to enable
full Phase 2 functionality and performance improvements.
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def run_command(cmd, description=""):
    """Run a command and return success status"""
    print(f"🔄 {description}")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd='/home/marku/ai_workflow_engine'
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ {description} - EXCEPTION: {e}")
        return False

def check_migration_status():
    """Check current database migration status"""
    print("📊 Checking current database migration status...")
    
    # Check current migration version
    cmd = 'docker compose exec -T postgres psql -U app_user -d ai_workflow_db -c "SELECT version_num FROM alembic_version;"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd='/home/marku/ai_workflow_engine')
    
    if result.returncode == 0:
        current_version = result.stdout.strip().split('\n')[2].strip()  # Extract version from psql output
        print(f"   Current migration: {current_version}")
        
        # Check available migrations
        cmd2 = 'docker compose exec -T api alembic current'
        result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True, cwd='/home/marku/ai_workflow_engine')
        
        if result2.returncode == 0:
            print(f"   Alembic status: {result2.stdout.strip()}")
        
        return current_version
    else:
        print("❌ Could not check migration status")
        return None

def apply_phase2_migration():
    """Apply the Phase 2 database migration"""
    print("\n🚀 Applying Phase 2 Database Migration...")
    
    # First, check if migration file exists
    migration_file = Path('/home/marku/ai_workflow_engine/app/alembic/versions/critical_database_fixes_20250807.py')
    if not migration_file.exists():
        print("❌ Phase 2 migration file not found!")
        return False
    
    print(f"✅ Migration file found: {migration_file.name}")
    
    # Apply the migration using Alembic
    success = run_command(
        'docker compose exec -T api alembic upgrade critical_db_fixes_20250807',
        "Applying Phase 2 database migration"
    )
    
    return success

def verify_migration_success():
    """Verify that the migration was applied successfully"""
    print("\n🔍 Verifying migration success...")
    
    # Check tables were created
    cmd = 'docker compose exec -T postgres psql -U app_user -d ai_workflow_db -c "\\dt"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd='/home/marku/ai_workflow_engine')
    
    if result.returncode == 0:
        tables_output = result.stdout
        print("📋 Current database tables:")
        print(tables_output)
        
        # Check for expected Phase 2 tables
        expected_tables = [
            'user_profiles',
            'calendars', 
            'events',
            'authentication_sessions',
            'user_oauth_tokens'
        ]
        
        created_tables = []
        for table in expected_tables:
            if table in tables_output:
                created_tables.append(table)
        
        if created_tables:
            print(f"✅ Phase 2 tables created: {', '.join(created_tables)}")
        else:
            print("⚠️  No Phase 2 tables found - migration may not have included table creation")
        
        # Check indexes were created
        cmd2 = 'docker compose exec -T postgres psql -U app_user -d ai_workflow_db -c "SELECT schemaname, tablename, indexname FROM pg_indexes WHERE indexname LIKE \'idx_%\' ORDER BY tablename, indexname;"'
        result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True, cwd='/home/marku/ai_workflow_engine')
        
        if result2.returncode == 0 and result2.stdout.strip():
            print("📇 Phase 2 indexes created:")
            print(result2.stdout)
        else:
            print("⚠️  No Phase 2 indexes found")
        
        return len(created_tables) > 0
    else:
        print("❌ Could not verify migration success")
        return False

def main():
    """Main execution function"""
    print("🔧 Phase 2 Database Migration Application")
    print("=" * 50)
    
    # Step 1: Check current status
    current_version = check_migration_status()
    if not current_version:
        print("❌ Cannot proceed without database connection")
        return 1
    
    # Step 2: Check if migration is already applied
    if 'critical_db_fixes_20250807' in current_version:
        print("✅ Phase 2 migration already applied!")
        verify_migration_success()
        return 0
    
    # Step 3: Apply migration
    if apply_phase2_migration():
        print("✅ Phase 2 migration applied successfully!")
        
        # Step 4: Verify success
        time.sleep(2)  # Give database time to process
        if verify_migration_success():
            print("\n🎉 Phase 2 database migration completed successfully!")
            print("   All Phase 2 performance improvements are now active.")
            return 0
        else:
            print("\n⚠️  Migration applied but verification incomplete")
            print("   Manual verification recommended")
            return 1
    else:
        print("\n❌ Phase 2 migration failed!")
        print("   Check database logs and migration file")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)