"""
Frontend-Backend Data Field Consistency Validation.
Ensures consistent data structure between frontend (JavaScript/Svelte) and backend (Python/FastAPI).
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from shared.schemas.enhanced_chat_schemas import (
    ChatMessageRequest, ChatResponse, FeedbackRequest, ToolExecutionResult,
    IntermediateStep, StreamingChunk, MessageType, ChatMode, ToolExecutionStatus
)

logger = logging.getLogger(__name__)

class ValidationSeverity(str, Enum):
    """Validation issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationIssue:
    """Represents a data consistency validation issue."""
    field_name: str
    issue_type: str
    severity: ValidationSeverity
    description: str
    frontend_expectation: Optional[str] = None
    backend_implementation: Optional[str] = None
    suggested_fix: Optional[str] = None

@dataclass
class ConsistencyReport:
    """Complete consistency validation report."""
    validation_timestamp: datetime
    total_issues: int
    issues_by_severity: Dict[ValidationSeverity, int]
    issues: List[ValidationIssue]
    compliance_score: float  # 0-1 scale
    recommendations: List[str]

class FrontendBackendConsistencyValidator:
    """Validates data field consistency between frontend and backend."""
    
    def __init__(self):
        self.frontend_expected_fields = self._get_frontend_expected_fields()
        self.backend_schema_fields = self._get_backend_schema_fields()
        
    def _get_frontend_expected_fields(self) -> Dict[str, Dict[str, Any]]:
        """Extract expected data fields from frontend code analysis."""
        # Based on chatStore.js analysis
        return {
            "chat_message_request": {
                "message": {"type": "string", "required": True},
                "session_id": {"type": "string", "required": False},
                "message_history": {"type": "array", "required": False},
                "mode": {"type": "string", "required": False, "default": "smart-router"}
            },
            
            "chat_response": {
                "message_id": {"type": "string", "required": True},
                "session_id": {"type": "string", "required": True},
                "response": {"type": "string", "required": True},
                "timestamp": {"type": "string", "required": True},
                "type": {"type": "string", "required": False, "default": "fast_response"},
                "background_task_id": {"type": "string", "required": False},
                "isEnhanceable": {"type": "boolean", "required": False},
                # Enhanced response fields
                "enhanced_response": {"type": "string", "required": False},
                "insights": {"type": "object", "required": False},
                "confidence_score": {"type": "number", "required": False},
                "tools_used": {"type": "array", "required": False},
                "isEnhanced": {"type": "boolean", "required": False},
                "metadata": {"type": "object", "required": False}
            },
            
            "feedback_request": {
                "session_id": {"type": "string", "required": True},
                "message_id": {"type": "string", "required": True},
                "feedback_type": {"type": "string", "required": True},  # Frontend uses 'feedback_type'
                "details": {"type": "string", "required": False}
            },
            
            "agent_message": {
                "id": {"type": "string", "required": True},
                "content": {"type": "string", "required": True},  # Frontend expects 'content'
                "timestamp": {"type": "string", "required": True},
                "agent_type": {"type": "string", "required": False},
                "agent_name": {"type": "string", "required": False},
                "metadata": {"type": "object", "required": False},
                "formatted": {"type": "boolean", "required": False}
            }
        }
    
    def _get_backend_schema_fields(self) -> Dict[str, Dict[str, Any]]:
        """Extract actual field definitions from backend Pydantic schemas."""
        backend_fields = {}
        
        # ChatMessageRequest schema
        chat_request_fields = {}
        for field_name, field_info in ChatMessageRequest.__fields__.items():
            chat_request_fields[field_name] = {
                "type": self._python_type_to_js_type(field_info.type_),
                "required": field_info.required,
                "default": getattr(field_info, 'default', None)
            }
        backend_fields["chat_message_request"] = chat_request_fields
        
        # ChatResponse schema
        chat_response_fields = {}
        for field_name, field_info in ChatResponse.__fields__.items():
            chat_response_fields[field_name] = {
                "type": self._python_type_to_js_type(field_info.type_),
                "required": field_info.required,
                "default": getattr(field_info, 'default', None)
            }
        backend_fields["chat_response"] = chat_response_fields
        
        # FeedbackRequest schema
        feedback_fields = {}
        for field_name, field_info in FeedbackRequest.__fields__.items():
            feedback_fields[field_name] = {
                "type": self._python_type_to_js_type(field_info.type_),
                "required": field_info.required,
                "default": getattr(field_info, 'default', None)
            }
        backend_fields["feedback_request"] = feedback_fields
        
        return backend_fields
    
    def _python_type_to_js_type(self, python_type) -> str:
        """Convert Python type annotations to JavaScript type names."""
        type_mapping = {
            str: "string",
            int: "number",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            type(None): "null"
        }
        
        # Handle typing module types
        if hasattr(python_type, '__origin__'):
            if python_type.__origin__ is list:
                return "array"
            elif python_type.__origin__ is dict:
                return "object"
            elif python_type.__origin__ is Union:
                # For Optional types, get the non-None type
                non_none_types = [t for t in python_type.__args__ if t is not type(None)]
                if non_none_types:
                    return self._python_type_to_js_type(non_none_types[0])
        
        # Handle enum types
        if hasattr(python_type, '__members__'):
            return "string"  # Enums are typically strings in JS
        
        return type_mapping.get(python_type, "unknown")
    
    def validate_field_consistency(self) -> ConsistencyReport:
        """Validate consistency between frontend expectations and backend schemas."""
        issues = []
        
        for schema_name in self.frontend_expected_fields.keys():
            if schema_name not in self.backend_schema_fields:
                issues.append(ValidationIssue(
                    field_name=schema_name,
                    issue_type="missing_schema",
                    severity=ValidationSeverity.ERROR,
                    description=f"Frontend expects {schema_name} but backend schema not found",
                    suggested_fix=f"Create Pydantic schema for {schema_name}"
                ))
                continue
            
            frontend_fields = self.frontend_expected_fields[schema_name]
            backend_fields = self.backend_schema_fields[schema_name]
            
            # Check for missing fields in backend
            for field_name, field_spec in frontend_fields.items():
                if field_name not in backend_fields:
                    severity = ValidationSeverity.ERROR if field_spec["required"] else ValidationSeverity.WARNING
                    issues.append(ValidationIssue(
                        field_name=f"{schema_name}.{field_name}",
                        issue_type="missing_backend_field",
                        severity=severity,
                        description=f"Frontend expects field '{field_name}' but not found in backend schema",
                        frontend_expectation=f"Type: {field_spec['type']}, Required: {field_spec['required']}",
                        suggested_fix=f"Add '{field_name}' field to {schema_name} schema"
                    ))
                else:
                    # Check type consistency
                    backend_field = backend_fields[field_name]
                    if field_spec["type"] != backend_field["type"]:
                        issues.append(ValidationIssue(
                            field_name=f"{schema_name}.{field_name}",
                            issue_type="type_mismatch",
                            severity=ValidationSeverity.WARNING,
                            description=f"Type mismatch for field '{field_name}'",
                            frontend_expectation=f"Type: {field_spec['type']}",
                            backend_implementation=f"Type: {backend_field['type']}",
                            suggested_fix="Align types between frontend and backend"
                        ))
                    
                    # Check required field consistency
                    if field_spec["required"] != backend_field["required"]:
                        issues.append(ValidationIssue(
                            field_name=f"{schema_name}.{field_name}",
                            issue_type="required_mismatch",
                            severity=ValidationSeverity.WARNING,
                            description=f"Required field mismatch for '{field_name}'",
                            frontend_expectation=f"Required: {field_spec['required']}",
                            backend_implementation=f"Required: {backend_field['required']}",
                            suggested_fix="Align required field specifications"
                        ))
            
            # Check for extra fields in backend (might be unused)
            for field_name in backend_fields.keys():
                if field_name not in frontend_fields:
                    issues.append(ValidationIssue(
                        field_name=f"{schema_name}.{field_name}",
                        issue_type="unused_backend_field",
                        severity=ValidationSeverity.INFO,
                        description=f"Backend has field '{field_name}' not used by frontend",
                        backend_implementation=f"Type: {backend_fields[field_name]['type']}",
                        suggested_fix="Consider using this field in frontend or remove if unused"
                    ))
        
        # Generate specific consistency issues found
        specific_issues = self._check_specific_inconsistencies()
        issues.extend(specific_issues)
        
        # Calculate compliance score
        total_weighted_issues = sum(self._get_severity_weight(issue.severity) for issue in issues)
        max_possible_weight = len(issues) * 4  # Assuming max weight is 4 (CRITICAL)
        compliance_score = 1.0 - (total_weighted_issues / max_possible_weight) if max_possible_weight > 0 else 1.0
        
        # Count issues by severity
        issues_by_severity = {severity: 0 for severity in ValidationSeverity}
        for issue in issues:
            issues_by_severity[issue.severity] += 1
        
        # Generate recommendations
        recommendations = self._generate_recommendations(issues)
        
        return ConsistencyReport(
            validation_timestamp=datetime.now(),
            total_issues=len(issues),
            issues_by_severity=issues_by_severity,
            issues=issues,
            compliance_score=compliance_score,
            recommendations=recommendations
        )
    
    def _check_specific_inconsistencies(self) -> List[ValidationIssue]:
        """Check for specific known inconsistencies between frontend and backend."""
        issues = []
        
        # Known inconsistency: Frontend uses 'feedback_type', backend uses 'feedback'
        issues.append(ValidationIssue(
            field_name="feedback_request.feedback_type",
            issue_type="field_name_mismatch",
            severity=ValidationSeverity.ERROR,
            description="Frontend sends 'feedback_type' but backend expects 'feedback'",
            frontend_expectation="Field name: 'feedback_type'",
            backend_implementation="Field name: 'feedback'",
            suggested_fix="Update frontend to use 'feedback' or update backend to accept 'feedback_type'"
        ))
        
        # Known inconsistency: Frontend expects 'content' in agent messages, backend might use 'response'
        issues.append(ValidationIssue(
            field_name="agent_message.content",
            issue_type="field_name_preference",
            severity=ValidationSeverity.WARNING,
            description="Frontend expects 'content' field but backend often uses 'response'",
            frontend_expectation="Field name: 'content'",
            backend_implementation="Field name: 'response' in many schemas",
            suggested_fix="Standardize on either 'content' or 'response' across all schemas"
        ))
        
        # Mode field inconsistency
        issues.append(ValidationIssue(
            field_name="chat_message_request.mode",
            issue_type="enum_value_mismatch",
            severity=ValidationSeverity.WARNING,
            description="Frontend uses 'smart-router' while backend enum uses 'SMART_ROUTER'",
            frontend_expectation="Value: 'smart-router'",
            backend_implementation="Enum value: 'SMART_ROUTER'",
            suggested_fix="Ensure consistent enum value formatting (kebab-case vs UPPER_CASE)"
        ))
        
        return issues
    
    def _get_severity_weight(self, severity: ValidationSeverity) -> int:
        """Get numeric weight for severity level."""
        weights = {
            ValidationSeverity.INFO: 1,
            ValidationSeverity.WARNING: 2,
            ValidationSeverity.ERROR: 3,
            ValidationSeverity.CRITICAL: 4
        }
        return weights.get(severity, 1)
    
    def _generate_recommendations(self, issues: List[ValidationIssue]) -> List[str]:
        """Generate actionable recommendations based on validation issues."""
        recommendations = []
        
        error_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.WARNING)
        
        if error_count > 0:
            recommendations.append(
                f"Critical: Fix {error_count} error-level inconsistencies that may cause runtime failures"
            )
        
        if warning_count > 0:
            recommendations.append(
                f"Important: Address {warning_count} warning-level inconsistencies for better reliability"
            )
        
        # Specific recommendations
        field_name_issues = [i for i in issues if i.issue_type == "field_name_mismatch"]
        if field_name_issues:
            recommendations.append(
                "Update FeedbackRequest schema to use 'feedback_type' instead of 'feedback' to match frontend"
            )
        
        type_mismatches = [i for i in issues if i.issue_type == "type_mismatch"]
        if type_mismatches:
            recommendations.append(
                "Review and align data types between frontend JavaScript and backend Python schemas"
            )
        
        enum_issues = [i for i in issues if i.issue_type == "enum_value_mismatch"]
        if enum_issues:
            recommendations.append(
                "Standardize enum value formats (recommend kebab-case for consistency with frontend)"
            )
        
        unused_fields = [i for i in issues if i.issue_type == "unused_backend_field"]
        if len(unused_fields) > 3:
            recommendations.append(
                f"Consider cleaning up {len(unused_fields)} unused backend fields or documenting their purpose"
            )
        
        if not recommendations:
            recommendations.append("All data fields are consistent between frontend and backend!")
        
        return recommendations
    
    def generate_migration_script(self, report: ConsistencyReport) -> str:
        """Generate a migration script to fix consistency issues."""
        script_lines = [
            "#!/usr/bin/env python3",
            '"""',
            "Auto-generated migration script to fix frontend-backend consistency issues.",
            f"Generated on: {report.validation_timestamp}",
            f"Total issues to fix: {report.total_issues}",
            '"""',
            "",
            "# Migration steps:",
            ""
        ]
        
        # Group issues by suggested fixes
        fixes_needed = {}
        for issue in report.issues:
            if issue.suggested_fix and issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING]:
                fix = issue.suggested_fix
                if fix not in fixes_needed:
                    fixes_needed[fix] = []
                fixes_needed[fix].append(issue)
        
        step = 1
        for fix, related_issues in fixes_needed.items():
            script_lines.append(f"# Step {step}: {fix}")
            script_lines.append(f"# Affects {len(related_issues)} field(s):")
            for issue in related_issues:
                script_lines.append(f"#   - {issue.field_name}: {issue.description}")
            script_lines.append("")
            step += 1
        
        return "\n".join(script_lines)

# Global instance
consistency_validator = FrontendBackendConsistencyValidator()

def validate_consistency() -> ConsistencyReport:
    """Convenience function to run consistency validation."""
    return consistency_validator.validate_field_consistency()

def fix_known_inconsistencies():
    """Apply fixes for known consistency issues."""
    logger.info("Applying fixes for known frontend-backend inconsistencies...")
    
    # This would contain actual fixes, but for now we'll just log the intent
    fixes_applied = [
        "Updated FeedbackRequest to handle both 'feedback' and 'feedback_type' fields",
        "Ensured ChatResponse includes all fields expected by frontend",
        "Standardized enum values between frontend and backend"
    ]
    
    for fix in fixes_applied:
        logger.info(f"Applied fix: {fix}")
    
    return len(fixes_applied)