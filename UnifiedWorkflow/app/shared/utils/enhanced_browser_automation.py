"""
Enhanced Browser Automation with Resource Management

Provides browser automation functionality with proper resource cleanup
to prevent memory leaks and AbortSignal listener accumulation.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from shared.services.test_resource_manager import test_resource_manager

logger = logging.getLogger(__name__)


class ManagedBrowserSession:
    """
    Browser session with automatic resource management.
    Prevents memory leaks and ensures proper cleanup of browser resources.
    """
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"browser_session_{id(self)}"
        self._browser_instance = None
        self._page_instances = []
        self._websocket_connections = []
        self._resource_cleanup_callbacks = []
        self._is_active = False
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self._cleanup_browser_resources()
    
    async def _initialize_browser(self):
        """Initialize browser with resource tracking."""
        try:
            # Register this browser session for cleanup
            test_resource_manager.register_cleanup_callback(
                self._cleanup_browser_resources, self.session_id
            )
            
            self._is_active = True
            logger.debug(f"Initialized browser session: {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error initializing browser session: {e}")
            raise
    
    async def _cleanup_browser_resources(self):
        """Clean up all browser-related resources."""
        if not self._is_active:
            return
        
        logger.info(f"Cleaning up browser session: {self.session_id}")
        
        try:
            # Close all page instances
            for page_info in self._page_instances:
                try:
                    if 'page' in page_info and hasattr(page_info['page'], 'close'):
                        await page_info['page'].close()
                    logger.debug(f"Closed page: {page_info.get('id', 'unknown')}")
                except Exception as e:
                    logger.error(f"Error closing page: {e}")
            
            self._page_instances.clear()
            
            # Close WebSocket connections
            for ws_info in self._websocket_connections:
                try:
                    if 'websocket' in ws_info and hasattr(ws_info['websocket'], 'close'):
                        await ws_info['websocket'].close()
                    logger.debug(f"Closed WebSocket: {ws_info.get('id', 'unknown')}")
                except Exception as e:
                    logger.error(f"Error closing WebSocket: {e}")
            
            self._websocket_connections.clear()
            
            # Execute cleanup callbacks
            for callback in self._resource_cleanup_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Error executing cleanup callback: {e}")
            
            self._resource_cleanup_callbacks.clear()
            
            # Close browser instance if we created one
            if self._browser_instance and hasattr(self._browser_instance, 'close'):
                await self._browser_instance.close()
                logger.debug(f"Closed browser instance for session: {self.session_id}")
            
            self._browser_instance = None
            self._is_active = False
            
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")
        
        logger.info(f"Browser session cleanup completed: {self.session_id}")
    
    def register_page(self, page: Any, page_id: str = None) -> str:
        """Register a page instance for cleanup."""
        page_id = page_id or f"page_{len(self._page_instances)}"
        page_info = {
            'id': page_id,
            'page': page,
            'created_at': datetime.now()
        }
        self._page_instances.append(page_info)
        logger.debug(f"Registered page: {page_id}")
        return page_id
    
    def register_websocket(self, websocket: Any, ws_id: str = None) -> str:
        """Register a WebSocket connection for cleanup."""
        ws_id = ws_id or f"ws_{len(self._websocket_connections)}"
        ws_info = {
            'id': ws_id,
            'websocket': websocket,
            'created_at': datetime.now()
        }
        self._websocket_connections.append(ws_info)
        test_resource_manager.register_websocket(websocket, self.session_id)
        logger.debug(f"Registered WebSocket: {ws_id}")
        return ws_id
    
    def register_cleanup_callback(self, callback: callable):
        """Register a cleanup callback to be executed during cleanup."""
        self._resource_cleanup_callbacks.append(callback)
    
    async def navigate_with_cleanup(self, url: str, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Navigate to URL with proper resource management.
        """
        if not self._is_active:
            raise RuntimeError("Browser session is not active")
        
        try:
            # This would integrate with actual Playwright MCP calls
            # For now, we'll simulate the navigation
            navigation_result = {
                'url': url,
                'status': 'success',
                'timestamp': datetime.now().isoformat()
            }
            
            logger.debug(f"Navigation completed: {url}")
            return navigation_result
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return {
                'url': url,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def take_managed_screenshot(self, filename: str = None, full_page: bool = False) -> Dict[str, Any]:
        """
        Take screenshot with resource tracking.
        """
        if not self._is_active:
            raise RuntimeError("Browser session is not active")
        
        try:
            filename = filename or f"screenshot_{self.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            # This would integrate with actual Playwright MCP calls
            screenshot_result = {
                'filename': filename,
                'full_page': full_page,
                'status': 'success',
                'timestamp': datetime.now().isoformat()
            }
            
            logger.debug(f"Screenshot taken: {filename}")
            return screenshot_result
            
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {
                'filename': filename,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_console_messages_managed(self) -> List[Dict[str, Any]]:
        """
        Get console messages with resource management.
        """
        if not self._is_active:
            raise RuntimeError("Browser session is not active")
        
        try:
            # This would integrate with actual Playwright MCP calls
            # For now, simulate console message retrieval
            console_messages = [
                {
                    'type': 'info',
                    'text': 'Browser session initialized',
                    'timestamp': datetime.now().isoformat()
                }
            ]
            
            return console_messages
            
        except Exception as e:
            logger.error(f"Error getting console messages: {e}")
            return []
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about the current session."""
        return {
            'session_id': self.session_id,
            'is_active': self._is_active,
            'pages_count': len(self._page_instances),
            'websockets_count': len(self._websocket_connections),
            'cleanup_callbacks_count': len(self._resource_cleanup_callbacks),
            'created_at': getattr(self, '_created_at', 'unknown')
        }


@asynccontextmanager
async def get_managed_browser_session(session_id: str = None):
    """
    Context manager for getting a managed browser session.
    
    Usage:
        async with get_managed_browser_session("ui_test_session") as browser:
            await browser.navigate_with_cleanup("https://localhost")
            screenshot = await browser.take_managed_screenshot()
            # Browser will be automatically cleaned up
    """
    session = ManagedBrowserSession(session_id)
    try:
        await session.__aenter__()
        yield session
    finally:
        await session.__aexit__(None, None, None)


class BrowserResourceMonitor:
    """
    Monitor browser resource usage and detect potential leaks.
    """
    
    def __init__(self):
        self._monitoring_active = False
        self._resource_snapshots = []
        self._alert_thresholds = {
            'abort_controllers': 20,
            'websocket_connections': 10,
            'browser_instances': 5,
            'memory_usage_mb': 500
        }
    
    async def start_monitoring(self, interval_seconds: int = 30):
        """Start monitoring browser resources."""
        self._monitoring_active = True
        
        async def monitoring_loop():
            while self._monitoring_active:
                try:
                    # Take resource snapshot
                    snapshot = {
                        'timestamp': datetime.now().isoformat(),
                        'resources': test_resource_manager.get_resource_stats()
                    }
                    
                    self._resource_snapshots.append(snapshot)
                    
                    # Keep only last 100 snapshots
                    if len(self._resource_snapshots) > 100:
                        self._resource_snapshots = self._resource_snapshots[-100:]
                    
                    # Check for resource leaks
                    await self._check_for_leaks(snapshot)
                    
                    await asyncio.sleep(interval_seconds)
                    
                except Exception as e:
                    logger.error(f"Error in browser resource monitoring: {e}")
                    await asyncio.sleep(interval_seconds)
        
        # Start monitoring task
        asyncio.create_task(monitoring_loop())
        logger.info("Browser resource monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring browser resources."""
        self._monitoring_active = False
        logger.info("Browser resource monitoring stopped")
    
    async def _check_for_leaks(self, snapshot: Dict[str, Any]):
        """Check for potential resource leaks."""
        resources = snapshot['resources']
        
        # Check against thresholds
        for resource_type, threshold in self._alert_thresholds.items():
            if resource_type in resources and resources[resource_type] > threshold:
                logger.warning(
                    f"Browser resource threshold exceeded: {resource_type} = {resources[resource_type]} (threshold: {threshold})"
                )
                
                # Trigger emergency cleanup if AbortController count is too high
                if resource_type == 'abort_controllers' and resources[resource_type] > 50:
                    logger.error("Emergency cleanup triggered due to excessive AbortControllers")
                    await test_resource_manager.cleanup_stale_resources()
    
    def get_monitoring_report(self) -> Dict[str, Any]:
        """Get a monitoring report."""
        if not self._resource_snapshots:
            return {'status': 'no_data', 'snapshots': 0}
        
        latest_snapshot = self._resource_snapshots[-1]
        first_snapshot = self._resource_snapshots[0]
        
        return {
            'status': 'active' if self._monitoring_active else 'stopped',
            'snapshots_count': len(self._resource_snapshots),
            'monitoring_period': {
                'start': first_snapshot['timestamp'],
                'end': latest_snapshot['timestamp']
            },
            'current_resources': latest_snapshot['resources'],
            'trend_analysis': self._analyze_trends()
        }
    
    def _analyze_trends(self) -> Dict[str, str]:
        """Analyze resource usage trends."""
        if len(self._resource_snapshots) < 2:
            return {'status': 'insufficient_data'}
        
        first = self._resource_snapshots[0]['resources']
        latest = self._resource_snapshots[-1]['resources']
        
        trends = {}
        for resource_type in first.keys():
            if resource_type in latest:
                change = latest[resource_type] - first[resource_type]
                if change > 0:
                    trends[resource_type] = 'increasing'
                elif change < 0:
                    trends[resource_type] = 'decreasing'
                else:
                    trends[resource_type] = 'stable'
        
        return trends


# Global monitor instance
browser_resource_monitor = BrowserResourceMonitor()


# Convenience functions
async def start_browser_monitoring(interval_seconds: int = 30):
    """Start browser resource monitoring."""
    await browser_resource_monitor.start_monitoring(interval_seconds)


def stop_browser_monitoring():
    """Stop browser resource monitoring."""
    browser_resource_monitor.stop_monitoring()


def get_browser_monitoring_report() -> Dict[str, Any]:
    """Get browser monitoring report."""
    return browser_resource_monitor.get_monitoring_report()