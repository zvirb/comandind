#!/usr/bin/env python3
"""
Session Factory Optimization and Async Session Performance Test
Tests connection pool utilization, session lifecycle, and async performance.
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import List, Dict, Any

import sys
sys.path.append('/home/marku/ai_workflow_engine/app')

from shared.utils.database_setup import (
    initialize_database, 
    get_async_session, 
    get_database_stats,
    get_session
)
from shared.utils.config import Settings
from shared.database.models import User, UserOAuthToken
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_session_lifecycle_management():
    """Test session lifecycle and connection pool behavior"""
    print("=== SESSION LIFECYCLE MANAGEMENT TEST ===")
    
    settings = Settings()
    initialize_database(settings)
    
    # Test 1: Connection Pool Health Check
    initial_stats = get_database_stats()
    print(f"Initial Pool Stats:")
    print(f"  Sync: {initial_stats['sync_engine']}")
    print(f"  Async: {initial_stats['async_engine']}")
    
    # Test 2: Multiple Async Session Creation/Cleanup
    session_count = 10
    session_times = []
    
    for i in range(session_count):
        start_time = time.time()
        
        async for db in get_async_session():
            try:
                # Simple query to test connection
                result = await db.execute(select(User).limit(1))
                user = result.scalars().first()
                
                # Test OAuth token query if user exists
                if user:
                    oauth_result = await db.execute(select(UserOAuthToken).filter(
                        UserOAuthToken.user_id == user.id
                    ).limit(1))
                    token = oauth_result.scalars().first()
                
                session_times.append(time.time() - start_time)
                break
            except Exception as e:
                logger.error(f"Session {i} failed: {e}")
                break
    
    avg_session_time = sum(session_times) / len(session_times) if session_times else 0
    print(f"\nSession Performance:")
    print(f"  Sessions tested: {len(session_times)}/{session_count}")
    print(f"  Average session time: {avg_session_time:.4f}s")
    print(f"  Min/Max times: {min(session_times):.4f}s / {max(session_times):.4f}s")
    
    # Test 3: Connection Pool Utilization After Load
    final_stats = get_database_stats()
    print(f"\nFinal Pool Stats:")
    print(f"  Sync: {final_stats['sync_engine']}")  
    print(f"  Async: {final_stats['async_engine']}")
    
    # Calculate pool utilization
    if final_stats['async_engine']:
        async_pool = final_stats['async_engine']
        utilization = (async_pool['connections_created'] / 
                      (async_pool['pool_size'] + async_pool['connections_overflow'])) * 100
        print(f"  Async Pool Utilization: {utilization:.1f}%")
    
    return {
        'session_count': len(session_times),
        'avg_session_time': avg_session_time,
        'pool_utilization': utilization if final_stats['async_engine'] else 0
    }

async def test_concurrent_async_operations():
    """Test concurrent async operations for race conditions"""
    print("\n=== CONCURRENT ASYNC OPERATIONS TEST ===")
    
    async def single_async_operation(session_id: int):
        """Single async operation to test concurrency"""
        async for db in get_async_session():
            try:
                # Simulate OAuth token lookup (common calendar operation)
                result = await db.execute(select(UserOAuthToken).limit(5))
                tokens = result.scalars().all()
                
                # Simulate user lookup 
                user_result = await db.execute(select(User).limit(1))
                user = user_result.scalars().first()
                
                return {
                    'session_id': session_id,
                    'tokens_found': len(tokens),
                    'user_found': user is not None,
                    'success': True
                }
            except Exception as e:
                logger.error(f"Concurrent session {session_id} failed: {e}")
                return {
                    'session_id': session_id,
                    'success': False,
                    'error': str(e)
                }
            break
    
    # Run 20 concurrent async operations
    concurrent_count = 20
    start_time = time.time()
    
    tasks = [single_async_operation(i) for i in range(concurrent_count)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    
    successful_operations = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
    failed_operations = concurrent_count - successful_operations
    
    print(f"Concurrent Operations Results:")
    print(f"  Total operations: {concurrent_count}")
    print(f"  Successful: {successful_operations}")
    print(f"  Failed: {failed_operations}")
    print(f"  Total time: {end_time - start_time:.4f}s")
    print(f"  Average per operation: {(end_time - start_time) / concurrent_count:.4f}s")
    
    # Check for any race condition errors
    race_conditions = [r for r in results if isinstance(r, dict) and 'race' in str(r.get('error', '')).lower()]
    if race_conditions:
        print(f"  ⚠️  Race conditions detected: {len(race_conditions)}")
    else:
        print(f"  ✅  No race conditions detected")
    
    return {
        'concurrent_count': concurrent_count,
        'successful': successful_operations,
        'failed': failed_operations,
        'total_time': end_time - start_time,
        'race_conditions': len(race_conditions)
    }

async def test_oauth_token_performance():
    """Test OAuth token operations performance under async load"""
    print("\n=== OAUTH TOKEN PERFORMANCE TEST ===")
    
    # Test token refresh atomicity simulation
    async def simulate_token_refresh(user_id: int):
        """Simulate atomic token refresh operation"""
        async for db in get_async_session():
            try:
                # Start transaction for atomic operation
                result = await db.execute(select(UserOAuthToken).filter(
                    UserOAuthToken.user_id == user_id,
                    UserOAuthToken.service == 'CALENDAR'
                ).limit(1))
                token = result.scalars().first()
                
                if token:
                    # Simulate token refresh (update expiry time)
                    token.updated_at = datetime.now(timezone.utc)
                    await db.commit()
                    return {'success': True, 'token_id': token.id}
                else:
                    return {'success': True, 'token_id': None, 'message': 'No token found'}
                    
            except Exception as e:
                await db.rollback()
                return {'success': False, 'error': str(e)}
            break
    
    # Test multiple token operations
    token_operations = 10
    start_time = time.time()
    
    tasks = [simulate_token_refresh(1) for _ in range(token_operations)]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    
    successful_refreshes = sum(1 for r in results if r.get('success', False))
    failed_refreshes = token_operations - successful_refreshes
    
    print(f"OAuth Token Operations Results:")
    print(f"  Token refresh operations: {token_operations}")
    print(f"  Successful: {successful_refreshes}")
    print(f"  Failed: {failed_refreshes}")
    print(f"  Total time: {end_time - start_time:.4f}s")
    print(f"  Average per refresh: {(end_time - start_time) / token_operations:.4f}s")
    
    if (end_time - start_time) / token_operations < 0.5:  # 500ms threshold
        print(f"  ✅  Token refresh latency under 500ms threshold")
    else:
        print(f"  ⚠️  Token refresh latency exceeds 500ms threshold")
    
    return {
        'operations': token_operations,
        'successful': successful_refreshes,
        'avg_latency': (end_time - start_time) / token_operations,
        'under_threshold': (end_time - start_time) / token_operations < 0.5
    }

async def main():
    """Run all session factory optimization tests"""
    print("DATABASE ASYNC OPERATIONS OPTIMIZATION TEST")
    print("="*60)
    
    try:
        # Run all tests
        lifecycle_results = await test_session_lifecycle_management()
        concurrent_results = await test_concurrent_async_operations()
        oauth_results = await test_oauth_token_performance()
        
        # Summary
        print("\n" + "="*60)
        print("OPTIMIZATION TEST SUMMARY")
        print("="*60)
        
        # Success criteria validation
        success_criteria = {
            'connection_pool_utilization': lifecycle_results['pool_utilization'] < 80,
            'session_performance': lifecycle_results['avg_session_time'] < 0.1,
            'concurrent_operations': concurrent_results['failed'] == 0,
            'oauth_latency': oauth_results['avg_latency'] < 0.5,
            'no_race_conditions': concurrent_results['race_conditions'] == 0
        }
        
        all_passed = all(success_criteria.values())
        
        print(f"✅ Connection Pool Utilization < 80%: {success_criteria['connection_pool_utilization']}")
        print(f"✅ Session Performance < 100ms: {success_criteria['session_performance']}")
        print(f"✅ No Concurrent Operation Failures: {success_criteria['concurrent_operations']}")
        print(f"✅ OAuth Token Latency < 500ms: {success_criteria['oauth_latency']}")
        print(f"✅ No Race Conditions: {success_criteria['no_race_conditions']}")
        
        print(f"\nOVERALL RESULT: {'✅ ALL TESTS PASSED' if all_passed else '⚠️  SOME TESTS FAILED'}")
        
        return all_passed
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)