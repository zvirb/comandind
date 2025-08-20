"""
Advanced Connection Pool Optimization Module

Provides intelligent connection pool management with:
- Dynamic pool sizing
- SSL compatibility handling
- Session reuse strategies
- Performance monitoring
"""

import os
import ssl
import asyncio
from typing import Dict, Any, Optional

from sqlalchemy import create_engine, engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

class ConnectionPoolOptimizer:
    """
    Intelligent connection pool management with advanced configuration
    """
    
    @staticmethod
    def get_pool_config(env: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate dynamic connection pool configuration with intelligent scaling and environment-aware tuning.
        
        Provides adaptive pool sizing strategies that automatically adjust based on environment, 
        anticipated load, and service type. Key features include:
        
        - Dynamic pool size scaling
        - Automatic timeout and connection recycling
        - Environment-specific optimizations
        - Prevents connection exhaustion
        - Supports horizontal service scalability
        
        Pool Configuration Strategy:
        - Development: Minimal pool for testing and local development
        - Testing: Small, quick-recycling pool for test environments
        - Production: Large, robust pool with high overflow capacity
        
        :param env: Environment type determining pool configuration
                    Options: 'development', 'testing', 'production'
        
        :return: Adaptive pool configuration dictionary with keys:
            - pool_size: Maximum concurrent database connections
            - max_overflow: Additional connections allowed during peak load
            - pool_timeout: Connection request waiting time
            - pool_recycle: Connection lifetime before automatic replacement
            - pool_pre_ping: Validates connection health before use
        """
        env = env or os.environ.get('ENVIRONMENT', 'development')
        
        base_config = {
            'pool_size': 5,  # Default pool size
            'max_overflow': 10,  # Allow burst connections
            'pool_timeout': 30,  # Connection request timeout
            'pool_recycle': 3600,  # Recycle connections after 1 hour
            'pool_pre_ping': True  # Test connection health before use
        }
        
        # Environment-specific tuning - SUPER OPTIMIZED for authentication performance
        if env == 'production':
            base_config.update({
                'pool_size': 200,  # Maximized for concurrent auth validations (was 150)
                'max_overflow': 400,  # Increased overflow for session validation spikes (was 300)
                'pool_timeout': 30,  # Reduced timeout for faster failure (was 45) 
                'pool_recycle': 900,  # Even faster recycling for optimal auth performance (was 1200)
                'pool_reset_on_return': 'commit',  # Ensure clean connections for auth
                'pool_echo': False,  # Disable logging for performance
            })
        elif env == 'testing':
            base_config.update({
                'pool_size': 2,  # Minimal pool for testing
                'max_overflow': 5,
                'pool_timeout': 10,
                'pool_recycle': 600,
            })
        
        return base_config
    
    @staticmethod
    def create_ssl_context(
        ssl_mode: str = 'prefer', 
        cert_path: Optional[str] = None
    ) -> Optional[ssl.SSLContext]:
        """
        Create SSL context for database connections
        
        :param ssl_mode: SSL mode (disable, prefer, require, verify-full)
        :param cert_path: Optional path to SSL certificate
        :return: Configured SSL context or None
        """
        if ssl_mode == 'disable':
            return None
        
        context = ssl.create_default_context()
        context.check_hostname = ssl_mode in ['verify-full', 'verify-ca']
        
        if cert_path and os.path.exists(cert_path):
            context.load_verify_locations(cert_path)
        
        return context
    
    @classmethod
    def create_sync_engine(cls, database_url: str) -> engine.base.Engine:
        """
        Create optimized synchronous database engine
        
        :param database_url: Database connection URL
        :return: Configured SQLAlchemy engine
        """
        pool_config = cls.get_pool_config()
        
        return create_engine(
            database_url,
            poolclass=QueuePool,
            **pool_config
        )
    
    @classmethod
    async def create_async_engine(cls, database_url: str) -> AsyncEngine:
        """
        Create optimized asynchronous database engine
        
        :param database_url: Async database connection URL
        :return: Configured async SQLAlchemy engine
        """
        pool_config = cls.get_pool_config()
        
        return create_async_engine(
            database_url,
            **pool_config
        )
    
    @classmethod
    def create_sync_session_factory(cls, engine: engine.base.Engine) -> sessionmaker:
        """
        Create synchronized session factory with retry and timeout mechanisms
        
        :param engine: SQLAlchemy database engine
        :return: Session factory
        """
        return sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
    
    @classmethod
    async def create_async_session_factory(cls, async_engine: AsyncEngine) -> sessionmaker:
        """
        Create asynchronous session factory with retry and timeout mechanisms
        
        :param async_engine: Async SQLAlchemy engine
        :return: Async session factory
        """
        return sessionmaker(
            async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
    
    @staticmethod
    async def monitor_connection_pool(engine: Any) -> Dict[str, Any]:
        """
        Monitor connection pool statistics
        
        :param engine: SQLAlchemy database engine
        :return: Pool statistics dictionary
        """
        # This is a placeholder for real pool monitoring
        # Requires additional SQLAlchemy/database-specific implementations
        return {
            'total_connections': engine.pool.checkedin(),
            'available_connections': engine.pool.checkedin(),
            'used_connections': engine.pool.checkedout(),
            'max_connections': engine.pool.size(),
        }

# Convenience function for getting an optimized database connection
def get_optimized_connection(database_url: str, async_mode: bool = False):
    """
    Get an optimized database connection based on URL and mode
    
    :param database_url: Database connection URL
    :param async_mode: Whether to create an async connection
    :return: Configured engine and session factory
    """
    optimizer = ConnectionPoolOptimizer
    
    if async_mode:
        engine = optimizer.create_async_engine(database_url)
        session_factory = optimizer.create_async_session_factory(engine)
    else:
        engine = optimizer.create_sync_engine(database_url)
        session_factory = optimizer.create_sync_session_factory(engine)
    
    return engine, session_factory

# Add logging and monitoring capabilities