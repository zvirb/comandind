# Focus Nudge Android API Specification

This document provides the complete API specification for implementing the Focus Nudge system on Android devices, with mobile-specific optimizations and Android platform integrations.

## Overview

The Android Focus Nudge system consists of:
1. **Mobile Data Collection**: Android app usage tracking via UsageStatsManager and AccessibilityService
2. **AI Analysis**: Server analyzes mobile usage patterns and generates contextual nudges
3. **Hybrid Delivery**: WebSocket for active app, FCM push notifications for background
4. **Mobile Feedback Loop**: Touch-optimized feedback collection and effectiveness tracking

## Android-Specific Considerations

### Platform Differences
- **Battery Optimization**: Android aggressively kills background processes
- **Permission Model**: Complex runtime permissions for usage stats and accessibility
- **App Lifecycle**: Apps can be killed/restored at any time
- **Network Changes**: WiFi/mobile transitions require connection handling
- **Context Awareness**: Rich mobile context (location, battery, connectivity)

### Required Android Permissions

```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.PACKAGE_USAGE_STATS" />
<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.ACCESS_NOTIFICATION_POLICY" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.WAKE_LOCK" />
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />
<uses-permission android:name="android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS" />

<!-- For notification access -->
<uses-permission android:name="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE" />

<!-- For accessibility service (advanced usage tracking) -->
<uses-permission android:name="android.permission.BIND_ACCESSIBILITY_SERVICE" />
```

## Authentication

All endpoints require authentication via JWT token:
```
Authorization: Bearer <your-jwt-token>
```

## REST API Endpoints

### 1. Register FCM Push Token

**Endpoint**: `POST /api/v1/focus-nudge/register-push-token`

**Purpose**: Register Firebase Cloud Messaging token for background nudge delivery.

**Request Body**:
```json
{
  "client_id": "android_client_uuid",
  "fcm_token": "firebase_cloud_messaging_token_here",
  "device_info": {
    "platform": "Android",
    "android_version": "13",
    "device_model": "Google Pixel 7",
    "manufacturer": "Google",
    "app_version": "1.0.0",
    "sdk_version": 33,
    "device_id": "unique_device_identifier"
  },
  "notification_preferences": {
    "allow_background_nudges": true,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "08:00",
    "max_nudges_per_day": 10
  }
}
```

**Response**:
```json
{
  "status": "registered",
  "message": "FCM token registered successfully",
  "client_id": "android_client_uuid",
  "token_id": "token_registration_id",
  "expires_at": "2024-02-15T10:30:00Z"
}
```

### 2. Submit Android Usage Data

**Endpoint**: `POST /api/v1/focus-nudge/usage-data`

**Purpose**: Submit Android-specific usage data including app usage stats, screen time, and mobile context.

**Request Body**:
```json
{
  "client_id": "android_client_uuid",
  "report_timestamp": "2024-01-15T10:30:00Z",
  "usage_data": [
    {
      "timestamp": "2024-01-15T10:25:00Z",
      "active_application": "com.google.android.apps.docs",
      "app_name": "Google Docs",
      "activity_name": "DocumentEditActivity",
      "session_duration_ms": 1800000,
      "foreground_time_ms": 1650000,
      "background_time_ms": 150000,
      "idle_time_ms": 0,
      "focus_score": 0.85,
      "app_category": "productivity",
      "usage_stats": {
        "total_screen_time_ms": 1800000,
        "app_launches": 3,
        "notification_interactions": 2,
        "last_time_used": "2024-01-15T10:25:00Z",
        "first_time_used": "2024-01-15T09:00:00Z"
      },
      "mobile_context": {
        "device_orientation": "portrait",
        "screen_brightness": 75,
        "battery_level": 68,
        "charging_state": false,
        "connectivity_type": "wifi",
        "network_strength": 4,
        "location_context": "home",
        "calendar_context": "work_meeting_in_30min",
        "do_not_disturb": false,
        "headphones_connected": true
      },
      "interaction_patterns": {
        "tap_count": 45,
        "swipe_count": 12,
        "back_button_presses": 3,
        "home_button_presses": 1,
        "task_switches": 2
      }
    }
  ],
  "notification_interactions": [
    {
      "notification_id": "nudge_123",
      "action": "acted_upon",
      "timestamp": "2024-01-15T10:20:00Z",
      "response_time_ms": 5000,
      "interaction_type": "notification_tap",
      "context": {
        "effectiveness_rating": 4,
        "location": "home",
        "battery_level": 70
      }
    }
  ],
  "system_info": {
    "platform": "Android",
    "android_version": "13",
    "device_model": "Google Pixel 7",
    "client_version": "1.0.0",
    "permissions_granted": [
      "usage_stats",
      "notification_access",
      "location"
    ],
    "battery_optimization_disabled": true
  }
}
```

**Response**:
```json
{
  "status": "received",
  "message": "Android usage data received successfully",
  "report_id": "report_uuid",
  "processed_usage_points": 1,
  "processed_notifications": 1,
  "timestamp": "2024-01-15T10:30:00Z",
  "next_report_suggested_ms": 600000
}
```

### 3. Mobile Nudge Feedback

**Endpoint**: `POST /api/v1/focus-nudge/nudge-feedback`

**Purpose**: Provide feedback on nudge effectiveness with mobile-specific interaction data.

**Request Body**:
```json
{
  "nudge_id": "nudge_123",
  "action": "acted_upon",
  "effectiveness_rating": 4,
  "feedback_text": "Helped me close distracting apps",
  "interaction_details": {
    "delivery_method": "fcm_push",
    "response_time_ms": 8000,
    "interaction_type": "notification_action_button",
    "device_state": {
      "screen_on": false,
      "locked": true,
      "battery_level": 65,
      "location": "office"
    }
  },
  "follow_up_behavior": {
    "closed_distracting_apps": true,
    "focus_improvement_duration_ms": 1800000,
    "task_completion": true
  }
}
```

### 4. Android Focus Analytics

**Endpoint**: `GET /api/v1/focus-nudge/mobile-analytics?timeframe_hours=24`

**Purpose**: Get mobile-specific focus analytics and insights.

**Response**:
```json
{
  "timeframe_hours": 24,
  "mobile_metrics": {
    "total_screen_time_ms": 18000000,
    "productive_screen_time_ms": 12600000,
    "focus_score_average": 0.72,
    "app_switch_rate": 2.3,
    "notification_response_rate": 0.65,
    "deep_work_sessions": 4,
    "average_session_duration_ms": 1800000
  },
  "app_categories": {
    "productivity": {
      "time_spent_ms": 7200000,
      "focus_score": 0.88
    },
    "communication": {
      "time_spent_ms": 3600000,
      "focus_score": 0.65
    },
    "entertainment": {
      "time_spent_ms": 2400000,
      "focus_score": 0.32
    },
    "social_media": {
      "time_spent_ms": 1800000,
      "focus_score": 0.25
    }
  },
  "context_insights": {
    "most_productive_location": "office",
    "most_productive_time": "09:00-11:00",
    "distraction_triggers": [
      "low_battery",
      "social_notifications",
      "transition_periods"
    ]
  },
  "nudge_effectiveness": {
    "total_nudges_sent": 12,
    "fcm_delivered": 8,
    "websocket_delivered": 4,
    "acknowledged": 9,
    "acted_upon": 6,
    "average_rating": 4.1,
    "most_effective_time": "14:00-16:00"
  }
}
```

## Firebase Cloud Messaging Integration

### FCM Message Format

**Server-to-Android Push Notification**:
```json
{
  "to": "fcm_token_here",
  "data": {
    "type": "focus_nudge",
    "nudge_id": "nudge_456",
    "title": "Focus Reminder",
    "message": "You've been on social media for 15 minutes. Time to get back to work?",
    "priority": "high",
    "suggested_actions": "[\"Close distracting apps\", \"Start 25-min focus session\", \"Take a short break\"]",
    "expires_at": "2024-01-15T10:45:00Z",
    "action_buttons": "[{\"text\":\"Focus Now\",\"action\":\"start_focus\"},{\"text\":\"5 Min Break\",\"action\":\"short_break\"}]"
  },
  "android": {
    "priority": "high",
    "notification": {
      "title": "Focus Reminder",
      "body": "You've been on social media for 15 minutes. Time to get back to work?",
      "icon": "focus_nudge_icon",
      "color": "#4285F4",
      "sound": "gentle_chime",
      "click_action": "OPEN_FOCUS_ACTIVITY"
    }
  }
}
```

## WebSocket Connection (Active App Only)

### Android WebSocket Endpoint

**Endpoint**: `ws://your-server.com/api/v1/ws/focus-nudge/{client_id}?token={jwt_token}`

**Usage**: Only when app is in foreground to preserve battery life.

**Connection Management**:
```kotlin
class AndroidFocusNudgeWebSocket {
    private var webSocket: WebSocket? = null
    
    fun connectWhenAppActive() {
        if (isAppInForeground() && !isWebSocketConnected()) {
            connectWebSocket()
        }
    }
    
    fun disconnectWhenAppInactive() {
        if (!isAppInForeground() && isWebSocketConnected()) {
            disconnectWebSocket()
        }
    }
}
```

### Real-time Focus Nudge Event
```json
{
  "type": "focus_nudge",
  "client_id": "android_client_uuid",
  "nudge": {
    "nudge_id": "nudge_789",
    "type": "suggestion",
    "message": "Great focus session! You've been productive for 45 minutes. Consider a short break?",
    "priority": "low",
    "action_required": false,
    "suggested_actions": [
      "Take a 5-minute walk",
      "Do some stretches",
      "Continue for 15 more minutes"
    ],
    "expires_at": "2024-01-15T11:00:00Z",
    "mobile_display": {
      "show_as_overlay": false,
      "notification_style": "gentle",
      "vibration_pattern": [0, 100, 200, 100]
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Android Data Collection Implementation

### UsageStatsManager Integration

```kotlin
class AndroidUsageCollector {
    private val usageStatsManager = getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
    private val appUsageDao = AppDatabase.getInstance(context).appUsageDao()
    
    fun collectUsageData(intervalMinutes: Int = 10): List<AndroidUsageData> {
        val endTime = System.currentTimeMillis()
        val startTime = endTime - TimeUnit.MINUTES.toMillis(intervalMinutes.toLong())
        
        val usageStats = usageStatsManager.queryUsageStats(
            UsageStatsManager.INTERVAL_BEST,
            startTime,
            endTime
        )
        
        return usageStats.filter { it.totalTimeInForeground > 0 }.map { stat ->
            AndroidUsageData(
                timestamp = Instant.ofEpochMilli(stat.lastTimeUsed),
                activeApplication = stat.packageName,
                appName = getAppName(stat.packageName),
                sessionDurationMs = stat.totalTimeInForeground,
                foregroundTimeMs = stat.totalTimeInForeground,
                backgroundTimeMs = estimateBackgroundTime(stat),
                focusScore = calculateMobileFocusScore(stat),
                appCategory = getAppCategory(stat.packageName),
                mobileContext = collectMobileContext(),
                interactionPatterns = collectInteractionPatterns(stat.packageName)
            )
        }
    }
    
    private fun collectMobileContext(): MobileContext {
        return MobileContext(
            deviceOrientation = getDeviceOrientation(),
            batteryLevel = getBatteryLevel(),
            chargingState = isCharging(),
            connectivityType = getConnectivityType(),
            locationContext = getLocationContext(),
            doNotDisturb = isDoNotDisturbEnabled(),
            headphonesConnected = areHeadphonesConnected()
        )
    }
}
```

### Accessibility Service for Advanced Tracking

```kotlin
class FocusNudgeAccessibilityService : AccessibilityService() {
    
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        event?.let {
            when (it.eventType) {
                AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> {
                    trackAppSwitch(it.packageName?.toString())
                }
                AccessibilityEvent.TYPE_VIEW_CLICKED -> {
                    trackUserInteraction("tap", it.packageName?.toString())
                }
                AccessibilityEvent.TYPE_VIEW_SCROLLED -> {
                    trackUserInteraction("scroll", it.packageName?.toString())
                }
            }
        }
    }
    
    private fun trackAppSwitch(packageName: String?) {
        packageName?.let {
            FocusDataCollector.recordAppSwitch(it, System.currentTimeMillis())
        }
    }
}
```

## Mobile-Specific Focus Patterns

### Android Focus Score Calculation

```kotlin
class MobileFocusScoreCalculator {
    
    fun calculateFocusScore(
        appUsage: AndroidUsageData,
        interactionPattern: InteractionPattern,
        context: MobileContext
    ): Float {
        var baseScore = 0.5f
        
        // App category weighting
        baseScore += when (appUsage.appCategory) {
            "productivity" -> 0.3f
            "education" -> 0.25f
            "communication" -> 0.1f
            "entertainment" -> -0.2f
            "social_media" -> -0.3f
            "games" -> -0.4f
            else -> 0.0f
        }
        
        // Session duration (sweet spot around 25-45 minutes)
        val sessionMinutes = appUsage.sessionDurationMs / 60000
        baseScore += when {
            sessionMinutes in 20..50 -> 0.2f
            sessionMinutes in 10..20 -> 0.1f
            sessionMinutes < 5 -> -0.1f
            sessionMinutes > 60 -> -0.15f
            else -> 0.0f
        }
        
        // Interaction intensity (less is more for focus)
        val interactionRate = interactionPattern.totalInteractions / sessionMinutes
        baseScore += when {
            interactionRate < 2 -> 0.1f  // Deep focus
            interactionRate < 5 -> 0.05f
            interactionRate > 15 -> -0.1f  // Too scattered
            else -> 0.0f
        }
        
        // Context factors
        if (context.doNotDisturb) baseScore += 0.1f
        if (context.headphonesConnected) baseScore += 0.05f
        if (context.batteryLevel < 20) baseScore -= 0.05f
        
        return baseScore.coerceIn(0.0f, 1.0f)
    }
}
```

## Error Handling & Battery Optimization

### Android-Specific Error Codes

- `1001 PERMISSION_DENIED`: Usage stats permission not granted
- `1002 ACCESSIBILITY_DISABLED`: Accessibility service not enabled
- `1003 BATTERY_OPTIMIZATION`: App is being battery optimized
- `1004 FCM_TOKEN_INVALID`: Firebase token expired or invalid
- `1005 BACKGROUND_RESTRICTED`: Background execution restricted

### Battery Optimization Handling

```kotlin
class BatteryOptimizationManager {
    
    fun requestBatteryOptimizationExemption(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val intent = Intent().apply {
                action = Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
                data = Uri.parse("package:${context.packageName}")
            }
            context.startActivity(intent)
        }
    }
    
    fun isBatteryOptimizationDisabled(context: Context): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
            powerManager.isIgnoringBatteryOptimizations(context.packageName)
        } else {
            true
        }
    }
}
```

## Implementation Checklist

### Initial Setup
- [ ] Request required permissions (usage stats, accessibility, notifications)
- [ ] Set up Firebase Cloud Messaging
- [ ] Implement battery optimization exemption request
- [ ] Create foreground service for data collection

### Data Collection
- [ ] Implement UsageStatsManager integration
- [ ] Set up accessibility service (optional, for advanced tracking)
- [ ] Create mobile context collection
- [ ] Implement focus score calculation for mobile

### Communication
- [ ] Implement FCM message handling
- [ ] Set up WebSocket for active app communication
- [ ] Handle network connectivity changes
- [ ] Implement offline data caching

### User Experience
- [ ] Create mobile-optimized nudge display
- [ ] Implement notification actions
- [ ] Add feedback collection UI
- [ ] Create settings for nudge preferences

## Testing & Validation

### Test Scenarios
1. **Foreground App**: Verify WebSocket connection when app is active
2. **Background Nudges**: Test FCM delivery when app is in background
3. **Permission Handling**: Test graceful degradation when permissions denied
4. **Battery Optimization**: Verify functionality with/without battery optimization
5. **Network Changes**: Test WiFi/mobile transitions
6. **App Lifecycle**: Test data collection across app kills/restores

### Performance Monitoring
- Monitor battery usage impact
- Track memory consumption
- Measure network usage
- Monitor CPU usage during data collection

This Android-specific implementation maintains the core Focus Nudge functionality while adapting to Android's unique constraints and capabilities, providing an optimal mobile experience for focus management and productivity enhancement.