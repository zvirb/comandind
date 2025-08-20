#!/usr/bin/env python3
"""
Simple Authentication Performance Analysis
==========================================

Analyze authentication performance bottlenecks by measuring service initialization
and token validation performance.
"""

import asyncio
import time
import logging
import sys
import os
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.append(os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimplePerformanceProfiler:
    """Simple profiler for authentication performance."""
    
    def __init__(self):
        self.measurements = {}
        
    def measure_time(self, operation_name):
        """Context manager to measure operation time."""
        class TimeContext:
            def __init__(self, profiler, name):
                self.profiler = profiler
                self.name = name
                self.start_time = None
                
            def __enter__(self):
                self.start_time = time.perf_counter()
                logger.info(f"Starting: {self.name}")
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = (time.perf_counter() - self.start_time) * 1000  # ms
                self.profiler.measurements[self.name] = duration
                status = "FAILED" if exc_type else "OK"
                logger.info(f"Completed: {self.name} - {duration:.1f}ms [{status}]")
                
        return TimeContext(self, operation_name)


async def main():
    """Main performance analysis."""
    profiler = SimplePerformanceProfiler()
    
    print("="*80)
    print("AUTHENTICATION PERFORMANCE ANALYSIS")
    print("="*80)
    print(f"Analysis started at: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    # 1. Service Import Performance
    print("1. SERVICE IMPORT PERFORMANCE")
    print("-" * 40)
    
    with profiler.measure_time("auth_middleware_service_import"):
        try:
            from shared.services.auth_middleware_service import auth_middleware_service
            import_success_middleware = True
        except Exception as e:
            logger.error(f"auth_middleware_service import failed: {e}")
            import_success_middleware = False
    
    with profiler.measure_time("auth_queue_service_import"):
        try:
            from shared.services.auth_queue_service import auth_queue_service
            import_success_queue = True
        except Exception as e:
            logger.error(f"auth_queue_service import failed: {e}")
            import_success_queue = False
    
    with profiler.measure_time("secure_token_storage_import"):
        try:
            from shared.services.secure_token_storage_service import secure_token_storage
            import_success_storage = True
        except Exception as e:
            logger.error(f"secure_token_storage import failed: {e}")
            import_success_storage = False
    
    with profiler.measure_time("enhanced_jwt_service_import"):
        try:
            from shared.services.enhanced_jwt_service import enhanced_jwt_service
            import_success_jwt = True
        except Exception as e:
            logger.error(f"enhanced_jwt_service import failed: {e}")
            import_success_jwt = False
    
    # 2. Service Initialization Performance
    print("\n2. SERVICE INITIALIZATION PERFORMANCE")
    print("-" * 40)
    
    if import_success_middleware:
        with profiler.measure_time("auth_middleware_service_initialize"):
            try:
                await auth_middleware_service.initialize()
                logger.info("auth_middleware_service initialized successfully")
            except Exception as e:
                logger.error(f"auth_middleware_service initialization failed: {e}")
    
    if import_success_queue:
        with profiler.measure_time("auth_queue_service_start"):
            try:
                await auth_queue_service.start(num_workers=3)
                logger.info("auth_queue_service started successfully")
            except Exception as e:
                logger.error(f"auth_queue_service start failed: {e}")
    
    if import_success_storage:
        with profiler.measure_time("secure_token_storage_initialize"):
            try:
                await secure_token_storage.initialize()
                logger.info("secure_token_storage initialized successfully")
            except Exception as e:
                logger.error(f"secure_token_storage initialization failed: {e}")
    
    # 3. Database Connection Performance
    print("\n3. DATABASE CONNECTION PERFORMANCE")
    print("-" * 40)
    
    with profiler.measure_time("database_connection_setup"):
        try:
            from shared.utils.database_setup import get_async_session
            session_gen = get_async_session()
            session = await anext(session_gen)
            logger.info("Database connection established successfully")
            
            with profiler.measure_time("database_user_query"):
                try:
                    from sqlalchemy import select
                    from shared.database.models import User
                    
                    result = await session.execute(select(User).limit(1))
                    user = result.scalar_one_or_none()
                    logger.info(f"Database query executed successfully, user found: {user is not None}")
                    
                except Exception as e:
                    logger.error(f"Database query failed: {e}")
            
            await session.close()
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
    
    # 4. Authentication Flow Performance
    print("\n4. AUTHENTICATION FLOW PERFORMANCE")
    print("-" * 40)
    
    with profiler.measure_time("legacy_jwt_validation"):
        try:
            from api.dependencies import get_current_user_payload
            
            # Create mock request
            class MockRequest:
                def __init__(self):
                    self.headers = {"authorization": "Bearer test_token"}
                    self.cookies = {}
                    self.url = type('obj', (object,), {'path': '/api/test'})()
            
            try:
                mock_request = MockRequest()
                token_data = get_current_user_payload(mock_request)
                logger.info("JWT validation completed (expected to fail with test token)")
            except Exception as e:
                logger.info(f"JWT validation failed as expected: {type(e).__name__}")
                
        except Exception as e:
            logger.error(f"JWT validation setup failed: {e}")
    
    with profiler.measure_time("enhanced_auth_compatibility"):
        try:
            from api.auth_compatibility import enhanced_get_current_user
            from shared.utils.database_setup import get_async_session
            
            class MockRequest:
                def __init__(self):
                    self.headers = {"authorization": "Bearer test_token"}
                    self.cookies = {}
                    self.url = type('obj', (object,), {'path': '/api/test'})()
            
            session_gen = get_async_session()
            session = await anext(session_gen)
            
            try:
                mock_request = MockRequest()
                user = await enhanced_get_current_user(mock_request, session)
                logger.info("Enhanced authentication completed")
            except Exception as e:
                logger.info(f"Enhanced authentication failed as expected: {type(e).__name__}")
            finally:
                await session.close()
                
        except Exception as e:
            logger.error(f"Enhanced authentication setup failed: {e}")
    
    # 5. Performance Analysis
    print("\n5. PERFORMANCE ANALYSIS RESULTS")
    print("="*80)
    
    total_time = sum(profiler.measurements.values())
    
    print(f"Total measured time: {total_time:.1f}ms ({total_time/1000:.1f}s)")
    print()
    print("Breakdown by component:")
    
    for operation, duration in sorted(profiler.measurements.items(), key=lambda x: x[1], reverse=True):
        percentage = (duration / total_time) * 100 if total_time > 0 else 0
        print(f"  {operation:<35}: {duration:>8.1f}ms ({percentage:>5.1f}%)")
    
    # Analysis and Recommendations
    print("\n6. BOTTLENECK ANALYSIS")
    print("="*80)
    
    bottlenecks = []
    optimizations = []
    
    # Service initialization bottlenecks
    service_init_total = sum(
        duration for op, duration in profiler.measurements.items() 
        if 'initialize' in op or 'start' in op
    )
    
    if service_init_total > 5000:  # >5 seconds
        bottlenecks.append(f"Service initialization takes {service_init_total:.0f}ms")
        optimizations.append("Lazy initialization - initialize services only when needed")
        optimizations.append("Pre-warm services at application startup, not first request")
    
    # Individual service analysis
    if profiler.measurements.get('auth_middleware_service_initialize', 0) > 3000:
        bottlenecks.append("auth_middleware_service initialization >3s")
        optimizations.append("Simplify auth_middleware_service initialization")
        optimizations.append("Remove unnecessary background task creation")
    
    if profiler.measurements.get('auth_queue_service_start', 0) > 2000:
        bottlenecks.append("auth_queue_service start >2s")
        optimizations.append("Reduce default worker count from 5 to 1-2")
        optimizations.append("Use simple queuing instead of complex worker pools")
    
    if profiler.measurements.get('secure_token_storage_initialize', 0) > 2000:
        bottlenecks.append("secure_token_storage initialization >2s")
        optimizations.append("Pre-compute cryptographic objects")
        optimizations.append("Lazy initialize encryption components")
    
    # Database performance
    db_total = sum(
        duration for op, duration in profiler.measurements.items() 
        if 'database' in op
    )
    
    if db_total > 1000:  # >1 second
        bottlenecks.append(f"Database operations take {db_total:.0f}ms")
        optimizations.append("Optimize database connection pool settings")
        optimizations.append("Add database query caching")
    
    print("IDENTIFIED BOTTLENECKS:")
    for i, bottleneck in enumerate(bottlenecks, 1):
        print(f"  {i}. {bottleneck}")
    
    print(f"\nOPTIMIZATION OPPORTUNITIES:")
    for i, optimization in enumerate(optimizations, 1):
        print(f"  {i}. {optimization}")
    
    # Performance targets
    print("\n7. PERFORMANCE TARGETS")
    print("="*80)
    
    current_performance = total_time / 1000  # seconds
    target_performance = 0.5  # 500ms
    improvement_needed = ((current_performance - target_performance) / current_performance) * 100
    
    print(f"Current Performance: {current_performance:.1f}s")
    print(f"Target Performance:  {target_performance}s")
    print(f"Improvement Needed:  {improvement_needed:.1f}%")
    
    print(f"\nSTATUS: {'✓ MEETS TARGET' if current_performance <= target_performance else '✗ NEEDS OPTIMIZATION'}")
    
    # Priority actions
    print("\n8. IMMEDIATE ACTION ITEMS")
    print("="*80)
    print("HIGH PRIORITY:")
    print("  1. Move service initialization to application startup (FastAPI lifespan)")
    print("  2. Replace complex queue system with direct JWT validation for simple cases")
    print("  3. Implement lazy initialization for non-critical services")
    print("  4. Reduce auth_queue_service worker count to 1-2")
    
    print("\nMEDIUM PRIORITY:")
    print("  1. Add database connection pooling optimization")
    print("  2. Implement authentication result caching")
    print("  3. Pre-compute cryptographic operations")
    print("  4. Add performance monitoring and alerting")
    
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())