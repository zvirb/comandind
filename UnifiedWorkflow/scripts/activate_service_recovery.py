#!/usr/bin/env python3
"""
Service Recovery Activation Script
Activates and configures the automated recovery system for production deployment
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure_recovery_service.automated_recovery import automated_recovery
from app.infrastructure_recovery_service.config import infrastructure_recovery_config

async def configure_recovery_system():
    """Configure and activate the automated recovery system."""
    print("🔧 Configuring Automated Recovery System...")
    
    # Initialize the recovery system
    await automated_recovery.initialize()
    
    # Configure recovery thresholds
    config_updates = {
        'HEALTH_SCORE_THRESHOLD': 0.7,  # Trigger recovery below 70% health
        'COOLDOWN_PERIOD_SECONDS': 300,  # 5 minute cooldown between recoveries
        'MAX_RETRY_ATTEMPTS': 3,
        'GRACEFUL_SHUTDOWN_TIMEOUT': 30
    }
    
    for key, value in config_updates.items():
        setattr(infrastructure_recovery_config, key, value)
    
    print("✅ Recovery system configured with:")
    print(f"  • Health threshold: {config_updates['HEALTH_SCORE_THRESHOLD']}")
    print(f"  • Cooldown period: {config_updates['COOLDOWN_PERIOD_SECONDS']}s")
    print(f"  • Max retries: {config_updates['MAX_RETRY_ATTEMPTS']}")

async def setup_monitoring_integration():
    """Integrate recovery system with monitoring stack."""
    print("\n📊 Setting up monitoring integration...")
    
    # Create Prometheus alerting rules for recovery triggers
    alert_rules = {
        'groups': [{
            'name': 'recovery_triggers',
            'rules': [
                {
                    'alert': 'ServiceHealthLow',
                    'expr': 'service_health_score < 0.7',
                    'for': '2m',
                    'labels': {
                        'severity': 'warning',
                        'recovery': 'auto'
                    },
                    'annotations': {
                        'summary': 'Service health below threshold',
                        'description': 'Service {{ $labels.service }} health score is {{ $value }}'
                    }
                },
                {
                    'alert': 'ServiceDown',
                    'expr': 'up == 0',
                    'for': '1m',
                    'labels': {
                        'severity': 'critical',
                        'recovery': 'auto'
                    },
                    'annotations': {
                        'summary': 'Service is down',
                        'description': 'Service {{ $labels.job }} is down'
                    }
                }
            ]
        }]
    }
    
    # Save alert rules
    alert_file = Path('/home/marku/ai_workflow_engine/config/prometheus/recovery_alerts.yml')
    alert_file.parent.mkdir(parents=True, exist_ok=True)
    
    import yaml
    with open(alert_file, 'w') as f:
        yaml.dump(alert_rules, f)
    
    print(f"✅ Alert rules saved to {alert_file}")

async def create_recovery_scripts():
    """Create recovery automation scripts."""
    print("\n📝 Creating recovery automation scripts...")
    
    # Service restart script
    restart_script = """#!/bin/bash
# Automated Service Restart Script

SERVICE=$1
ACTION=${2:-restart}

echo "🔄 Performing $ACTION on $SERVICE..."

case $ACTION in
    restart)
        docker-compose restart $SERVICE
        ;;
    graceful)
        docker-compose kill -s SIGTERM $SERVICE
        sleep 10
        docker-compose up -d $SERVICE
        ;;
    health-check)
        docker-compose exec $SERVICE /health-check.sh || true
        ;;
    clear-cache)
        docker-compose exec redis redis-cli FLUSHDB
        ;;
    *)
        echo "Unknown action: $ACTION"
        exit 1
        ;;
esac

# Wait for service to be healthy
for i in {1..30}; do
    if docker-compose ps $SERVICE | grep -q "healthy"; then
        echo "✅ $SERVICE is healthy"
        exit 0
    fi
    sleep 2
done

echo "⚠️ $SERVICE failed to become healthy"
exit 1
"""
    
    script_path = Path('/home/marku/ai_workflow_engine/scripts/service_recovery.sh')
    with open(script_path, 'w') as f:
        f.write(restart_script)
    
    # Make executable
    os.chmod(script_path, 0o755)
    print(f"✅ Recovery script created: {script_path}")
    
    # Health check script
    health_check_script = """#!/bin/bash
# Service Health Check Script

check_service_health() {
    local service=$1
    local port=$2
    
    curl -s -f "http://localhost:$port/health" > /dev/null 2>&1
    return $?
}

# Check all services
services=(
    "api:8000"
    "webui:3001"
    "perception:8001"
    "memory:8002"
    "reasoning:8003"
    "coordination:8004"
    "learning:8005"
)

unhealthy=()

for service_port in "${services[@]}"; do
    IFS=':' read -r service port <<< "$service_port"
    if ! check_service_health "$service" "$port"; then
        unhealthy+=("$service")
    fi
done

if [ ${#unhealthy[@]} -gt 0 ]; then
    echo "❌ Unhealthy services: ${unhealthy[*]}"
    exit 1
else
    echo "✅ All services healthy"
    exit 0
fi
"""
    
    health_script_path = Path('/home/marku/ai_workflow_engine/scripts/check_all_health.sh')
    with open(health_script_path, 'w') as f:
        f.write(health_check_script)
    
    os.chmod(health_script_path, 0o755)
    print(f"✅ Health check script created: {health_script_path}")

async def test_recovery_system():
    """Test the recovery system with a simulated failure."""
    print("\n🧪 Testing recovery system...")
    
    # Get current status
    status = await automated_recovery.get_recovery_status()
    print(f"  • Recovery system running: {status.get('running', False)}")
    print(f"  • Active recoveries: {status.get('active_recoveries', 0)}")
    print(f"  • Services in cooldown: {status.get('services_in_cooldown', 0)}")
    
    # Simulate a service health issue
    print("\n  Simulating service health degradation...")
    
    # This would normally be triggered by actual health monitoring
    # For testing, we'll manually trigger a recovery
    from app.infrastructure_recovery_service.automated_recovery import RecoveryAction, RecoveryActionType
    
    test_recovery = RecoveryAction(
        action_type=RecoveryActionType.HEALTH_CHECK_RESET,
        service='test-service',
        parameters={'test': True},
        priority=5
    )
    
    await automated_recovery.queue_recovery_action(test_recovery)
    print("  ✅ Test recovery action queued")
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Check status again
    status = await automated_recovery.get_recovery_status()
    print(f"\n  • Active recoveries after test: {status.get('active_recoveries', 0)}")
    print(f"  • Recovery history: {status.get('recovery_history_count', 0)}")

async def create_systemd_service():
    """Create systemd service for automated recovery."""
    print("\n🔧 Creating systemd service...")
    
    service_content = """[Unit]
Description=AI Workflow Engine Automated Recovery System
After=docker.service
Requires=docker.service

[Service]
Type=simple
Restart=always
RestartSec=10
User=marku
WorkingDirectory=/home/marku/ai_workflow_engine
ExecStart=/usr/bin/python3 /home/marku/ai_workflow_engine/app/infrastructure_recovery_service/main.py
StandardOutput=append:/var/log/aiwfe-recovery.log
StandardError=append:/var/log/aiwfe-recovery.error.log

[Install]
WantedBy=multi-user.target
"""
    
    service_path = Path('/home/marku/ai_workflow_engine/aiwfe-recovery.service')
    with open(service_path, 'w') as f:
        f.write(service_content)
    
    print(f"✅ Systemd service file created: {service_path}")
    print("  To install: sudo cp aiwfe-recovery.service /etc/systemd/system/")
    print("  To enable: sudo systemctl enable aiwfe-recovery")
    print("  To start: sudo systemctl start aiwfe-recovery")

async def main():
    """Main activation function."""
    print("=" * 60)
    print("🚀 ACTIVATING AUTOMATED SERVICE RECOVERY SYSTEM")
    print("=" * 60)
    
    try:
        # Configure recovery system
        await configure_recovery_system()
        
        # Setup monitoring integration
        await setup_monitoring_integration()
        
        # Create recovery scripts
        await create_recovery_scripts()
        
        # Test the system
        await test_recovery_system()
        
        # Create systemd service
        await create_systemd_service()
        
        print("\n" + "=" * 60)
        print("✅ AUTOMATED RECOVERY SYSTEM ACTIVATED SUCCESSFULLY")
        print("=" * 60)
        
        print("\n📋 Next Steps:")
        print("  1. Install systemd service for automatic startup")
        print("  2. Configure Prometheus to use recovery alert rules")
        print("  3. Test recovery actions with './scripts/service_recovery.sh <service> <action>'")
        print("  4. Monitor recovery events in Redis and logs")
        
        # Save activation status
        activation_status = {
            'activated': True,
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'health_threshold': 0.7,
                'cooldown_period': 300,
                'max_retries': 3
            },
            'scripts_created': [
                '/home/marku/ai_workflow_engine/scripts/service_recovery.sh',
                '/home/marku/ai_workflow_engine/scripts/check_all_health.sh'
            ],
            'monitoring_integration': True,
            'systemd_service': 'aiwfe-recovery.service'
        }
        
        status_file = Path('/home/marku/ai_workflow_engine/.claude/recovery_activation_status.json')
        with open(status_file, 'w') as f:
            json.dump(activation_status, f, indent=2)
        
        print(f"\n📁 Activation status saved to: {status_file}")
        
    except Exception as e:
        print(f"\n❌ Error activating recovery system: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(main())