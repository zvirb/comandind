#!/usr/bin/env python3
"""
Evidence Validation Tool
Practical tool for validating agent success claims with evidence
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import workflow_enforcement


class EvidenceValidator:
    """Practical evidence validation for agent success claims"""
    
    def __init__(self):
        self.enforcer = workflow_enforcement.WorkflowEnforcer()
        self.validation_dir = Path(".claude/evidence").resolve()
        self.validation_dir.mkdir(parents=True, exist_ok=True)
        
        # Track validation sessions
        self.current_session = None
        self.validated_claims = {}
        
    def start_validation_session(self, session_name):
        """Start a new evidence validation session"""
        timestamp = datetime.now().isoformat()
        
        self.current_session = {
            "session_name": session_name,
            "started": timestamp,
            "claims_validated": 0,
            "claims_failed": 0,
            "validation_results": {}
        }
        
        print(f"🔍 Starting evidence validation session: {session_name}")
        return session_name
    
    def validate_claim(self, agent_name, claim_description, claim_type, evidence_files=None, evidence_data=None):
        """Validate a single agent success claim with evidence"""
        if not self.current_session:
            raise Exception("No active validation session. Call start_validation_session() first.")
        
        timestamp = datetime.now().isoformat()
        
        print(f"\n📋 Validating claim from {agent_name}")
        print(f"   Claim: {claim_description}")
        print(f"   Type: {claim_type}")
        
        # Require evidence through enforcement system
        evidence_req = self.enforcer.require_evidence(agent_name, claim_type, claim_description)
        
        if evidence_req["status"] == "evidence_not_required":
            # Simple validation for non-critical claims
            validation_result = {
                "agent": agent_name,
                "claim": claim_description,
                "claim_type": claim_type,
                "timestamp": timestamp,
                "status": "accepted_no_evidence_required",
                "evidence_required": False
            }
            
            self.current_session["claims_validated"] += 1
            self.current_session["validation_results"][agent_name] = validation_result
            
            print("   ✅ Claim accepted (no evidence required)")
            return validation_result
        
        # Evidence is required
        required_types = evidence_req["evidence_types"]
        print(f"   📋 Evidence required: {', '.join(required_types)}")
        
        # Collect evidence data
        collected_evidence = {}
        
        if evidence_files:
            for evidence_type, file_path in evidence_files.items():
                if os.path.exists(file_path):
                    collected_evidence[evidence_type] = f"file:{file_path}"
                    print(f"   📄 Evidence file found: {evidence_type} -> {file_path}")
                else:
                    print(f"   ⚠️ Evidence file missing: {evidence_type} -> {file_path}")
        
        if evidence_data:
            for evidence_type, data in evidence_data.items():
                collected_evidence[evidence_type] = data
                print(f"   📊 Evidence data provided: {evidence_type}")
        
        # Validate evidence through enforcement system
        requirement_id = evidence_req["requirement_id"]
        validation_result = self.enforcer.validate_evidence(requirement_id, collected_evidence)
        
        if validation_result["status"] == "validated":
            print("   ✅ Evidence validated - Claim ACCEPTED")
            
            self.current_session["claims_validated"] += 1
            self.current_session["validation_results"][agent_name] = {
                "agent": agent_name,
                "claim": claim_description,
                "claim_type": claim_type,
                "timestamp": timestamp,
                "status": "validated",
                "evidence_provided": list(collected_evidence.keys()),
                "evidence_required": required_types,
                "requirement_id": requirement_id
            }
            
            return {"status": "validated", "agent": agent_name}
        
        elif validation_result["status"] == "insufficient":
            missing = validation_result["missing"]
            print(f"   ❌ Evidence insufficient - Missing: {', '.join(missing)}")
            print("   🚫 Claim REJECTED")
            
            self.current_session["claims_failed"] += 1
            self.current_session["validation_results"][agent_name] = {
                "agent": agent_name,
                "claim": claim_description,
                "claim_type": claim_type,
                "timestamp": timestamp,
                "status": "rejected_insufficient_evidence",
                "evidence_provided": list(collected_evidence.keys()),
                "evidence_required": required_types,
                "missing_evidence": missing,
                "requirement_id": requirement_id
            }
            
            return {"status": "rejected", "missing": missing, "agent": agent_name}
    
    def validate_authentication_fix(self, agent_name, claim_description, 
                                  live_test_results=None, screenshot_evidence=None, integration_test=None):
        """Specialized validation for authentication fixes"""
        evidence_files = {}
        evidence_data = {}
        
        if live_test_results:
            if isinstance(live_test_results, str) and os.path.exists(live_test_results):
                evidence_files["live_test_results"] = live_test_results
            else:
                evidence_data["live_test_results"] = str(live_test_results)
        
        if screenshot_evidence and os.path.exists(screenshot_evidence):
            evidence_files["screenshot_evidence"] = screenshot_evidence
        
        if integration_test:
            if isinstance(integration_test, str) and os.path.exists(integration_test):
                evidence_files["integration_test"] = integration_test
            else:
                evidence_data["integration_test"] = str(integration_test)
        
        return self.validate_claim(
            agent_name, claim_description, "authentication_fix",
            evidence_files=evidence_files, evidence_data=evidence_data
        )
    
    def validate_performance_improvement(self, agent_name, claim_description,
                                       benchmark_results=None, before_after_metrics=None, automated_test=None):
        """Specialized validation for performance improvements"""
        evidence_files = {}
        evidence_data = {}
        
        if benchmark_results:
            if isinstance(benchmark_results, str) and os.path.exists(benchmark_results):
                evidence_files["benchmark_results"] = benchmark_results
            else:
                evidence_data["benchmark_results"] = str(benchmark_results)
        
        if before_after_metrics:
            evidence_data["before_after_metrics"] = str(before_after_metrics)
        
        if automated_test:
            if isinstance(automated_test, str) and os.path.exists(automated_test):
                evidence_files["automated_test"] = automated_test
            else:
                evidence_data["automated_test"] = str(automated_test)
        
        return self.validate_claim(
            agent_name, claim_description, "performance_improvement",
            evidence_files=evidence_files, evidence_data=evidence_data
        )
    
    def complete_validation_session(self):
        """Complete validation session and generate report"""
        if not self.current_session:
            print("⚠️ No active validation session to complete")
            return None
        
        timestamp = datetime.now().isoformat()
        self.current_session["completed"] = timestamp
        
        # Generate validation report
        total_claims = self.current_session["claims_validated"] + self.current_session["claims_failed"]
        success_rate = self.current_session["claims_validated"] / total_claims if total_claims > 0 else 0
        
        self.current_session["total_claims"] = total_claims
        self.current_session["success_rate"] = success_rate
        
        # Save validation report
        report_file = self.validation_dir / f"validation_report_{self.current_session['session_name']}_{timestamp.replace(':', '').replace('-', '').replace('.', '')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.current_session, f, indent=2)
        
        print(f"\n📊 Validation session completed: {self.current_session['session_name']}")
        print(f"   Total claims evaluated: {total_claims}")
        print(f"   Claims validated: {self.current_session['claims_validated']}")
        print(f"   Claims rejected: {self.current_session['claims_failed']}")
        print(f"   Success rate: {success_rate:.1%}")
        print(f"   Report saved: {report_file}")
        
        # Reset session
        completed_session = self.current_session
        self.current_session = None
        
        return completed_session
    
    def get_validation_status(self):
        """Get current validation session status"""
        if not self.current_session:
            return {"status": "no_active_session"}
        
        total_claims = self.current_session["claims_validated"] + self.current_session["claims_failed"]
        success_rate = self.current_session["claims_validated"] / total_claims if total_claims > 0 else 0
        
        return {
            "status": "active_session",
            "session_name": self.current_session["session_name"],
            "total_claims": total_claims,
            "validated": self.current_session["claims_validated"],
            "failed": self.current_session["claims_failed"],
            "success_rate": success_rate
        }


# Global validator instance
validator = EvidenceValidator()


# Convenience functions for easy validation
def start_validation(session_name):
    """Start evidence validation session"""
    return validator.start_validation_session(session_name)


def validate_auth_fix(agent_name, claim, live_test=None, screenshot=None, integration=None):
    """Validate authentication fix claim"""
    return validator.validate_authentication_fix(agent_name, claim, live_test, screenshot, integration)


def validate_performance_fix(agent_name, claim, benchmarks=None, metrics=None, tests=None):
    """Validate performance improvement claim"""
    return validator.validate_performance_improvement(agent_name, claim, benchmarks, metrics, tests)


def validate_general_claim(agent_name, claim, claim_type, evidence_files=None, evidence_data=None):
    """Validate general agent claim"""
    return validator.validate_claim(agent_name, claim, claim_type, evidence_files, evidence_data)


def complete_validation():
    """Complete validation session"""
    return validator.complete_validation_session()


def get_validation_status():
    """Get validation status"""
    return validator.get_validation_status()


if __name__ == "__main__":
    print("Testing Evidence Validation Tool...")
    
    # Start validation session
    start_validation("test_validation")
    
    # Test authentication fix validation (should fail - no evidence)
    print("\n1. Testing authentication fix without evidence:")
    result1 = validate_auth_fix("test-agent", "Fixed authentication system")
    
    # Test authentication fix validation with evidence
    print("\n2. Testing authentication fix with evidence:")
    result2 = validate_auth_fix(
        "test-agent-2", 
        "Fixed authentication system with proper validation",
        live_test="Authentication test passed - login works correctly",
        integration="End-to-end auth flow verified"
        # Missing screenshot evidence - should fail
    )
    
    # Test performance improvement
    print("\n3. Testing performance improvement with full evidence:")
    result3 = validate_performance_fix(
        "performance-agent",
        "Optimized API response times by 80%",
        benchmarks="Before: 500ms, After: 100ms average response",
        metrics="80% improvement in response time metrics",
        tests="Automated performance tests all passing"
    )
    
    # Complete validation
    report = complete_validation()
    
    print("\n✅ Evidence validation tool test completed")