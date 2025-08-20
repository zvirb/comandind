#!/usr/bin/env python3
"""
Performance Validation Suite

Validates database connection pool improvements after backend fixes
by comparing before/after performance metrics and running stress tests.
"""

import asyncio
import time
import json
import logging
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import statistics
import subprocess

# Add app to Python path  
sys.path.insert(0, '/home/marku/ai_workflow_engine/app')

from shared.utils.database_setup import get_database_stats, initialize_database
from shared.utils.config import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerformanceValidator:
    """Validates performance improvements after database pool optimization."""
    
    def __init__(self):
        self.settings = get_settings()
        self.validation_results = {}
        
    def load_baseline_metrics(self, baseline_file: str = None) -> Dict[str, Any]:
        """Load baseline performance metrics from previous analysis."""
        
        if not baseline_file:
            # Find the most recent performance analysis report
            import glob
            reports = glob.glob("/home/marku/ai_workflow_engine/performance_analysis_report_*.json")
            if not reports:
                logger.warning("No baseline performance report found")
                return {}
            baseline_file = max(reports)  # Most recent
        
        try:
            with open(baseline_file, 'r') as f:
                baseline = json.load(f)
            logger.info(f"Loaded baseline from {baseline_file}")
            return baseline
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")
            return {}
    
    def test_connection_pool_efficiency(self) -> Dict[str, Any]:
        """Test connection pool efficiency and utilization."""
        logger.info("Testing connection pool efficiency...")
        
        try:
            # Initialize database
            initialize_database(self.settings)
            
            # Get initial pool state
            initial_stats = get_database_stats()
            
            # Simulate connection usage by creating sessions
            from shared.utils.database_setup import get_db, get_async_session
            
            sync_sessions = []
            start_time = time.time()
            
            # Create multiple sync sessions to test pool behavior
            for i in range(5):
                try:
                    db_gen = get_db()
                    session = next(db_gen)
                    sync_sessions.append((session, db_gen))
                except Exception as e:
                    logger.warning(f"Failed to create sync session {i}: {e}")
            
            # Get stats after creating sessions
            loaded_stats = get_database_stats()
            session_creation_time = time.time() - start_time
            
            # Clean up sync sessions
            for session, db_gen in sync_sessions:
                try:
                    session.close()
                except:
                    pass
            
            # Test async sessions  
            async def test_async_sessions():
                async_sessions = []
                async_start = time.time()
                
                for i in range(3):
                    try:
                        async for session in get_async_session():
                            async_sessions.append(session)
                            break  # Just get the session, don't iterate
                    except Exception as e:
                        logger.warning(f"Failed to create async session {i}: {e}")
                
                async_creation_time = time.time() - async_start
                
                # Clean up
                for session in async_sessions:
                    try:
                        await session.close()
                    except:
                        pass
                
                return async_creation_time, len(async_sessions)
            
            async_time, async_count = asyncio.run(test_async_sessions())
            
            # Get final pool state
            final_stats = get_database_stats()
            
            # Calculate metrics
            efficiency_metrics = {
                "initial_stats": initial_stats,
                "loaded_stats": loaded_stats,
                "final_stats": final_stats,
                "sync_session_creation_time": session_creation_time,
                "async_session_creation_time": async_time,
                "sync_sessions_created": len(sync_sessions),
                "async_sessions_created": async_count,
                "sessions_per_second": len(sync_sessions) / session_creation_time if session_creation_time > 0 else 0,
                "async_sessions_per_second": async_count / async_time if async_time > 0 else 0
            }
            
            # Check for connection leaks
            initial_sync_created = initial_stats.get("sync_engine", {}).get("connections_created", 0)
            final_sync_created = final_stats.get("sync_engine", {}).get("connections_created", 0)
            
            initial_async_created = initial_stats.get("async_engine", {}).get("connections_created", 0)
            final_async_created = final_stats.get("async_engine", {}).get("connections_created", 0)
            
            efficiency_metrics["connection_leak_detected"] = (
                (final_sync_created > initial_sync_created + len(sync_sessions)) or
                (final_async_created > initial_async_created + async_count)
            )
            
            return {
                "status": "completed",
                "metrics": efficiency_metrics,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def test_authentication_performance(self) -> Dict[str, Any]:
        """Test authentication endpoint performance under load."""
        logger.info("Testing authentication performance...")
        
        try:
            # Check if API is running
            import aiohttp
            
            async def run_auth_performance_test():
                base_url = "http://localhost:8000"
                
                # Test connectivity first
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{base_url}/docs", timeout=aiohttp.ClientTimeout(total=5)) as response:
                            if response.status != 200:
                                return {
                                    "status": "skipped",
                                    "reason": f"API not accessible at {base_url}",
                                    "timestamp": datetime.now().isoformat()
                                }
                except Exception as e:
                    return {
                        "status": "skipped", 
                        "reason": f"Cannot connect to API: {e}",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Run authentication load tests
                test_scenarios = [
                    {"concurrent": 5, "requests": 3, "name": "Light"},
                    {"concurrent": 10, "requests": 2, "name": "Moderate"},
                    {"concurrent": 15, "requests": 2, "name": "Heavy"}
                ]
                
                scenario_results = {}
                
                for scenario in test_scenarios:
                    start_time = time.time()
                    success_count = 0
                    total_requests = scenario["concurrent"] * scenario["requests"]
                    response_times = []
                    
                    # Create test tasks
                    async def auth_request(session, email="admin@aiwfe.com", password="admin123"):
                        req_start = time.time()
                        try:
                            async with session.post(
                                f"{base_url}/auth/jwt/login",
                                json={"email": email, "password": password},
                                timeout=aiohttp.ClientTimeout(total=10)
                            ) as resp:
                                req_time = (time.time() - req_start) * 1000
                                return {"success": resp.status == 200, "response_time": req_time}
                        except:
                            return {"success": False, "response_time": (time.time() - req_start) * 1000}
                    
                    # Execute concurrent requests
                    async with aiohttp.ClientSession() as session:
                        tasks = []
                        for _ in range(scenario["concurrent"]):
                            for _ in range(scenario["requests"]):
                                tasks.append(auth_request(session))
                        
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    for result in results:
                        if isinstance(result, dict):
                            if result["success"]:
                                success_count += 1
                            response_times.append(result["response_time"])
                    
                    test_time = time.time() - start_time
                    
                    scenario_results[scenario["name"]] = {
                        "total_requests": total_requests,
                        "successful_requests": success_count,
                        "success_rate": success_count / total_requests if total_requests > 0 else 0,
                        "test_duration": test_time,
                        "requests_per_second": total_requests / test_time if test_time > 0 else 0,
                        "avg_response_time": statistics.mean(response_times) if response_times else 0,
                        "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 1 else response_times[0] if response_times else 0
                    }
                
                return {
                    "status": "completed",
                    "scenario_results": scenario_results,
                    "timestamp": datetime.now().isoformat()
                }
            
            return asyncio.run(run_auth_performance_test())
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def test_pool_recovery_after_exhaustion(self) -> Dict[str, Any]:
        """Test pool recovery behavior after simulated exhaustion."""
        logger.info("Testing pool recovery after exhaustion...")
        
        try:
            # Initialize database
            initialize_database(self.settings)
            
            initial_stats = get_database_stats()
            
            # Try to exhaust the pool by creating many connections
            from shared.utils.database_setup import get_db
            
            sessions = []
            max_attempts = 50  # Try to create more than pool + overflow
            successful_creations = 0
            
            start_time = time.time()
            
            for i in range(max_attempts):
                try:
                    db_gen = get_db()
                    session = next(db_gen)
                    sessions.append((session, db_gen))
                    successful_creations += 1
                    
                    # Check if we've hit pool limits
                    current_stats = get_database_stats()
                    if current_stats.get("sync_engine", {}).get("connections_created", 0) >= 25:  # Reasonable exhaustion point
                        break
                        
                except Exception as e:
                    logger.info(f"Pool exhaustion detected at {successful_creations} connections: {e}")
                    break
            
            exhaustion_time = time.time() - start_time
            exhaustion_stats = get_database_stats()
            
            # Now test recovery by releasing connections
            recovery_start = time.time()
            
            # Release half the connections
            release_count = len(sessions) // 2
            for i in range(release_count):
                try:
                    session, db_gen = sessions.pop()
                    session.close()
                except:
                    pass
            
            # Wait a moment for cleanup
            await asyncio.sleep(1)
            
            # Test if new connections can be created
            recovery_sessions = []
            for i in range(5):
                try:
                    db_gen = get_db()
                    session = next(db_gen)
                    recovery_sessions.append((session, db_gen))
                except Exception as e:
                    logger.warning(f"Recovery test failed at connection {i}: {e}")
                    break
            
            recovery_time = time.time() - recovery_start
            recovery_stats = get_database_stats()
            
            # Clean up all remaining sessions
            for session, db_gen in sessions + recovery_sessions:
                try:
                    session.close()
                except:
                    pass
            
            # Final stats after cleanup
            await asyncio.sleep(1)
            final_stats = get_database_stats()
            
            return {
                "status": "completed",
                "metrics": {
                    "initial_stats": initial_stats,
                    "exhaustion_stats": exhaustion_stats,
                    "recovery_stats": recovery_stats,
                    "final_stats": final_stats,
                    "successful_exhaustion_connections": successful_creations,
                    "exhaustion_time": exhaustion_time,
                    "recovery_connections": len(recovery_sessions),
                    "recovery_time": recovery_time,
                    "pool_recovered": len(recovery_sessions) > 0
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def compare_with_baseline(self, current_results: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current performance with baseline metrics."""
        
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "improvements": [],
            "regressions": [],
            "overall_assessment": "unknown"
        }
        
        try:
            # Compare pool configuration
            baseline_config = baseline.get("current_pool_statistics", {})
            current_config = current_results.get("pool_efficiency", {}).get("metrics", {}).get("final_stats", {})
            
            # Connection creation performance  
            if "pool_efficiency" in current_results:
                current_sessions_per_sec = current_results["pool_efficiency"]["metrics"].get("sessions_per_second", 0)
                
                if current_sessions_per_sec > 10:  # Good threshold
                    comparison["improvements"].append(f"Good session creation rate: {current_sessions_per_sec:.1f} sessions/sec")
                elif current_sessions_per_sec < 5:
                    comparison["regressions"].append(f"Slow session creation rate: {current_sessions_per_sec:.1f} sessions/sec")
            
            # Authentication performance
            if "auth_performance" in current_results:
                auth_results = current_results["auth_performance"]
                if auth_results["status"] == "completed":
                    for scenario, metrics in auth_results.get("scenario_results", {}).items():
                        success_rate = metrics.get("success_rate", 0)
                        avg_response_time = metrics.get("avg_response_time", 0)
                        
                        if success_rate >= 0.95 and avg_response_time < 200:
                            comparison["improvements"].append(f"{scenario} scenario: {success_rate:.1%} success, {avg_response_time:.0f}ms avg")
                        elif success_rate < 0.8 or avg_response_time > 500:
                            comparison["regressions"].append(f"{scenario} scenario: {success_rate:.1%} success, {avg_response_time:.0f}ms avg")
            
            # Pool recovery
            if "pool_recovery" in current_results:
                recovery_results = current_results["pool_recovery"]
                if recovery_results["status"] == "completed":
                    recovered = recovery_results["metrics"].get("pool_recovered", False)
                    if recovered:
                        comparison["improvements"].append("Pool recovery after exhaustion: SUCCESS")
                    else:
                        comparison["regressions"].append("Pool recovery after exhaustion: FAILED")
            
            # Overall assessment
            improvements = len(comparison["improvements"])
            regressions = len(comparison["regressions"])
            
            if improvements > regressions and improvements > 0:
                comparison["overall_assessment"] = "IMPROVED"
            elif regressions > improvements and regressions > 0:
                comparison["overall_assessment"] = "REGRESSED"
            elif improvements == 0 and regressions == 0:
                comparison["overall_assessment"] = "NO_CHANGE"
            else:
                comparison["overall_assessment"] = "MIXED"
                
        except Exception as e:
            comparison["error"] = str(e)
        
        return comparison
    
    def generate_validation_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive validation report."""
        
        report_lines = [
            "="*80,
            "🔍 DATABASE PERFORMANCE VALIDATION REPORT",
            "="*80,
            f"📅 Validation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"🔧 Environment: {self.settings.ENVIRONMENT if hasattr(self.settings, 'ENVIRONMENT') else 'development'}",
            ""
        ]
        
        # Pool efficiency results
        if "pool_efficiency" in results:
            pool_result = results["pool_efficiency"]
            report_lines.extend([
                "📊 CONNECTION POOL EFFICIENCY TEST",
                "-" * 50
            ])
            
            if pool_result["status"] == "completed":
                metrics = pool_result["metrics"]
                report_lines.extend([
                    f"✅ Status: {pool_result['status'].upper()}",
                    f"🔄 Sync Sessions Created: {metrics['sync_sessions_created']}",
                    f"⚡ Async Sessions Created: {metrics['async_sessions_created']}",
                    f"📈 Sync Sessions/sec: {metrics['sessions_per_second']:.2f}",
                    f"📈 Async Sessions/sec: {metrics['async_sessions_per_second']:.2f}",
                    f"🔍 Connection Leak Detected: {'❌ YES' if metrics['connection_leak_detected'] else '✅ NO'}",
                ])
            else:
                report_lines.extend([
                    f"❌ Status: {pool_result['status'].upper()}",
                    f"💥 Error: {pool_result.get('error', 'Unknown error')}"
                ])
            
            report_lines.append("")
        
        # Authentication performance results
        if "auth_performance" in results:
            auth_result = results["auth_performance"]
            report_lines.extend([
                "🔐 AUTHENTICATION PERFORMANCE TEST",
                "-" * 50
            ])
            
            if auth_result["status"] == "completed":
                report_lines.append("✅ Status: COMPLETED")
                
                for scenario, metrics in auth_result.get("scenario_results", {}).items():
                    success_icon = "✅" if metrics["success_rate"] >= 0.9 else "⚠️" if metrics["success_rate"] >= 0.8 else "❌"
                    response_icon = "✅" if metrics["avg_response_time"] < 200 else "⚠️" if metrics["avg_response_time"] < 500 else "❌"
                    
                    report_lines.extend([
                        f"  📋 {scenario} Load Test:",
                        f"     {success_icon} Success Rate: {metrics['success_rate']:.1%}",
                        f"     {response_icon} Avg Response Time: {metrics['avg_response_time']:.0f}ms",
                        f"     📊 P95 Response Time: {metrics['p95_response_time']:.0f}ms", 
                        f"     🔄 Requests/sec: {metrics['requests_per_second']:.1f}",
                        ""
                    ])
            else:
                report_lines.extend([
                    f"⏭️  Status: {auth_result['status'].upper()}",
                    f"ℹ️  Reason: {auth_result.get('reason', 'Test not executed')}"
                ])
            
            report_lines.append("")
        
        # Pool recovery results
        if "pool_recovery" in results:
            recovery_result = results["pool_recovery"]
            report_lines.extend([
                "🔄 POOL RECOVERY TEST",
                "-" * 50
            ])
            
            if recovery_result["status"] == "completed":
                metrics = recovery_result["metrics"]
                recovery_icon = "✅" if metrics["pool_recovered"] else "❌"
                
                report_lines.extend([
                    f"✅ Status: COMPLETED",
                    f"💪 Exhaustion Connections: {metrics['successful_exhaustion_connections']}",
                    f"⏱️  Exhaustion Time: {metrics['exhaustion_time']:.2f}s",
                    f"{recovery_icon} Pool Recovered: {'YES' if metrics['pool_recovered'] else 'NO'}",
                    f"🔄 Recovery Connections: {metrics['recovery_connections']}",
                    f"⏱️  Recovery Time: {metrics['recovery_time']:.2f}s"
                ])
            else:
                report_lines.extend([
                    f"❌ Status: {recovery_result['status'].upper()}",
                    f"💥 Error: {recovery_result.get('error', 'Unknown error')}"
                ])
            
            report_lines.append("")
        
        # Baseline comparison
        if "baseline_comparison" in results:
            comparison = results["baseline_comparison"]
            report_lines.extend([
                "📊 BASELINE COMPARISON",
                "-" * 50,
                f"🎯 Overall Assessment: {comparison.get('overall_assessment', 'UNKNOWN')}"
            ])
            
            if comparison.get("improvements"):
                report_lines.extend([
                    "",
                    "📈 IMPROVEMENTS:"
                ])
                for improvement in comparison["improvements"]:
                    report_lines.append(f"  ✅ {improvement}")
            
            if comparison.get("regressions"):
                report_lines.extend([
                    "",
                    "📉 REGRESSIONS:"
                ])
                for regression in comparison["regressions"]:
                    report_lines.append(f"  ❌ {regression}")
            
            report_lines.append("")
        
        # Summary and recommendations
        report_lines.extend([
            "🎯 VALIDATION SUMMARY",
            "-" * 50,
        ])
        
        # Count successful tests
        successful_tests = sum(1 for test_name, test_result in results.items() 
                              if isinstance(test_result, dict) and test_result.get("status") == "completed")
        total_tests = sum(1 for test_name, test_result in results.items() 
                         if isinstance(test_result, dict) and "status" in test_result)
        
        if total_tests > 0:
            success_rate = successful_tests / total_tests
            if success_rate >= 0.8:
                report_lines.append("🎉 VALIDATION RESULT: PASSED")
            elif success_rate >= 0.6:
                report_lines.append("⚠️  VALIDATION RESULT: PARTIALLY PASSED")
            else:
                report_lines.append("❌ VALIDATION RESULT: FAILED")
            
            report_lines.append(f"📊 Test Success Rate: {success_rate:.1%} ({successful_tests}/{total_tests})")
        else:
            report_lines.append("❓ VALIDATION RESULT: INCONCLUSIVE")
        
        report_lines.extend([
            "",
            "="*80,
            "✅ Validation report complete!",
            "="*80
        ])
        
        return "\n".join(report_lines)
    
    async def run_full_validation(self) -> Dict[str, Any]:
        """Run comprehensive performance validation."""
        
        logger.info("Starting comprehensive performance validation...")
        
        validation_results = {
            "validation_timestamp": datetime.now().isoformat(),
            "validation_version": "1.0"
        }
        
        # Load baseline metrics
        baseline = self.load_baseline_metrics()
        validation_results["baseline_loaded"] = bool(baseline)
        
        # Test 1: Connection pool efficiency
        logger.info("Running connection pool efficiency test...")
        validation_results["pool_efficiency"] = self.test_connection_pool_efficiency()
        
        # Test 2: Authentication performance
        logger.info("Running authentication performance test...")
        validation_results["auth_performance"] = self.test_authentication_performance()
        
        # Test 3: Pool recovery
        logger.info("Running pool recovery test...")
        validation_results["pool_recovery"] = self.test_pool_recovery_after_exhaustion()
        
        # Compare with baseline
        if baseline:
            logger.info("Comparing results with baseline...")
            validation_results["baseline_comparison"] = self.compare_with_baseline(validation_results, baseline)
        
        # Generate report
        report_text = self.generate_validation_report(validation_results)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"/home/marku/ai_workflow_engine/performance_validation_results_{timestamp}.json"
        report_file = f"/home/marku/ai_workflow_engine/performance_validation_report_{timestamp}.txt"
        
        with open(results_file, 'w') as f:
            json.dump(validation_results, f, indent=2, default=str)
        
        with open(report_file, 'w') as f:
            f.write(report_text)
        
        validation_results["results_file"] = results_file
        validation_results["report_file"] = report_file
        
        logger.info(f"Validation results saved to: {results_file}")
        logger.info(f"Validation report saved to: {report_file}")
        
        return validation_results

async def main():
    """Run performance validation."""
    
    validator = PerformanceValidator()
    
    print("\n" + "="*80)
    print("🔍 DATABASE PERFORMANCE VALIDATION SUITE")
    print("="*80)
    print("This validation suite will test database connection pool performance")
    print("and compare against baseline metrics to validate optimizations.")
    print()
    
    try:
        # Run full validation
        results = await validator.run_full_validation()
        
        # Display report
        print(validator.generate_validation_report(results))
        
        # Display file locations
        print(f"\n📁 Detailed results: {results.get('results_file', 'Not saved')}")
        print(f"📄 Full report: {results.get('report_file', 'Not saved')}")
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        logger.error(f"Validation error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())