"""
Test Resource Management Service

Manages cleanup of testing resources to prevent memory leaks and listener accumulation.
This service ensures proper cleanup of AbortControllers, WebSocket connections, 
browser instances, and other resources used during testing.
"""

import asyncio
import logging
import weakref
from typing import Dict, List, Any, Optional, Set
from contextlib import asynccontextmanager
import signal
import gc
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TestResourceManager:
    """
    Centralized resource management for testing to prevent memory leaks.
    """
    
    def __init__(self):
        self._abort_controllers: List[Any] = []
        self._websocket_connections: List[Any] = []
        self._browser_instances: List[Any] = []
        self._active_sessions: Set[str] = set()
        self._cleanup_callbacks: List[callable] = []
        self._resource_registry: Dict[str, Any] = {}
        self._max_listeners_per_signal = 10  # Conservative limit
        self._cleanup_interval = 30  # seconds
        self._last_cleanup = datetime.now()
        self._periodic_cleanup_task = None
        self._initialized = False
    
    def _setup_periodic_cleanup(self):
        """Set up periodic resource cleanup to prevent accumulation."""
        if self._periodic_cleanup_task is not None:
            return  # Already set up
            
        async def periodic_cleanup():
            while True:
                try:
                    await asyncio.sleep(self._cleanup_interval)
                    await self.cleanup_stale_resources()
                except Exception as e:
                    logger.error(f"Error in periodic cleanup: {e}")
        
        # Only start the cleanup task if we have a running event loop
        try:
            self._periodic_cleanup_task = asyncio.create_task(periodic_cleanup())
        except RuntimeError:
            # No event loop running, will set up later when needed
            self._periodic_cleanup_task = None
    
    async def _ensure_initialized(self):
        """Ensure the resource manager is properly initialized."""
        if not self._initialized:
            self._setup_periodic_cleanup()
            self._initialized = True
    
    def register_abort_controller(self, controller: Any, session_id: str = None) -> str:
        """
        Register an AbortController for proper cleanup.
        Returns a cleanup token.
        """
        # Ensure initialization
        try:
            asyncio.create_task(self._ensure_initialized())
        except RuntimeError:
            pass  # No event loop, will initialize later
        
        if len(self._abort_controllers) >= self._max_listeners_per_signal * 5:
            logger.warning(f"Too many AbortControllers registered: {len(self._abort_controllers)}")
            # Force cleanup of oldest controllers
            self._cleanup_old_controllers()
        
        controller_id = f"ac_{len(self._abort_controllers)}_{session_id or 'default'}"
        self._abort_controllers.append({
            'id': controller_id,
            'controller': controller,
            'session_id': session_id,
            'created_at': datetime.now()
        })
        
        logger.debug(f"Registered AbortController {controller_id}")
        return controller_id
    
    def register_websocket(self, websocket: Any, session_id: str = None) -> str:
        """
        Register a WebSocket connection for proper cleanup.
        Returns a cleanup token.
        """
        ws_id = f"ws_{len(self._websocket_connections)}_{session_id or 'default'}"
        self._websocket_connections.append({
            'id': ws_id,
            'websocket': websocket,
            'session_id': session_id,
            'created_at': datetime.now()
        })
        
        logger.debug(f"Registered WebSocket {ws_id}")
        return ws_id
    
    def register_browser_instance(self, browser: Any, session_id: str = None) -> str:
        """
        Register a browser instance for proper cleanup.
        Returns a cleanup token.
        """
        browser_id = f"browser_{len(self._browser_instances)}_{session_id or 'default'}"
        self._browser_instances.append({
            'id': browser_id,
            'browser': browser,
            'session_id': session_id,
            'created_at': datetime.now()
        })
        
        logger.debug(f"Registered browser instance {browser_id}")
        return browser_id
    
    def register_cleanup_callback(self, callback: callable, session_id: str = None):
        """
        Register a cleanup callback to be called during resource cleanup.
        """
        self._cleanup_callbacks.append({
            'callback': callback,
            'session_id': session_id,
            'created_at': datetime.now()
        })
    
    async def cleanup_session(self, session_id: str):
        """
        Clean up all resources associated with a specific session.
        """
        logger.info(f"Cleaning up session: {session_id}")
        
        # Cleanup AbortControllers for this session
        controllers_to_remove = []
        for i, controller_info in enumerate(self._abort_controllers):
            if controller_info.get('session_id') == session_id:
                try:
                    controller = controller_info['controller']
                    if hasattr(controller, 'abort') and not controller.signal.aborted:
                        controller.abort()
                    controllers_to_remove.append(i)
                    logger.debug(f"Cleaned up AbortController {controller_info['id']}")
                except Exception as e:
                    logger.error(f"Error cleaning up AbortController: {e}")
        
        # Remove cleaned up controllers
        for i in reversed(controllers_to_remove):
            self._abort_controllers.pop(i)
        
        # Cleanup WebSockets for this session
        websockets_to_remove = []
        for i, ws_info in enumerate(self._websocket_connections):
            if ws_info.get('session_id') == session_id:
                try:
                    websocket = ws_info['websocket']
                    if hasattr(websocket, 'close'):
                        await websocket.close()
                    websockets_to_remove.append(i)
                    logger.debug(f"Cleaned up WebSocket {ws_info['id']}")
                except Exception as e:
                    logger.error(f"Error cleaning up WebSocket: {e}")
        
        # Remove cleaned up websockets
        for i in reversed(websockets_to_remove):
            self._websocket_connections.pop(i)
        
        # Cleanup browsers for this session
        browsers_to_remove = []
        for i, browser_info in enumerate(self._browser_instances):
            if browser_info.get('session_id') == session_id:
                try:
                    browser = browser_info['browser']
                    if hasattr(browser, 'close'):
                        await browser.close()
                    browsers_to_remove.append(i)
                    logger.debug(f"Cleaned up browser {browser_info['id']}")
                except Exception as e:
                    logger.error(f"Error cleaning up browser: {e}")
        
        # Remove cleaned up browsers
        for i in reversed(browsers_to_remove):
            self._browser_instances.pop(i)
        
        # Run cleanup callbacks for this session
        callbacks_to_remove = []
        for i, callback_info in enumerate(self._cleanup_callbacks):
            if callback_info.get('session_id') == session_id:
                try:
                    await callback_info['callback']()
                    callbacks_to_remove.append(i)
                    logger.debug(f"Executed cleanup callback for session {session_id}")
                except Exception as e:
                    logger.error(f"Error executing cleanup callback: {e}")
        
        # Remove executed callbacks
        for i in reversed(callbacks_to_remove):
            self._cleanup_callbacks.pop(i)
        
        # Remove session from active sessions
        self._active_sessions.discard(session_id)
        
        logger.info(f"Session cleanup completed: {session_id}")
    
    async def cleanup_all_resources(self):
        """
        Clean up all registered resources.
        """
        logger.info("Starting cleanup of all resources")
        
        # Cleanup all AbortControllers
        for controller_info in self._abort_controllers:
            try:
                controller = controller_info['controller']
                if hasattr(controller, 'abort') and not controller.signal.aborted:
                    controller.abort()
                logger.debug(f"Cleaned up AbortController {controller_info['id']}")
            except Exception as e:
                logger.error(f"Error cleaning up AbortController: {e}")
        
        self._abort_controllers.clear()
        
        # Cleanup all WebSockets
        for ws_info in self._websocket_connections:
            try:
                websocket = ws_info['websocket']
                if hasattr(websocket, 'close'):
                    await websocket.close()
                logger.debug(f"Cleaned up WebSocket {ws_info['id']}")
            except Exception as e:
                logger.error(f"Error cleaning up WebSocket: {e}")
        
        self._websocket_connections.clear()
        
        # Cleanup all browsers
        for browser_info in self._browser_instances:
            try:
                browser = browser_info['browser']
                if hasattr(browser, 'close'):
                    await browser.close()
                logger.debug(f"Cleaned up browser {browser_info['id']}")
            except Exception as e:
                logger.error(f"Error cleaning up browser: {e}")
        
        self._browser_instances.clear()
        
        # Run all cleanup callbacks
        for callback_info in self._cleanup_callbacks:
            try:
                await callback_info['callback']()
                logger.debug("Executed cleanup callback")
            except Exception as e:
                logger.error(f"Error executing cleanup callback: {e}")
        
        self._cleanup_callbacks.clear()
        
        # Clear all sessions
        self._active_sessions.clear()
        self._resource_registry.clear()
        
        # Force garbage collection
        gc.collect()
        
        logger.info("All resources cleaned up successfully")
    
    async def cleanup_stale_resources(self):
        """
        Clean up resources that are older than a threshold.
        """
        now = datetime.now()
        stale_threshold = timedelta(minutes=5)
        
        # Cleanup stale AbortControllers
        controllers_to_remove = []
        for i, controller_info in enumerate(self._abort_controllers):
            if now - controller_info['created_at'] > stale_threshold:
                try:
                    controller = controller_info['controller']
                    if hasattr(controller, 'abort') and not controller.signal.aborted:
                        controller.abort()
                    controllers_to_remove.append(i)
                    logger.debug(f"Cleaned up stale AbortController {controller_info['id']}")
                except Exception as e:
                    logger.error(f"Error cleaning up stale AbortController: {e}")
        
        # Remove stale controllers
        for i in reversed(controllers_to_remove):
            self._abort_controllers.pop(i)
        
        if controllers_to_remove:
            logger.info(f"Cleaned up {len(controllers_to_remove)} stale AbortControllers")
    
    def _cleanup_old_controllers(self):
        """
        Emergency cleanup of oldest AbortControllers when limit is reached.
        """
        if len(self._abort_controllers) > self._max_listeners_per_signal:
            controllers_to_remove = len(self._abort_controllers) - self._max_listeners_per_signal
            
            for i in range(controllers_to_remove):
                try:
                    controller_info = self._abort_controllers[i]
                    controller = controller_info['controller']
                    if hasattr(controller, 'abort') and not controller.signal.aborted:
                        controller.abort()
                    logger.debug(f"Emergency cleanup of AbortController {controller_info['id']}")
                except Exception as e:
                    logger.error(f"Error in emergency cleanup: {e}")
            
            # Remove the cleaned up controllers
            self._abort_controllers = self._abort_controllers[controllers_to_remove:]
            logger.warning(f"Emergency cleanup: removed {controllers_to_remove} old AbortControllers")
    
    @asynccontextmanager
    async def test_session(self, session_id: str):
        """
        Context manager for test sessions that ensures proper cleanup.
        
        Usage:
            async with test_resource_manager.test_session("test_login") as session:
                # Your test code here
                controller = session.create_abort_controller()
                # Test will automatically clean up when done
        """
        self._active_sessions.add(session_id)
        
        class TestSession:
            def __init__(self, manager, session_id):
                self.manager = manager
                self.session_id = session_id
            
            def create_abort_controller(self):
                """Create an AbortController that will be automatically cleaned up."""
                from http import HTTPStatus
                import signal
                
                class ManagedAbortController:
                    def __init__(self, manager, session_id):
                        self.signal = signal.SIGTERM  # Placeholder
                        self.aborted = False
                        self._manager = manager
                        self._id = manager.register_abort_controller(self, session_id)
                    
                    def abort(self):
                        if not self.aborted:
                            self.aborted = True
                
                return ManagedAbortController(self.manager, session_id)
            
            def register_cleanup(self, callback):
                """Register a cleanup callback for this session."""
                self.manager.register_cleanup_callback(callback, self.session_id)
        
        session = TestSession(self, session_id)
        
        try:
            logger.info(f"Starting test session: {session_id}")
            yield session
        finally:
            logger.info(f"Ending test session: {session_id}")
            await self.cleanup_session(session_id)
    
    def get_resource_stats(self) -> Dict[str, int]:
        """
        Get current resource usage statistics.
        """
        return {
            'abort_controllers': len(self._abort_controllers),
            'websocket_connections': len(self._websocket_connections),
            'browser_instances': len(self._browser_instances),
            'active_sessions': len(self._active_sessions),
            'cleanup_callbacks': len(self._cleanup_callbacks)
        }


# Global instance
test_resource_manager = TestResourceManager()


# Convenience functions for easy integration
async def cleanup_test_resources():
    """Clean up all test resources."""
    await test_resource_manager.cleanup_all_resources()


def get_test_session(session_id: str):
    """Get a managed test session context."""
    return test_resource_manager.test_session(session_id)


def register_test_abort_controller(controller, session_id: str = None) -> str:
    """Register an AbortController for cleanup."""
    return test_resource_manager.register_abort_controller(controller, session_id)


def register_test_websocket(websocket, session_id: str = None) -> str:
    """Register a WebSocket for cleanup."""
    return test_resource_manager.register_websocket(websocket, session_id)


def register_test_browser(browser, session_id: str = None) -> str:
    """Register a browser instance for cleanup."""
    return test_resource_manager.register_browser_instance(browser, session_id)