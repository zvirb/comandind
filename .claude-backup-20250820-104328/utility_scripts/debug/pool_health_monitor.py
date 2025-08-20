#!/usr/bin/env python3
"""
Real-Time Database Pool Health Monitor

Provides continuous monitoring of database connection pool health with
real-time alerts and performance metrics dashboard.
"""

import asyncio
import time
import json
import logging
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import signal

# Add app to Python path
sys.path.insert(0, '/home/marku/ai_workflow_engine/app')

from shared.utils.database_setup import get_database_stats, initialize_database
from shared.utils.config import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PoolHealthMetrics:
    """Structure for pool health metrics."""
    timestamp: str
    sync_pool_utilization: float
    async_pool_utilization: float
    sync_connections_active: int
    async_connections_active: int
    sync_overflow_used: int
    async_overflow_used: int
    total_sync_capacity: int
    total_async_capacity: int
    connection_churn_rate: float
    health_status: str
    alerts: List[str]

class PoolHealthMonitor:
    """Real-time database pool health monitor."""
    
    def __init__(self, check_interval: int = 3):
        self.check_interval = check_interval
        self.metrics_history = []
        self.previous_stats = None
        self.is_running = False
        self.start_time = None
        
        # Health thresholds
        self.thresholds = {
            "pool_utilization_warning": 0.7,    # 70%
            "pool_utilization_critical": 0.9,   # 90%
            "overflow_warning": 0.5,             # 50% of overflow used
            "overflow_critical": 0.8,            # 80% of overflow used
            "connection_churn_warning": 5.0,     # 5 connections/second
            "connection_churn_critical": 15.0,   # 15 connections/second
            "response_time_warning": 100,        # 100ms (simulated)
            "response_time_critical": 500        # 500ms (simulated)
        }
    
    def calculate_pool_metrics(self, stats: Dict[str, Any]) -> PoolHealthMetrics:
        """Calculate comprehensive pool health metrics."""
        
        timestamp = datetime.now().isoformat()
        
        # Initialize metrics
        sync_util = async_util = 0.0
        sync_active = async_active = 0
        sync_overflow = async_overflow = 0
        sync_capacity = async_capacity = 0
        churn_rate = 0.0
        alerts = []
        
        # Process sync engine stats
        if stats.get("sync_engine"):
            sync_stats = stats["sync_engine"]
            pool_size = sync_stats.get("pool_size", 0)
            created = sync_stats.get("connections_created", 0)
            available = sync_stats.get("connections_available", 0)
            overflow = sync_stats.get("connections_overflow", 0)
            total = sync_stats.get("total_connections", 0)
            
            sync_util = created / pool_size if pool_size > 0 else 0
            sync_active = created - available
            sync_overflow = overflow
            sync_capacity = total
        
        # Process async engine stats
        if stats.get("async_engine"):
            async_stats = stats["async_engine"]
            pool_size = async_stats.get("pool_size", 0)
            created = async_stats.get("connections_created", 0)
            available = async_stats.get("connections_available", 0)
            overflow = async_stats.get("connections_overflow", 0)
            total = async_stats.get("total_connections", 0)
            
            async_util = created / pool_size if pool_size > 0 else 0
            async_active = created - available
            async_overflow = overflow
            async_capacity = total
        
        # Calculate connection churn rate
        if self.previous_stats and self.previous_stats.get("timestamp"):
            time_delta = time.time() - self.previous_stats["timestamp"]
            if time_delta > 0:
                prev_sync_created = self.previous_stats.get("sync_engine", {}).get("connections_created", 0)
                prev_async_created = self.previous_stats.get("async_engine", {}).get("connections_created", 0)
                
                current_sync_created = stats.get("sync_engine", {}).get("connections_created", 0)
                current_async_created = stats.get("async_engine", {}).get("connections_created", 0)
                
                total_new_connections = (current_sync_created - prev_sync_created) + (current_async_created - prev_async_created)
                churn_rate = max(0, total_new_connections / time_delta)
        
        # Generate alerts
        if sync_util >= self.thresholds["pool_utilization_critical"]:
            alerts.append(f"🚨 CRITICAL: Sync pool utilization at {sync_util:.1%}")
        elif sync_util >= self.thresholds["pool_utilization_warning"]:
            alerts.append(f"⚠️  WARNING: Sync pool utilization at {sync_util:.1%}")
            
        if async_util >= self.thresholds["pool_utilization_critical"]:
            alerts.append(f"🚨 CRITICAL: Async pool utilization at {async_util:.1%}")
        elif async_util >= self.thresholds["pool_utilization_warning"]:
            alerts.append(f"⚠️  WARNING: Async pool utilization at {async_util:.1%}")
        
        # Overflow alerts
        sync_overflow_util = sync_overflow / max(1, sync_capacity - stats.get("sync_engine", {}).get("pool_size", 0)) if sync_capacity > 0 else 0
        async_overflow_util = async_overflow / max(1, async_capacity - stats.get("async_engine", {}).get("pool_size", 0)) if async_capacity > 0 else 0
        
        if sync_overflow_util >= self.thresholds["overflow_critical"]:
            alerts.append(f"🚨 CRITICAL: Sync overflow at {sync_overflow_util:.1%}")
        elif sync_overflow_util >= self.thresholds["overflow_warning"]:
            alerts.append(f"⚠️  WARNING: Sync overflow at {sync_overflow_util:.1%}")
            
        if async_overflow_util >= self.thresholds["overflow_critical"]:
            alerts.append(f"🚨 CRITICAL: Async overflow at {async_overflow_util:.1%}")
        elif async_overflow_util >= self.thresholds["overflow_warning"]:
            alerts.append(f"⚠️  WARNING: Async overflow at {async_overflow_util:.1%}")
        
        # Connection churn alerts
        if churn_rate >= self.thresholds["connection_churn_critical"]:
            alerts.append(f"🚨 CRITICAL: High connection churn at {churn_rate:.1f} conn/sec")
        elif churn_rate >= self.thresholds["connection_churn_warning"]:
            alerts.append(f"⚠️  WARNING: Elevated connection churn at {churn_rate:.1f} conn/sec")
        
        # Determine overall health status
        if any("🚨 CRITICAL" in alert for alert in alerts):
            health_status = "CRITICAL"
        elif any("⚠️  WARNING" in alert for alert in alerts):
            health_status = "WARNING" 
        else:
            health_status = "HEALTHY"
        
        return PoolHealthMetrics(
            timestamp=timestamp,
            sync_pool_utilization=sync_util,
            async_pool_utilization=async_util,
            sync_connections_active=sync_active,
            async_connections_active=async_active,
            sync_overflow_used=sync_overflow,
            async_overflow_used=async_overflow,
            total_sync_capacity=sync_capacity,
            total_async_capacity=async_capacity,
            connection_churn_rate=churn_rate,
            health_status=health_status,
            alerts=alerts
        )
    
    def display_dashboard(self, metrics: PoolHealthMetrics):
        """Display real-time dashboard."""
        
        # Calculate uptime
        uptime = time.time() - self.start_time if self.start_time else 0
        uptime_str = str(timedelta(seconds=int(uptime)))
        
        # Clear screen for dashboard effect
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("="*90)
        print("🏥 DATABASE CONNECTION POOL HEALTH MONITOR")
        print("="*90)
        print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')} | 🕐 Uptime: {uptime_str} | 🔄 Refresh: {self.check_interval}s")
        print("="*90)
        
        # Health status banner
        status_color = {
            "HEALTHY": "🟢",
            "WARNING": "🟡", 
            "CRITICAL": "🔴"
        }
        print(f"{status_color.get(metrics.health_status, '⚪')} OVERALL STATUS: {metrics.health_status}")
        print()
        
        # Connection pool overview
        print("📊 CONNECTION POOL OVERVIEW")
        print("-" * 50)
        
        # Sync engine
        sync_bar = self.create_utilization_bar(metrics.sync_pool_utilization)
        print(f"🔄 SYNC ENGINE")
        print(f"   Utilization: [{sync_bar}] {metrics.sync_pool_utilization:.1%}")
        print(f"   Active Connections: {metrics.sync_connections_active}")
        print(f"   Overflow Used: {metrics.sync_overflow_used}")
        print(f"   Total Capacity: {metrics.total_sync_capacity}")
        
        print()
        
        # Async engine
        async_bar = self.create_utilization_bar(metrics.async_pool_utilization)
        print(f"⚡ ASYNC ENGINE")
        print(f"   Utilization: [{async_bar}] {metrics.async_pool_utilization:.1%}")
        print(f"   Active Connections: {metrics.async_connections_active}")
        print(f"   Overflow Used: {metrics.async_overflow_used}")
        print(f"   Total Capacity: {metrics.total_async_capacity}")
        
        print()
        
        # Performance metrics
        print("⚡ PERFORMANCE METRICS")
        print("-" * 50)
        print(f"🔄 Connection Churn Rate: {metrics.connection_churn_rate:.2f} conn/sec")
        
        # Display recent trend
        if len(self.metrics_history) >= 2:
            recent_metrics = self.metrics_history[-5:]  # Last 5 measurements
            avg_sync_util = sum(m.sync_pool_utilization for m in recent_metrics) / len(recent_metrics)
            avg_async_util = sum(m.async_pool_utilization for m in recent_metrics) / len(recent_metrics)
            
            sync_trend = "📈" if metrics.sync_pool_utilization > avg_sync_util else "📉" if metrics.sync_pool_utilization < avg_sync_util else "➡️"
            async_trend = "📈" if metrics.async_pool_utilization > avg_async_util else "📉" if metrics.async_pool_utilization < avg_async_util else "➡️"
            
            print(f"📊 5-min Trend: Sync {sync_trend} Async {async_trend}")
        
        print()
        
        # Alerts section
        if metrics.alerts:
            print("🚨 ACTIVE ALERTS")
            print("-" * 50)
            for alert in metrics.alerts:
                print(f"   {alert}")
        else:
            print("✅ NO ACTIVE ALERTS - System operating normally")
        
        print()
        
        # Historical summary
        if len(self.metrics_history) > 1:
            print("📈 SESSION SUMMARY")
            print("-" * 50)
            
            all_sync_utils = [m.sync_pool_utilization for m in self.metrics_history]
            all_async_utils = [m.async_pool_utilization for m in self.metrics_history]
            
            print(f"   Peak Sync Utilization: {max(all_sync_utils):.1%}")
            print(f"   Peak Async Utilization: {max(all_async_utils):.1%}")
            print(f"   Avg Sync Utilization: {sum(all_sync_utils)/len(all_sync_utils):.1%}")
            print(f"   Avg Async Utilization: {sum(all_async_utils)/len(all_async_utils):.1%}")
            
            critical_events = sum(1 for m in self.metrics_history if m.health_status == "CRITICAL")
            warning_events = sum(1 for m in self.metrics_history if m.health_status == "WARNING")
            
            print(f"   Critical Events: {critical_events}")
            print(f"   Warning Events: {warning_events}")
            print(f"   Measurements: {len(self.metrics_history)}")
        
        print()
        print("="*90)
        print("💡 Press Ctrl+C to stop monitoring | 📁 Logs saved to pool_monitor.log")
        print("="*90)
    
    def create_utilization_bar(self, utilization: float, width: int = 20) -> str:
        """Create ASCII utilization bar."""
        filled = int(utilization * width)
        empty = width - filled
        
        if utilization >= self.thresholds["pool_utilization_critical"]:
            color = "🔴"
        elif utilization >= self.thresholds["pool_utilization_warning"]:
            color = "🟡"
        else:
            color = "🟢"
        
        bar = "█" * filled + "░" * empty
        return f"{color} {bar}"
    
    def save_metrics_snapshot(self, metrics: PoolHealthMetrics):
        """Save current metrics to log file."""
        log_entry = {
            "timestamp": metrics.timestamp,
            "metrics": asdict(metrics),
            "session_stats": {
                "uptime_seconds": int(time.time() - self.start_time) if self.start_time else 0,
                "total_measurements": len(self.metrics_history)
            }
        }
        
        # Append to log file
        log_file = "/home/marku/ai_workflow_engine/pool_monitor.log"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    async def monitor_loop(self):
        """Main monitoring loop."""
        logger.info("Starting database pool health monitor...")
        logger.info(f"Check interval: {self.check_interval} seconds")
        
        self.is_running = True
        self.start_time = time.time()
        
        try:
            while self.is_running:
                # Get current database statistics
                stats = get_database_stats()
                stats["timestamp"] = time.time()
                
                # Calculate health metrics
                metrics = self.calculate_pool_metrics(stats)
                
                # Store metrics
                self.metrics_history.append(metrics)
                
                # Keep only last hour of data (assuming 3s intervals = 1200 points)
                if len(self.metrics_history) > 1200:
                    self.metrics_history = self.metrics_history[-1200:]
                
                # Display dashboard
                self.display_dashboard(metrics)
                
                # Save to log
                self.save_metrics_snapshot(metrics)
                
                # Store for next iteration
                self.previous_stats = stats
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitor error: {e}")
        finally:
            self.is_running = False
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.is_running = False

async def main():
    """Initialize and start monitoring."""
    
    # Setup signal handlers for clean shutdown
    monitor = PoolHealthMonitor(check_interval=3)
    
    def signal_handler(signum, frame):
        print("\n🛑 Stopping monitor...")
        monitor.stop_monitoring()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize database connection
        logger.info("Initializing database connection...")
        settings = get_settings()
        initialize_database(settings)
        logger.info("Database initialized successfully")
        
        # Start monitoring
        await monitor.monitor_loop()
        
    except Exception as e:
        logger.error(f"Failed to start monitor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())