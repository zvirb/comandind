#!/usr/bin/env python3
"""
Memory Service Migration Script

Migrates existing markdown files to memory MCP service entities.
Removes the anti-pattern of documentation clutter in project root.

Features:
- Scans for markdown files in project
- Categorizes by content and filename
- Migrates to appropriate memory entity types
- Preserves file metadata and history
- Validates migration success
- Option to remove original files after migration

Usage:
    python migration_script.py --scan-only          # Just scan and report
    python migration_script.py --migrate           # Migrate files to memory
    python migration_script.py --migrate --cleanup # Migrate and remove originals
"""

import argparse
import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .memory_service_integration import (
    MemoryServiceIntegration,
    MemoryEntityType,
    create_memory_integration_instance
)

logger = logging.getLogger(__name__)


class MarkdownMigrator:
    """
    Migrates existing markdown files to memory MCP service.
    
    Analyzes markdown files, categorizes them appropriately,
    and migrates to structured memory entities.
    """
    
    def __init__(self, mcp_functions: Dict[str, Any], project_root: str):
        """
        Initialize migrator with MCP functions and project root.
        
        Args:
            mcp_functions: Dictionary of MCP function references
            project_root: Root directory of project to scan
        """
        self.project_root = Path(project_root)
        self.mcp_functions = mcp_functions
        self.memory_integration = None
        self.migration_log = []
        
        # Statistics
        self.stats = {
            "files_found": 0,
            "files_migrated": 0,
            "files_skipped": 0,
            "errors": 0,
            "total_size": 0,
            "entity_types": {}
        }
    
    async def initialize(self):
        """Initialize memory integration."""
        self.memory_integration = await create_memory_integration_instance(self.mcp_functions)
        logger.info("Memory integration initialized for migration")
    
    def scan_markdown_files(self, exclude_patterns: Optional[List[str]] = None) -> List[Path]:
        """
        Scan project for markdown files.
        
        Args:
            exclude_patterns: List of path patterns to exclude
            
        Returns:
            List of markdown file paths found
        """
        if exclude_patterns is None:
            exclude_patterns = [
                "*/node_modules/*",
                "*/.git/*",
                "*/venv/*",
                "*/__pycache__/*",
                "*/modelcontextprotocol/*",  # External dependency
                "*/servers/*"  # External dependency
            ]
        
        markdown_files = []
        
        # Find all .md files recursively
        for md_file in self.project_root.rglob("*.md"):
            # Check if file should be excluded
            should_exclude = False
            for pattern in exclude_patterns:
                if md_file.match(pattern):
                    should_exclude = True
                    break
            
            if not should_exclude:
                markdown_files.append(md_file)
        
        self.stats["files_found"] = len(markdown_files)
        logger.info(f"Found {len(markdown_files)} markdown files")
        
        return markdown_files
    
    def categorize_markdown_file(self, file_path: Path) -> Tuple[str, str]:
        """
        Categorize markdown file by content and filename.
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            Tuple of (entity_type, suggested_name)
        """
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            filename = file_path.name.lower()
            content_lower = content.lower()
            
            # Analyze filename patterns
            filename_category = self._categorize_by_filename(filename)
            if filename_category:
                entity_type = filename_category
            else:
                # Analyze content patterns
                entity_type = self._categorize_by_content(content_lower)
            
            # Generate suggested entity name
            suggested_name = self._generate_entity_name(file_path, entity_type)
            
            return entity_type, suggested_name
            
        except Exception as e:
            logger.error(f"Error categorizing file {file_path}: {e}")
            return MemoryEntityType.AGENT_FINDINGS, f"migrated_{file_path.stem}"
    
    def _categorize_by_filename(self, filename: str) -> Optional[str]:
        """Categorize by filename patterns."""
        filename_patterns = {
            # Orchestration and workflow files
            MemoryEntityType.ORCHESTRATION_WORKFLOW: [
                "orchestration", "workflow", "phase", "coordination"
            ],
            
            # Analysis and research files
            MemoryEntityType.AGENT_FINDINGS: [
                "analysis", "research", "findings", "summary", "report"
            ],
            
            # Validation and evidence files
            MemoryEntityType.DEPLOYMENT_EVIDENCE: [
                "validation", "evidence", "proof", "verification", "test"
            ],
            
            # Security files
            MemoryEntityType.SECURITY_VALIDATION: [
                "security", "auth", "vulnerability", "penetration", "audit"
            ],
            
            # Performance files
            MemoryEntityType.PERFORMANCE_METRICS: [
                "performance", "metrics", "benchmark", "optimization", "profiling"
            ],
            
            # Infrastructure files
            MemoryEntityType.INFRASTRUCTURE_ANALYSIS: [
                "infrastructure", "deployment", "docker", "k8s", "monitoring"
            ],
            
            # Configuration files
            MemoryEntityType.SYSTEM_CONFIGURATION: [
                "config", "setup", "installation", "configuration"
            ],
            
            # Error and troubleshooting files
            MemoryEntityType.ERROR_PATTERNS: [
                "error", "bug", "issue", "troubleshoot", "debug", "fix"
            ],
            
            # API documentation
            MemoryEntityType.API_DOCUMENTATION: [
                "api", "endpoint", "swagger", "openapi", "rest"
            ],
            
            # Database files
            MemoryEntityType.DATABASE_SCHEMA: [
                "database", "db", "schema", "migration", "sql"
            ],
            
            # Integration guides
            MemoryEntityType.INTEGRATION_GUIDE: [
                "integration", "guide", "howto", "tutorial", "setup"
            ],
            
            # Decision records
            MemoryEntityType.DECISION_RECORD: [
                "decision", "adr", "architecture", "design"
            ],
            
            # Pattern libraries
            MemoryEntityType.PATTERN_LIBRARY: [
                "pattern", "template", "example", "best_practice"
            ]
        }
        
        for entity_type, patterns in filename_patterns.items():
            for pattern in patterns:
                if pattern in filename:
                    return entity_type
        
        return None
    
    def _categorize_by_content(self, content: str) -> str:
        """Categorize by content analysis."""
        content_patterns = {
            # High priority patterns (check first)
            MemoryEntityType.ORCHESTRATION_WORKFLOW: [
                "orchestration", "phase", "workflow", "agent coordination",
                "step 1", "step 2", "step 3", "agentic flow"
            ],
            
            MemoryEntityType.DEPLOYMENT_EVIDENCE: [
                "validation evidence", "test results", "curl output",
                "health check", "endpoint validation", "production validation"
            ],
            
            MemoryEntityType.SECURITY_VALIDATION: [
                "security scan", "vulnerability", "penetration test",
                "authentication", "authorization", "owasp", "cve"
            ],
            
            MemoryEntityType.PERFORMANCE_METRICS: [
                "performance", "latency", "throughput", "response time",
                "cpu usage", "memory usage", "optimization", "benchmark"
            ],
            
            MemoryEntityType.INFRASTRUCTURE_ANALYSIS: [
                "infrastructure", "deployment", "container", "docker",
                "kubernetes", "monitoring", "prometheus", "grafana"
            ],
            
            MemoryEntityType.ERROR_PATTERNS: [
                "error occurred", "exception", "traceback", "failed",
                "troubleshooting", "debugging", "fix", "solution"
            ],
            
            MemoryEntityType.API_DOCUMENTATION: [
                "api endpoint", "rest api", "http", "json", "swagger",
                "openapi", "request", "response", "curl"
            ],
            
            MemoryEntityType.DATABASE_SCHEMA: [
                "database", "table", "column", "index", "query",
                "postgresql", "sql", "migration", "alembic"
            ],
            
            MemoryEntityType.SYSTEM_CONFIGURATION: [
                "configuration", "config", "environment", "setup",
                "installation", "environment variable"
            ],
            
            # Lower priority patterns
            MemoryEntityType.INTEGRATION_GUIDE: [
                "integration", "guide", "tutorial", "how to",
                "step by step", "instructions"
            ],
            
            MemoryEntityType.DECISION_RECORD: [
                "decision", "architecture decision", "design decision",
                "pros and cons", "alternatives considered"
            ],
            
            MemoryEntityType.PATTERN_LIBRARY: [
                "pattern", "template", "example", "best practice",
                "recommendation", "standard"
            ]
        }
        
        # Score each category
        category_scores = {}
        for entity_type, patterns in content_patterns.items():
            score = 0
            for pattern in patterns:
                score += content.count(pattern)
            if score > 0:
                category_scores[entity_type] = score
        
        # Return highest scoring category
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        # Default to agent findings
        return MemoryEntityType.AGENT_FINDINGS
    
    def _generate_entity_name(self, file_path: Path, entity_type: str) -> str:
        """Generate appropriate entity name from file path."""
        # Clean filename
        name_base = file_path.stem.lower()
        name_base = re.sub(r'[^a-zA-Z0-9_]', '_', name_base)
        name_base = re.sub(r'_+', '_', name_base).strip('_')
        
        # Add timestamp for uniqueness
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        return f"migrated_{name_base}_{timestamp}"
    
    async def migrate_file(
        self,
        file_path: Path,
        entity_type: str,
        entity_name: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Migrate a single markdown file to memory entity.
        
        Args:
            file_path: Path to markdown file
            entity_type: Target entity type
            entity_name: Target entity name
            dry_run: If True, don't actually migrate
            
        Returns:
            Migration result dictionary
        """
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8')
            file_size = len(content)
            
            # Prepare metadata
            metadata = {
                "source_file": str(file_path),
                "original_filename": file_path.name,
                "file_size": file_size,
                "migrated_at": datetime.utcnow().isoformat() + "Z",
                "migration_tool": "memory_service_migration_script",
                "entity_type_determined": entity_type
            }
            
            # Add file stats if available
            try:
                stat = file_path.stat()
                metadata.update({
                    "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat() + "Z",
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z"
                })
            except Exception:
                pass
            
            result = {
                "file_path": str(file_path),
                "entity_name": entity_name,
                "entity_type": entity_type,
                "file_size": file_size,
                "status": "dry_run" if dry_run else "pending"
            }
            
            if not dry_run:
                # Migrate to memory service
                await self.memory_integration.store_orchestration_knowledge(
                    entity_name=entity_name,
                    entity_type=entity_type,
                    content=content,
                    metadata=metadata,
                    tags=["migrated", "markdown", "legacy", entity_type]
                )
                
                result["status"] = "migrated"
                self.stats["files_migrated"] += 1
                
                # Update entity type stats
                if entity_type not in self.stats["entity_types"]:
                    self.stats["entity_types"][entity_type] = 0
                self.stats["entity_types"][entity_type] += 1
            
            self.stats["total_size"] += file_size
            
            # Log migration
            migration_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "migrate",
                "file": str(file_path),
                "entity": entity_name,
                "type": entity_type,
                "size": file_size,
                "dry_run": dry_run
            }
            self.migration_log.append(migration_entry)
            
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrated {file_path} -> {entity_name} ({entity_type})")
            
            return result
            
        except Exception as e:
            self.stats["errors"] += 1
            error_result = {
                "file_path": str(file_path),
                "entity_name": entity_name,
                "entity_type": entity_type,
                "status": "error",
                "error": str(e)
            }
            
            logger.error(f"Failed to migrate {file_path}: {e}")
            return error_result
    
    async def migrate_all_files(
        self,
        markdown_files: List[Path],
        dry_run: bool = False,
        skip_large_files: bool = True,
        max_file_size: int = 1000000  # 1MB
    ) -> List[Dict[str, Any]]:
        """
        Migrate all markdown files to memory entities.
        
        Args:
            markdown_files: List of markdown files to migrate
            dry_run: If True, don't actually migrate
            skip_large_files: If True, skip files larger than max_file_size
            max_file_size: Maximum file size to migrate (bytes)
            
        Returns:
            List of migration results
        """
        results = []
        
        for file_path in markdown_files:
            try:
                # Check file size
                if skip_large_files:
                    file_size = file_path.stat().st_size
                    if file_size > max_file_size:
                        logger.warning(f"Skipping large file: {file_path} ({file_size} bytes)")
                        self.stats["files_skipped"] += 1
                        continue
                
                # Categorize file
                entity_type, entity_name = self.categorize_markdown_file(file_path)
                
                # Migrate file
                result = await self.migrate_file(file_path, entity_type, entity_name, dry_run)
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                self.stats["errors"] += 1
                results.append({
                    "file_path": str(file_path),
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    def cleanup_migrated_files(
        self,
        migration_results: List[Dict[str, Any]],
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Remove original markdown files after successful migration.
        
        Args:
            migration_results: Results from migration process
            confirm: If True, actually delete files
            
        Returns:
            Cleanup results
        """
        cleanup_stats = {
            "files_deleted": 0,
            "files_kept": 0,
            "errors": 0,
            "total_size_freed": 0
        }
        
        for result in migration_results:
            if result.get("status") == "migrated":
                file_path = Path(result["file_path"])
                
                try:
                    if confirm and file_path.exists():
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        cleanup_stats["files_deleted"] += 1
                        cleanup_stats["total_size_freed"] += file_size
                        logger.info(f"Deleted migrated file: {file_path}")
                    else:
                        cleanup_stats["files_kept"] += 1
                        if not confirm:
                            logger.info(f"Would delete: {file_path} (use --confirm to actually delete)")
                        
                except Exception as e:
                    cleanup_stats["errors"] += 1
                    logger.error(f"Failed to delete {file_path}: {e}")
            else:
                cleanup_stats["files_kept"] += 1
        
        return cleanup_stats
    
    def generate_migration_report(
        self,
        migration_results: List[Dict[str, Any]],
        cleanup_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive migration report."""
        report = {
            "migration_timestamp": datetime.utcnow().isoformat() + "Z",
            "project_root": str(self.project_root),
            "statistics": self.stats.copy(),
            "migration_log": self.migration_log.copy(),
            "results_summary": {
                "total_processed": len(migration_results),
                "successful_migrations": len([r for r in migration_results if r.get("status") == "migrated"]),
                "failed_migrations": len([r for r in migration_results if r.get("status") == "error"]),
                "skipped_files": self.stats["files_skipped"]
            },
            "entity_type_distribution": self.stats["entity_types"].copy()
        }
        
        if cleanup_results:
            report["cleanup_results"] = cleanup_results
        
        return report


async def main():
    """Main migration script function."""
    parser = argparse.ArgumentParser(description="Migrate markdown files to memory MCP service")
    parser.add_argument("--project-root", default=".", help="Project root directory to scan")
    parser.add_argument("--scan-only", action="store_true", help="Only scan and report, don't migrate")
    parser.add_argument("--migrate", action="store_true", help="Perform migration to memory service")
    parser.add_argument("--cleanup", action="store_true", help="Remove original files after migration")
    parser.add_argument("--dry-run", action="store_true", help="Test migration without actually migrating")
    parser.add_argument("--output-report", help="Output JSON report to file")
    parser.add_argument("--max-file-size", type=int, default=1000000, help="Maximum file size to migrate (bytes)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Validate arguments
    if not args.scan_only and not args.migrate:
        parser.error("Must specify either --scan-only or --migrate")
    
    if args.cleanup and not args.migrate:
        parser.error("--cleanup can only be used with --migrate")
    
    try:
        # Note: In actual usage, MCP functions would be provided here
        # This is a placeholder for the actual implementation
        print("NOTE: This script requires MCP function initialization")
        print("In actual usage, initialize with:")
        print("  mcp_functions = {...}")
        print("  migrator = MarkdownMigrator(mcp_functions, args.project_root)")
        
        # Simulate the migration process for demonstration
        migrator = MarkdownMigrator({}, args.project_root)
        
        # Scan for markdown files
        markdown_files = migrator.scan_markdown_files()
        
        print(f"\nFound {len(markdown_files)} markdown files in {args.project_root}")
        
        if args.scan_only:
            # Just show what would be migrated
            print("\nMarkdown files found:")
            for file_path in markdown_files[:10]:  # Show first 10
                entity_type, entity_name = migrator.categorize_markdown_file(file_path)
                print(f"  {file_path} -> {entity_name} ({entity_type})")
            
            if len(markdown_files) > 10:
                print(f"  ... and {len(markdown_files) - 10} more files")
        
        else:
            print("Migration would require actual MCP function initialization")
            print("This is a template showing the migration structure")
        
        # Generate example report
        example_report = {
            "migration_timestamp": datetime.utcnow().isoformat() + "Z",
            "project_root": args.project_root,
            "files_found": len(markdown_files),
            "example_categorizations": [
                {
                    "file": str(f),
                    "entity_type": migrator.categorize_markdown_file(f)[0],
                    "entity_name": migrator.categorize_markdown_file(f)[1]
                }
                for f in markdown_files[:5]
            ]
        }
        
        if args.output_report:
            with open(args.output_report, 'w') as f:
                json.dump(example_report, f, indent=2)
            print(f"\nExample report written to: {args.output_report}")
        
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))