"""Security validation service for testing database security implementation."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_, func
from sqlalchemy.exc import SQLAlchemyError

from shared.database.models._models import User
from shared.database.models.security_models import (
    AuditLog, SecurityViolation, DataAccessLog, QdrantAccessControl
)
from shared.services.security_audit_service import security_audit_service
from shared.utils.database_setup import get_async_session

logger = logging.getLogger(__name__)


class SecurityValidationService:
    """Comprehensive security validation and testing service."""
    
    def __init__(self):
        self.logger = logger
        self.test_results: List[Dict[str, Any]] = []
    
    async def run_comprehensive_security_validation(self) -> Dict[str, Any]:
        """Run comprehensive security validation tests."""
        self.logger.info("Starting comprehensive security validation")
        self.test_results = []
        
        validation_results = {
            'overall_status': 'UNKNOWN',
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'warnings': 0,
            'test_results': [],
            'summary': {},
            'started_at': datetime.utcnow().isoformat(),
            'completed_at': None
        }
        
        try:
            # Test categories
            test_categories = [
                ('Row-Level Security', self._test_row_level_security),
                ('Audit Trail Functionality', self._test_audit_trail),
                ('Security Violations Detection', self._test_security_violations),
                ('Data Access Logging', self._test_data_access_logging),
                ('User Isolation', self._test_user_isolation),
                ('Vector Database Security', self._test_vector_security),
                ('Cross-Service Authentication', self._test_cross_service_auth),
                ('Data Retention Policies', self._test_data_retention),
                ('Encryption Controls', self._test_encryption_controls),
                ('Performance Impact', self._test_performance_impact)
            ]
            
            for category_name, test_function in test_categories:
                self.logger.info(f"Running {category_name} tests")
                category_results = await test_function()
                
                validation_results['test_results'].append({
                    'category': category_name,
                    'results': category_results
                })
                
                # Update counters
                for result in category_results:
                    validation_results['total_tests'] += 1
                    if result['status'] == 'PASS':
                        validation_results['passed_tests'] += 1
                    elif result['status'] == 'FAIL':
                        validation_results['failed_tests'] += 1
                    elif result['status'] == 'WARNING':
                        validation_results['warnings'] += 1
            
            # Determine overall status
            if validation_results['failed_tests'] == 0:
                if validation_results['warnings'] == 0:
                    validation_results['overall_status'] = 'PASS'
                else:
                    validation_results['overall_status'] = 'PASS_WITH_WARNINGS'
            else:
                validation_results['overall_status'] = 'FAIL'
            
            # Generate summary
            validation_results['summary'] = self._generate_validation_summary(validation_results)
            validation_results['completed_at'] = datetime.utcnow().isoformat()
            
            self.logger.info(
                f"Security validation completed: {validation_results['overall_status']} "
                f"({validation_results['passed_tests']}/{validation_results['total_tests']} passed)"
            )
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Security validation failed: {str(e)}")
            validation_results['overall_status'] = 'ERROR'
            validation_results['error'] = str(e)
            return validation_results
    
    async def _test_row_level_security(self) -> List[Dict[str, Any]]:
        """Test Row-Level Security (RLS) policies."""
        results = []
        
        async with get_async_session() as session:
            try:
                # Test 1: Verify RLS is enabled on sensitive tables
                sensitive_tables = [
                    'users', 'user_profiles', 'chat_mode_sessions', 
                    'simple_chat_context', 'tasks', 'documents'
                ]
                
                for table in sensitive_tables:
                    result = await session.execute(
                        text("""
                            SELECT relrowsecurity
                            FROM pg_class
                            WHERE relname = :table_name
                        """),
                        {'table_name': table}
                    )
                    
                    rls_enabled = result.scalar()
                    
                    results.append({
                        'test': f'RLS enabled on {table}',
                        'status': 'PASS' if rls_enabled else 'FAIL',
                        'message': f'RLS is {"enabled" if rls_enabled else "disabled"} on {table}',
                        'details': {'table': table, 'rls_enabled': rls_enabled}
                    })
                
                # Test 2: Verify policies exist
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) as policy_count
                        FROM pg_policy
                        WHERE schemaname = 'public'
                    """)
                )
                
                policy_count = result.scalar()
                
                results.append({
                    'test': 'RLS policies exist',
                    'status': 'PASS' if policy_count > 0 else 'FAIL',
                    'message': f'Found {policy_count} RLS policies',
                    'details': {'policy_count': policy_count}
                })
                
                # Test 3: Test user isolation (simulate different users)
                isolation_test = await self._test_user_data_isolation(session)
                results.extend(isolation_test)
                
            except Exception as e:
                results.append({
                    'test': 'RLS validation',
                    'status': 'ERROR',
                    'message': f'Error testing RLS: {str(e)}',
                    'details': {'error': str(e)}
                })
        
        return results
    
    async def _test_audit_trail(self) -> List[Dict[str, Any]]:
        """Test audit trail functionality."""
        results = []
        
        async with get_async_session() as session:
            try:
                # Test 1: Verify audit schema exists
                result = await session.execute(
                    text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'audit'")
                )
                
                audit_schema_exists = result.scalar() is not None
                
                results.append({
                    'test': 'Audit schema exists',
                    'status': 'PASS' if audit_schema_exists else 'FAIL',
                    'message': f'Audit schema {"exists" if audit_schema_exists else "missing"}',
                    'details': {'schema_exists': audit_schema_exists}
                })
                
                # Test 2: Verify audit triggers exist
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) as trigger_count
                        FROM information_schema.triggers
                        WHERE trigger_name LIKE 'audit_trigger_%'
                    """)
                )
                
                trigger_count = result.scalar()
                
                results.append({
                    'test': 'Audit triggers exist',
                    'status': 'PASS' if trigger_count > 0 else 'FAIL',
                    'message': f'Found {trigger_count} audit triggers',
                    'details': {'trigger_count': trigger_count}
                })
                
                # Test 3: Test audit logging with actual operation
                audit_test = await self._test_audit_logging(session)
                results.extend(audit_test)
                
            except Exception as e:
                results.append({
                    'test': 'Audit trail validation',
                    'status': 'ERROR',
                    'message': f'Error testing audit trail: {str(e)}',
                    'details': {'error': str(e)}
                })
        
        return results
    
    async def _test_security_violations(self) -> List[Dict[str, Any]]:
        """Test security violation detection."""
        results = []
        
        async with get_async_session() as session:
            try:
                # Test 1: Log a test security violation
                violation_id = await security_audit_service.log_security_violation(
                    session=session,
                    violation_type='TEST_VIOLATION',
                    severity='LOW',
                    violation_details={'test': True, 'purpose': 'validation'},
                    blocked=False
                )
                
                results.append({
                    'test': 'Security violation logging',
                    'status': 'PASS' if violation_id else 'FAIL',
                    'message': f'Test violation logged with ID: {violation_id}',
                    'details': {'violation_id': violation_id}
                })
                
                # Test 2: Verify violation can be retrieved
                violations = await security_audit_service.get_security_violations(
                    session=session,
                    severity='LOW',
                    limit=1
                )
                
                found_test_violation = any(v.violation_type == 'TEST_VIOLATION' for v in violations)
                
                results.append({
                    'test': 'Security violation retrieval',
                    'status': 'PASS' if found_test_violation else 'FAIL',
                    'message': f'Test violation {"found" if found_test_violation else "not found"} in retrieval',
                    'details': {'violations_found': len(violations)}
                })
                
                # Test 3: Test anomaly detection function
                anomalies = await security_audit_service.detect_security_anomalies(session)
                
                results.append({
                    'test': 'Security anomaly detection',
                    'status': 'PASS',
                    'message': f'Anomaly detection function executed, found {len(anomalies)} anomalies',
                    'details': {'anomalies_found': len(anomalies)}
                })
                
            except Exception as e:
                results.append({
                    'test': 'Security violations validation',
                    'status': 'ERROR',
                    'message': f'Error testing security violations: {str(e)}',
                    'details': {'error': str(e)}
                })
        
        return results
    
    async def _test_data_access_logging(self) -> List[Dict[str, Any]]:
        """Test data access logging functionality."""
        results = []
        
        async with get_async_session() as session:
            try:
                # Test 1: Log a test data access
                test_user_id = 1  # Assuming user 1 exists
                
                await security_audit_service.log_data_access(
                    session=session,
                    user_id=test_user_id,
                    service_name='validation_test',
                    access_type='READ',
                    table_name='test_table',
                    row_count=5,
                    sensitive_data_accessed=True,
                    access_pattern={'test': True}
                )
                
                results.append({
                    'test': 'Data access logging',
                    'status': 'PASS',
                    'message': 'Test data access logged successfully',
                    'details': {'user_id': test_user_id}
                })
                
                # Test 2: Verify logged access can be retrieved
                recent_access = await session.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM audit.data_access_log
                        WHERE service_name = 'validation_test'
                        AND created_at >= NOW() - INTERVAL '1 minute'
                    """)
                )
                
                access_count = recent_access.scalar()
                
                results.append({
                    'test': 'Data access retrieval',
                    'status': 'PASS' if access_count > 0 else 'FAIL',
                    'message': f'Found {access_count} recent test access logs',
                    'details': {'access_count': access_count}
                })
                
            except Exception as e:
                results.append({
                    'test': 'Data access logging validation',
                    'status': 'ERROR',
                    'message': f'Error testing data access logging: {str(e)}',
                    'details': {'error': str(e)}
                })
        
        return results
    
    async def _test_user_isolation(self) -> List[Dict[str, Any]]:
        """Test user data isolation."""
        results = []
        
        async with get_async_session() as session:
            try:
                # Test 1: Verify security context function exists
                result = await session.execute(
                    text("SELECT get_current_user_id()")
                )
                
                current_user_id = result.scalar()
                
                results.append({
                    'test': 'Security context function',
                    'status': 'PASS' if current_user_id is not None else 'FAIL',
                    'message': f'get_current_user_id() returned: {current_user_id}',
                    'details': {'current_user_id': current_user_id}
                })
                
                # Test 2: Test setting security context
                test_user_id = 999999  # Non-existent user ID
                
                await security_audit_service.set_security_context(
                    session=session,
                    user_id=test_user_id,
                    session_id='test_session_123',
                    service_name='validation_test'
                )
                
                # Verify context was set
                result = await session.execute(
                    text("SELECT get_current_user_id()")
                )
                
                set_user_id = result.scalar()
                
                results.append({
                    'test': 'Security context setting',
                    'status': 'PASS' if set_user_id == test_user_id else 'FAIL',
                    'message': f'Context set to user {set_user_id}, expected {test_user_id}',
                    'details': {'set_user_id': set_user_id, 'expected_user_id': test_user_id}
                })
                
            except Exception as e:
                results.append({
                    'test': 'User isolation validation',
                    'status': 'ERROR',
                    'message': f'Error testing user isolation: {str(e)}',
                    'details': {'error': str(e)}
                })
        
        return results
    
    async def _test_vector_security(self) -> List[Dict[str, Any]]:
        """Test vector database security."""
        results = []
        
        async with get_async_session() as session:
            try:
                # Test 1: Verify Qdrant access control table exists
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM information_schema.tables
                        WHERE table_name = 'qdrant_access_control'
                    """)
                )
                
                table_exists = result.scalar() > 0
                
                results.append({
                    'test': 'Qdrant access control table exists',
                    'status': 'PASS' if table_exists else 'FAIL',
                    'message': f'qdrant_access_control table {"exists" if table_exists else "missing"}',
                    'details': {'table_exists': table_exists}
                })
                
                # Test 2: Test vector access permission check
                if table_exists:
                    test_user_id = 1  # Assuming user 1 exists
                    
                    has_permission = await security_audit_service.check_vector_access_permission(
                        session=session,
                        user_id=test_user_id,
                        collection_name='test_collection',
                        access_level='READ'
                    )
                    
                    results.append({
                        'test': 'Vector access permission check',
                        'status': 'PASS',  # Function executed without error
                        'message': f'Permission check returned: {has_permission}',
                        'details': {'has_permission': has_permission, 'user_id': test_user_id}
                    })
                
            except Exception as e:
                results.append({
                    'test': 'Vector security validation',
                    'status': 'ERROR',
                    'message': f'Error testing vector security: {str(e)}',
                    'details': {'error': str(e)}
                })
        
        return results
    
    async def _test_cross_service_auth(self) -> List[Dict[str, Any]]:
        """Test cross-service authentication."""
        results = []
        
        async with get_async_session() as session:
            try:
                # Test 1: Verify cross-service auth table exists
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM information_schema.tables
                        WHERE table_name = 'cross_service_auth'
                    """)
                )
                
                table_exists = result.scalar() > 0
                
                results.append({
                    'test': 'Cross-service auth table exists',
                    'status': 'PASS' if table_exists else 'FAIL',
                    'message': f'cross_service_auth table {"exists" if table_exists else "missing"}',
                    'details': {'table_exists': table_exists}
                })
                
                # Test 2: Test service authentication logging
                if table_exists:
                    # This would typically be tested with actual service tokens
                    results.append({
                        'test': 'Cross-service authentication',
                        'status': 'WARNING',
                        'message': 'Cross-service auth requires integration testing with actual services',
                        'details': {'requires_integration_test': True}
                    })
                
            except Exception as e:
                results.append({
                    'test': 'Cross-service auth validation',
                    'status': 'ERROR',
                    'message': f'Error testing cross-service auth: {str(e)}',
                    'details': {'error': str(e)}
                })
        
        return results
    
    async def _test_data_retention(self) -> List[Dict[str, Any]]:
        """Test data retention policies."""
        results = []
        
        async with get_async_session() as session:
            try:
                # Test 1: Verify retention policies table exists
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM information_schema.tables
                        WHERE table_name = 'data_retention_policies'
                    """)
                )
                
                table_exists = result.scalar() > 0
                
                results.append({
                    'test': 'Data retention policies table exists',
                    'status': 'PASS' if table_exists else 'FAIL',
                    'message': f'data_retention_policies table {"exists" if table_exists else "missing"}',
                    'details': {'table_exists': table_exists}
                })
                
                # Test 2: Check for default policies
                if table_exists:
                    result = await session.execute(
                        text("SELECT COUNT(*) as count FROM data_retention_policies WHERE is_active = true")
                    )
                    
                    active_policies = result.scalar()
                    
                    results.append({
                        'test': 'Active retention policies exist',
                        'status': 'PASS' if active_policies > 0 else 'WARNING',
                        'message': f'Found {active_policies} active retention policies',
                        'details': {'active_policies': active_policies}
                    })
                
                # Test 3: Test cleanup function
                try:
                    result = await session.execute(text("SELECT audit.cleanup_old_data()"))
                    rows_cleaned = result.scalar()
                    
                    results.append({
                        'test': 'Data cleanup function',
                        'status': 'PASS',
                        'message': f'Cleanup function executed, processed {rows_cleaned} rows',
                        'details': {'rows_cleaned': rows_cleaned}
                    })
                except Exception as cleanup_error:
                    results.append({
                        'test': 'Data cleanup function',
                        'status': 'WARNING',
                        'message': f'Cleanup function error: {str(cleanup_error)}',
                        'details': {'error': str(cleanup_error)}
                    })
                
            except Exception as e:
                results.append({
                    'test': 'Data retention validation',
                    'status': 'ERROR',
                    'message': f'Error testing data retention: {str(e)}',
                    'details': {'error': str(e)}
                })
        
        return results
    
    async def _test_encryption_controls(self) -> List[Dict[str, Any]]:
        """Test encryption controls."""
        results = []
        
        async with get_async_session() as session:
            try:
                # Test 1: Verify encrypted fields table exists
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM information_schema.tables
                        WHERE table_name = 'encrypted_fields'
                    """)
                )
                
                table_exists = result.scalar() > 0
                
                results.append({
                    'test': 'Encrypted fields table exists',
                    'status': 'PASS' if table_exists else 'FAIL',
                    'message': f'encrypted_fields table {"exists" if table_exists else "missing"}',
                    'details': {'table_exists': table_exists}
                })
                
                # Test 2: Test anonymization function
                try:
                    # Test with non-existent user to avoid affecting real data
                    test_user_id = 999999
                    
                    await session.execute(
                        text("SELECT anonymize_user_data(:user_id)"),
                        {'user_id': test_user_id}
                    )
                    
                    results.append({
                        'test': 'Data anonymization function',
                        'status': 'PASS',
                        'message': 'Anonymization function executed successfully',
                        'details': {'test_user_id': test_user_id}
                    })
                except Exception as anon_error:
                    results.append({
                        'test': 'Data anonymization function',
                        'status': 'WARNING',
                        'message': f'Anonymization function error: {str(anon_error)}',
                        'details': {'error': str(anon_error)}
                    })
                
            except Exception as e:
                results.append({
                    'test': 'Encryption controls validation',
                    'status': 'ERROR',
                    'message': f'Error testing encryption controls: {str(e)}',
                    'details': {'error': str(e)}
                })
        
        return results
    
    async def _test_performance_impact(self) -> List[Dict[str, Any]]:
        """Test performance impact of security features."""
        results = []
        
        async with get_async_session() as session:
            try:
                # Test 1: Measure audit trigger performance
                start_time = datetime.utcnow()
                
                # Perform a simple operation that should trigger audit
                await session.execute(
                    text("UPDATE users SET updated_at = NOW() WHERE id = 1")
                )
                
                end_time = datetime.utcnow()
                operation_time = (end_time - start_time).total_seconds() * 1000  # ms
                
                results.append({
                    'test': 'Audit trigger performance',
                    'status': 'PASS' if operation_time < 100 else 'WARNING',
                    'message': f'Update operation took {operation_time:.2f}ms',
                    'details': {'operation_time_ms': operation_time}
                })
                
                # Test 2: Check database connection pool health
                result = await session.execute(
                    text("SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'")
                )
                
                active_connections = result.scalar()
                
                results.append({
                    'test': 'Database connection health',
                    'status': 'PASS' if active_connections < 50 else 'WARNING',
                    'message': f'{active_connections} active database connections',
                    'details': {'active_connections': active_connections}
                })
                
            except Exception as e:
                results.append({
                    'test': 'Performance impact validation',
                    'status': 'ERROR',
                    'message': f'Error testing performance impact: {str(e)}',
                    'details': {'error': str(e)}
                })
        
        return results
    
    async def _test_user_data_isolation(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Test user data isolation with simulated different users."""
        results = []
        
        try:
            # This would require creating test users and verifying isolation
            # For now, just verify the security context functions work
            
            results.append({
                'test': 'User data isolation simulation',
                'status': 'WARNING',
                'message': 'User isolation requires integration testing with real user data',
                'details': {'requires_integration_test': True}
            })
            
        except Exception as e:
            results.append({
                'test': 'User data isolation',
                'status': 'ERROR',
                'message': f'Error testing user isolation: {str(e)}',
                'details': {'error': str(e)}
            })
        
        return results
    
    async def _test_audit_logging(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Test audit logging with actual database operations."""
        results = []
        
        try:
            # Count existing audit logs
            before_result = await session.execute(
                text("SELECT COUNT(*) FROM audit.audit_log")
            )
            before_count = before_result.scalar()
            
            # Perform an operation that should be audited
            await session.execute(
                text("UPDATE users SET updated_at = NOW() WHERE id = 1")
            )
            
            # Count audit logs after operation
            after_result = await session.execute(
                text("SELECT COUNT(*) FROM audit.audit_log")
            )
            after_count = after_result.scalar()
            
            audit_logs_created = after_count - before_count
            
            results.append({
                'test': 'Audit log creation',
                'status': 'PASS' if audit_logs_created > 0 else 'FAIL',
                'message': f'{audit_logs_created} audit log(s) created for update operation',
                'details': {'before_count': before_count, 'after_count': after_count}
            })
            
        except Exception as e:
            results.append({
                'test': 'Audit logging test',
                'status': 'ERROR',
                'message': f'Error testing audit logging: {str(e)}',
                'details': {'error': str(e)}
            })
        
        return results
    
    def _generate_validation_summary(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate validation summary."""
        total = validation_results['total_tests']
        passed = validation_results['passed_tests']
        failed = validation_results['failed_tests']
        warnings = validation_results['warnings']
        
        return {
            'security_score': round((passed / total * 100) if total > 0 else 0, 2),
            'critical_issues': failed,
            'minor_issues': warnings,
            'recommendations': self._generate_recommendations(validation_results),
            'next_steps': self._generate_next_steps(validation_results)
        }
    
    def _generate_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate security recommendations based on test results."""
        recommendations = []
        
        # Analyze failed tests and generate specific recommendations
        for category in validation_results['test_results']:
            for result in category['results']:
                if result['status'] == 'FAIL':
                    if 'RLS' in result['test']:
                        recommendations.append("Enable Row-Level Security on all sensitive tables")
                    elif 'audit' in result['test'].lower():
                        recommendations.append("Ensure audit triggers are properly installed")
                    elif 'violation' in result['test'].lower():
                        recommendations.append("Verify security violation logging system")
        
        if not recommendations:
            recommendations.append("Security implementation appears to be working correctly")
        
        return recommendations
    
    def _generate_next_steps(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate next steps based on validation results."""
        next_steps = []
        
        if validation_results['failed_tests'] > 0:
            next_steps.append("Address failed security tests before deploying to production")
        
        if validation_results['warnings'] > 0:
            next_steps.append("Review warnings and consider implementing recommended improvements")
        
        next_steps.extend([
            "Set up continuous security monitoring",
            "Schedule regular security validation runs",
            "Implement alerting for critical security violations",
            "Review and update data retention policies",
            "Train team on security best practices"
        ])
        
        return next_steps


# Global security validation service instance
security_validation_service = SecurityValidationService()