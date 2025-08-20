"""Handles the setup and configuration of the SQLAlchemy database connection."""

import os
import re
import ssl
import logging
from typing import Generator, Optional, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from .config import Settings
from typing import Dict, Any, Optional
from .connection_pool_optimizer import ConnectionPoolOptimizer

# Configure basic logging. The level can be controlled by an environment variable.
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "DEBUG").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models with type annotation support."""
    pass

class _Database:
    """A singleton-like class to manage the database engine and session factory."""

    def __init__(self):
        self.engine: Optional[Engine] = None
        self.session_local: Optional[sessionmaker[Session]] = None
        self.async_engine: Optional[Engine] = None
        self.async_session_local: Optional[async_sessionmaker[AsyncSession]] = None


# Create a single instance to hold the database state.
_db = _Database()


def create_ssl_context(cert_dir: str) -> Optional[ssl.SSLContext]:
    """
    Create SSL context for asyncpg connections with proper certificate loading.
    Returns None if certificates are not available or invalid.
    """
    try:
        # Check for certificate files with different naming conventions
        rootca_path = f"{cert_dir}/rootCA.pem"
        
        # Try different client certificate naming patterns
        cert_candidates = [
            (f"{cert_dir}/client-cert.pem", f"{cert_dir}/client-key.pem"),  # Original naming
            (f"{cert_dir}/unified-cert.pem", f"{cert_dir}/unified-key.pem"),  # Unified cert naming
            (f"{cert_dir}/api-cert.pem", f"{cert_dir}/api-key.pem"),  # Service-specific naming
            (f"{cert_dir}/server.crt", f"{cert_dir}/server.key")  # Server cert naming
        ]
        
        client_cert_path = None
        client_key_path = None
        
        # Find the first valid certificate pair
        for cert_path, key_path in cert_candidates:
            if os.path.exists(cert_path) and os.path.exists(key_path):
                client_cert_path = cert_path
                client_key_path = key_path
                logger.info(f"Found SSL certificates: {cert_path}, {key_path}")
                break
        
        if not os.path.exists(rootca_path) or not client_cert_path or not client_key_path:
            logger.warning(f"SSL certificates not found in {cert_dir}. Checked: {cert_candidates}")
            return None
        
        # Create SSL context with proper settings
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_context.check_hostname = False  # pgbouncer doesn't use proper hostname
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        # Load certificates into context
        ssl_context.load_verify_locations(rootca_path)
        ssl_context.load_cert_chain(client_cert_path, client_key_path)
        
        logger.info(f"SSL context created successfully with certificates from {cert_dir}")
        logger.info(f"Using CA: {rootca_path}, Cert: {client_cert_path}, Key: {client_key_path}")
        return ssl_context
        
    except Exception as e:
        logger.error(f"Failed to create SSL context: {e}")
        return None


def fix_async_database_url(database_url: str) -> str:
    """
    Enhanced database URL conversion with proper handling of special characters in passwords.
    Fixes the Invalid IPv6 URL error by properly encoding password components.
    """
    logger.debug(f"Converting database URL to async: {database_url[:50]}...")
    
    # First, handle special characters in the password component
    # Pattern to extract user:password from URL
    import re
    from urllib.parse import quote
    
    auth_pattern = r'postgresql(?:\+psycopg2)?://([^@]+)@'
    auth_match = re.search(auth_pattern, database_url)
    
    if auth_match:
        auth_part = auth_match.group(1)  # user:password
        if ':' in auth_part:
            username, password = auth_part.split(':', 1)
            
            # URL-encode the password to handle special characters
            encoded_password = quote(password, safe='')
            encoded_auth = f"{username}:{encoded_password}"
            
            # Replace the auth part in the original URL
            safe_database_url = database_url.replace(auth_part, encoded_auth)
            logger.info(f"Encoded special characters in password for URL parsing")
        else:
            safe_database_url = database_url
    else:
        safe_database_url = database_url
    
    # Convert driver
    if 'postgresql+psycopg2://' in safe_database_url:
        async_url = safe_database_url.replace('postgresql+psycopg2://', 'postgresql+asyncpg://')
    elif 'postgresql://' in safe_database_url:
        async_url = safe_database_url.replace('postgresql://', 'postgresql+asyncpg://')
    else:
        async_url = safe_database_url
    
    # Parse URL to handle SSL parameters properly
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    try:
        parsed = urlparse(async_url)
        if parsed.query:
            # Parse query parameters
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            
            # Handle SSL parameters for AsyncPG compatibility
            ssl_mode = query_params.get('sslmode', [None])[0]
            
            if ssl_mode is None:
                # No SSL mode specified - leave as is
                logger.debug("No sslmode parameter found - leaving URL unchanged")
            elif ssl_mode == 'disable':
                # For sslmode=disable, remove ALL SSL parameters for AsyncPG
                logger.info("Removing all SSL parameters for sslmode=disable with AsyncPG")
                ssl_params_to_remove = ['sslmode', 'sslcert', 'sslkey', 'sslrootcert', 'sslcrl', 'ssl']
                for param in ssl_params_to_remove:
                    if param in query_params:
                        logger.debug(f"Removing SSL parameter: {param}")
                        del query_params[param]
            
            elif ssl_mode in ['require', 'prefer', 'allow', 'verify-ca', 'verify-full']:
                # AsyncPG doesn't accept SSL parameters in URL - remove all SSL params
                logger.info(f"Removing SSL parameters from URL for AsyncPG (sslmode='{ssl_mode}' will be handled in connect_args)")
                ssl_params_to_remove = ['sslmode', 'sslcert', 'sslkey', 'sslrootcert', 'sslcrl', 'ssl']
                for param in ssl_params_to_remove:
                    if param in query_params:
                        logger.debug(f"Removing SSL parameter: {param}")
                        del query_params[param]
            else:
                # Handle unrecognized SSL modes by removing them
                logger.warning(f"Unrecognized sslmode '{ssl_mode}' - removing for AsyncPG compatibility")
                if 'sslmode' in query_params:
                    del query_params['sslmode']
                # Remove certificate parameters for safety
                cert_params = ['sslcert', 'sslkey', 'sslrootcert', 'sslcrl']
                for param in cert_params:
                    if param in query_params:
                        logger.debug(f"Removing cert parameter: {param}")
                        del query_params[param]
            
            # Rebuild query string
            if query_params:
                # Flatten single-item lists for cleaner URLs
                flattened_params = {}
                for key, values in query_params.items():
                    if len(values) == 1:
                        flattened_params[key] = values[0]
                    else:
                        flattened_params[key] = values
                
                new_query = urlencode(flattened_params, doseq=True)
                async_url = urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path,
                    parsed.params, new_query, parsed.fragment
                ))
            else:
                # No query parameters left
                async_url = urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path,
                    parsed.params, '', parsed.fragment
                ))
        
        # Validate the final URL by parsing it
        test_parsed = urlparse(async_url)
        if not all([test_parsed.scheme, test_parsed.netloc]):
            raise ValueError(f"URL conversion produced invalid result: {async_url}")
    
    except ValueError as ve:
        if "Invalid IPv6 URL" in str(ve):
            logger.error(f"IPv6 URL parsing error - likely special characters in password: {ve}")
            # Enhanced fallback for IPv6 parsing issues
            logger.info("Applying enhanced fallback for special character handling")
            
            # Fallback: Simple removal of problematic SSL parameters without URL parsing
            ssl_params = ['sslmode', 'sslcert', 'sslkey', 'sslrootcert', 'sslcrl']
            for param in ssl_params:
                pattern = rf'[?&]{param}=[^&]*'
                async_url = re.sub(pattern, '', async_url)
            
            # Clean up URL formatting
            async_url = re.sub(r'[?&]+$', '', async_url)  # Remove trailing ? or &
            async_url = re.sub(r'\?&', '?', async_url)     # Fix ?& to ?
            async_url = re.sub(r'&{2,}', '&', async_url)   # Fix multiple &
            
            logger.info("Enhanced fallback SSL parameter removal completed")
        else:
            raise ve
    
    except Exception as e:
        logger.error(f"Failed to parse URL for SSL parameter conversion: {e}")
        # Fallback: Simple removal of problematic SSL parameters
        import re
        
        ssl_params = ['sslmode', 'sslcert', 'sslkey', 'sslrootcert', 'sslcrl']
        for param in ssl_params:
            pattern = rf'[?&]{param}=[^&]*'
            async_url = re.sub(pattern, '', async_url)
        
        # Clean up URL formatting
        async_url = re.sub(r'[?&]+$', '', async_url)  # Remove trailing ? or &
        async_url = re.sub(r'\?&', '?', async_url)     # Fix ?& to ?
        async_url = re.sub(r'&{2,}', '&', async_url)   # Fix multiple &
        
        logger.warning(f"Used fallback SSL parameter removal")
    
    # Validate final result doesn't raise IPv6 error
    try:
        final_test = urlparse(async_url)
        logger.info(f"Successfully converted database URL for AsyncPG compatibility")
        logger.debug(f"Original: {database_url}")
        logger.debug(f"Converted: {async_url}")
        return async_url
    except ValueError as e:
        if "Invalid IPv6 URL" in str(e):
            # This should not happen with proper encoding, but as final safety
            logger.error(f"Final validation failed with IPv6 error: {e}")
            raise ValueError(f"Database URL conversion failed: special characters in password need proper encoding")
        else:
            raise e
def initialize_database(settings: Settings, pool_config: Optional[Dict[str, Any]] = None):
    """
    Initializes the SQLAlchemy engine and session factory using provided settings
    with optimized connection pool configuration for high performance.
    This function should be called once at application startup or test setup.
    Bootstrap sequence ensures proper connection pool health before proceeding.
    """
    database_url = settings.database_url
    logger.info(f"Initializing database with URL: {database_url}")
    logger.info(f"POSTGRES_HOST from settings: {settings.POSTGRES_HOST}")
    
    try:
        # Bootstrap sequence: Test basic connectivity before creating full pool
        logger.info("Starting database connection bootstrap sequence...")
        _test_database_connectivity(database_url)
        # SSL connection arguments for pgbouncer with proper certificate verification
        connect_args = {}
        async_connect_args = {}
        
        logger.info(f"Database URL check - pgbouncer in URL: {'pgbouncer' in database_url}")
        logger.info(f"Database URL check - POSTGRES_HOST: {settings.POSTGRES_HOST}")
        
        if "pgbouncer" in database_url or settings.POSTGRES_HOST == "pgbouncer":
            # Enable SSL for pgbouncer connections with proper configuration
            logger.info("Configuring SSL for pgbouncer connection")
            connect_args = {"sslmode": "require"}  # psycopg2 SSL parameter
            
            # For asyncpg with pgbouncer, we need to handle SSL properly
            # asyncpg will use SSL if the URL contains sslmode parameter
            async_connect_args = {}
            
            # Check for SSL certificate directory for enhanced security
            cert_dir = "/etc/certs/api"
            if os.path.exists(cert_dir):
                logger.info(f"Found SSL certificate directory: {cert_dir}")
                ssl_context = create_ssl_context(cert_dir)
                if ssl_context:
                    # For sync connections with certificates
                    connect_args.update({
                        "sslmode": "require",
                        "sslcert": f"{cert_dir}/client-cert.pem",
                        "sslkey": f"{cert_dir}/client-key.pem",
                        "sslrootcert": f"{cert_dir}/rootCA.pem"
                    })
                    logger.info("Enhanced SSL configuration applied for pgbouncer with certificates")
                else:
                    logger.warning("SSL certificates found but SSL context creation failed - using basic SSL")
        else:
            logger.info("Not using pgbouncer configuration - using standard postgres connection")
            # For direct postgres connection, respect the URL's SSL settings
            connect_args = {}
            async_connect_args = {}
        
        # Use the new ConnectionPoolOptimizer for pool configuration
        pool_config = pool_config or ConnectionPoolOptimizer.get_pool_config()
        pool_size = pool_config.get('pool_size', 10)
        max_overflow = pool_config.get('max_overflow', 20)
        pool_timeout = pool_config.get('pool_timeout', 45)
        pool_recycle = pool_config.get('pool_recycle', 3600)
        
        logger.info(f'Using connection pool configuration: size={pool_size}, max_overflow={max_overflow}, '
                   f'timeout={pool_timeout}s, recycle={pool_recycle}s')
        
        logger.info(f"Configuring sync database pool: size={pool_size}, max_overflow={max_overflow}, "
                   f"timeout={pool_timeout}s, recycle={pool_recycle}s")
        
        # Determine if this is a production environment
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        
        _db.engine = create_engine(
            database_url,
            # Connection pool configuration
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,
            
            # Connection health and reliability
            pool_reset_on_return='commit',
            echo_pool=not is_production,  # Pool logging for dev/debug
            
            # Connection arguments
            connect_args=connect_args
        )
        
        _db.session_local = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=_db.engine
        )

        # Initialize async database for enhanced authentication with optimized pool
        async_database_url = fix_async_database_url(database_url)
        logger.info(f"Original database URL: {database_url}")
        logger.info(f"Converted async database URL: {async_database_url}")
        try:
            # Async pool configuration optimized for authentication workloads
            # Keep async pools closer to sync pools for authentication-heavy usage
            async_pool_size = max(10, int(pool_size * 0.7))  # 70% of sync pool
            async_max_overflow = max(15, int(max_overflow * 0.6))  # 60% of sync overflow
            
            logger.info(f"Configuring async database pool: size={async_pool_size}, "
                       f"max_overflow={async_max_overflow}")
            
            # Configure SSL for AsyncPG properly via connect_args
            async_connect_args_with_ssl = async_connect_args.copy()
            
            # Determine SSL configuration based on original URL
            from urllib.parse import urlparse, parse_qs
            original_parsed = urlparse(database_url)
            original_params = parse_qs(original_parsed.query) if original_parsed.query else {}
            original_ssl_mode = original_params.get('sslmode', [None])[0]
            
            if original_ssl_mode in ['require', 'prefer', 'allow']:
                logger.info(f"Configuring AsyncPG SSL for sslmode='{original_ssl_mode}'")
                async_connect_args_with_ssl['ssl'] = 'require'
            elif original_ssl_mode in ['verify-ca', 'verify-full']:
                logger.info(f"Configuring AsyncPG SSL with verification for sslmode='{original_ssl_mode}'")
                # For verify modes, create SSL context
                ssl_context = ssl.create_default_context()
                if original_ssl_mode == 'verify-full':
                    ssl_context.check_hostname = True
                else:
                    ssl_context.check_hostname = False
                async_connect_args_with_ssl['ssl'] = ssl_context
            elif original_ssl_mode == 'disable':
                logger.info("SSL disabled for AsyncPG")
                async_connect_args_with_ssl['ssl'] = False
            else:
                # Default to require SSL for security
                logger.info("Defaulting to SSL required for AsyncPG")
                async_connect_args_with_ssl['ssl'] = 'require'
            
            logger.info(f"AsyncPG connect_args SSL config: {async_connect_args_with_ssl.get('ssl', 'Not set')}")
            
            _db.async_engine = create_async_engine(
                async_database_url,
                # Async pool configuration
                pool_size=async_pool_size,
                max_overflow=async_max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                pool_pre_ping=True,
                
                # Async-specific optimizations
                pool_reset_on_return='commit',
                echo_pool=not is_production,
                
                # Connection arguments for async with proper SSL configuration
                connect_args=async_connect_args_with_ssl
            )
            
            _db.async_session_local = async_sessionmaker(
                _db.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False  # Prevent automatic flushes for better control
            )
            logger.info("Async database initialization completed successfully.")
        except Exception as async_error:
            logger.error(f"Failed to initialize async database: {async_error}")
            logger.info("Continuing with sync-only database setup for compatibility")
            _db.async_engine = None
            _db.async_session_local = None

        logger.info("Database engine and SessionLocal configured successfully with optimized pools.")
    except Exception as e:
        logger.critical("Error initializing database: %s", e, exc_info=True)
        raise


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a SQLAlchemy session and ensures it's closed."""
    if _db.session_local is None:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    db = _db.session_local()
    try:
        yield db
    finally:
        db.close()

def get_session() -> Session:
    """Direct session getter for non-FastAPI usage. Remember to close the session."""
    if _db.session_local is None:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    return _db.session_local()

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async SQLAlchemy session with connection pool monitoring."""
    if _db.async_session_local is None:
        raise RuntimeError("Async database not initialized. Using sync sessions only.")
    
    # Check pool health before creating session
    if _db.async_engine:
        pool = _db.async_engine.pool
        if pool.checkedout() >= (pool.size() + getattr(pool, '_overflow', 0)) * 0.9:
            logger.warning(f"Async connection pool near exhaustion: {pool.checkedout()}/{pool.size() + getattr(pool, '_overflow', 0)}")
    
    session = None
    try:
        session = _db.async_session_local()
        yield session
        await session.commit()
    except Exception as e:
        logger.error(f"Async session error: {e}")
        if session:
            try:
                await session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during session rollback: {rollback_error}")
        
        # Check if this is a connection pool exhaustion error
        if "pool" in str(e).lower() or "timeout" in str(e).lower():
            logger.error("Connection pool exhaustion detected - consider scaling database connections")
        
        # Re-raise the original exception
        raise
    finally:
        if session:
            try:
                await session.close()
            except Exception as close_error:
                logger.error(f"Error closing async session: {close_error}")
                # Log current pool stats for debugging
                if _db.async_engine:
                    stats = get_database_stats()
                    logger.debug(f"Pool stats after session close error: {stats.get('async_engine', {})}")


@asynccontextmanager
async def get_async_session_context():
    """
    Async context manager for database sessions - supports 'async with' syntax.
    
    This provides proper async context manager protocol support for direct usage.
    Use this when you need 'async with get_async_session_context() as session:' pattern.
    """
    if _db.async_session_local is None:
        raise RuntimeError("Async database not initialized. Using sync sessions only.")
    
    # Check pool health before creating session
    if _db.async_engine:
        pool = _db.async_engine.pool
        if pool.checkedout() >= (pool.size() + getattr(pool, '_overflow', 0)) * 0.9:
            logger.warning(f"Async connection pool near exhaustion: {pool.checkedout()}/{pool.size() + getattr(pool, '_overflow', 0)}")
    
    session = None
    try:
        session = _db.async_session_local()
        yield session
        await session.commit()
    except Exception as e:
        logger.error(f"Async session context error: {e}")
        if session:
            try:
                await session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during session rollback: {rollback_error}")
        
        # Check if this is a connection pool exhaustion error
        if "pool" in str(e).lower() or "timeout" in str(e).lower():
            logger.error("Connection pool exhaustion detected - consider scaling database connections")
        
        # Re-raise the original exception
        raise
    finally:
        if session:
            try:
                await session.close()
            except Exception as close_error:
                logger.error(f"Error closing async session: {close_error}")
                # Log current pool stats for debugging
                if _db.async_engine:
                    stats = get_database_stats()
                    logger.debug(f"Pool stats after session close error: {stats.get('async_engine', {})}")

def get_database_stats() -> dict:
    """Get current database connection pool statistics for monitoring and metrics."""
    stats = {
        "sync_engine": None,
        "async_engine": None,
        "prometheus_metrics": {}
    }
    
    def _compute_pool_health(pool, pool_type):
        pool_size = pool.size()
        checked_out = pool.checkedout()
        checked_in = pool.checkedin()
        overflow = getattr(pool, '_overflow', 0)
        total_connections = pool_size + overflow
        utilization_percent = (checked_out / total_connections * 100) if total_connections > 0 else 0
        
        stats['prometheus_metrics'][f'{pool_type}_pool_total_connections'] = total_connections
        stats['prometheus_metrics'][f'{pool_type}_pool_checked_out'] = checked_out
        stats['prometheus_metrics'][f'{pool_type}_pool_utilization_percent'] = utilization_percent
        
        return {
            "pool_size": pool_size,
            "connections_created": checked_out,
            "connections_available": checked_in,
            "connections_overflow": overflow,
            "total_connections": total_connections,
            "utilization_percent": utilization_percent,
            "pool_class": pool.__class__.__name__
        }
    
    if _db.engine:
        pool = _db.engine.pool
        stats["sync_engine"] = _compute_pool_health(pool, 'sync')
    
    if _db.async_engine:
        pool = _db.async_engine.pool
        stats["async_engine"] = _compute_pool_health(pool, 'async')
    
    return stats


def get_engine() -> Optional[Engine]:
    """Get the sync database engine for direct access."""
    return _db.engine


def get_async_engine():
    """Get the async database engine for direct access."""
    return _db.async_engine


async def close_database_connections():
    """Close all database connections gracefully on shutdown."""
    if _db.engine:
        _db.engine.dispose()
        logger.info("Sync database connections closed")
    
    if _db.async_engine:
        await _db.async_engine.dispose()
        logger.info("Async database connections closed")


def _test_database_connectivity(database_url: str) -> bool:
    """
    Bootstrap helper: Test basic database connectivity before creating connection pools.
    This prevents pool initialization issues and provides early error detection.
    """
    logger.info("Testing database connectivity for bootstrap validation...")
    
    try:
        # Create a minimal engine for connectivity test
        test_engine = create_engine(
            database_url,
            pool_size=1,
            max_overflow=0,
            pool_timeout=10,
            pool_pre_ping=True,
            connect_args={}  # Basic connection without SSL complexity
        )
        
        # Test connection with simple query
        with test_engine.connect() as connection:
            result = connection.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            if test_value != 1:
                raise ValueError(f"Bootstrap test returned unexpected value: {test_value}")
        
        # Clean up test engine
        test_engine.dispose()
        logger.info("Database connectivity bootstrap test successful")
        return True
        
    except Exception as e:
        logger.error(f"Database connectivity bootstrap test failed: {e}")
        logger.error("This indicates a fundamental database connectivity issue")
        raise RuntimeError(f"Database bootstrap failed: {e}")


logger.info("database_setup.py loaded with optimized connection pooling. Database initialization deferred.")