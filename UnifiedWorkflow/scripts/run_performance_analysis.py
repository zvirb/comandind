#!/usr/bin/env python3
"""
Performance Analysis Execution Script

This script coordinates the execution of comprehensive performance analysis
including system baselines, bottleneck identification, and optimization recommendations.
"""

import asyncio
import sys
import os
import logging
import json
from pathlib import Path
from datetime import datetime
import subprocess
import time

# Add the app directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'performance_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_system_prerequisites() -> bool:
    """Check if the system meets prerequisites for performance analysis."""
    logger.info("🔍 Checking system prerequisites...")
    
    # Check if Docker services are running
    try:
        result = subprocess.run(['docker', 'compose', 'ps'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.error("Docker Compose services not running")
            return False
        
        # Check for key services
        required_services = ['postgres', 'redis', 'api']
        running_services = result.stdout.lower()
        
        missing_services = []
        for service in required_services:
            if service not in running_services or 'up' not in running_services:
                missing_services.append(service)
        
        if missing_services:
            logger.error(f"Required services not running: {missing_services}")
            return False
            
        logger.info("✅ Docker services are running")
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout checking Docker services")
        return False
    except Exception as e:
        logger.error(f"Error checking Docker services: {e}")
        return False
    
    # Check if API is responsive
    try:
        import requests
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            logger.info("✅ API service is responsive")
        else:
            logger.warning(f"API service returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"API service not responsive: {e}")
        logger.info("📝 Continuing with analysis - some API tests may fail")
    
    # Check Python dependencies
    try:
        import psutil
        import aiohttp
        logger.info("✅ Python dependencies available")
    except ImportError as e:
        logger.error(f"Missing Python dependency: {e}")
        return False
    
    logger.info("✅ System prerequisites check complete")
    return True

async def run_performance_monitoring_service_analysis():
    """Run analysis using the existing performance monitoring service."""
    logger.info("🔧 Running performance monitoring service analysis...")
    
    try:
        from shared.services.performance_monitoring_service import get_performance_monitor
        from shared.services.redis_cache_service import get_redis_cache
        from shared.services.query_performance_service import get_performance_summary, start_query_monitoring
        
        # Initialize monitoring
        start_query_monitoring()
        monitor = await get_performance_monitor()
        
        # Get comprehensive metrics
        db_health = await monitor.get_database_health_metrics()
        recommendations = await monitor.get_performance_recommendations()
        query_summary = await get_performance_summary()
        
        # Get cache metrics
        cache_metrics = {}
        try:
            cache = await get_redis_cache()
            cache_metrics = await cache.get_cache_metrics()
        except Exception as e:
            cache_metrics = {"error": str(e)}
        
        analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "database_health": {
                "active_connections": db_health.active_connections,
                "connection_utilization_percent": db_health.connection_utilization_percent,
                "avg_query_time_ms": db_health.avg_query_time_ms,
                "slow_queries_count": db_health.slow_queries_count,
                "database_size_mb": db_health.database_size_mb,
                "largest_tables": db_health.largest_tables[:5],
                "unused_indexes": db_health.unused_indexes[:10],
                "missing_indexes": db_health.missing_indexes[:5]
            },
            "performance_recommendations": recommendations,
            "query_performance": query_summary,
            "cache_metrics": cache_metrics
        }
        
        logger.info("✅ Performance monitoring service analysis complete")
        return analysis_results
        
    except Exception as e:
        logger.error(f"Performance monitoring service analysis failed: {e}")
        return {"error": str(e)}

def run_system_resource_analysis():
    """Analyze current system resource utilization."""
    logger.info("💻 Analyzing system resources...")
    
    try:
        import psutil
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        load_avg = list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0.0, 0.0, 0.0]
        
        # Memory metrics
        memory = psutil.virtual_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        # Network metrics
        network = psutil.net_io_counters()
        
        # Process metrics
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if proc.info['cpu_percent'] > 5 or proc.info['memory_percent'] > 5:
                    processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage
        processes = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:10]
        
        system_analysis = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "usage_percent": cpu_percent,
                "core_count": cpu_count,
                "load_average": load_avg
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "usage_percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "usage_percent": (disk.used / disk.total) * 100
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            },
            "top_processes": processes
        }
        
        logger.info(f"✅ System analysis complete - CPU: {cpu_percent:.1f}%, Memory: {memory.percent:.1f}%, Disk: {(disk.used/disk.total)*100:.1f}%")
        return system_analysis
        
    except Exception as e:
        logger.error(f"System resource analysis failed: {e}")
        return {"error": str(e)}

async def run_api_performance_tests():
    """Test API endpoint performance."""
    logger.info("🌐 Testing API performance...")
    
    try:
        import aiohttp
        import time
        
        api_base = "http://localhost:8000"
        
        # Test endpoints
        endpoints = [
            {"method": "GET", "path": "/health", "name": "Health Check"},
            {"method": "GET", "path": "/api/v1/performance/status", "name": "Performance Status"},
            {"method": "GET", "path": "/api/v1/performance/health", "name": "Performance Health"},
        ]
        
        results = {}
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                try:
                    times = []
                    errors = 0
                    
                    # Test each endpoint 10 times
                    for i in range(10):
                        start_time = time.time()
                        try:
                            url = f"{api_base}{endpoint['path']}"
                            async with session.get(url, timeout=10) as response:
                                await response.text()
                                if response.status < 400:
                                    times.append((time.time() - start_time) * 1000)
                                else:
                                    errors += 1
                        except Exception:
                            errors += 1
                    
                    if times:
                        results[endpoint['name']] = {
                            "avg_response_time_ms": sum(times) / len(times),
                            "min_response_time_ms": min(times),
                            "max_response_time_ms": max(times),
                            "success_rate": (len(times) / 10) * 100,
                            "error_count": errors
                        }
                    else:
                        results[endpoint['name']] = {
                            "error": "All requests failed",
                            "error_count": errors
                        }
                    
                    logger.info(f"✅ {endpoint['name']}: {results[endpoint['name']].get('avg_response_time_ms', 'N/A')}ms avg")
                    
                except Exception as e:
                    logger.error(f"Error testing {endpoint['name']}: {e}")
                    results[endpoint['name']] = {"error": str(e)}
        
        return {
            "timestamp": datetime.now().isoformat(),
            "api_performance": results
        }
        
    except Exception as e:
        logger.error(f"API performance testing failed: {e}")
        return {"error": str(e)}

def run_docker_container_analysis():
    """Analyze Docker container resource usage."""
    logger.info("🐳 Analyzing Docker container performance...")
    
    try:
        result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format', 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}'],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0:
            logger.error("Failed to get Docker stats")
            return {"error": "Docker stats unavailable"}
        
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return {"error": "No container stats available"}
        
        # Parse container stats
        containers = []
        for line in lines[1:]:  # Skip header
            parts = line.split('\t')
            if len(parts) >= 5:
                containers.append({
                    "container": parts[0],
                    "cpu_percent": parts[1],
                    "memory_usage": parts[2],
                    "network_io": parts[3],
                    "block_io": parts[4]
                })
        
        logger.info(f"✅ Docker analysis complete - {len(containers)} containers analyzed")
        return {
            "timestamp": datetime.now().isoformat(),
            "container_stats": containers
        }
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout getting Docker stats")
        return {"error": "Docker stats timeout"}
    except Exception as e:
        logger.error(f"Docker analysis failed: {e}")
        return {"error": str(e)}

def generate_performance_insights(analysis_data):
    """Generate insights and recommendations from analysis data."""
    logger.info("🧠 Generating performance insights...")
    
    insights = {
        "timestamp": datetime.now().isoformat(),
        "overall_assessment": "healthy",
        "critical_issues": [],
        "recommendations": [],
        "performance_score": 85  # Default score
    }
    
    try:
        # System resource insights
        system_data = analysis_data.get("system_analysis", {})
        if isinstance(system_data, dict):
            cpu_usage = system_data.get("cpu", {}).get("usage_percent", 0)
            memory_usage = system_data.get("memory", {}).get("usage_percent", 0)
            disk_usage = system_data.get("disk", {}).get("usage_percent", 0)
            
            # CPU analysis
            if cpu_usage > 90:
                insights["critical_issues"].append("Critical CPU usage detected")
                insights["recommendations"].append("Immediate CPU optimization or scaling required")
                insights["performance_score"] -= 20
                insights["overall_assessment"] = "critical"
            elif cpu_usage > 80:
                insights["recommendations"].append("High CPU usage - monitor for performance impact")
                insights["performance_score"] -= 10
                if insights["overall_assessment"] == "healthy":
                    insights["overall_assessment"] = "warning"
            
            # Memory analysis
            if memory_usage > 95:
                insights["critical_issues"].append("Critical memory usage - risk of OOM")
                insights["recommendations"].append("Immediate memory optimization required")
                insights["performance_score"] -= 25
                insights["overall_assessment"] = "critical"
            elif memory_usage > 85:
                insights["recommendations"].append("High memory usage - consider optimization")
                insights["performance_score"] -= 10
                if insights["overall_assessment"] == "healthy":
                    insights["overall_assessment"] = "warning"
            
            # Disk analysis
            if disk_usage > 95:
                insights["critical_issues"].append("Critical disk usage")
                insights["recommendations"].append("Free up disk space immediately")
                insights["performance_score"] -= 15
            elif disk_usage > 90:
                insights["recommendations"].append("High disk usage - plan for cleanup")
                insights["performance_score"] -= 5
        
        # Database insights
        monitoring_data = analysis_data.get("monitoring_analysis", {})
        if isinstance(monitoring_data, dict):
            db_health = monitoring_data.get("database_health", {})
            
            conn_util = db_health.get("connection_utilization_percent", 0)
            if conn_util > 90:
                insights["critical_issues"].append("Database connection pool nearly exhausted")
                insights["recommendations"].append("Increase connection pool size or optimize queries")
                insights["performance_score"] -= 20
            
            avg_query_time = db_health.get("avg_query_time_ms", 0)
            if avg_query_time > 1000:
                insights["recommendations"].append("Optimize slow database queries")
                insights["performance_score"] -= 15
        
        # API performance insights
        api_data = analysis_data.get("api_analysis", {})
        if isinstance(api_data, dict):
            api_perf = api_data.get("api_performance", {})
            slow_endpoints = 0
            
            for endpoint, metrics in api_perf.items():
                if isinstance(metrics, dict):
                    avg_time = metrics.get("avg_response_time_ms", 0)
                    if avg_time > 1000:
                        slow_endpoints += 1
            
            if slow_endpoints > 0:
                insights["recommendations"].append(f"Optimize {slow_endpoints} slow API endpoints")
                insights["performance_score"] -= (slow_endpoints * 5)
        
        # Ensure minimum score
        insights["performance_score"] = max(0, insights["performance_score"])
        
        # Determine overall assessment based on score
        if insights["performance_score"] < 50:
            insights["overall_assessment"] = "critical"
        elif insights["performance_score"] < 70:
            insights["overall_assessment"] = "warning"
        elif insights["performance_score"] < 85:
            insights["overall_assessment"] = "good"
        else:
            insights["overall_assessment"] = "excellent"
        
        logger.info(f"✅ Performance insights generated - Score: {insights['performance_score']}/100")
        
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        insights["error"] = str(e)
    
    return insights

def save_analysis_results(analysis_data, insights):
    """Save analysis results to files."""
    logger.info("💾 Saving analysis results...")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comprehensive JSON report
        json_filename = f"performance_analysis_report_{timestamp}.json"
        complete_report = {
            "analysis_metadata": {
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "comprehensive_performance_baseline",
                "duration_minutes": 10  # Approximate
            },
            "performance_insights": insights,
            "detailed_analysis": analysis_data
        }
        
        with open(json_filename, 'w') as f:
            json.dump(complete_report, f, indent=2, default=str)
        
        # Save executive summary
        summary_filename = f"performance_executive_summary_{timestamp}.txt"
        with open(summary_filename, 'w') as f:
            f.write("="*80 + "\n")
            f.write("PERFORMANCE ANALYSIS EXECUTIVE SUMMARY\n")
            f.write("="*80 + "\n")
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Overall Assessment: {insights.get('overall_assessment', 'Unknown').upper()}\n")
            f.write(f"Performance Score: {insights.get('performance_score', 'N/A')}/100\n\n")
            
            # Critical Issues
            critical_issues = insights.get("critical_issues", [])
            if critical_issues:
                f.write("CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:\n")
                f.write("-" * 50 + "\n")
                for i, issue in enumerate(critical_issues, 1):
                    f.write(f"{i}. {issue}\n")
                f.write("\n")
            else:
                f.write("✅ No critical issues identified.\n\n")
            
            # Recommendations
            recommendations = insights.get("recommendations", [])
            if recommendations:
                f.write("PERFORMANCE OPTIMIZATION RECOMMENDATIONS:\n")
                f.write("-" * 50 + "\n")
                for i, rec in enumerate(recommendations, 1):
                    f.write(f"{i}. {rec}\n")
                f.write("\n")
            
            # System Metrics Summary
            system_data = analysis_data.get("system_analysis", {})
            if isinstance(system_data, dict):
                f.write("SYSTEM METRICS SUMMARY:\n")
                f.write("-" * 30 + "\n")
                cpu_data = system_data.get("cpu", {})
                memory_data = system_data.get("memory", {})
                disk_data = system_data.get("disk", {})
                
                f.write(f"CPU Usage: {cpu_data.get('usage_percent', 'N/A')}%\n")
                f.write(f"Memory Usage: {memory_data.get('usage_percent', 'N/A')}%\n")
                f.write(f"Disk Usage: {disk_data.get('usage_percent', 'N/A')}%\n")
                f.write(f"Memory Available: {memory_data.get('available_gb', 'N/A')} GB\n\n")
            
            # Database Summary
            monitoring_data = analysis_data.get("monitoring_analysis", {})
            if isinstance(monitoring_data, dict):
                db_health = monitoring_data.get("database_health", {})
                if db_health:
                    f.write("DATABASE PERFORMANCE SUMMARY:\n")
                    f.write("-" * 35 + "\n")
                    f.write(f"Connection Pool Utilization: {db_health.get('connection_utilization_percent', 'N/A')}%\n")
                    f.write(f"Average Query Time: {db_health.get('avg_query_time_ms', 'N/A')} ms\n")
                    f.write(f"Slow Queries Count: {db_health.get('slow_queries_count', 'N/A')}\n")
                    f.write(f"Database Size: {db_health.get('database_size_mb', 'N/A')} MB\n\n")
            
            f.write("="*80 + "\n")
            f.write("For detailed metrics, see the full JSON report.\n")
            f.write("="*80 + "\n")
        
        logger.info(f"✅ Results saved to {json_filename} and {summary_filename}")
        return json_filename, summary_filename
        
    except Exception as e:
        logger.error(f"Failed to save analysis results: {e}")
        return None, None

async def main():
    """Main orchestration function for performance analysis."""
    logger.info("🚀 Starting Comprehensive Performance Analysis")
    logger.info("=" * 60)
    
    # Check prerequisites
    if not check_system_prerequisites():
        logger.error("❌ Prerequisites not met - aborting analysis")
        return 1
    
    analysis_data = {}
    
    try:
        # Phase 1: System Resource Analysis
        logger.info("📊 Phase 1: System Resource Analysis")
        analysis_data["system_analysis"] = run_system_resource_analysis()
        
        # Phase 2: Docker Container Analysis
        logger.info("🐳 Phase 2: Docker Container Analysis")
        analysis_data["docker_analysis"] = run_docker_container_analysis()
        
        # Phase 3: Performance Monitoring Service Analysis
        logger.info("🔧 Phase 3: Performance Monitoring Service Analysis")
        analysis_data["monitoring_analysis"] = await run_performance_monitoring_service_analysis()
        
        # Phase 4: API Performance Tests
        logger.info("🌐 Phase 4: API Performance Testing")
        analysis_data["api_analysis"] = await run_api_performance_tests()
        
        # Phase 5: Generate Insights and Recommendations
        logger.info("🧠 Phase 5: Generating Performance Insights")
        insights = generate_performance_insights(analysis_data)
        
        # Phase 6: Save Results
        logger.info("💾 Phase 6: Saving Analysis Results")
        json_file, summary_file = save_analysis_results(analysis_data, insights)
        
        # Final Report
        print("\n" + "=" * 80)
        print("PERFORMANCE ANALYSIS COMPLETE")
        print("=" * 80)
        print(f"📊 Overall Assessment: {insights.get('overall_assessment', 'Unknown').upper()}")
        print(f"📈 Performance Score: {insights.get('performance_score', 'N/A')}/100")
        print(f"🚨 Critical Issues: {len(insights.get('critical_issues', []))}")
        print(f"💡 Recommendations: {len(insights.get('recommendations', []))}")
        
        if json_file and summary_file:
            print(f"📄 Detailed Report: {json_file}")
            print(f"📋 Executive Summary: {summary_file}")
        
        print("=" * 80)
        
        # Show critical issues if any
        critical_issues = insights.get("critical_issues", [])
        if critical_issues:
            print("\n🚨 CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:")
            for i, issue in enumerate(critical_issues, 1):
                print(f"  {i}. {issue}")
        
        # Show top recommendations
        recommendations = insights.get("recommendations", [])[:3]  # Top 3
        if recommendations:
            print("\n💡 TOP PERFORMANCE RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        print("\n✅ Analysis complete! Check the generated reports for detailed findings.")
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n❌ Analysis interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)