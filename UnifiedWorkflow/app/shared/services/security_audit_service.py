"""Security audit service for comprehensive database security monitoring."""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from shared.database.models.security_models import (
    AuditLog, SecurityViolation, DataAccessLog, SecurityMetric,
    PrivacyRequest, QdrantAccessControl, DataRetentionPolicy,
    SecurityAction
)
from shared.database.models._models import User
from shared.utils.database_setup import get_db
from shared.services.redis_cache_service import get_redis_cache

logger = logging.getLogger(__name__)


class SecurityAuditService:
    """Comprehensive security audit and monitoring service with Redis caching."""
    
    def __init__(self):
        self.logger = logger
        self._cache = None
        
        # Cache TTL configurations (in seconds)
        self.security_context_ttl = 300  # 5 minutes
        self.permission_cache_ttl = 600  # 10 minutes
        self.user_violation_cache_ttl = 180  # 3 minutes
        self.metrics_cache_ttl = 60  # 1 minute
    
    async def _get_cache(self):
        """Get Redis cache instance with lazy initialization."""
        if not self._cache:
            self._cache = await get_redis_cache()
        return self._cache
    
    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Generate consistent cache keys for security contexts."""
        key_parts = [prefix] + [str(arg) for arg in args]
        base_key = ":security:".join(key_parts)
        
        # Hash long keys to prevent Redis key length issues
        if len(base_key) > 200:
            key_hash = hashlib.md5(base_key.encode()).hexdigest()
            return f"security:{prefix}:hash:{key_hash}"
        
        return f"security:{base_key}"
    
    async def set_security_context(
        self, 
        session: AsyncSession,
        user_id: int,
        session_id: Optional[str] = None,
        service_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Set security context for the current database session with Redis caching."""
        try:
            cache = await self._get_cache()
            context_key = self._generate_cache_key("context", user_id, session_id or "none")
            
            # Check if context is already cached
            cached_context = await cache.get(context_key)
            if cached_context:
                # Context already set recently, skip database operations
                self.logger.debug(f"Using cached security context for user {user_id}")
                return
            
            # Set application-level security context
            await session.execute(text(f"SELECT set_security_context({user_id}, :session_id, :service_name)"), {
                'session_id': session_id or '',
                'service_name': service_name or 'unknown'
            })
            
            # Set additional context variables if provided
            if ip_address:
                await session.execute(text("SELECT set_config('app.current_ip', :ip, false)"), {'ip': ip_address})
            if user_agent:
                await session.execute(text("SELECT set_config('app.current_user_agent', :ua, false)"), {'ua': user_agent})
            
            await session.commit()
            
            # Cache the security context to avoid repeated database calls
            context_data = {
                'user_id': user_id,
                'session_id': session_id,
                'service_name': service_name,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'set_at': datetime.utcnow().isoformat()
            }
            
            await cache.set(context_key, context_data, ttl=self.security_context_ttl)
            self.logger.info(f"Security context set and cached for user {user_id}, session {session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to set security context: {str(e)}")
            await session.rollback()
            raise
    
    async def invalidate_user_cache(self, user_id: int) -> None:
        """Invalidate all cached data for a specific user."""
        try:
            cache = await self._get_cache()
            
            # Define cache patterns to invalidate for the user
            patterns = [
                f"security:context:{user_id}:*",
                f"security:permission:{user_id}:*",
                f"security:violations:{user_id}:*",
                f"security:anomaly_check:{user_id}:*"
            ]
            
            total_deleted = 0
            for pattern in patterns:
                deleted = await cache.delete_pattern(pattern)
                total_deleted += deleted
            
            self.logger.info(f"Invalidated {total_deleted} cache entries for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to invalidate user cache: {str(e)}")
    
    async def get_cache_performance_metrics(self) -> Dict[str, Any]:
        """Get security cache performance metrics."""
        try:
            cache = await self._get_cache()
            cache_metrics = await cache.get_cache_metrics()
            
            return {
                'security_cache_config': {
                    'security_context_ttl': self.security_context_ttl,
                    'permission_cache_ttl': self.permission_cache_ttl,
                    'user_violation_cache_ttl': self.user_violation_cache_ttl,
                    'metrics_cache_ttl': self.metrics_cache_ttl
                },
                'redis_performance': cache_metrics,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cache performance metrics: {str(e)}")
            return {}
    
    async def log_data_access(
        self,
        session: AsyncSession,
        user_id: int,
        service_name: str,
        access_type: str,
        table_name: str,
        row_count: int = 0,
        sensitive_data_accessed: bool = False,
        access_pattern: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        response_time_ms: Optional[int] = None
    ) -> None:
        """Log data access for privacy compliance and monitoring."""
        try:
            access_log = DataAccessLog(
                user_id=user_id,
                service_name=service_name,
                access_type=access_type,
                table_name=table_name,
                row_count=row_count,
                sensitive_data_accessed=sensitive_data_accessed,
                access_pattern=access_pattern,
                session_id=session_id,
                ip_address=ip_address,
                response_time_ms=response_time_ms
            )
            
            session.add(access_log)
            await session.commit()
            
            # Check for anomalous access patterns
            await self._check_access_anomalies(session, user_id, service_name)
            
        except Exception as e:
            self.logger.error(f"Failed to log data access: {str(e)}")
            await session.rollback()
            raise
    
    async def log_security_violation(
        self,
        session: AsyncSession,
        violation_type: str,
        severity: str,
        violation_details: Dict[str, Any],
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        table_name: Optional[str] = None,
        attempted_operation: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        blocked: bool = True
    ) -> str:
        """Log security violation and return violation ID."""
        try:
            violation = SecurityViolation(
                violation_type=violation_type,
                severity=severity,
                user_id=user_id,
                session_id=session_id,
                table_name=table_name,
                attempted_operation=attempted_operation,
                violation_details=violation_details,
                ip_address=ip_address,
                user_agent=user_agent,
                blocked=blocked
            )
            
            session.add(violation)
            await session.commit()
            
            self.logger.warning(
                f"Security violation logged: {violation_type} (severity: {severity}) "
                f"for user {user_id}, blocked: {blocked}"
            )
            
            # Trigger immediate alerting for critical violations
            if severity == 'CRITICAL':
                await self._trigger_security_alert(violation)
            
            return str(violation.id)
            
        except Exception as e:
            self.logger.error(f"Failed to log security violation: {str(e)}")
            await session.rollback()
            raise
    
    async def check_vector_access_permission(
        self,
        session: AsyncSession,
        user_id: int,
        collection_name: str,
        access_level: str
    ) -> bool:
        """Check if user has permission to access Qdrant collection with caching."""
        try:
            cache = await self._get_cache()
            permission_key = self._generate_cache_key("permission", user_id, collection_name, access_level)
            
            # Check cached permission first
            cached_permission = await cache.get(permission_key)
            if cached_permission is not None:
                self.logger.debug(f"Using cached permission for user {user_id}, collection {collection_name}")
                return cached_permission
            
            # Check for active access control in database
            result = await session.execute(
                select(QdrantAccessControl).where(
                    and_(
                        QdrantAccessControl.user_id == user_id,
                        QdrantAccessControl.collection_name == collection_name,
                        QdrantAccessControl.access_level == access_level,
                        QdrantAccessControl.is_active == True,
                        or_(
                            QdrantAccessControl.expires_at.is_(None),
                            QdrantAccessControl.expires_at > datetime.utcnow()
                        )
                    )
                )
            )
            
            access_control = result.scalar_one_or_none()
            has_permission = access_control is not None
            
            # Cache the permission result
            await cache.set(permission_key, has_permission, ttl=self.permission_cache_ttl)
            
            # Log access attempt
            await self.log_data_access(
                session=session,
                user_id=user_id,
                service_name='qdrant',
                access_type=access_level,
                table_name=f'vector_{collection_name}',
                sensitive_data_accessed=True,
                access_pattern={'permission_check': True, 'granted': has_permission, 'cached': False}
            )
            
            if not has_permission:
                await self.log_security_violation(
                    session=session,
                    violation_type='UNAUTHORIZED_VECTOR_ACCESS',
                    severity='HIGH',
                    violation_details={
                        'collection_name': collection_name,
                        'requested_access_level': access_level,
                        'reason': 'No valid access control found'
                    },
                    user_id=user_id,
                    blocked=True
                )
            
            return has_permission
            
        except Exception as e:
            self.logger.error(f"Failed to check vector access permission: {str(e)}")
            return False
    
    async def get_security_violations(
        self,
        session: AsyncSession,
        user_id: Optional[int] = None,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SecurityViolation]:
        """Get security violations with filtering and caching."""
        try:
            cache = await self._get_cache()
            
            # Create cache key based on filters
            cache_key_parts = ["violations", str(user_id or "all"), str(severity or "all"), 
                              str(resolved if resolved is not None else "all"), str(limit), str(offset)]
            violations_key = self._generate_cache_key(*cache_key_parts)
            
            # Check cache first for frequent queries
            if user_id is not None:  # Only cache user-specific queries
                cached_violations = await cache.get(violations_key)
                if cached_violations is not None:
                    self.logger.debug(f"Using cached violations for user {user_id}")
                    # Convert back to SecurityViolation objects
                    return [SecurityViolation(**violation_data) for violation_data in cached_violations]
            
            query = select(SecurityViolation)
            
            # Apply filters
            conditions = []
            if user_id is not None:
                conditions.append(SecurityViolation.user_id == user_id)
            if severity is not None:
                conditions.append(SecurityViolation.severity == severity)
            if resolved is not None:
                conditions.append(SecurityViolation.resolved == resolved)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(desc(SecurityViolation.created_at)).limit(limit).offset(offset)
            
            result = await session.execute(query)
            violations = list(result.scalars().all())
            
            # Cache user-specific queries
            if user_id is not None and violations:
                violation_data = [{
                    'id': v.id,
                    'violation_type': v.violation_type,
                    'severity': v.severity,
                    'user_id': v.user_id,
                    'session_id': v.session_id,
                    'table_name': v.table_name,
                    'attempted_operation': v.attempted_operation,
                    'violation_details': v.violation_details,
                    'ip_address': v.ip_address,
                    'user_agent': v.user_agent,
                    'blocked': v.blocked,
                    'resolved': v.resolved,
                    'created_at': v.created_at.isoformat() if v.created_at else None,
                    'resolved_at': v.resolved_at.isoformat() if v.resolved_at else None
                } for v in violations]
                
                await cache.set(violations_key, violation_data, ttl=self.user_violation_cache_ttl)
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Failed to get security violations: {str(e)}")
            return []
    
    async def get_audit_trail(
        self,
        session: AsyncSession,
        user_id: Optional[int] = None,
        table_name: Optional[str] = None,
        operation: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Get audit trail with filtering."""
        try:
            # Use raw SQL for audit schema access
            conditions = []
            params = {}
            
            if user_id is not None:
                conditions.append("user_id = :user_id")
                params['user_id'] = user_id
            if table_name is not None:
                conditions.append("table_name = :table_name")
                params['table_name'] = table_name
            if operation is not None:
                conditions.append("operation = :operation")
                params['operation'] = operation
            if start_date is not None:
                conditions.append("created_at >= :start_date")
                params['start_date'] = start_date
            if end_date is not None:
                conditions.append("created_at <= :end_date")
                params['end_date'] = end_date
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            params['limit'] = limit
            params['offset'] = offset
            
            query = f"""
                SELECT * FROM audit.audit_log
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """
            
            result = await session.execute(text(query), params)
            rows = result.fetchall()
            
            # Convert to AuditLog objects
            audit_logs = []
            for row in rows:
                audit_log = AuditLog()
                for column, value in row._mapping.items():
                    setattr(audit_log, column, value)
                audit_logs.append(audit_log)
            
            return audit_logs
            
        except Exception as e:
            self.logger.error(f"Failed to get audit trail: {str(e)}")
            return []
    
    async def detect_security_anomalies(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Detect security anomalies using database function."""
        try:
            result = await session.execute(text("SELECT * FROM audit.detect_security_anomalies()"))
            anomalies = []
            
            for row in result.fetchall():
                anomalies.append({
                    'anomaly_type': row.anomaly_type,
                    'severity': row.severity,
                    'details': row.details,
                    'detected_at': row.detected_at
                })
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Failed to detect security anomalies: {str(e)}")
            return []
    
    async def get_security_metrics(
        self,
        session: AsyncSession,
        metric_name: Optional[str] = None,
        time_window: str = '24h',
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get security metrics and statistics with Redis caching."""
        try:
            cache = await self._get_cache()
            
            # Create cache key for metrics
            metrics_key = self._generate_cache_key(
                "metrics", 
                metric_name or "all", 
                time_window, 
                str(user_id or "global")
            )
            
            # Check cache first
            cached_metrics = await cache.get(metrics_key)
            if cached_metrics is not None:
                self.logger.debug(f"Using cached metrics for time_window={time_window}, user_id={user_id}")
                return cached_metrics
            
            # Calculate time range
            if time_window == '1h':
                start_time = datetime.utcnow() - timedelta(hours=1)
            elif time_window == '24h':
                start_time = datetime.utcnow() - timedelta(hours=24)
            elif time_window == '7d':
                start_time = datetime.utcnow() - timedelta(days=7)
            else:
                start_time = datetime.utcnow() - timedelta(hours=24)
            
            # Get violation counts by severity
            violation_query = """
                SELECT severity, COUNT(*) as count
                FROM audit.security_violations
                WHERE created_at >= :start_time
                GROUP BY severity
            """
            
            violations_result = await session.execute(
                text(violation_query), 
                {'start_time': start_time}
            )
            
            violations_by_severity = {
                row.severity: row.count for row in violations_result.fetchall()
            }
            
            # Get data access statistics
            access_query = """
                SELECT 
                    service_name,
                    access_type,
                    COUNT(*) as access_count,
                    SUM(row_count) as total_rows,
                    COUNT(CASE WHEN sensitive_data_accessed THEN 1 END) as sensitive_access_count
                FROM audit.data_access_log
                WHERE created_at >= :start_time
            """
            
            if user_id:
                access_query += " AND user_id = :user_id"
            
            access_query += " GROUP BY service_name, access_type"
            
            params = {'start_time': start_time}
            if user_id:
                params['user_id'] = user_id
            
            access_result = await session.execute(text(access_query), params)
            
            access_stats = []
            for row in access_result.fetchall():
                access_stats.append({
                    'service_name': row.service_name,
                    'access_type': row.access_type,
                    'access_count': row.access_count,
                    'total_rows': row.total_rows,
                    'sensitive_access_count': row.sensitive_access_count
                })
            
            # Get user activity statistics
            user_query = """
                SELECT 
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(DISTINCT session_id) as active_sessions
                FROM audit.data_access_log
                WHERE created_at >= :start_time
            """
            
            user_result = await session.execute(text(user_query), {'start_time': start_time})
            user_stats = user_result.fetchone()
            
            metrics_data = {
                'time_window': time_window,
                'start_time': start_time.isoformat(),
                'violations_by_severity': violations_by_severity,
                'access_statistics': access_stats,
                'user_activity': {
                    'active_users': user_stats.active_users,
                    'active_sessions': user_stats.active_sessions
                },
                'generated_at': datetime.utcnow().isoformat(),
                'cache_status': 'fresh'
            }
            
            # Cache the metrics data
            await cache.set(metrics_key, metrics_data, ttl=self.metrics_cache_ttl)
            
            return metrics_data
            
        except Exception as e:
            self.logger.error(f"Failed to get security metrics: {str(e)}")
            return {}
    
    async def cleanup_old_audit_data(self, session: AsyncSession) -> int:
        """Clean up old audit data according to retention policies."""
        try:
            result = await session.execute(text("SELECT audit.cleanup_old_data()"))
            rows_deleted = result.scalar()
            
            self.logger.info(f"Cleaned up {rows_deleted} old audit records")
            return rows_deleted
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old audit data: {str(e)}")
            return 0
    
    async def anonymize_user_data(self, session: AsyncSession, user_id: int) -> bool:
        """Anonymize user data for GDPR compliance."""
        try:
            await session.execute(text("SELECT anonymize_user_data(:user_id)"), {'user_id': user_id})
            await session.commit()
            
            self.logger.info(f"Successfully anonymized data for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to anonymize user data: {str(e)}")
            await session.rollback()
            return False
    
    async def _check_access_anomalies(
        self, 
        session: AsyncSession, 
        user_id: int, 
        service_name: str
    ) -> None:
        """Check for anomalous access patterns with Redis caching."""
        try:
            cache = await self._get_cache()
            anomaly_key = self._generate_cache_key("anomaly_check", user_id, service_name)
            
            # Check if we've recently checked anomalies for this user/service
            recent_check = await cache.get(anomaly_key)
            if recent_check is not None:
                # Skip check if done recently (avoid excessive DB queries)
                return
            
            # Check access frequency in the last hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            result = await session.execute(
                text("""
                    SELECT COUNT(*) as access_count
                    FROM audit.data_access_log
                    WHERE user_id = :user_id 
                    AND service_name = :service_name
                    AND created_at >= :one_hour_ago
                """),
                {
                    'user_id': user_id,
                    'service_name': service_name,
                    'one_hour_ago': one_hour_ago
                }
            )
            
            access_count = result.scalar()
            
            # Cache the anomaly check result (prevents repeated checks)
            await cache.set(anomaly_key, {
                'checked_at': datetime.utcnow().isoformat(),
                'access_count': access_count
            }, ttl=300)  # Cache for 5 minutes
            
            # Alert if user has made more than 50 requests in the last hour
            if access_count > 50:
                await self.log_security_violation(
                    session=session,
                    violation_type='EXCESSIVE_ACCESS_RATE',
                    severity='MEDIUM',
                    violation_details={
                        'access_count': access_count,
                        'time_window': '1 hour',
                        'threshold': 50,
                        'service_name': service_name
                    },
                    user_id=user_id,
                    blocked=False
                )
            
        except Exception as e:
            self.logger.error(f"Failed to check access anomalies: {str(e)}")
    
    async def _trigger_security_alert(self, violation: SecurityViolation) -> None:
        """Trigger immediate security alert for critical violations."""
        try:
            # In a real implementation, this would send alerts via email, Slack, etc.
            self.logger.critical(
                f"CRITICAL SECURITY VIOLATION: {violation.violation_type} "
                f"for user {violation.user_id} at {violation.created_at}. "
                f"Details: {violation.violation_details}"
            )
            
            # Here you could integrate with alerting systems:
            # - Send email to security team
            # - Post to Slack security channel
            # - Create incident in PagerDuty
            # - Update security dashboard
            
        except Exception as e:
            self.logger.error(f"Failed to trigger security alert: {str(e)}")
    
    async def log_security_action(
        self,
        session: AsyncSession,
        action_type: str,
        target: str,
        reason: str,
        evidence: Dict[str, Any],
        severity: str = "MEDIUM",
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        auto_created: bool = True
    ) -> SecurityAction:
        """Log a security action to the database."""
        try:
            from shared.database.models.security_models import (
                SecurityActionType,
                SecurityActionStatus,
                ViolationSeverity
            )
            
            security_action = SecurityAction(
                action_type=SecurityActionType(action_type),
                target=target,
                reason=reason,
                evidence=evidence,
                severity=ViolationSeverity(severity),
                status=SecurityActionStatus.ACTIVE,
                auto_created=auto_created,
                created_by_user_id=user_id,
                created_by_session_id=session_id
            )
            
            session.add(security_action)
            await session.commit()
            
            self.logger.info(f"Logged security action: {action_type} for {target}")
            return security_action
            
        except Exception as e:
            self.logger.error(f"Failed to log security action: {str(e)}")
            await session.rollback()
            raise


# Global security audit service instance
security_audit_service = SecurityAuditService()