"""
Token Refresh Background Scheduler
Automatically refreshes OAuth tokens before they expire to prevent service interruptions.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import UserOAuthToken
from shared.utils.database_setup import get_async_session_context
from .oauth_token_manager import OAuthTokenManager

logger = logging.getLogger(__name__)


class TokenRefreshScheduler:
    """
    Background scheduler that automatically refreshes OAuth tokens before expiry.
    
    Features:
    - Runs every 5 minutes to check for expiring tokens
    - Refreshes tokens that expire within 10 minutes
    - Handles multiple users concurrently
    - Graceful error handling and logging
    - Circuit breaker integration
    """
    
    def __init__(self, check_interval_minutes: int = 5):
        self.check_interval_minutes = check_interval_minutes
        self.running = False
        self._task = None
    
    def start(self):
        """Start the background token refresh scheduler."""
        if self.running:
            logger.warning("Token refresh scheduler is already running")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"Started token refresh scheduler (checking every {self.check_interval_minutes} minutes)")
    
    def stop(self):
        """Stop the background token refresh scheduler."""
        if not self.running:
            return
        
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
        
        logger.info("Stopped token refresh scheduler")
    
    async def _scheduler_loop(self):
        """Main scheduler loop that runs token refresh checks."""
        while self.running:
            try:
                await self._refresh_expiring_tokens()
            except Exception as e:
                logger.error(f"Error in token refresh scheduler: {e}", exc_info=True)
            
            # Wait for next check interval
            if self.running:
                await asyncio.sleep(self.check_interval_minutes * 60)
    
    async def _refresh_expiring_tokens(self):
        """Check for and refresh tokens expiring within the next 10 minutes."""
        try:
            # Get database session
            async with get_async_session_context() as db:
                # Find tokens expiring within 10 minutes
                cutoff_time = datetime.now(timezone.utc) + timedelta(minutes=10)
                
                result = await db.execute(
                    select(UserOAuthToken).filter(
                        UserOAuthToken.refresh_token.isnot(None),
                        UserOAuthToken.token_expiry <= cutoff_time,
                        UserOAuthToken.token_expiry > datetime.now(timezone.utc)  # Not already expired
                    )
                )
                
                expiring_tokens = result.scalars().all()
                
                if not expiring_tokens:
                    logger.debug("No tokens need refreshing")
                    return
                
                logger.info(f"Found {len(expiring_tokens)} tokens that need refreshing")
                
                # Group tokens by user for batch processing
                user_tokens = {}
                for token in expiring_tokens:
                    if token.user_id not in user_tokens:
                        user_tokens[token.user_id] = []
                    user_tokens[token.user_id].append(token)
                
                # Process each user's tokens concurrently
                tasks = []
                for user_id, tokens in user_tokens.items():
                    task = asyncio.create_task(
                        self._refresh_user_tokens(user_id, tokens)
                    )
                    tasks.append(task)
                
                # Wait for all refresh operations to complete
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Log results
                    success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
                    error_count = sum(1 for r in results if isinstance(r, Exception))
                    
                    logger.info(f"Token refresh completed: {success_count} successful, {error_count} failed")
                    
                    # Log any exceptions
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"Token refresh task failed: {result}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Error in _refresh_expiring_tokens: {e}", exc_info=True)
    
    async def _refresh_user_tokens(self, user_id: int, tokens: List[UserOAuthToken]) -> Dict[str, Any]:
        """Refresh all tokens for a specific user."""
        try:
            async with get_async_session_context() as db:
                token_manager = OAuthTokenManager(db)
                
                results = {
                    "user_id": user_id,
                    "success": True,
                    "tokens_processed": 0,
                    "tokens_refreshed": 0,
                    "errors": []
                }
                
                for token in tokens:
                    try:
                        results["tokens_processed"] += 1
                        
                        logger.info(f"Refreshing {token.service.value} token for user {user_id} (expires: {token.token_expiry})")
                        
                        if await token_manager.refresh_token(token):
                            results["tokens_refreshed"] += 1
                            logger.info(f"Successfully refreshed {token.service.value} token for user {user_id}")
                        else:
                            error_msg = f"Failed to refresh {token.service.value} token for user {user_id}"
                            results["errors"].append(error_msg)
                            logger.warning(error_msg)
                    
                    except Exception as e:
                        error_msg = f"Error refreshing {token.service.value} token for user {user_id}: {str(e)}"
                        results["errors"].append(error_msg)
                        logger.error(error_msg, exc_info=True)
                
                # Mark as failed if no tokens were successfully refreshed
                if results["tokens_processed"] > 0 and results["tokens_refreshed"] == 0:
                    results["success"] = False
                
                return results
        
        except Exception as e:
            logger.error(f"Error refreshing tokens for user {user_id}: {e}", exc_info=True)
            return {
                "user_id": user_id,
                "success": False,
                "error": str(e)
            }


# Global scheduler instance
token_refresh_scheduler = TokenRefreshScheduler()


def start_token_refresh_scheduler():
    """Start the global token refresh scheduler."""
    token_refresh_scheduler.start()


def stop_token_refresh_scheduler():
    """Stop the global token refresh scheduler."""
    token_refresh_scheduler.stop()


# Function to trigger manual token refresh for testing
async def trigger_manual_token_refresh() -> Dict[str, Any]:
    """
    Manually trigger token refresh for all expiring tokens.
    Useful for testing or immediate refresh needs.
    """
    scheduler = TokenRefreshScheduler()
    try:
        await scheduler._refresh_expiring_tokens()
        return {"status": "success", "message": "Manual token refresh completed"}
    except Exception as e:
        logger.error(f"Manual token refresh failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}