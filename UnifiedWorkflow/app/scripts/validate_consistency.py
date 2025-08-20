#!/usr/bin/env python3
"""
Script to validate frontend-backend data field consistency.
"""

import sys
import json
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.validation.frontend_backend_consistency import validate_consistency

def main():
    """Run consistency validation and display results."""
    print("🔍 Validating frontend-backend data field consistency...")
    print("=" * 60)
    
    try:
        report = validate_consistency()
        
        # Display summary
        print(f"📊 VALIDATION SUMMARY")
        print(f"   Timestamp: {report.validation_timestamp}")
        print(f"   Total Issues: {report.total_issues}")
        print(f"   Compliance Score: {report.compliance_score:.2%}")
        print()
        
        # Display issues by severity
        print("🚨 ISSUES BY SEVERITY")
        for severity, count in report.issues_by_severity.items():
            if count > 0:
                emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}
                print(f"   {emoji.get(severity.value, '•')} {severity.value.upper()}: {count}")
        print()
        
        # Display specific issues
        if report.issues:
            print("📋 DETAILED ISSUES")
            for i, issue in enumerate(report.issues, 1):
                severity_emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}
                print(f"{i}. {severity_emoji.get(issue.severity.value, '•')} {issue.field_name}")
                print(f"   Type: {issue.issue_type}")
                print(f"   Description: {issue.description}")
                if issue.frontend_expectation:
                    print(f"   Frontend: {issue.frontend_expectation}")
                if issue.backend_implementation:
                    print(f"   Backend: {issue.backend_implementation}")
                if issue.suggested_fix:
                    print(f"   Fix: {issue.suggested_fix}")
                print()
        
        # Display recommendations
        if report.recommendations:
            print("💡 RECOMMENDATIONS")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"{i}. {rec}")
            print()
        
        # Generate migration script if needed
        if report.total_issues > 0:
            print("🔧 MIGRATION SCRIPT")
            print("Run the following to generate a migration script:")
            print("   python scripts/generate_migration.py")
            print()
        
        # Return appropriate exit code
        error_count = report.issues_by_severity.get("error", 0) + report.issues_by_severity.get("critical", 0)
        if error_count > 0:
            print(f"❌ Validation failed with {error_count} critical issues")
            return 1
        elif report.total_issues > 0:
            print(f"⚠️  Validation passed with {report.total_issues} warnings")
            return 0
        else:
            print("✅ All data fields are consistent!")
            return 0
            
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())