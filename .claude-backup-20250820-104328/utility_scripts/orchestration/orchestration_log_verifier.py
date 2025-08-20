#!/usr/bin/env python3
"""
Orchestration Log Verification System
Validates that orchestration logs are being generated correctly
Used by orchestration auditor to catch missing/broken logging
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import hashlib

class OrchestrationLogVerifier:
    """Comprehensive verification system for orchestration logging"""
    
    def __init__(self):
        self.base_path = Path("/home/marku/ai_workflow_engine")
        self.logs_dir = self.base_path / ".claude" / "logs"
        
        # Expected log structure
        self.expected_directories = [
            self.logs_dir,
            self.logs_dir / "executions",
            self.logs_dir / "agents", 
            self.logs_dir / "phases",
            self.logs_dir / "validations"
        ]
        
        # Expected log files
        self.expected_main_logs = [
            self.logs_dir / "orchestration_executions.log",
            self.logs_dir / "orchestration_health_monitor.log"
        ]
        
        # Verification results
        self.last_verification = None
        
    def verify_directory_structure(self) -> Dict[str, Any]:
        """Verify that all expected log directories exist"""
        
        directory_check = {
            "timestamp": datetime.utcnow().isoformat(),
            "directories": {}
        }
        
        for directory in self.expected_directories:
            directory_check["directories"][str(directory)] = {
                "exists": directory.exists(),
                "is_directory": directory.is_dir() if directory.exists() else False,
                "file_count": len(list(directory.glob("*"))) if directory.exists() else 0
            }
        
        return directory_check
    
    def verify_main_log_files(self) -> Dict[str, Any]:
        """Verify that main orchestration log files exist and are being updated"""
        
        main_logs_check = {
            "timestamp": datetime.utcnow().isoformat(),
            "main_logs": {}
        }
        
        for log_file in self.expected_main_logs:
            if log_file.exists():
                stat = log_file.stat()
                
                # Check if log was updated recently (within last hour)
                last_modified = datetime.fromtimestamp(stat.st_mtime)
                recently_updated = (datetime.now() - last_modified) < timedelta(hours=1)
                
                main_logs_check["main_logs"][str(log_file)] = {
                    "exists": True,
                    "size_bytes": stat.st_size,
                    "last_modified": last_modified.isoformat(),
                    "recently_updated": recently_updated,
                    "readable": self._check_file_readable(log_file)
                }
            else:
                main_logs_check["main_logs"][str(log_file)] = {
                    "exists": False,
                    "error": "Log file does not exist"
                }
        
        return main_logs_check
    
    def verify_execution_logs(self) -> Dict[str, Any]:
        """Verify execution logs for completeness and integrity"""
        
        executions_dir = self.logs_dir / "executions"
        execution_check = {
            "timestamp": datetime.utcnow().isoformat(),
            "executions_directory_exists": executions_dir.exists(),
            "execution_logs": [],
            "summary_files": [],
            "recent_executions": 0,
            "orphaned_logs": []
        }
        
        if not executions_dir.exists():
            execution_check["error"] = "Executions directory does not exist"
            return execution_check
        
        # Find execution logs
        execution_logs = list(executions_dir.glob("exec_*.log"))
        summary_files = list(executions_dir.glob("exec_*_summary.json"))
        
        execution_check["execution_logs"] = [str(log) for log in execution_logs]
        execution_check["summary_files"] = [str(summary) for summary in summary_files]
        
        # Count recent executions (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for log in execution_logs:
            if log.stat().st_mtime > cutoff_time.timestamp():
                execution_check["recent_executions"] += 1
        
        # Find orphaned logs (logs without corresponding summaries)
        log_ids = {log.stem for log in execution_logs}
        summary_ids = {summary.stem.replace('_summary', '') for summary in summary_files}
        
        orphaned = log_ids - summary_ids
        execution_check["orphaned_logs"] = list(orphaned)
        
        return execution_check
    
    def verify_agent_logs(self) -> Dict[str, Any]:
        """Verify agent-specific logs"""
        
        agents_dir = self.logs_dir / "agents"
        agent_check = {
            "timestamp": datetime.utcnow().isoformat(),
            "agents_directory_exists": agents_dir.exists(),
            "agent_logs": [],
            "active_agents": set(),
            "recent_activity": 0
        }
        
        if not agents_dir.exists():
            agent_check["error"] = "Agents directory does not exist"
            return agent_check
        
        # Find agent logs
        agent_logs = list(agents_dir.glob("*.log"))
        agent_check["agent_logs"] = [str(log) for log in agent_logs]
        
        # Extract active agents from filenames
        for log in agent_logs:
            # Format: exec_TIMESTAMP_HASH_agent_name.log
            parts = log.stem.split('_')
            if len(parts) >= 4:
                agent_name = '_'.join(parts[3:])  # Join remaining parts as agent name
                agent_check["active_agents"].add(agent_name)
        
        agent_check["active_agents"] = list(agent_check["active_agents"])
        
        # Count recent agent activity (last hour)
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        for log in agent_logs:
            if log.stat().st_mtime > cutoff_time.timestamp():
                agent_check["recent_activity"] += 1
        
        return agent_check
    
    def verify_validation_logs(self) -> Dict[str, Any]:
        """Verify validation logs for orchestration auditing"""
        
        validations_dir = self.logs_dir / "validations"
        validation_check = {
            "timestamp": datetime.utcnow().isoformat(),
            "validations_directory_exists": validations_dir.exists(),
            "validation_logs": [],
            "recent_validations": 0,
            "validation_summary": {}
        }
        
        if not validations_dir.exists():
            validation_check["error"] = "Validations directory does not exist"
            return validation_check
        
        # Find validation logs
        validation_logs = list(validations_dir.glob("*_validations.log"))
        validation_check["validation_logs"] = [str(log) for log in validation_logs]
        
        # Count recent validations
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        for log in validation_logs:
            if log.stat().st_mtime > cutoff_time.timestamp():
                validation_check["recent_validations"] += 1
                
                # Try to parse validation results from recent logs
                try:
                    validation_results = self._parse_validation_log(log)
                    validation_check["validation_summary"][str(log)] = validation_results
                except Exception as e:
                    validation_check["validation_summary"][str(log)] = {"error": str(e)}
        
        return validation_check
    
    def verify_log_content_integrity(self) -> Dict[str, Any]:
        """Verify that log content is properly formatted and complete"""
        
        integrity_check = {
            "timestamp": datetime.utcnow().isoformat(),
            "log_format_compliance": {},
            "content_integrity": {},
            "corruption_detected": False
        }
        
        # Check main orchestration log
        main_log = self.logs_dir / "orchestration_executions.log"
        
        if main_log.exists():
            integrity_check["log_format_compliance"][str(main_log)] = self._check_log_format(main_log)
        
        # Check recent execution logs
        executions_dir = self.logs_dir / "executions"
        
        if executions_dir.exists():
            recent_logs = [log for log in executions_dir.glob("exec_*.log") 
                          if (datetime.now() - datetime.fromtimestamp(log.stat().st_mtime)) < timedelta(hours=24)]
            
            for log in recent_logs[-5:]:  # Check last 5 recent logs
                integrity_check["log_format_compliance"][str(log)] = self._check_log_format(log)
        
        # Determine if any corruption was detected
        integrity_check["corruption_detected"] = any(
            result.get("has_corruption", False) 
            for result in integrity_check["log_format_compliance"].values()
        )
        
        return integrity_check
    
    def generate_comprehensive_verification_report(self) -> Dict[str, Any]:
        """Generate comprehensive verification report for orchestration auditor"""
        
        verification_report = {
            "verification_id": hashlib.md5(f"{datetime.utcnow().isoformat()}".encode()).hexdigest(),
            "timestamp": datetime.utcnow().isoformat(),
            "verifier": "orchestration-log-verifier",
            "directory_structure": self.verify_directory_structure(),
            "main_log_files": self.verify_main_log_files(),
            "execution_logs": self.verify_execution_logs(),
            "agent_logs": self.verify_agent_logs(),
            "validation_logs": self.verify_validation_logs(),
            "content_integrity": self.verify_log_content_integrity()
        }
        
        # Calculate overall health score
        verification_report["overall_health"] = self._calculate_health_score(verification_report)
        
        # Store verification result
        self.last_verification = verification_report
        
        # Save verification report
        report_file = self.logs_dir / f"log_verification_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(verification_report, f, indent=2)
        
        return verification_report
    
    def _check_file_readable(self, file_path: Path) -> bool:
        """Check if a file is readable"""
        try:
            with open(file_path, 'r') as f:
                f.read(1)  # Try to read one character
            return True
        except Exception:
            return False
    
    def _check_log_format(self, log_file: Path) -> Dict[str, Any]:
        """Check log file format compliance"""
        
        format_check = {
            "file_path": str(log_file),
            "readable": True,
            "line_count": 0,
            "properly_formatted_lines": 0,
            "malformed_lines": 0,
            "has_corruption": False,
            "sample_lines": []
        }
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                format_check["line_count"] = len(lines)
                
                for i, line in enumerate(lines):
                    # Check for basic timestamp format
                    if line.startswith('[') and '] [' in line:
                        format_check["properly_formatted_lines"] += 1
                    else:
                        format_check["malformed_lines"] += 1
                        
                        # Collect sample of malformed lines
                        if len(format_check["sample_lines"]) < 5:
                            format_check["sample_lines"].append({
                                "line_number": i + 1,
                                "content": line.strip()[:100]  # First 100 chars
                            })
                
                # Detect corruption
                if format_check["malformed_lines"] > format_check["line_count"] * 0.1:  # More than 10% malformed
                    format_check["has_corruption"] = True
                    
        except Exception as e:
            format_check.update({
                "readable": False,
                "error": str(e),
                "has_corruption": True
            })
        
        return format_check
    
    def _parse_validation_log(self, log_file: Path) -> Dict[str, Any]:
        """Parse validation log to extract validation results"""
        
        validation_summary = {
            "total_validations": 0,
            "passed_validations": 0,
            "failed_validations": 0,
            "validators": set()
        }
        
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    if "VALIDATION PASSED" in line or "VALIDATION FAILED" in line:
                        validation_summary["total_validations"] += 1
                        
                        if "VALIDATION PASSED" in line:
                            validation_summary["passed_validations"] += 1
                        else:
                            validation_summary["failed_validations"] += 1
                        
                        # Extract validator name
                        if "] [" in line:
                            parts = line.split("] [")
                            if len(parts) >= 3:
                                validator = parts[2].split("]")[0]
                                validation_summary["validators"].add(validator)
            
            validation_summary["validators"] = list(validation_summary["validators"])
            
        except Exception as e:
            validation_summary["error"] = str(e)
        
        return validation_summary
    
    def _calculate_health_score(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall logging system health score"""
        
        health_score = {
            "score": 100,  # Start with perfect score
            "deductions": [],
            "status": "healthy"
        }
        
        # Check directory structure
        directories = report["directory_structure"]["directories"]
        missing_dirs = sum(1 for info in directories.values() if not info["exists"])
        if missing_dirs > 0:
            deduction = missing_dirs * 10
            health_score["score"] -= deduction
            health_score["deductions"].append(f"Missing directories: -{deduction}")
        
        # Check main log files
        main_logs = report["main_log_files"]["main_logs"]
        missing_main_logs = sum(1 for info in main_logs.values() if not info.get("exists", False))
        if missing_main_logs > 0:
            deduction = missing_main_logs * 15
            health_score["score"] -= deduction
            health_score["deductions"].append(f"Missing main logs: -{deduction}")
        
        # Check recent activity
        recent_executions = report["execution_logs"]["recent_executions"]
        if recent_executions == 0:
            health_score["score"] -= 20
            health_score["deductions"].append("No recent executions: -20")
        
        # Check content integrity
        if report["content_integrity"]["corruption_detected"]:
            health_score["score"] -= 25
            health_score["deductions"].append("Content corruption detected: -25")
        
        # Determine status
        if health_score["score"] >= 80:
            health_score["status"] = "healthy"
        elif health_score["score"] >= 60:
            health_score["status"] = "warning"
        else:
            health_score["status"] = "critical"
        
        return health_score

# Command line interface
if __name__ == "__main__":
    import sys
    
    verifier = OrchestrationLogVerifier()
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        # Quick verification
        print("Running quick log verification...")
        directory_check = verifier.verify_directory_structure()
        main_logs_check = verifier.verify_main_log_files()
        
        print(f"Directory structure: {len([d for d in directory_check['directories'].values() if d['exists']])}/{len(directory_check['directories'])} directories exist")
        print(f"Main logs: {len([l for l in main_logs_check['main_logs'].values() if l.get('exists', False)])}/{len(main_logs_check['main_logs'])} main logs exist")
        
    else:
        # Full comprehensive report
        print("Running comprehensive log verification...")
        report = verifier.generate_comprehensive_verification_report()
        
        print(f"Verification complete. Health score: {report['overall_health']['score']}/100 ({report['overall_health']['status']})")
        
        if report['overall_health']['deductions']:
            print("Issues found:")
            for deduction in report['overall_health']['deductions']:
                print(f"  - {deduction}")
        
        print(f"Full report saved to: {verifier.logs_dir}/log_verification_report_*.json")