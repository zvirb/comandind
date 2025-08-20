#!/usr/bin/env python3
"""
File Placement Guard System
Prevents root directory clutter by automatically organizing misplaced files
"""

import os
import sys
import shutil
from pathlib import Path
import re
from datetime import datetime

class FilePlacementGuard:
    def __init__(self, base_path="/home/marku/ai_workflow_engine"):
        self.base_path = Path(base_path)
        self.docs_path = self.base_path / "docs"
        
        # Files that should stay in root
        self.allowed_root_files = {
            "CLAUDE.md",
            "CLAUDE.local.md", 
            "PROJECT_OVERVIEW.md",
            "ARCHITECTURE_PRINCIPLES.md",
            "DOCUMENTATION_INDEX.md",
            "DOCUMENTATION_MIGRATION_GUIDE.md",
            "README.md",
            "LICENSE",
            "CONTRIBUTING.md",
            ".gitignore",
            "docker-compose.yml",  # Main docker compose
            "docker-compose.override.yml",  # Main override
            "requirements.txt",  # Main requirements
            "pyproject.toml",
            "poetry.lock",
            "pytest.ini",
            "pylint.conf",
            "alembic.ini",
            "local.env",
            "local.env.template"
        }
        
        # File extensions that should never be in root (except allowed files)
        self.restricted_extensions = {
            ".md", ".txt", ".json", ".yaml", ".yml", 
            ".log", ".csv", ".xml", ".html"
        }
        
        # Categorization patterns
        self.category_patterns = {
            # Docker and infrastructure configs
            "infrastructure/docker": [
                r"docker-compose.*\.yml$", r"docker-compose.*\.yaml$", 
                r"Dockerfile.*$", r"\.dockerignore$"
            ],
            
            # Log files
            "logs": [
                r".*\.log$", r".*_log\.txt$", r"validation_.*\.log$"
            ],
            
            # Test and validation files
            "testing": [
                r"test.*\.html$", r"test.*\.json$", r".*test.*\.py$",
                r"validation_.*\.json$", r".*validation.*\.log$",
                r"simple_test\.json$", r"response\.json$"
            ],
            
            # Configuration files
            "config": [
                r".*\.json$", r".*\.yaml$", r".*\.yml$", r".*\.ini$",
                r".*config.*\.", r"prometheus_.*\.yml$"
            ],
            
            # Temporary/working files
            "temp": [
                r"cookies\.txt$", r"emergency_.*\.html$", r"backend_csrf\.json$"
            ],
            
            # Security validation results
            "security/validation": [
                r"security_validation_results.*\.json$", r"auth_.*\.json$"
            ],
            
            # Markdown documentation (existing patterns)
            "orchestration/phases": [r"PHASE.*_.*\.md$", r"phase.*_.*\.md$"],
            "orchestration/audits": [r".*ORCHESTRATION.*AUDIT.*\.md$", r".*AUDIT.*ORCHESTRATION.*\.md$", r"EVIDENCE_AUDIT.*\.md$"],
            "orchestration": [r"AGENT_REGISTRY\.md$", r"ORCHESTRATION_.*\.md$"],
            "security": [r".*AUTHENTICATION.*\.md$", r".*SECURITY.*\.md$", r".*OAUTH.*\.md$", r".*SSL.*\.md$", r"auth_.*\.md$"],
            "backend": [r"BACKEND.*\.md$", r".*API.*\.md$", r".*GATEWAY.*\.md$", r".*SERVICE.*\.md$"],
            "frontend/webgl": [r"WEBGL.*\.md$"],
            "frontend/auth": [r"FRONTEND.*AUTH.*\.md$"],
            "frontend/performance": [r"FRONTEND.*PERFORMANCE.*\.md$"],
            "frontend": [r"FRONTEND.*\.md$", r"WEBUI.*\.md$", r"UX.*\.md$", r"USER.*\.md$"],
            "infrastructure": [r"REDIS.*\.md$", r"NETWORK.*\.md$", r".*INFRASTRUCTURE.*\.md$"],
            "database": [r"DATABASE.*\.md$", r".*database.*\.md$"],
            "performance": [r"PERFORMANCE.*\.md$", r".*PERFORMANCE.*\.md$"],
            "fixes": [r".*FIX.*\.md$", r".*FIXES.*\.md$", r"EMERGENCY.*\.md$"],
            "ux": [r"USER_.*\.md$", r"UX_.*\.md$", r".*EXPERIENCE.*\.md$"],
            "implementation": [r".*IMPLEMENTATION.*\.md$", r".*INTEGRATION.*\.md$"],
            "research": [r".*ANALYSIS.*\.md$", r".*REPORT\.md$", r".*SUMMARY\.md$"]
        }
    
    def categorize_file(self, filename):
        """Determine category for a file"""
        if filename in self.allowed_root_files:
            return None  # Keep in root
            
        # Check patterns in order of specificity
        category_order = [
            "security/validation", "infrastructure/docker", "logs", 
            "testing", "temp", "config",
            "frontend/webgl", "frontend/auth", "frontend/performance",
            "orchestration/phases", "orchestration/audits", 
            "security", "backend", "frontend", "infrastructure",
            "database", "performance", "fixes", "ux", 
            "implementation", "orchestration", "research"
        ]
        
        for category in category_order:
            if category in self.category_patterns:
                for pattern in self.category_patterns[category]:
                    if re.match(pattern, filename, re.IGNORECASE):
                        return category
        
        return "research"  # Default category
    
    def scan_root_directory(self):
        """Scan for misplaced files in root directory"""
        misplaced_files = []
        
        for file_path in self.base_path.iterdir():
            if file_path.is_file():
                filename = file_path.name
                
                # Skip allowed files and non-restricted extensions
                if filename in self.allowed_root_files:
                    continue
                    
                # Check if file extension is restricted
                if any(filename.endswith(ext) for ext in self.restricted_extensions):
                    if filename not in self.allowed_root_files:
                        category = self.categorize_file(filename)
                        misplaced_files.append((file_path, category))
        
        return misplaced_files
    
    def auto_organize_file(self, file_path, category):
        """Automatically move a misplaced file to its proper location"""
        if category is None:
            return f"KEPT: {file_path.name} (allowed in root)"
            
        target_dir = self.docs_path / category
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = target_dir / file_path.name
        
        try:
            shutil.move(str(file_path), str(target_path))
            return f"AUTO-MOVED: {file_path.name} → docs/{category}/"
        except Exception as e:
            return f"ERROR: Failed to move {file_path.name} - {e}"
    
    def create_placement_report(self, actions):
        """Create a report of placement actions"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.base_path / f"file_placement_report_{timestamp}.log"
        
        with open(report_path, 'w') as f:
            f.write(f"File Placement Guard Report - {datetime.now()}\n")
            f.write("=" * 50 + "\n\n")
            
            for action in actions:
                f.write(f"{action}\n")
        
        return report_path
    
    def run_guard(self, auto_fix=False):
        """Run the file placement guard"""
        misplaced_files = self.scan_root_directory()
        
        if not misplaced_files:
            return "✅ No misplaced files found in root directory"
        
        actions = []
        
        for file_path, category in misplaced_files:
            if auto_fix:
                result = self.auto_organize_file(file_path, category)
                actions.append(result)
            else:
                actions.append(f"FOUND: {file_path.name} → should be in docs/{category}/")
        
        if auto_fix:
            report_path = self.create_placement_report(actions)
            return f"✅ Auto-organized {len(misplaced_files)} files. Report: {report_path}"
        else:
            return f"📋 Found {len(misplaced_files)} misplaced files:\n" + "\n".join(actions)

def main():
    """Main entry point"""
    guard = FilePlacementGuard()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--auto-fix":
        result = guard.run_guard(auto_fix=True)
    else:
        result = guard.run_guard(auto_fix=False)
    
    print(result)

if __name__ == "__main__":
    main()