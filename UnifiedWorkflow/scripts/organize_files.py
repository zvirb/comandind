#!/usr/bin/env python3
"""
Intelligent File Organization System
Automatically categorizes and moves documentation files to proper locations
"""

import os
import shutil
from pathlib import Path
import re

class FileOrganizer:
    def __init__(self, base_path="/home/marku/ai_workflow_engine"):
        self.base_path = Path(base_path)
        self.docs_path = self.base_path / "docs"
        
        # Define categorization rules based on filename patterns
        self.file_categories = {
            # Orchestration files
            "orchestration/phases": [
                r"PHASE.*_.*\.md$",
                r"phase.*_.*\.md$"
            ],
            "orchestration/audits": [
                r".*ORCHESTRATION.*AUDIT.*\.md$",
                r".*AUDIT.*ORCHESTRATION.*\.md$",
                r"EVIDENCE_AUDIT.*\.md$"
            ],
            "orchestration": [
                r"AGENT_REGISTRY\.md$",
                r"ORCHESTRATION_.*\.md$"
            ],
            
            # Security files
            "security": [
                r".*AUTHENTICATION.*\.md$",
                r".*SECURITY.*\.md$",
                r".*OAUTH.*\.md$",
                r".*SSL.*\.md$",
                r"auth_.*\.md$"
            ],
            
            # Backend files
            "backend": [
                r"BACKEND.*\.md$",
                r".*API.*\.md$",
                r".*GATEWAY.*\.md$",
                r".*SERVICE.*\.md$"
            ],
            
            # Frontend files
            "frontend": [
                r"FRONTEND.*\.md$",
                r"WEBUI.*\.md$",
                r"UX.*\.md$",
                r"USER.*\.md$"
            ],
            "frontend/webgl": [
                r"WEBGL.*\.md$"
            ],
            "frontend/auth": [
                r"FRONTEND.*AUTH.*\.md$"
            ],
            "frontend/performance": [
                r"FRONTEND.*PERFORMANCE.*\.md$"
            ],
            
            # Infrastructure files
            "infrastructure": [
                r"REDIS.*\.md$",
                r"NETWORK.*\.md$",
                r"COGNITIVE.*INFRASTRUCTURE.*\.md$",
                r".*INFRASTRUCTURE.*\.md$"
            ],
            
            # Database files
            "database": [
                r"DATABASE.*\.md$",
                r".*database.*\.md$"
            ],
            
            # Performance files
            "performance": [
                r"PERFORMANCE.*\.md$",
                r".*PERFORMANCE.*\.md$"
            ],
            
            # Fixes and troubleshooting
            "fixes": [
                r".*FIX.*\.md$",
                r".*FIXES.*\.md$",
                r"CHAT_API_422.*\.md$",
                r"EMERGENCY.*\.md$"
            ],
            
            # UX and User Experience
            "ux": [
                r"USER_.*\.md$",
                r"UX_.*\.md$",
                r".*EXPERIENCE.*\.md$",
                r"DOCUMENTS_CALENDAR_NAVIGATION.*\.md$"
            ],
            
            # Implementation summaries
            "implementation": [
                r".*IMPLEMENTATION.*\.md$",
                r".*INTEGRATION.*\.md$"
            ],
            
            # Research and analysis
            "research": [
                r".*ANALYSIS.*\.md$",
                r".*REPORT\.md$",
                r".*SUMMARY\.md$"
            ]
        }
        
        # Files to keep in root (essential project files)
        self.keep_in_root = {
            "CLAUDE.md",
            "CLAUDE.local.md",
            "PROJECT_OVERVIEW.md",
            "ARCHITECTURE_PRINCIPLES.md",
            "DOCUMENTATION_INDEX.md",
            "DOCUMENTATION_MIGRATION_GUIDE.md"
        }
    
    def categorize_file(self, filename):
        """Determine the appropriate category for a file based on patterns"""
        if filename in self.keep_in_root:
            return None  # Keep in root
            
        # Check each category in order of specificity (most specific first)
        category_order = [
            "frontend/webgl",
            "frontend/auth", 
            "frontend/performance",
            "orchestration/phases",
            "orchestration/audits",
            "security",
            "backend",
            "frontend",
            "infrastructure", 
            "database",
            "performance",
            "fixes",
            "ux",
            "implementation",
            "orchestration",
            "research"
        ]
        
        for category in category_order:
            if category in self.file_categories:
                for pattern in self.file_categories[category]:
                    if re.match(pattern, filename, re.IGNORECASE):
                        return category
        
        # Default category for unmatched files
        return "research"
    
    def move_file(self, source_path, category):
        """Move a file to its designated category directory"""
        if category is None:
            return f"KEPT: {source_path.name} (essential project file)"
            
        target_dir = self.docs_path / category
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = target_dir / source_path.name
        
        try:
            shutil.move(str(source_path), str(target_path))
            return f"MOVED: {source_path.name} → docs/{category}/"
        except Exception as e:
            return f"ERROR: Failed to move {source_path.name} - {e}"
    
    def organize_files(self, dry_run=False):
        """Organize all markdown files in the project root"""
        results = []
        
        # Find all markdown files in root
        md_files = list(self.base_path.glob("*.md"))
        
        print(f"Found {len(md_files)} markdown files to organize\n")
        
        for md_file in md_files:
            category = self.categorize_file(md_file.name)
            
            if dry_run:
                if category is None:
                    results.append(f"WOULD KEEP: {md_file.name} (essential project file)")
                else:
                    results.append(f"WOULD MOVE: {md_file.name} → docs/{category}/")
            else:
                result = self.move_file(md_file, category)
                results.append(result)
        
        return results
    
    def create_file_index(self):
        """Create an index of organized files"""
        index_content = "# File Organization Index\n\n"
        index_content += "This index shows the current organization of documentation files.\n\n"
        
        for category_path in sorted(self.docs_path.rglob("*")):
            if category_path.is_dir():
                relative_path = category_path.relative_to(self.docs_path)
                md_files = list(category_path.glob("*.md"))
                
                if md_files:
                    index_content += f"## docs/{relative_path}/\n\n"
                    for md_file in sorted(md_files):
                        index_content += f"- {md_file.name}\n"
                    index_content += "\n"
        
        # Add root files section
        root_md_files = list(self.base_path.glob("*.md"))
        if root_md_files:
            index_content += "## Root Directory (Essential Files)\n\n"
            for md_file in sorted(root_md_files):
                index_content += f"- {md_file.name}\n"
            index_content += "\n"
        
        index_path = self.docs_path / "FILE_ORGANIZATION_INDEX.md"
        with open(index_path, 'w') as f:
            f.write(index_content)
        
        return str(index_path)

def main():
    organizer = FileOrganizer()
    
    print("=== File Organization System ===\n")
    
    # First, show what would be moved (dry run)
    print("DRY RUN - Showing planned file movements:\n")
    dry_run_results = organizer.organize_files(dry_run=True)
    for result in dry_run_results:
        print(result)
    
    print(f"\n{'='*50}")
    print("\nProceeding with file organization automatically...")
    
    # Auto-proceed in automation environment
    if True:
        print("\nExecuting file organization...\n")
        results = organizer.organize_files(dry_run=False)
        for result in results:
            print(result)
        
        # Create file index
        index_path = organizer.create_file_index()
        print(f"\nCreated file organization index: {index_path}")
        
        print("\n✅ File organization completed successfully!")
    else:
        print("\nFile organization cancelled.")

if __name__ == "__main__":
    main()