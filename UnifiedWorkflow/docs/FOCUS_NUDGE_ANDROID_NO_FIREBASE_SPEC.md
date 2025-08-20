# Focus Nudge Android API Specification (No Firebase)

This document provides the complete API specification for implementing the Focus Nudge system on Android devices using only your existing infrastructure - no Firebase or external push services required.

## Overview

The Android Focus Nudge system consists of:
1. **Mobile Data Collection**: Android app usage tracking via UsageStatsManager and AccessibilityService
2. **AI Analysis**: Server analyzes mobile usage patterns and generates contextual nudges
3. **Smart Delivery**: Hybrid approach using WebSocket, intelligent polling, and local notifications
4. **Mobile Feedback Loop**: Touch-optimized feedback collection and effectiveness tracking

## No-Firebase Architecture

### Delivery Methods (Priority Order)
1. **Active App WebSocket**: Real-time when app is foreground
2. **Background WebSocket**: Short-lived background connections
3. **Intelligent Polling**: Efficient background checks for pending nudges
4. **Local Notifications**: Triggered by background service with server sync

### Android-Specific Considerations

- **Battery Optimization**: Smart connection management and efficient polling
- **Permission Model**: Minimal permissions, graceful degradation
- **Background Execution**: Work within Android's Doze mode and App Standby
- **Network Efficiency**: Minimize data usage with intelligent sync strategies

## Required Android Permissions

```xml
<!-- AndroidManifest.xml - Minimal permission set -->
<uses-permission android:name="android.permission.PACKAGE_USAGE_STATS" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.WAKE_LOCK" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
<uses-permission android:name="android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS" />

<!-- Optional for enhanced features -->
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
<uses-permission android:name="android.permission.BIND_ACCESSIBILITY_SERVICE" />
```

## Authentication

All endpoints require authentication via JWT token:
```
Authorization: Bearer <your-jwt-token>
```

## REST API Endpoints

### 1. Register Android Client

**Endpoint**: `POST /api/v1/focus-nudge/register-android-client`

**Purpose**: Register Android client for nudge delivery without external push services.

**Request Body**:
```json
{
  "client_id": "android_client_uuid",
  "device_info": {
    "platform": "Android",
    "android_version": "13",
    "device_model": "Google Pixel 7",
    "manufacturer": "Google",
    "app_version": "1.0.0",
    "sdk_version": 33,
    "device_id": "unique_device_identifier"
  },
  "connection_preferences": {
    "preferred_polling_interval_minutes": 10,
    "allow_background_websocket": true,
    "battery_optimization_disabled": false,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "08:00",
    "max_nudges_per_day": 10
  },
  "capabilities": {
    "websocket_support": true,
    "background_execution": true,
    "local_notifications": true,
    "overlay_permissions": false
  }
}
```

**Response**:
```json
{
  "status": "registered",
  "message": "Android client registered successfully",
  "client_id": "android_client_uuid",
  "server_config": {
    "websocket_url": "wss://your-server.com/api/v1/ws/focus-nudge/android_client_uuid",
    "polling_endpoint": "/api/v1/focus-nudge/check-pending",
    "recommended_polling_interval_minutes": 15,
    "background_connection_timeout_seconds": 30
  },
  "registration_id": "reg_12345"
}
```

### 2. Check Pending Nudges (Polling Endpoint)

**Endpoint**: `GET /api/v1/focus-nudge/check-pending/{client_id}`

**Purpose**: Efficient polling endpoint for background nudge checks when WebSocket isn't available.

**Query Parameters**:
- `last_check`: ISO timestamp of last successful check
- `app_state`: `foreground|background|unknown`

**Response**:
```json
{
  "has_pending_nudges": true,
  "nudges": [
    {
      "nudge_id": "nudge_456",
      "type": "suggestion",
      "message": "You've been focused for 45 minutes. Consider a short break?",
      "priority": "medium",
      "created_at": "2024-01-15T10:30:00Z",
      "expires_at": "2024-01-15T11:00:00Z",
      "suggested_actions": [
        "Take a 5-minute walk",
        "Do some stretches",
        "Continue for 15 more minutes"
      ],
      "android_display": {
        "notification_title": "Focus Break Suggestion",
        "notification_text": "You've been focused for 45 minutes. Consider a short break?",
        "notification_priority": "default",
        "vibration_pattern": [0, 100, 200, 100],
        "led_color": "#4285F4",
        "action_buttons": [
          {
            "text": "Take Break",
            "action": "take_break",
            "icon": "break_icon"
          },
          {
            "text": "Continue",
            "action": "continue_focus",
            "icon": "focus_icon"
          }
        ]
      }
    }
  ],
  "next_check_in_minutes": 15,
  "server_time": "2024-01-15T10:35:00Z"
}
```

### 3. Submit Android Usage Data

**Endpoint**: `POST /api/v1/focus-nudge/usage-data`

**Purpose**: Submit Android usage data with efficient batching for minimal network usage.

**Request Body**:
```json
{
  "client_id": "android_client_uuid",
  "report_timestamp": "2024-01-15T10:30:00Z",
  "connection_method": "websocket",
  "usage_data": [
    {
      "timestamp": "2024-01-15T10:25:00Z",
      "active_application": "com.google.android.apps.docs",
      "app_name": "Google Docs",
      "session_duration_ms": 1800000,
      "foreground_time_ms": 1650000,
      "idle_time_ms": 0,
      "focus_score": 0.85,
      "app_category": "productivity",
      "mobile_context": {
        "battery_level": 68,
        "charging_state": false,
        "connectivity_type": "wifi",
        "screen_brightness": 75,
        "do_not_disturb": false,
        "location_context": "home"
      },
      "interaction_summary": {
        "total_interactions": 45,
        "app_switches": 2,
        "notification_responses": 1
      }
    }
  ],
  "notification_interactions": [
    {
      "notification_id": "nudge_123",
      "action": "acted_upon",
      "timestamp": "2024-01-15T10:20:00Z",
      "response_time_ms": 5000,
      "interaction_method": "notification_action_button"
    }
  ],
  "system_status": {
    "app_state": "foreground",
    "battery_optimization_disabled": true,
    "background_restricted": false,
    "last_websocket_connection": "2024-01-15T10:15:00Z"
  }
}
```

### 4. Mark Nudges as Delivered

**Endpoint**: `POST /api/v1/focus-nudge/mark-delivered`

**Purpose**: Confirm nudge delivery to prevent duplicate notifications.

**Request Body**:
```json
{
  "client_id": "android_client_uuid",
  "delivered_nudges": [
    {
      "nudge_id": "nudge_456",
      "delivered_at": "2024-01-15T10:35:00Z",
      "delivery_method": "local_notification",
      "user_action": "notification_shown"
    }
  ]
}
```

## WebSocket Implementation (No Firebase Needed)

### Smart WebSocket Management

**Endpoint**: `wss://your-server.com/api/v1/ws/focus-nudge/{client_id}?token={jwt_token}`

**Android Implementation Strategy**:
```kotlin
class SmartWebSocketManager {
    private var webSocket: WebSocket? = null
    private var isAppInForeground = false
    private var lastBackgroundConnection = 0L
    private val backgroundConnectionInterval = 15 * 60 * 1000L // 15 minutes
    
    fun manageConnection() {
        when {
            isAppInForeground -> {
                // Maintain persistent connection when app is active
                if (!isConnected()) connectWebSocket()
            }
            canUseBackgroundWebSocket() -> {
                // Brief background connections for urgent nudges
                connectForBackgroundCheck()
            }
            else -> {
                // Disconnect and rely on polling
                disconnectWebSocket()
            }
        }
    }
    
    private fun canUseBackgroundWebSocket(): Boolean {
        val timeSinceLastConnection = System.currentTimeMillis() - lastBackgroundConnection
        return timeSinceLastConnection > backgroundConnectionInterval &&
               !isBatteryOptimized() &&
               !isDozeMode()
    }
    
    private fun connectForBackgroundCheck() {
        // Connect briefly to check for urgent nudges
        connectWebSocket()
        Handler().postDelayed({
            if (!isAppInForeground) {
                disconnectWebSocket()
            }
        }, 30000) // 30 second background connection
    }
}
```

### WebSocket Message Format

**Server-to-Android Real-time Nudge**:
```json
{
  "type": "focus_nudge",
  "client_id": "android_client_uuid",
  "nudge": {
    "nudge_id": "nudge_789",
    "type": "reminder",
    "message": "You've been away for 20 minutes. Ready to get back to work?",
    "priority": "medium",
    "expires_at": "2024-01-15T11:00:00Z",
    "suggested_actions": [
      "Review current task",
      "Start 25-min focus session",
      "Take 5 more minutes"
    ],
    "android_display": {
      "show_immediately": true,
      "notification_style": "heads_up",
      "sound": "gentle_chime",
      "vibration_pattern": [0, 100, 50, 100]
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Intelligent Polling System

### Background Service Implementation

```kotlin
class FocusNudgeBackgroundService : JobIntentService() {
    
    companion object {
        private const val JOB_ID = 1001
        private const val POLLING_INTERVAL_MS = 15 * 60 * 1000L // 15 minutes
    }
    
    override fun onHandleWork(intent: Intent) {
        if (shouldCheckForNudges()) {
            checkForPendingNudges()
        }
        scheduleNextCheck()
    }
    
    private fun shouldCheckForNudges(): Boolean {
        return !isWebSocketConnected() &&
               !isDozeMode() &&
               hasNetworkConnection() &&
               !isQuietHours()
    }
    
    private suspend fun checkForPendingNudges() {
        try {
            val response = apiClient.checkPendingNudges(
                clientId = getClientId(),
                lastCheck = getLastCheckTimestamp(),
                appState = if (isAppInForeground()) "foreground" else "background"
            )
            
            if (response.hasPendingNudges) {
                response.nudges.forEach { nudge ->
                    displayLocalNotification(nudge)
                    markNudgeAsDelivered(nudge.nudgeId)
                }
            }
            
            updateLastCheckTimestamp()
            
        } catch (e: Exception) {
            // Exponential backoff on failure
            scheduleRetryCheck()
        }
    }
    
    private fun displayLocalNotification(nudge: FocusNudge) {
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(nudge.androidDisplay.notificationTitle)
            .setContentText(nudge.androidDisplay.notificationText)
            .setSmallIcon(R.drawable.focus_icon)
            .setPriority(mapPriority(nudge.priority))
            .setVibrate(nudge.androidDisplay.vibrationPattern)
            .setLights(Color.parseColor(nudge.androidDisplay.ledColor), 1000, 1000)
            .setAutoCancel(true)
            .apply {
                // Add action buttons
                nudge.androidDisplay.actionButtons.forEach { button ->
                    addAction(createNotificationAction(button, nudge.nudgeId))
                }
            }
            .build()
            
        NotificationManagerCompat.from(this).notify(nudge.nudgeId.hashCode(), notification)
    }
}
```

### Smart Polling Schedule

```kotlin
class AdaptivePollingScheduler {
    
    fun calculateNextPollingInterval(
        userActivity: UserActivity,
        batteryLevel: Int,
        networkType: NetworkType
    ): Long {
        var baseInterval = 15 * 60 * 1000L // 15 minutes base
        
        // Adjust based on user activity
        when (userActivity) {
            UserActivity.HIGHLY_ACTIVE -> baseInterval = 10 * 60 * 1000L // 10 min
            UserActivity.MODERATELY_ACTIVE -> baseInterval = 15 * 60 * 1000L // 15 min
            UserActivity.LOW_ACTIVITY -> baseInterval = 30 * 60 * 1000L // 30 min
            UserActivity.INACTIVE -> baseInterval = 60 * 60 * 1000L // 1 hour
        }
        
        // Battery level adjustments
        when {
            batteryLevel < 15 -> baseInterval *= 4 // Reduce frequency on low battery
            batteryLevel < 30 -> baseInterval *= 2
            batteryLevel > 80 -> baseInterval = (baseInterval * 0.8).toLong()
        }
        
        // Network type adjustments
        when (networkType) {
            NetworkType.WIFI -> baseInterval = (baseInterval * 0.9).toLong()
            NetworkType.MOBILE_DATA -> baseInterval = (baseInterval * 1.2).toLong()
            NetworkType.ROAMING -> baseInterval *= 3
            NetworkType.NONE -> baseInterval = Long.MAX_VALUE // No polling without network
        }
        
        return baseInterval.coerceIn(5 * 60 * 1000L, 2 * 60 * 60 * 1000L) // 5 min to 2 hours
    }
}
```

## Local Notification System

### Notification Channel Setup

```kotlin
class NotificationSetup {
    
    fun createNotificationChannels(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channels = listOf(
                NotificationChannel(
                    "focus_nudges_high",
                    "Focus Nudges (High Priority)",
                    NotificationManager.IMPORTANCE_HIGH
                ).apply {
                    description = "Important focus reminders and suggestions"
                    enableVibration(true)
                    setShowBadge(true)
                },
                NotificationChannel(
                    "focus_nudges_normal",
                    "Focus Nudges (Normal)",
                    NotificationManager.IMPORTANCE_DEFAULT
                ).apply {
                    description = "Regular focus suggestions and updates"
                    enableVibration(true)
                    setShowBadge(false)
                },
                NotificationChannel(
                    "focus_nudges_low",
                    "Focus Nudges (Gentle)",
                    NotificationManager.IMPORTANCE_LOW
                ).apply {
                    description = "Gentle focus reminders"
                    enableVibration(false)
                    setShowBadge(false)
                }
            )
            
            val notificationManager = context.getSystemService(NotificationManager::class.java)
            channels.forEach { notificationManager.createNotificationChannel(it) }
        }
    }
}
```

## Battery Optimization & Performance

### Doze Mode & App Standby Handling

```kotlin
class PowerManagementHelper {
    
    fun optimizeForBatteryLife(context: Context) {
        // Request battery optimization exemption for consistent operation
        requestBatteryOptimizationExemption(context)
        
        // Set up intelligent work scheduling
        scheduleIntelligentWork(context)
    }
    
    private fun scheduleIntelligentWork(context: Context) {
        val jobScheduler = context.getSystemService(Context.JOB_SCHEDULER_SERVICE) as JobScheduler
        
        val jobInfo = JobInfo.Builder(FOCUS_NUDGE_JOB_ID, ComponentName(context, FocusNudgeJobService::class.java))
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setPersisted(true)
            .setPeriodic(15 * 60 * 1000L) // 15 minutes minimum on Android
            .setRequiresCharging(false)
            .setRequiresDeviceIdle(false)
            .build()
            
        jobScheduler.schedule(jobInfo)
    }
    
    fun isInDozeMode(context: Context): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
            powerManager.isDeviceIdleMode
        } else {
            false
        }
    }
}
```

## Error Handling & Fallbacks

### Connection Failure Handling

```kotlin
class ConnectionFailureHandler {
    
    fun handleConnectionFailure(
        error: ConnectionError,
        retryCount: Int
    ): RetryStrategy {
        return when (error.type) {
            ConnectionError.Type.NETWORK_UNAVAILABLE -> {
                RetryStrategy.WaitForNetwork
            }
            ConnectionError.Type.SERVER_ERROR -> {
                RetryStrategy.ExponentialBackoff(
                    baseDelay = 30000L, // 30 seconds
                    maxDelay = 15 * 60 * 1000L, // 15 minutes
                    retryCount = retryCount
                )
            }
            ConnectionError.Type.AUTHENTICATION_FAILED -> {
                RetryStrategy.RefreshTokenAndRetry
            }
            ConnectionError.Type.RATE_LIMITED -> {
                RetryStrategy.BackoffUntil(error.retryAfter ?: 60000L)
            }
            else -> {
                RetryStrategy.FallbackToPolling
            }
        }
    }
}
```

## Implementation Checklist

### Phase 1: Basic Implementation
- [ ] Implement smart WebSocket connection management
- [ ] Create intelligent polling system with adaptive intervals
- [ ] Set up local notification system with action buttons
- [ ] Implement basic usage data collection

### Phase 2: Optimization
- [ ] Add battery optimization exemption requests
- [ ] Implement Doze mode and App Standby handling
- [ ] Create adaptive polling based on user behavior
- [ ] Add offline data caching and sync

### Phase 3: Enhanced Features
- [ ] Implement advanced usage tracking with AccessibilityService
- [ ] Add location-based context (with permission)
- [ ] Create smart notification scheduling
- [ ] Implement feedback collection UI

## Benefits of No-Firebase Approach

### Advantages
✅ **No External Dependencies**: Full control over your infrastructure  
✅ **Privacy First**: All data stays within your system  
✅ **Cost Control**: No Firebase usage fees  
✅ **Customization**: Full control over delivery logic  
✅ **Simplified Architecture**: One less service to manage  

### Trade-offs
⚠️ **Battery Usage**: Slightly higher battery usage than FCM  
⚠️ **Reliability**: Need to handle network failures gracefully  
⚠️ **Complexity**: More client-side logic required  

### Mitigation Strategies
- Intelligent polling intervals based on user behavior
- Smart WebSocket connection management
- Efficient local notification system
- Graceful degradation when permissions are limited

This approach gives you complete control over the nudge delivery system while working within Android's constraints, providing reliable focus management without external dependencies.