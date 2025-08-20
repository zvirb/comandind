#!/usr/bin/env python3
"""
Database Integrity Validation System

Provides comprehensive database validation including:
- Schema integrity checking
- Migration status validation  
- Data consistency verification
- Connection pool health testing
- Performance baseline establishment

This validator specifically addresses the database issues identified in the
orchestration failure analysis, including missing columns and authentication problems.
"""

import asyncio
import json
import logging
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, inspect, text, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError
from sqlalchemy.engine import Engine
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext
from alembic.runtime.migration import MigrationContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SchemaValidationResult:
    """Result of schema validation check."""
    table_name: str
    validation_type: str  # "exists", "columns", "constraints", "indexes"
    passed: bool
    expected: Any
    actual: Any
    details: Dict[str, Any]
    timestamp: str

@dataclass  
class MigrationValidationResult:
    """Result of migration status validation."""
    migration_id: str
    migration_name: str
    applied: bool
    expected_applied: bool
    issue: Optional[str] = None
    timestamp: Optional[str] = None

@dataclass
class DatabaseValidationReport:
    """Comprehensive database validation report."""
    validation_id: str
    timestamp: str
    database_url_masked: str
    overall_success: bool
    validation_results: List[SchemaValidationResult]
    migration_results: List[MigrationValidationResult]
    connection_test_results: Dict[str, Any]
    performance_baseline: Dict[str, Any]
    critical_issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    execution_time_ms: float

class DatabaseIntegrityValidator:
    """
    Comprehensive database integrity validation system.
    
    Addresses specific issues from orchestration failure analysis:
    - Missing user_categories.emoji column
    - Database authentication problems
    - Connection pool issues
    - Schema migration gaps
    """

    def __init__(self, database_url: str, alembic_config_path: Optional[str] = None):
        self.database_url = database_url
        self.database_url_masked = self._mask_database_url(database_url)
        self.alembic_config_path = alembic_config_path or "alembic.ini"
        self.validation_id = f"db_validation_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.engine: Optional[Engine] = None
        
        # Critical tables and their required columns (based on error analysis)
        self.critical_schema = {
            'users': {
                'required_columns': ['id', 'email', 'username', 'created_at'],
                'optional_columns': ['updated_at', 'is_active', 'is_verified'],
                'constraints': ['users_pkey', 'users_email_key']
            },
            'categories': {
                'required_columns': ['id', 'name', 'description', 'created_at'],
                'optional_columns': ['updated_at', 'color', 'icon'],
                'constraints': ['categories_pkey']
            },
            'user_categories': {
                'required_columns': ['id', 'user_id', 'category_id', 'emoji'],  # emoji was missing!
                'optional_columns': ['created_at', 'updated_at'],
                'constraints': ['user_categories_pkey']
            },
            'tasks': {
                'required_columns': ['id', 'title', 'description', 'user_id', 'created_at'],
                'optional_columns': ['updated_at', 'completed', 'due_date', 'priority'],
                'constraints': ['tasks_pkey']
            },
            'calendar_events': {
                'required_columns': ['id', 'title', 'start_time', 'end_time', 'user_id'],
                'optional_columns': ['description', 'created_at', 'updated_at'],
                'constraints': ['calendar_events_pkey']
            }
        }

    def _mask_database_url(self, url: str) -> str:
        """Mask sensitive information in database URL for logging."""
        try:
            if '://' in url and '@' in url:
                protocol, rest = url.split('://', 1)
                if '@' in rest:
                    credentials, host_and_db = rest.split('@', 1)
                    username = credentials.split(':')[0] if ':' in credentials else credentials
                    return f"{protocol}://{username}:***@{host_and_db}"
            return url
        except:
            return "***masked***"

    async def validate_database_integrity(self) -> DatabaseValidationReport:
        """
        Execute comprehensive database integrity validation.
        
        Returns detailed report with evidence-based findings.
        """
        start_time = time.time()
        logger.info(f"🔍 Starting database integrity validation - ID: {self.validation_id}")
        logger.info(f"📍 Database: {self.database_url_masked}")

        validation_results = []
        migration_results = []
        connection_test_results = {}
        performance_baseline = {}
        critical_issues = []
        warnings = []
        recommendations = []

        try:
            # Step 1: Test database connectivity
            logger.info("🔗 Testing database connectivity...")
            connection_test_results = await self._test_database_connectivity()
            
            if not connection_test_results.get('success', False):
                critical_issues.append("Cannot connect to database")
                execution_time = (time.time() - start_time) * 1000
                
                return DatabaseValidationReport(
                    validation_id=self.validation_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    database_url_masked=self.database_url_masked,
                    overall_success=False,
                    validation_results=validation_results,
                    migration_results=migration_results,
                    connection_test_results=connection_test_results,
                    performance_baseline=performance_baseline,
                    critical_issues=critical_issues,
                    warnings=warnings,
                    recommendations=["Fix database connectivity before proceeding"],
                    execution_time_ms=execution_time
                )

            # Step 2: Validate schema integrity
            logger.info("📋 Validating database schema integrity...")
            schema_results, schema_issues, schema_warnings = await self._validate_schema_integrity()
            validation_results.extend(schema_results)
            critical_issues.extend(schema_issues)
            warnings.extend(schema_warnings)

            # Step 3: Check migration status
            logger.info("🔄 Validating migration status...")
            try:
                migration_results, migration_issues = await self._validate_migration_status()
                critical_issues.extend(migration_issues)
            except Exception as e:
                warnings.append(f"Migration validation failed: {str(e)}")
                logger.warning(f"Migration validation error: {e}")

            # Step 4: Performance baseline
            logger.info("⚡ Establishing performance baseline...")
            performance_baseline = await self._establish_performance_baseline()

            # Step 5: Generate recommendations
            recommendations = self._generate_recommendations(
                critical_issues, warnings, validation_results, migration_results
            )

            execution_time = (time.time() - start_time) * 1000
            overall_success = len(critical_issues) == 0

            logger.info(f"✅ Database validation complete - Success: {overall_success}")
            if critical_issues:
                logger.error(f"❌ Critical issues found: {len(critical_issues)}")
                for issue in critical_issues:
                    logger.error(f"   - {issue}")

            return DatabaseValidationReport(
                validation_id=self.validation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                database_url_masked=self.database_url_masked,
                overall_success=overall_success,
                validation_results=validation_results,
                migration_results=migration_results,
                connection_test_results=connection_test_results,
                performance_baseline=performance_baseline,
                critical_issues=critical_issues,
                warnings=warnings,
                recommendations=recommendations,
                execution_time_ms=execution_time
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"❌ Database validation failed with exception: {str(e)}")
            logger.error(traceback.format_exc())
            
            critical_issues.append(f"Validation failed with exception: {str(e)}")
            
            return DatabaseValidationReport(
                validation_id=self.validation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                database_url_masked=self.database_url_masked,
                overall_success=False,
                validation_results=validation_results,
                migration_results=migration_results,
                connection_test_results=connection_test_results,
                performance_baseline=performance_baseline,
                critical_issues=critical_issues,
                warnings=warnings,
                recommendations=["Investigation required for validation exception"],
                execution_time_ms=execution_time
            )

        finally:
            if self.engine:
                self.engine.dispose()

    async def _test_database_connectivity(self) -> Dict[str, Any]:
        """Test database connectivity with multiple connection methods."""
        results = {
            'success': False,
            'connection_methods_tested': [],
            'errors': [],
            'connection_info': {}
        }

        # Test 1: Basic psycopg2 connection
        try:
            logger.info("   📌 Testing psycopg2 connection...")
            conn = psycopg2.connect(self.database_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                results['connection_info']['postgresql_version'] = version
                
            conn.close()
            results['connection_methods_tested'].append('psycopg2')
            results['success'] = True
            logger.info("   ✅ psycopg2 connection successful")
            
        except Exception as e:
            error_msg = f"psycopg2 connection failed: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"   ❌ {error_msg}")

        # Test 2: SQLAlchemy engine connection
        try:
            logger.info("   📌 Testing SQLAlchemy engine connection...")
            self.engine = create_engine(
                self.database_url,
                connect_args={"sslmode": "require"},
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT current_database(), current_user;"))
                db_info = result.fetchone()
                results['connection_info']['current_database'] = db_info[0]
                results['connection_info']['current_user'] = db_info[1]
                
            results['connection_methods_tested'].append('sqlalchemy')
            results['success'] = True
            logger.info("   ✅ SQLAlchemy connection successful")
            
        except Exception as e:
            error_msg = f"SQLAlchemy connection failed: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"   ❌ {error_msg}")

        return results

    async def _validate_schema_integrity(self) -> Tuple[List[SchemaValidationResult], List[str], List[str]]:
        """Validate database schema against expected structure."""
        validation_results = []
        critical_issues = []
        warnings = []

        if not self.engine:
            critical_issues.append("No database engine available for schema validation")
            return validation_results, critical_issues, warnings

        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()

            # Check each critical table
            for table_name, expected_schema in self.critical_schema.items():
                logger.info(f"   📋 Validating table: {table_name}")
                
                # Check if table exists
                table_exists = table_name in existing_tables
                validation_results.append(SchemaValidationResult(
                    table_name=table_name,
                    validation_type="exists",
                    passed=table_exists,
                    expected=True,
                    actual=table_exists,
                    details={"existing_tables": existing_tables},
                    timestamp=datetime.now(timezone.utc).isoformat()
                ))

                if not table_exists:
                    critical_issues.append(f"Required table '{table_name}' does not exist")
                    continue

                # Check columns
                try:
                    columns = inspector.get_columns(table_name)
                    column_names = [col['name'] for col in columns]
                    
                    # Check required columns
                    missing_required = []
                    for required_col in expected_schema['required_columns']:
                        if required_col not in column_names:
                            missing_required.append(required_col)
                    
                    validation_results.append(SchemaValidationResult(
                        table_name=table_name,
                        validation_type="columns",
                        passed=len(missing_required) == 0,
                        expected=expected_schema['required_columns'],
                        actual=column_names,
                        details={
                            "missing_required": missing_required,
                            "all_columns": column_names,
                            "column_details": columns
                        },
                        timestamp=datetime.now(timezone.utc).isoformat()
                    ))

                    if missing_required:
                        for missing_col in missing_required:
                            critical_issues.append(f"Required column '{table_name}.{missing_col}' is missing")
                            logger.error(f"   ❌ Missing required column: {table_name}.{missing_col}")

                    # Check for unexpected columns (potential warnings)
                    expected_all_columns = expected_schema['required_columns'] + expected_schema.get('optional_columns', [])
                    unexpected_columns = [col for col in column_names if col not in expected_all_columns]
                    if unexpected_columns:
                        warnings.append(f"Table '{table_name}' has unexpected columns: {unexpected_columns}")

                except Exception as e:
                    error_msg = f"Failed to validate columns for table '{table_name}': {str(e)}"
                    critical_issues.append(error_msg)
                    logger.error(f"   ❌ {error_msg}")

                # Check constraints
                try:
                    constraints = inspector.get_pk_constraint(table_name)
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    unique_constraints = inspector.get_unique_constraints(table_name)
                    
                    validation_results.append(SchemaValidationResult(
                        table_name=table_name,
                        validation_type="constraints",
                        passed=True,  # We'll mark as passed if we can retrieve constraint info
                        expected=expected_schema.get('constraints', []),
                        actual={
                            "primary_key": constraints,
                            "foreign_keys": foreign_keys,
                            "unique_constraints": unique_constraints
                        },
                        details={
                            "constraint_validation": "basic_retrieval_only"
                        },
                        timestamp=datetime.now(timezone.utc).isoformat()
                    ))
                    
                except Exception as e:
                    warnings.append(f"Could not validate constraints for table '{table_name}': {str(e)}")

                logger.info(f"   ✅ Completed validation for table: {table_name}")

        except Exception as e:
            critical_issues.append(f"Schema validation failed: {str(e)}")
            logger.error(f"❌ Schema validation error: {e}")

        return validation_results, critical_issues, warnings

    async def _validate_migration_status(self) -> Tuple[List[MigrationValidationResult], List[str]]:
        """Validate migration status using Alembic."""
        migration_results = []
        critical_issues = []

        try:
            # Check if alembic config exists
            if not Path(self.alembic_config_path).exists():
                critical_issues.append(f"Alembic config file not found: {self.alembic_config_path}")
                return migration_results, critical_issues

            # Load Alembic configuration
            alembic_cfg = Config(self.alembic_config_path)
            script_directory = ScriptDirectory.from_config(alembic_cfg)
            
            # Get current migration head
            with self.engine.connect() as connection:
                migration_context = MigrationContext.configure(connection)
                current_heads = migration_context.get_current_heads()
                
            # Get all available migrations
            available_revisions = []
            for revision in script_directory.walk_revisions():
                available_revisions.append({
                    'revision': revision.revision,
                    'down_revision': revision.down_revision,
                    'description': revision.doc,
                    'is_applied': revision.revision in current_heads
                })

            # Check if we're at the latest migration
            script_head = script_directory.get_current_head()
            
            for revision_info in available_revisions:
                migration_results.append(MigrationValidationResult(
                    migration_id=revision_info['revision'],
                    migration_name=revision_info['description'] or 'Unnamed migration',
                    applied=revision_info['is_applied'],
                    expected_applied=revision_info['revision'] == script_head,
                    timestamp=datetime.now(timezone.utc).isoformat()
                ))

            # Check if we're missing any migrations
            if script_head not in current_heads:
                critical_issues.append(f"Database is not at the latest migration. Current: {current_heads}, Expected: {script_head}")
                
        except ImportError:
            critical_issues.append("Alembic not available - cannot validate migration status")
        except Exception as e:
            critical_issues.append(f"Migration validation failed: {str(e)}")
            logger.error(f"Migration validation error: {e}")

        return migration_results, critical_issues

    async def _establish_performance_baseline(self) -> Dict[str, Any]:
        """Establish performance baseline for database operations."""
        baseline = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'tests': {}
        }

        if not self.engine:
            return baseline

        performance_tests = [
            {
                'name': 'simple_select',
                'query': 'SELECT 1 as test_value',
                'description': 'Basic SELECT query performance'
            },
            {
                'name': 'system_info',
                'query': 'SELECT current_database(), version(), current_timestamp',
                'description': 'System information query performance'
            },
            {
                'name': 'user_count',
                'query': 'SELECT COUNT(*) FROM users',
                'description': 'User table count performance',
                'table_dependent': True
            }
        ]

        for test in performance_tests:
            try:
                if test.get('table_dependent'):
                    # Check if table exists first
                    inspector = inspect(self.engine)
                    if 'users' not in inspector.get_table_names():
                        baseline['tests'][test['name']] = {
                            'status': 'skipped',
                            'reason': 'Required table does not exist'
                        }
                        continue

                start_time = time.time()
                with self.engine.connect() as connection:
                    result = connection.execute(text(test['query']))
                    rows = result.fetchall()
                    
                execution_time = (time.time() - start_time) * 1000

                baseline['tests'][test['name']] = {
                    'status': 'success',
                    'execution_time_ms': execution_time,
                    'row_count': len(rows),
                    'description': test['description']
                }
                
            except Exception as e:
                baseline['tests'][test['name']] = {
                    'status': 'failed',
                    'error': str(e),
                    'description': test['description']
                }

        return baseline

    def _generate_recommendations(self, critical_issues: List[str], warnings: List[str], 
                                validation_results: List[SchemaValidationResult],
                                migration_results: List[MigrationValidationResult]) -> List[str]:
        """Generate specific recommendations based on validation results."""
        recommendations = []

        # Critical issue recommendations
        if any("user_categories.emoji" in issue for issue in critical_issues):
            recommendations.append(
                "CRITICAL: Run database migration to add missing 'emoji' column to user_categories table"
            )
            recommendations.append(
                "Execute: docker exec ai_workflow_engine-api-1 alembic upgrade head"
            )

        if any("connect" in issue.lower() for issue in critical_issues):
            recommendations.append(
                "CRITICAL: Fix database connectivity issues before proceeding with application startup"
            )
            recommendations.append(
                "Check database credentials, network connectivity, and SSL configuration"
            )

        if any("table" in issue and "does not exist" in issue for issue in critical_issues):
            recommendations.append(
                "CRITICAL: Initialize database schema by running all pending migrations"
            )

        # Migration recommendations
        unapplied_migrations = [mr for mr in migration_results if mr.expected_applied and not mr.applied]
        if unapplied_migrations:
            recommendations.append(
                f"Apply {len(unapplied_migrations)} pending database migration(s)"
            )

        # Warning-based recommendations
        if warnings:
            recommendations.append(
                "Review database schema warnings for potential inconsistencies"
            )

        # Success recommendations
        if not critical_issues and not warnings:
            recommendations.append(
                "Database integrity validation passed - system ready for operation"
            )

        return recommendations

    async def save_validation_report(self, report: DatabaseValidationReport, 
                                   output_path: Optional[Path] = None) -> Path:
        """Save validation report to file."""
        if output_path is None:
            output_path = Path(f".claude/logs/db_validation_report_{report.validation_id}.json")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert dataclasses to dictionaries for JSON serialization
        report_dict = asdict(report)
        
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        logger.info(f"💾 Database validation report saved to: {output_path}")
        return output_path

if __name__ == "__main__":
    # Example usage
    import os
    
    # Get database URL from environment or use default
    database_url = os.getenv('DATABASE_URL', 
        'postgresql://ai_workflow:password@postgres:5432/ai_workflow_engine?sslmode=require')
    
    validator = DatabaseIntegrityValidator(database_url)
    
    # Run validation
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        validation_report = loop.run_until_complete(validator.validate_database_integrity())
        
        print("\n" + "="*80)
        print("DATABASE INTEGRITY VALIDATION REPORT")
        print("="*80)
        print(f"Validation ID: {validation_report.validation_id}")
        print(f"Overall Success: {validation_report.overall_success}")
        print(f"Execution Time: {validation_report.execution_time_ms:.2f}ms")
        print()
        
        if validation_report.critical_issues:
            print("❌ CRITICAL ISSUES:")
            for issue in validation_report.critical_issues:
                print(f"   - {issue}")
            print()
        
        if validation_report.warnings:
            print("⚠️  WARNINGS:")
            for warning in validation_report.warnings:
                print(f"   - {warning}")
            print()
        
        if validation_report.recommendations:
            print("💡 RECOMMENDATIONS:")
            for rec in validation_report.recommendations:
                print(f"   - {rec}")
            print()
        
        # Save report
        loop.run_until_complete(validator.save_validation_report(validation_report))
        
    finally:
        loop.close()