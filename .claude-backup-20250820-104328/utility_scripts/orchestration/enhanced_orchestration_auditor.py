#!/usr/bin/env python3
"""
Enhanced Orchestration Auditor with Multi-Layer Validation Framework Integration
Validates orchestration execution with comprehensive evidence-based validation
Prevents false positives through rigorous evidence collection and analysis
"""

import json
import subprocess
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests

# Import the new validation systems
from enhanced_validation_framework import EnhancedValidationFramework
from database_integrity_validator import DatabaseIntegrityValidator
from authenticated_endpoint_tester import AuthenticatedEndpointTester
from evidence_based_validation_system import EvidenceBasedValidationSystem

class EnhancedOrchestrationAuditor:
    """Enhanced auditor that validates both execution and log generation"""
    
    def __init__(self):
        self.base_path = Path("/home/marku/ai_workflow_engine")
        self.logs_dir = self.base_path / ".claude" / "logs"
        
        # Import log verification system
        self.log_verifier_path = self.base_path / "orchestration_log_verifier.py"
        
        # Critical validation endpoints (from user's browser console evidence)
        self.critical_endpoints = {
            "categories_api": "https://aiwfe.com/api/v1/categories",
            "calendar_events_api": "https://aiwfe.com/api/v1/calendar/events", 
            "tasks_api": "https://aiwfe.com/api/v1/tasks"
        }
        
    def audit_orchestration_execution(self, execution_id: str = None) -> Dict[str, Any]:
        """Comprehensive audit of orchestration execution with enhanced multi-layer validation"""
        
        audit_start_time = datetime.utcnow()
        
        # Generate audit ID
        audit_id = f"audit_{audit_start_time.strftime('%Y%m%d_%H%M%S')}"
        
        audit_report = {
            "audit_id": audit_id,
            "audit_timestamp": audit_start_time.isoformat(),
            "auditor": "enhanced-orchestration-auditor-v2",
            "validation_framework": "multi_layer_evidence_based",
            "execution_id_audited": execution_id,
            "log_generation_validation": None,
            "comprehensive_endpoint_validation": None,
            "legacy_endpoint_validation": None,
            "execution_analysis": None,
            "improvement_recommendations": [],
            "overall_assessment": None
        }
        
        # Step 1: Validate log generation (MANDATORY)
        print("🔍 Step 1: Validating orchestration log generation...")
        log_validation = self.validate_log_generation()
        audit_report["log_generation_validation"] = log_validation
        
        if log_validation["health"]["status"] != "healthy":
            audit_report["improvement_recommendations"].append({
                "priority": "CRITICAL",
                "category": "logging_infrastructure",
                "issue": "Orchestration logging system unhealthy",
                "recommendation": "Fix logging infrastructure before proceeding",
                "evidence": log_validation["health"]["deductions"]
            })
        
        # Step 2: Comprehensive Multi-Layer Validation (NEW)
        print("🚀 Step 2: Comprehensive multi-layer validation with evidence-based validation...")
        try:
            # Run async validation in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                comprehensive_validation = loop.run_until_complete(
                    self.validate_critical_endpoints_comprehensive()
                )
                audit_report["comprehensive_endpoint_validation"] = comprehensive_validation
            finally:
                loop.close()
                
        except Exception as e:
            print(f"❌ Comprehensive validation failed: {str(e)}")
            audit_report["comprehensive_endpoint_validation"] = {
                "validation_error": str(e),
                "overall_validation": {"success": False, "confidence": 0.0}
            }
            audit_report["improvement_recommendations"].append({
                "priority": "CRITICAL",
                "category": "validation_system_failure",
                "issue": f"Enhanced validation system failed: {str(e)}",
                "recommendation": "Fix validation framework before proceeding",
                "fallback_used": True
            })
        
        # Step 3: Legacy endpoint validation (for comparison)
        print("🌐 Step 3: Legacy endpoint validation (for comparison)...")
        legacy_validation = self.validate_critical_endpoints()
        audit_report["legacy_endpoint_validation"] = legacy_validation
        
        # Compare comprehensive vs legacy results
        if audit_report.get("comprehensive_endpoint_validation"):
            comp_success = audit_report["comprehensive_endpoint_validation"].get("overall_validation", {}).get("success", False)
            legacy_healthy = legacy_validation["summary"]["healthy_endpoints"]
            legacy_failing = legacy_validation["summary"]["failing_endpoints"]
            
            if comp_success != (legacy_failing == 0):
                audit_report["improvement_recommendations"].append({
                    "priority": "HIGH",
                    "category": "validation_discrepancy",
                    "issue": f"Validation discrepancy: Comprehensive={comp_success}, Legacy={legacy_failing==0}",
                    "recommendation": "Investigate validation methodology differences",
                    "evidence": {
                        "comprehensive_success": comp_success,
                        "legacy_healthy": legacy_healthy,
                        "legacy_failing": legacy_failing
                    }
                })
        
        # Check for persistent HTTP 500 errors (user's original issue)
        persistent_500_errors = []
        if legacy_validation["summary"]["http_500_errors"] > 0:
            persistent_500_errors = [
                endpoint for endpoint, result in legacy_validation["results"].items()
                if result.get("server_error", False)
            ]
            
            audit_report["improvement_recommendations"].append({
                "priority": "CRITICAL", 
                "category": "endpoint_failures",
                "issue": f"HTTP 500 errors persist on {len(persistent_500_errors)} critical endpoints",
                "endpoints": persistent_500_errors,
                "recommendation": "Immediate API service investigation required",
                "user_impact": "User's browser console showing persistent failures",
                "evidence_type": "server_errors"
            })
        
        # Check for authentication failures (previously incorrectly marked as healthy)
        auth_failures = [
            endpoint for endpoint, result in legacy_validation["results"].items()
            if result.get("authentication_failure", False)
        ]
        
        if auth_failures:
            audit_report["improvement_recommendations"].append({
                "priority": "HIGH",
                "category": "authentication_failures", 
                "issue": f"Authentication failures on {len(auth_failures)} endpoints",
                "endpoints": auth_failures,
                "recommendation": "Fix authentication system - 401/403 errors are NOT healthy",
                "previous_false_positive": "These were incorrectly marked as healthy before"
            })
        
        # Step 4: Analyze execution logs if execution ID provided
        if execution_id:
            print(f"📋 Step 4: Analyzing execution logs for {execution_id}...")
            execution_analysis = self.analyze_execution_logs(execution_id)
            audit_report["execution_analysis"] = execution_analysis
            
            if execution_analysis and not execution_analysis["execution_successful"]:
                audit_report["improvement_recommendations"].append({
                    "priority": "HIGH",
                    "category": "execution_failure",
                    "issue": "Orchestration execution failed",
                    "recommendation": "Review execution logs and implement fixes",
                    "evidence": execution_analysis.get("failure_reasons", [])
                })
        
        # Step 5: Generate enhanced overall assessment
        audit_report["overall_assessment"] = self.generate_enhanced_overall_assessment(audit_report)
        
        # Step 6: Save audit report
        audit_file = self.logs_dir / f"orchestration_audit_{audit_id}.json"
        with open(audit_file, 'w') as f:
            json.dump(audit_report, f, indent=2, default=str)
        
        print(f"📊 Enhanced audit complete. Report saved: {audit_file}")
        print(f"🎯 Overall Assessment: {audit_report['overall_assessment']['status']}")
        print(f"📈 Validation Confidence: {audit_report['overall_assessment'].get('evidence_confidence', 0.0):.2f}")
        
        if audit_report['improvement_recommendations']:
            print(f"⚠️  Found {len(audit_report['improvement_recommendations'])} improvement recommendations")
            for rec in audit_report['improvement_recommendations']:
                priority_emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "📝", "LOW": "💡"}.get(rec["priority"], "📝")
                print(f"  {priority_emoji} {rec['priority']}: {rec['issue']}")
        
        return audit_report
    
    def validate_log_generation(self) -> Dict[str, Any]:
        """Validate that orchestration logs are being generated correctly"""
        
        print("🔧 Running log generation verification...")
        
        try:
            # Run the log verification system
            result = subprocess.run([
                "python3", str(self.log_verifier_path)
            ], capture_output=True, text=True, timeout=30)
            
            # Parse the output to extract health information
            output_lines = result.stdout.strip().split('\n')
            
            log_validation = {
                "verifier_executed": True,
                "verifier_exit_code": result.returncode,
                "verification_output": result.stdout,
                "verification_errors": result.stderr,
                "health": {
                    "status": "unknown",
                    "score": 0,
                    "deductions": []
                }
            }
            
            # Extract health score from output
            for line in output_lines:
                if "Health score:" in line:
                    # Parse "Health score: 100/100 (healthy)"
                    parts = line.split("Health score: ")[1]
                    score_part = parts.split(" ")[0]  # "100/100"
                    status_part = parts.split("(")[1].split(")")[0]  # "healthy"
                    
                    log_validation["health"]["score"] = int(score_part.split("/")[0])
                    log_validation["health"]["status"] = status_part
                    break
            
            # Check if log verification report files exist
            verification_reports = list(self.logs_dir.glob("log_verification_report_*.json"))
            
            if verification_reports:
                # Load the latest report
                latest_report = max(verification_reports, key=lambda f: f.stat().st_mtime)
                
                with open(latest_report, 'r') as f:
                    report_data = json.load(f)
                    log_validation["latest_verification_report"] = str(latest_report)
                    log_validation["health"] = report_data.get("overall_health", log_validation["health"])
            
            print(f"✅ Log verification completed: {log_validation['health']['status']} (Score: {log_validation['health']['score']}/100)")
            
            return log_validation
            
        except subprocess.TimeoutExpired:
            return {
                "verifier_executed": False,
                "error": "Log verifier timed out",
                "health": {"status": "critical", "score": 0, "deductions": ["Verifier timeout"]}
            }
        except Exception as e:
            return {
                "verifier_executed": False, 
                "error": str(e),
                "health": {"status": "critical", "score": 0, "deductions": [f"Verifier error: {str(e)}"]}
            }
    
    async def validate_critical_endpoints_comprehensive(self) -> Dict[str, Any]:
        """Comprehensive multi-layer validation of critical endpoints"""
        
        print("🔍 Running comprehensive multi-layer endpoint validation...")
        
        # Configuration for enhanced validation
        validation_config = {
            'database_url': 'postgresql://ai_workflow:password@postgres:5432/ai_workflow_engine?sslmode=require',
            'redis_url': 'redis://redis:6379',
            'evidence_path': '.claude/logs/validation_evidence',
            'critical_endpoints': self.critical_endpoints,
            'jwt_secret': 'test_secret_key_for_development'
        }
        
        comprehensive_results = {
            "validation_timestamp": datetime.utcnow().isoformat(),
            "validation_framework": "enhanced_multi_layer",
            "surface_validation": {},
            "authentication_validation": {},
            "database_validation": {}, 
            "evidence_validation": {},
            "overall_validation": {}
        }
        
        try:
            # 1. Enhanced Multi-Layer Framework Validation
            print("  📋 Running enhanced validation framework...")
            framework = EnhancedValidationFramework(validation_config)
            framework_report = await framework.execute_full_validation()
            comprehensive_results["surface_validation"] = framework_report
            
            # 2. Database Integrity Validation
            print("  🗄️  Running database integrity validation...")
            db_validator = DatabaseIntegrityValidator(validation_config['database_url'])
            db_report = await db_validator.validate_database_integrity()
            comprehensive_results["database_validation"] = {
                "overall_success": db_report.overall_success,
                "critical_issues": db_report.critical_issues,
                "validation_results_count": len(db_report.validation_results),
                "execution_time_ms": db_report.execution_time_ms
            }
            
            # 3. Authenticated Endpoint Testing
            print("  🔐 Running authenticated endpoint testing...")
            auth_tester = AuthenticatedEndpointTester(validation_config)
            auth_report = await auth_tester.test_all_endpoints()
            comprehensive_results["authentication_validation"] = {
                "overall_success": auth_report.overall_success,
                "endpoints_passed": auth_report.endpoints_passed,
                "endpoints_failed": auth_report.endpoints_failed,
                "authentication_issues": auth_report.authentication_issues,
                "critical_findings": auth_report.critical_findings
            }
            
            # 4. Evidence-Based Validation
            print("  📊 Running evidence-based validation...")
            evidence_data = {
                "overall_assessment": framework_report.get("overall_assessment", {}),
                "critical_endpoint_validation": {"results": {}},
                "database_validation": {"connection_successful": db_report.overall_success},
                "error_analysis": await self._get_current_error_analysis()
            }
            
            # Extract endpoint results for evidence validation
            if framework_report.get("layer_results", {}).get("surface"):
                surface_results = framework_report["layer_results"]["surface"]
                for test_result in surface_results.get("test_results", []):
                    endpoint_name = test_result.get("test_name", "unknown")
                    evidence_data["critical_endpoint_validation"]["results"][endpoint_name] = {
                        "status_code": 200 if test_result.get("success") else 500,
                        "healthy": test_result.get("success", False),
                        "user_console_match": not test_result.get("success", True)
                    }
            
            evidence_system = EvidenceBasedValidationSystem(validation_config)
            evidence_report = await evidence_system.validate_with_evidence(evidence_data)
            comprehensive_results["evidence_validation"] = {
                "overall_validation_confidence": evidence_report.overall_validation_confidence,
                "assertions_validated": evidence_report.assertions_validated,
                "assertions_failed": evidence_report.assertions_failed,
                "critical_evidence_gaps": evidence_report.critical_evidence_gaps,
                "false_positive_risks": evidence_report.false_positive_risks
            }
            
            # 5. Overall Assessment
            overall_success = all([
                framework_report.get("overall_assessment", {}).get("success", False),
                db_report.overall_success,
                auth_report.overall_success,
                evidence_report.overall_validation_confidence > 0.8
            ])
            
            comprehensive_results["overall_validation"] = {
                "success": overall_success,
                "confidence": evidence_report.overall_validation_confidence,
                "validation_layers_passed": sum([
                    1 if framework_report.get("overall_assessment", {}).get("success") else 0,
                    1 if db_report.overall_success else 0,
                    1 if auth_report.overall_success else 0,
                    1 if evidence_report.overall_validation_confidence > 0.8 else 0
                ]),
                "total_validation_layers": 4,
                "prevents_false_positives": len(evidence_report.false_positive_risks) == 0
            }
            
            print(f"  ✅ Comprehensive validation complete - Overall success: {overall_success}")
            print(f"  📊 Evidence confidence: {evidence_report.overall_validation_confidence:.2f}")
            
        except Exception as e:
            print(f"  ❌ Comprehensive validation failed: {str(e)}")
            comprehensive_results["validation_error"] = str(e)
            comprehensive_results["overall_validation"] = {
                "success": False,
                "confidence": 0.0,
                "error": str(e)
            }
        
        return comprehensive_results
    
    async def _get_current_error_analysis(self) -> Dict[str, Any]:
        """Get current error analysis from logs"""
        try:
            error_log_path = Path("logs/error_summary.log")
            if error_log_path.exists():
                with open(error_log_path, 'r') as f:
                    content = f.read()
                
                # Extract current error count
                current_count = 0
                if "ERROR:" in content:
                    for line in content.split('\n'):
                        if line.startswith("ERROR:"):
                            parts = line.split()
                            if len(parts) > 1:
                                current_count = int(parts[1])
                                break
                
                return {
                    "current_error_count": current_count,
                    "previous_error_count": 34205,  # From previous logs
                    "error_count_reduced": current_count < 34205
                }
            
        except Exception:
            pass
        
        return {
            "current_error_count": 0,
            "previous_error_count": 0,
            "error_count_reduced": False
        }

    def validate_critical_endpoints(self) -> Dict[str, Any]:
        """Legacy endpoint validation - kept for backwards compatibility"""
        
        endpoint_validation = {
            "validation_timestamp": datetime.utcnow().isoformat(),
            "endpoints_tested": len(self.critical_endpoints),
            "results": {},
            "summary": {
                "healthy_endpoints": 0,
                "failing_endpoints": 0,
                "http_500_errors": 0
            }
        }
        
        for endpoint_name, url in self.critical_endpoints.items():
            print(f"🌐 Testing {endpoint_name}: {url}")
            
            try:
                response = requests.get(url, timeout=10)
                
                # CRITICAL: Fix false positive logic - 401 is NOT healthy!
                is_healthy = response.status_code == 200
                is_auth_failure = response.status_code in [401, 403]
                is_server_error = response.status_code >= 500
                
                endpoint_result = {
                    "url": url,
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "healthy": is_healthy,
                    "authentication_failure": is_auth_failure,
                    "server_error": is_server_error,
                    "user_console_match": is_server_error,  # Only server errors match user evidence
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if is_healthy:
                    endpoint_validation["summary"]["healthy_endpoints"] += 1
                    print(f"  ✅ {endpoint_name}: HTTP {response.status_code}")
                else:
                    endpoint_validation["summary"]["failing_endpoints"] += 1
                    if is_server_error:
                        endpoint_validation["summary"]["http_500_errors"] += 1
                        print(f"  ❌ {endpoint_name}: HTTP {response.status_code} (SERVER ERROR - matches user console)")
                    elif is_auth_failure:
                        print(f"  🔐 {endpoint_name}: HTTP {response.status_code} (AUTH FAILURE - not healthy)")
                    else:
                        print(f"  ⚠️  {endpoint_name}: HTTP {response.status_code} (CLIENT ERROR)")
                
            except Exception as e:
                endpoint_result = {
                    "url": url,
                    "healthy": False,
                    "connection_error": True,
                    "error": str(e),
                    "user_console_match": True,  # Connection errors also match user evidence
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                endpoint_validation["summary"]["failing_endpoints"] += 1
                print(f"  ❌ {endpoint_name}: {str(e)}")
            
            endpoint_validation["results"][endpoint_name] = endpoint_result
        
        return endpoint_validation
    
    def analyze_execution_logs(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Analyze specific orchestration execution logs"""
        
        execution_log = self.logs_dir / "executions" / f"{execution_id}.log"
        execution_summary = self.logs_dir / "executions" / f"{execution_id}_summary.json"
        
        if not execution_log.exists():
            return {
                "execution_found": False,
                "error": f"Execution log not found: {execution_log}"
            }
        
        analysis = {
            "execution_found": True,
            "execution_id": execution_id,
            "log_file": str(execution_log),
            "summary_file": str(execution_summary) if execution_summary.exists() else None,
            "execution_successful": False,
            "phases_completed": 0,
            "phases_failed": 0,
            "validation_results": {"passed": 0, "failed": 0},
            "failure_reasons": [],
            "execution_duration": None
        }
        
        # Parse execution log
        try:
            with open(execution_log, 'r') as f:
                log_content = f.read()
                
                # Count phases
                analysis["phases_completed"] = log_content.count("COMPLETED")
                analysis["phases_failed"] = log_content.count("FAILED")
                
                # Count validations
                analysis["validation_results"]["passed"] = log_content.count("VALIDATION PASSED")
                analysis["validation_results"]["failed"] = log_content.count("VALIDATION FAILED")
                
                # Check overall success
                if "ORCHESTRATION COMPLETED SUCCESSFULLY" in log_content:
                    analysis["execution_successful"] = True
                elif "ORCHESTRATION FAILED" in log_content:
                    analysis["execution_successful"] = False
                    
                    # Extract failure reasons from log
                    for line in log_content.split('\n'):
                        if "[ERROR]" in line or "FAILED" in line:
                            analysis["failure_reasons"].append(line.strip())
        
        except Exception as e:
            analysis["log_parse_error"] = str(e)
        
        # Parse summary file if available
        if analysis["summary_file"] and Path(analysis["summary_file"]).exists():
            try:
                with open(analysis["summary_file"], 'r') as f:
                    summary_data = json.load(f)
                    analysis["execution_duration"] = summary_data.get("duration_seconds")
                    analysis["execution_successful"] = summary_data.get("success", False)
            except Exception as e:
                analysis["summary_parse_error"] = str(e)
        
        return analysis
    
    def generate_enhanced_overall_assessment(self, audit_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enhanced overall assessment with evidence-based confidence scoring"""
        
        assessment = {
            "status": "healthy",
            "evidence_confidence": 0.0,
            "validation_methodology": "enhanced_multi_layer",
            "prevents_false_positives": True,
            "critical_issues_count": 0,
            "major_concerns": [],
            "system_recommendations": [],
            "validation_layers": {
                "logging_system": "unknown",
                "comprehensive_validation": "unknown",
                "legacy_validation": "unknown",
                "evidence_validation": "unknown"
            }
        }
        
        # Evaluate logging system health
        log_health = audit_report["log_generation_validation"]["health"]
        assessment["validation_layers"]["logging_system"] = log_health["status"]
        
        if log_health["status"] == "critical":
            assessment["status"] = "critical"
            assessment["evidence_confidence"] = 0.0
            assessment["critical_issues_count"] += 1
            assessment["major_concerns"].append("Orchestration logging system is critical")
        elif log_health["status"] == "warning":
            assessment["evidence_confidence"] = max(0.0, assessment["evidence_confidence"] - 0.2)
            assessment["major_concerns"].append("Orchestration logging system has warnings")
        else:
            assessment["evidence_confidence"] += 0.25  # 25% confidence from logging
        
        # Evaluate comprehensive validation results
        comp_validation = audit_report.get("comprehensive_endpoint_validation", {})
        if comp_validation.get("validation_error"):
            assessment["validation_layers"]["comprehensive_validation"] = "failed"
            assessment["status"] = "critical"
            assessment["evidence_confidence"] = 0.0
            assessment["critical_issues_count"] += 1
            assessment["major_concerns"].append("Enhanced validation system failed")
            assessment["prevents_false_positives"] = False
        else:
            overall_validation = comp_validation.get("overall_validation", {})
            comp_success = overall_validation.get("success", False)
            comp_confidence = overall_validation.get("confidence", 0.0)
            
            assessment["validation_layers"]["comprehensive_validation"] = "passed" if comp_success else "failed"
            
            if comp_success and comp_confidence > 0.8:
                assessment["evidence_confidence"] += comp_confidence * 0.5  # Up to 50% from comprehensive validation
            else:
                assessment["status"] = "degraded" if assessment["status"] != "critical" else "critical"
                assessment["major_concerns"].append(f"Comprehensive validation failed or low confidence ({comp_confidence:.2f})")
                if comp_confidence < 0.5:
                    assessment["critical_issues_count"] += 1
        
        # Evaluate legacy validation (for comparison and fallback)
        legacy_validation = audit_report["legacy_endpoint_validation"]
        legacy_500_errors = legacy_validation["summary"]["http_500_errors"]
        legacy_auth_failures = sum(1 for result in legacy_validation["results"].values() 
                                  if result.get("authentication_failure", False))
        
        assessment["validation_layers"]["legacy_validation"] = "passed" if legacy_500_errors == 0 else "failed"
        
        if legacy_500_errors > 0:
            assessment["status"] = "critical"
            assessment["evidence_confidence"] = 0.0  # Cannot claim success with server errors
            assessment["critical_issues_count"] += 1
            assessment["major_concerns"].append(
                f"HTTP 500 errors on {legacy_500_errors} critical endpoints (user evidence confirmed)"
            )
        
        if legacy_auth_failures > 0:
            if assessment["status"] == "healthy":
                assessment["status"] = "degraded"
            assessment["evidence_confidence"] = max(0.0, assessment["evidence_confidence"] - 0.1)
            assessment["major_concerns"].append(
                f"Authentication failures on {legacy_auth_failures} endpoints (401/403 are NOT healthy)"
            )
        
        # Evidence validation layer
        evidence_validation = comp_validation.get("evidence_validation", {})
        if evidence_validation:
            evidence_confidence = evidence_validation.get("overall_validation_confidence", 0.0)
            false_positive_risks = evidence_validation.get("false_positive_risks", [])
            critical_gaps = evidence_validation.get("critical_evidence_gaps", [])
            
            assessment["validation_layers"]["evidence_validation"] = "passed" if evidence_confidence > 0.7 else "failed"
            
            if false_positive_risks:
                assessment["status"] = "critical"
                assessment["evidence_confidence"] = 0.0
                assessment["critical_issues_count"] += 1
                assessment["major_concerns"].append(
                    f"False positive risks detected: {len(false_positive_risks)} validation inconsistencies"
                )
                assessment["prevents_false_positives"] = False
            
            if critical_gaps:
                if assessment["status"] == "healthy":
                    assessment["status"] = "degraded"
                assessment["evidence_confidence"] = max(0.0, assessment["evidence_confidence"] - 0.2)
                assessment["major_concerns"].append(
                    f"Critical evidence gaps: {len(critical_gaps)} validation claims lack evidence"
                )
        
        # Final confidence adjustment based on overall status
        if assessment["status"] == "critical":
            assessment["evidence_confidence"] = 0.0
        elif assessment["status"] == "degraded":
            assessment["evidence_confidence"] = min(assessment["evidence_confidence"], 0.6)
        
        # Generate system recommendations
        if assessment["critical_issues_count"] > 0:
            assessment["system_recommendations"].append(
                "CRITICAL: Immediate intervention required - cannot claim system health with active failures"
            )
        
        if legacy_500_errors > 0:
            assessment["system_recommendations"].append(
                "CRITICAL: Resolve API service failures before claiming orchestration success"
            )
        
        if legacy_auth_failures > 0:
            assessment["system_recommendations"].append(
                "HIGH: Fix authentication system - 401/403 responses indicate system problems"
            )
        
        if assessment["evidence_confidence"] < 0.8:
            assessment["system_recommendations"].append(
                "MEDIUM: Improve validation evidence collection to increase confidence"
            )
        
        if not assessment["prevents_false_positives"]:
            assessment["system_recommendations"].append(
                "CRITICAL: False positive prevention failed - validation claims may be incorrect"
            )
        
        # Success criteria (very strict)
        if (assessment["critical_issues_count"] == 0 and 
            assessment["evidence_confidence"] >= 0.8 and 
            assessment["prevents_false_positives"]):
            assessment["system_recommendations"].append(
                "All validation layers passed with high evidence confidence - system appears healthy"
            )
        
        return assessment

    def generate_overall_assessment(self, audit_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall assessment of orchestration system health"""
        
        assessment = {
            "status": "healthy",
            "confidence": 100,
            "critical_issues_count": 0,
            "major_concerns": [],
            "system_recommendations": []
        }
        
        # Check log generation health
        log_health = audit_report["log_generation_validation"]["health"]
        
        if log_health["status"] == "critical":
            assessment["status"] = "critical"
            assessment["confidence"] -= 40
            assessment["critical_issues_count"] += 1
            assessment["major_concerns"].append("Orchestration logging system is critical")
        elif log_health["status"] == "warning":
            assessment["confidence"] -= 20
            assessment["major_concerns"].append("Orchestration logging system has warnings")
        
        # Check endpoint validation
        endpoint_validation = audit_report["critical_endpoint_validation"]
        
        if endpoint_validation["summary"]["http_500_errors"] > 0:
            assessment["status"] = "critical"
            assessment["confidence"] -= 50
            assessment["critical_issues_count"] += 1
            assessment["major_concerns"].append(
                f"HTTP 500 errors on {endpoint_validation['summary']['http_500_errors']} critical endpoints (user evidence confirmed)"
            )
        
        # Check execution analysis if available
        if audit_report["execution_analysis"]:
            exec_analysis = audit_report["execution_analysis"]
            
            if not exec_analysis.get("execution_successful", True):
                if assessment["status"] != "critical":
                    assessment["status"] = "degraded"
                assessment["confidence"] -= 30
                assessment["major_concerns"].append("Recent orchestration execution failed")
        
        # Generate system recommendations
        if assessment["critical_issues_count"] > 0:
            assessment["system_recommendations"].append(
                "Immediate intervention required - critical issues detected"
            )
        
        if endpoint_validation["summary"]["http_500_errors"] > 0:
            assessment["system_recommendations"].append(
                "Investigate and resolve API service failures - user's browser console evidence confirmed"
            )
        
        if log_health["score"] < 100:
            assessment["system_recommendations"].append(
                "Strengthen orchestration logging infrastructure"
            )
        
        # Never claim success if user evidence shows failures
        if endpoint_validation["summary"]["http_500_errors"] > 0:
            assessment["prevents_false_success_claims"] = True
            assessment["user_evidence_validated"] = True
        
        return assessment
    
    def generate_improvement_plan(self, audit_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate concrete improvement plan based on audit findings"""
        
        improvement_plan = {
            "plan_id": f"improvement_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "created": datetime.utcnow().isoformat(),
            "based_on_audit": audit_report["audit_id"],
            "priority_actions": [],
            "infrastructure_improvements": [],
            "monitoring_enhancements": [],
            "validation_strengthening": []
        }
        
        # Generate priority actions based on recommendations
        for rec in audit_report["improvement_recommendations"]:
            if rec["priority"] == "CRITICAL":
                improvement_plan["priority_actions"].append({
                    "action": rec["recommendation"],
                    "category": rec["category"],
                    "timeline": "immediate",
                    "evidence": rec.get("evidence", [])
                })
        
        # Infrastructure improvements
        if audit_report["log_generation_validation"]["health"]["status"] != "healthy":
            improvement_plan["infrastructure_improvements"].append(
                "Implement robust orchestration logging infrastructure with health monitoring"
            )
        
        # Monitoring enhancements
        if audit_report["critical_endpoint_validation"]["summary"]["http_500_errors"] > 0:
            improvement_plan["monitoring_enhancements"].append(
                "Implement real-time endpoint monitoring with automated failure detection"
            )
        
        # Validation strengthening
        improvement_plan["validation_strengthening"].append(
            "Mandatory evidence-based validation before claiming orchestration success"
        )
        improvement_plan["validation_strengthening"].append(
            "Cross-reference orchestration claims with actual user-facing functionality"
        )
        
        # Save improvement plan
        plan_file = self.logs_dir / f"orchestration_improvement_plan_{improvement_plan['plan_id']}.json"
        
        with open(plan_file, 'w') as f:
            json.dump(improvement_plan, f, indent=2)
        
        print(f"📋 Improvement plan generated: {plan_file}")
        
        return improvement_plan

# Command line interface
if __name__ == "__main__":
    import sys
    
    auditor = EnhancedOrchestrationAuditor()
    
    if len(sys.argv) > 1:
        execution_id = sys.argv[1]
        print(f"Auditing specific execution: {execution_id}")
        audit_report = auditor.audit_orchestration_execution(execution_id)
    else:
        print("Running comprehensive orchestration system audit...")
        audit_report = auditor.audit_orchestration_execution()
    
    # Generate improvement plan if issues found
    if audit_report["improvement_recommendations"]:
        improvement_plan = auditor.generate_improvement_plan(audit_report)
        print(f"📈 Improvement plan created with {len(improvement_plan['priority_actions'])} priority actions")