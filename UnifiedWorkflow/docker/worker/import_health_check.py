#!/usr/bin/env python3
"""
Import health check script for Worker service.
Validates all critical shared module imports on container startup.
"""

import sys
import traceback
from datetime import datetime

def check_critical_imports():
    """Test critical imports that the Worker service depends on."""
    import_tests = [
        ("shared.utils.database_setup", "Database setup utilities"),
        ("shared.utils.config", "Configuration management"),
        ("shared.database.models", "Database models"),
        ("shared.schemas", "Pydantic schemas"),
        ("shared.services.redis_cache_service", "Redis cache service"),
        ("shared.monitoring.prometheus_metrics", "Prometheus metrics"),
        ("shared.monitoring.worker_monitoring", "Worker monitoring"),
        ("worker.celery_app", "Celery application"),
        ("worker.tasks", "Worker tasks"),
        ("worker.services.ollama_service", "Ollama service"),
        ("worker.services.smart_router_service", "Smart router service"),
        ("worker.database_service", "Worker database service"),
    ]
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": "worker",
        "total_tests": len(import_tests),
        "passed": 0,
        "failed": 0,
        "failures": []
    }
    
    for module_name, description in import_tests:
        try:
            __import__(module_name)
            results["passed"] += 1
            print(f"✓ {module_name} - {description}")
        except Exception as e:
            results["failed"] += 1
            error_info = {
                "module": module_name,
                "description": description,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            results["failures"].append(error_info)
            print(f"✗ {module_name} - {description}: {e}")
    
    return results

def generate_evidence():
    """Generate concrete evidence of import health."""
    results = check_critical_imports()
    
    evidence = {
        "validation_type": "import_health_check",
        "service": "worker",
        "timestamp": results["timestamp"],
        "success": results["failed"] == 0,
        "summary": {
            "total_imports": results["total_tests"],
            "successful_imports": results["passed"],
            "failed_imports": results["failed"],
            "success_rate": f"{(results['passed']/results['total_tests']*100):.1f}%"
        },
        "evidence": {
            "pythonpath": sys.path,
            "working_directory": "/app",
            "import_results": results
        }
    }
    
    if results["failed"] > 0:
        evidence["failure_details"] = results["failures"]
        evidence["recommendation"] = "Fix PYTHONPATH configuration and missing dependencies"
    
    return evidence

if __name__ == "__main__":
    import json
    
    print("Worker Service Import Health Check")
    print("=" * 40)
    
    evidence = generate_evidence()
    
    print(f"\nResults: {evidence['summary']['successful_imports']}/{evidence['summary']['total_imports']} imports successful")
    print(f"Success Rate: {evidence['summary']['success_rate']}")
    
    # Save evidence for validation
    with open("/tmp/worker_import_health_evidence.json", "w") as f:
        json.dump(evidence, f, indent=2)
    
    if not evidence["success"]:
        print("\nFAILURES:")
        for failure in evidence.get("failure_details", []):
            print(f"- {failure['module']}: {failure['error']}")
        sys.exit(1)
    
    print("\n✓ All critical imports successful!")
    sys.exit(0)