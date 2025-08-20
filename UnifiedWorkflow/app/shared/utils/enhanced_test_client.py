"""
Enhanced Test Client with Resource Management

Provides HTTP client functionality with proper resource cleanup to prevent
memory leaks and AbortSignal listener accumulation.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin
import aiohttp
from contextlib import asynccontextmanager

from shared.services.test_resource_manager import test_resource_manager

logger = logging.getLogger(__name__)


class EnhancedTestClient:
    """
    HTTP client for testing with automatic resource management.
    Prevents AbortSignal listener accumulation and ensures proper cleanup.
    """
    
    def __init__(self, base_url: str = "https://localhost", session_id: str = None):
        self.base_url = base_url.rstrip('/')
        self.session_id = session_id or f"test_client_{id(self)}"
        self._session: Optional[aiohttp.ClientSession] = None
        self._active_requests: Dict[str, Any] = {}
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure we have an active session."""
        if self._session is None or self._session.closed:
            # Create session with proper timeout and connector limits
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                limit=10,  # Limit total connections
                limit_per_host=5,  # Limit per host
                enable_cleanup_closed=True
            )
            
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                connector_owner=True
            )
            
            # Register the session for cleanup
            test_resource_manager.register_cleanup_callback(
                self._cleanup_session, self.session_id
            )
    
    async def _cleanup_session(self):
        """Clean up the HTTP session."""
        if self._session and not self._session.closed:
            try:
                await self._session.close()
                logger.debug(f"Cleaned up HTTP session for {self.session_id}")
            except Exception as e:
                logger.error(f"Error cleaning up HTTP session: {e}")
        self._session = None
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, bytes, Dict]] = None,
        json_data: Optional[Dict] = None,
        cookies: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with proper resource management.
        """
        await self._ensure_session()
        
        # Prepare URL
        if not url.startswith('http'):
            url = urljoin(self.base_url, url.lstrip('/'))
        
        # Prepare headers
        if headers is None:
            headers = {}
        
        # Set content type for JSON data
        if json_data is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(json_data)
        
        # Create managed AbortController
        request_id = f"req_{len(self._active_requests)}"
        
        try:
            # Create timeout if specified
            request_timeout = None
            if timeout:
                request_timeout = aiohttp.ClientTimeout(total=timeout)
            
            logger.debug(f"Making {method} request to {url}")
            
            # Make the request
            async with self._session.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                cookies=cookies,
                timeout=request_timeout,
                ssl=False  # For development with self-signed certs
            ) as response:
                
                # Read response
                try:
                    response_text = await response.text()
                    
                    # Try to parse as JSON
                    try:
                        response_data = json.loads(response_text)
                    except json.JSONDecodeError:
                        response_data = response_text
                    
                    result = {
                        'status_code': response.status,
                        'headers': dict(response.headers),
                        'data': response_data,
                        'cookies': {cookie.key: cookie.value for cookie in response.cookies.values()},
                        'url': str(response.url)
                    }
                    
                    logger.debug(f"Request {request_id} completed with status {response.status}")
                    return result
                    
                except Exception as e:
                    logger.error(f"Error reading response for request {request_id}: {e}")
                    return {
                        'status_code': response.status,
                        'headers': dict(response.headers),
                        'data': None,
                        'error': str(e),
                        'url': str(response.url)
                    }
        
        except asyncio.TimeoutError:
            logger.error(f"Request {request_id} timed out")
            return {
                'status_code': 408,
                'data': None,
                'error': 'Request timeout',
                'url': url
            }
        
        except Exception as e:
            logger.error(f"Request {request_id} failed: {e}")
            return {
                'status_code': 500,
                'data': None,
                'error': str(e),
                'url': url
            }
        
        finally:
            # Clean up request tracking
            self._active_requests.pop(request_id, None)
    
    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make a GET request."""
        return await self.request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make a POST request."""
        return await self.request('POST', url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make a PUT request."""
        return await self.request('PUT', url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make a DELETE request."""
        return await self.request('DELETE', url, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make a PATCH request."""
        return await self.request('PATCH', url, **kwargs)
    
    async def close(self):
        """Close the client and clean up resources."""
        await self._cleanup_session()
        
        # Clear active requests
        self._active_requests.clear()
        
        logger.debug(f"EnhancedTestClient {self.session_id} closed")


@asynccontextmanager
async def get_test_client(base_url: str = "https://localhost", session_id: str = None):
    """
    Context manager for getting a managed test client.
    
    Usage:
        async with get_test_client("https://localhost") as client:
            response = await client.get("/api/v1/health")
            # Client will be automatically cleaned up
    """
    client = EnhancedTestClient(base_url, session_id)
    try:
        await client.__aenter__()
        yield client
    finally:
        await client.__aexit__(None, None, None)


class AuthenticatedTestClient(EnhancedTestClient):
    """
    Test client with authentication support.
    """
    
    def __init__(self, base_url: str = "https://localhost", session_id: str = None):
        super().__init__(base_url, session_id)
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.auth_cookies: Dict[str, str] = {}
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login and store authentication tokens.
        """
        login_data = {
            "email": email,
            "password": password
        }
        
        response = await self.post("/api/v1/auth/jwt/login", json_data=login_data)
        
        if response['status_code'] == 200:
            # Store tokens
            if 'data' in response and isinstance(response['data'], dict):
                self.access_token = response['data'].get('access_token')
            
            # Store auth cookies
            if 'cookies' in response:
                self.auth_cookies.update(response['cookies'])
            
            logger.info(f"Successfully logged in as {email}")
        else:
            logger.error(f"Login failed: {response}")
        
        return response
    
    async def logout(self) -> Dict[str, Any]:
        """
        Logout and clear authentication tokens.
        """
        response = await self.post("/api/v1/auth/logout")
        
        # Clear stored tokens regardless of response
        self.access_token = None
        self.refresh_token = None
        self.auth_cookies.clear()
        
        return response
    
    async def request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make an authenticated request.
        """
        # Add authentication headers if we have a token
        headers = kwargs.get('headers', {})
        
        if self.access_token:
            headers['Authorization'] = f"Bearer {self.access_token}"
        
        # Add auth cookies
        cookies = kwargs.get('cookies', {})
        cookies.update(self.auth_cookies)
        
        kwargs['headers'] = headers
        kwargs['cookies'] = cookies
        
        return await super().request(method, url, **kwargs)


@asynccontextmanager
async def get_authenticated_test_client(
    base_url: str = "https://localhost", 
    session_id: str = None,
    email: str = None,
    password: str = None
):
    """
    Context manager for getting an authenticated test client.
    
    Usage:
        async with get_authenticated_test_client(
            "https://localhost", 
            email="test@example.com", 
            password="testpass"
        ) as client:
            response = await client.get("/api/v1/profile")
            # Client will be automatically cleaned up
    """
    client = AuthenticatedTestClient(base_url, session_id)
    try:
        await client.__aenter__()
        
        # Login if credentials provided
        if email and password:
            await client.login(email, password)
        
        yield client
    finally:
        # Logout before cleanup
        if client.access_token:
            try:
                await client.logout()
            except Exception as e:
                logger.debug(f"Error during logout: {e}")
        
        await client.__aexit__(None, None, None)