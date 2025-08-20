# Testing Best Practices - Resource Management

## Overview

This document outlines best practices for testing in the AI Workflow Engine to prevent memory leaks, resource accumulation, and the MaxListenersExceededWarning error.

## The Problem

The MaxListenersExceededWarning occurs when:
- Multiple AbortSignal listeners accumulate without cleanup
- WebSocket connections aren't properly closed
- Browser instances aren't cleaned up after tests
- HTTP requests create AbortControllers that persist beyond test scope

## Solution Architecture

### 1. Test Resource Manager Service

The `TestResourceManager` service provides centralized resource management:

```python
from shared.services.test_resource_manager import test_resource_manager

# Use managed test sessions
async with test_resource_manager.test_session("test_login") as session:
    # All resources created in this session will be automatically cleaned up
    controller = session.create_abort_controller()
    # Test code here
    # Cleanup happens automatically when session ends
```

### 2. Enhanced Test Client

Use the `EnhancedTestClient` for HTTP requests:

```python
from shared.utils.enhanced_test_client import get_authenticated_test_client

async with get_authenticated_test_client(
    "https://localhost",
    email="test@example.com",
    password="password"
) as client:
    response = await client.get("/api/v1/profile")
    # Client automatically cleans up connections
```

### 3. Managed Browser Sessions

Use the `ManagedBrowserSession` for browser automation:

```python
from shared.utils.enhanced_browser_automation import get_managed_browser_session

async with get_managed_browser_session("ui_test") as browser:
    await browser.navigate_with_cleanup("https://localhost")
    screenshot = await browser.take_managed_screenshot()
    # Browser resources automatically cleaned up
```

## Testing Workflow

### Phase 1: Pre-Test Setup

```python
# 1. Initialize resource management
from shared.services.test_resource_manager import test_resource_manager
from datetime import datetime

session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# 2. Get baseline resource stats
initial_stats = test_resource_manager.get_resource_stats()
logger.info(f"Initial resources: {initial_stats}")

# 3. Set maximum listener limits (if needed temporarily)
import events
events.setMaxListeners(100)  # Only for testing, not permanent solution
```

### Phase 2: Test Execution

```python
# Use managed sessions for all testing
async with test_resource_manager.test_session(session_id) as session:
    
    # HTTP testing
    async with get_authenticated_test_client(
        base_url="https://localhost",
        session_id=session_id,
        email="test@example.com",
        password="password"
    ) as client:
        
        # Browser testing
        async with get_managed_browser_session(session_id) as browser:
            
            # Your test code here
            response = await client.get("/api/v1/profile")
            await browser.navigate_with_cleanup("https://localhost")
            
            # All resources are tracked and will be cleaned up
```

### Phase 3: Post-Test Cleanup

```python
# 1. Get final resource stats
final_stats = test_resource_manager.get_resource_stats()
logger.info(f"Final resources: {final_stats}")

# 2. Check for leaks
if final_stats['abort_controllers'] > initial_stats['abort_controllers'] + 5:
    logger.warning("Potential AbortController leak detected")

# 3. Force cleanup if needed
if resource_leak_detected:
    await test_resource_manager.cleanup_all_resources()

# 4. Generate cleanup report
cleanup_stats = test_resource_manager.get_resource_stats()
logger.info(f"Post-cleanup resources: {cleanup_stats}")
```

## Agent Configuration Updates

### UI Regression Debugger

Updated to include resource management protocols:

```markdown
**CRITICAL: Resource Management Protocol**
To prevent memory leaks and MaxListenersExceededWarning errors, you MUST:
1. Use the resource management service for all testing operations
2. Properly clean up AbortControllers, WebSocket connections, and browser instances
3. Execute tests within managed sessions that automatically handle cleanup
4. Monitor resource usage and implement cleanup between test phases
```

### Testing Guidelines

1. **Always Use Managed Sessions**: Never create raw AbortControllers or browser instances
2. **Monitor Resource Usage**: Check stats before and after tests
3. **Implement Cleanup Callbacks**: Register cleanup functions for custom resources
4. **Set Conservative Limits**: Use reasonable limits for connections and listeners
5. **Force Cleanup on Errors**: Implement emergency cleanup for failure scenarios

## Monitoring and Alerting

### Resource Monitoring

```python
from shared.utils.enhanced_browser_automation import start_browser_monitoring

# Start monitoring
await start_browser_monitoring(interval_seconds=30)

# Get monitoring report
report = get_browser_monitoring_report()
print(f"Resource trends: {report['trend_analysis']}")
```

### Alert Thresholds

- **AbortControllers**: Alert if > 20, emergency cleanup if > 50
- **WebSocket connections**: Alert if > 10
- **Browser instances**: Alert if > 5
- **Memory usage**: Alert if > 500MB

## Common Patterns

### Testing Authentication Endpoints

```python
async def test_authentication_endpoints():
    session_id = "auth_test"
    
    async with test_resource_manager.test_session(session_id) as session:
        async with get_test_client("https://localhost", session_id) as client:
            
            # Test login
            login_response = await client.post("/api/v1/auth/jwt/login", json_data={
                "email": "test@example.com",
                "password": "password"
            })
            
            # Test profile access
            if login_response['status_code'] == 200:
                token = login_response['data']['access_token']
                profile_response = await client.get("/api/v1/profile", headers={
                    "Authorization": f"Bearer {token}"
                })
            
            # Resources automatically cleaned up
```

### Browser UI Testing

```python
async def test_ui_components():
    session_id = "ui_test"
    
    async with get_managed_browser_session(session_id) as browser:
        
        # Navigate and test
        await browser.navigate_with_cleanup("https://localhost")
        
        # Take screenshots
        await browser.take_managed_screenshot("ui_test_overview.png")
        
        # Check console messages
        console_messages = await browser.get_console_messages_managed()
        
        # Resources automatically cleaned up
```

## Troubleshooting

### MaxListenersExceededWarning

If you still see this warning:

1. **Check Resource Stats**: `test_resource_manager.get_resource_stats()`
2. **Review Test Code**: Ensure all tests use managed sessions
3. **Force Cleanup**: `await test_resource_manager.cleanup_all_resources()`
4. **Restart Process**: If persistent, restart the testing process

### Memory Leaks

Signs of memory leaks:
- Increasing memory usage over time
- Accumulating AbortController counts
- WebSocket connections not closing
- Browser instances persisting

Solutions:
- Use managed sessions consistently
- Implement cleanup callbacks for custom resources
- Monitor resource trends
- Set up periodic cleanup

### Performance Impact

Resource management overhead:
- **Minimal**: Proper cleanup prevents larger performance issues
- **Monitoring**: ~1-2% CPU overhead for monitoring
- **Cleanup**: Brief pause during cleanup operations
- **Net Benefit**: Prevents memory leaks and crashes

## Implementation Checklist

- [ ] Update all test code to use managed sessions
- [ ] Replace raw HTTP clients with EnhancedTestClient
- [ ] Update browser automation to use ManagedBrowserSession
- [ ] Add resource monitoring to critical test suites
- [ ] Implement cleanup callbacks for custom resources
- [ ] Set up alerting for resource threshold breaches
- [ ] Document resource management patterns for team
- [ ] Create integration tests for resource cleanup
- [ ] Monitor production systems for resource leaks
- [ ] Establish resource usage baselines

## Resources

- **Test Resource Manager**: `/app/shared/services/test_resource_manager.py`
- **Enhanced Test Client**: `/app/shared/utils/enhanced_test_client.py`
- **Managed Browser Automation**: `/app/shared/utils/enhanced_browser_automation.py`
- **Updated Agent Config**: `/.claude/agents/ui-regression-debugger.md`

This approach ensures sustainable testing practices that prevent memory leaks and resource accumulation while maintaining test effectiveness and reliability.