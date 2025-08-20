#!/usr/bin/env python3
"""
Intelligent Caching Layer
Smart caching for agent outputs with adaptive invalidation and performance optimization
"""
import json
import pickle
import time
import hashlib
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
import threading
import asyncio
from functools import wraps
import psutil


@dataclass
class CacheEntry:
    """Individual cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    agent_name: str = ""
    task_signature: str = ""
    execution_time: float = 0.0
    size_bytes: int = 0
    dependencies: List[str] = field(default_factory=list)
    ttl_seconds: Optional[int] = None
    compression: bool = False
    invalidation_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_size_bytes: int = 0
    entries_count: int = 0
    evictions_count: int = 0
    average_response_time: float = 0.0
    space_saved_bytes: int = 0


class IntelligentCache:
    """Smart caching for agent outputs"""
    
    def __init__(self, cache_dir: str = ".claude/cache", max_size_mb: int = 100):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = self.cache_dir / "cache_data.json"
        self.binary_cache_dir = self.cache_dir / "binary"
        self.binary_cache_dir.mkdir(exist_ok=True)
        
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.cache = {}  # In-memory cache
        self.cache_stats = CacheStats()
        self.lock = threading.RLock()
        
        # Load existing cache
        self._load_cache()
        
        # Cache invalidation patterns
        self.invalidation_patterns = {
            'file_modified': self._check_file_modification,
            'time_based': self._check_time_expiry,
            'dependency_changed': self._check_dependency_changes,
            'agent_updated': self._check_agent_updates,
            'project_changed': self._check_project_changes
        }
        
        # Agent-specific cache policies
        self.agent_policies = {
            'codebase-research-analyst': {
                'default_ttl': 3600,  # 1 hour
                'cache_expensive_only': True,
                'min_execution_time': 2.0,
                'compression': True
            },
            'schema-database-expert': {
                'default_ttl': 1800,  # 30 minutes
                'cache_expensive_only': True,
                'min_execution_time': 1.0,
                'dependency_tracking': True
            },
            'ui-regression-debugger': {
                'default_ttl': 600,  # 10 minutes
                'cache_expensive_only': True,
                'min_execution_time': 5.0,
                'compression': False  # Screenshots are already compressed
            },
            'security-validator': {
                'default_ttl': 900,  # 15 minutes
                'cache_expensive_only': True,
                'min_execution_time': 3.0,
                'invalidate_on_code_change': True
            }
        }
        
        # Task-specific caching rules
        self.task_caching_rules = {
            'code_search': {'cacheable': True, 'ttl': 1800},
            'file_analysis': {'cacheable': True, 'ttl': 900, 'invalidate_on_file_change': True},
            'ui_testing': {'cacheable': True, 'ttl': 300},
            'security_scan': {'cacheable': True, 'ttl': 600, 'invalidate_on_code_change': True},
            'database_query': {'cacheable': True, 'ttl': 300, 'dependency_tracking': True}
        }
        
        # Start background maintenance
        self._start_background_maintenance()
    
    def _load_cache(self):
        """Load cache from persistent storage"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                
                # Load cache entries
                for key, entry_data in data.get('entries', {}).items():
                    entry = CacheEntry(
                        key=entry_data['key'],
                        value=entry_data.get('value'),  # May be None for binary data
                        created_at=datetime.fromisoformat(entry_data['created_at']),
                        last_accessed=datetime.fromisoformat(entry_data['last_accessed']),
                        access_count=entry_data.get('access_count', 0),
                        agent_name=entry_data.get('agent_name', ''),
                        task_signature=entry_data.get('task_signature', ''),
                        execution_time=entry_data.get('execution_time', 0.0),
                        size_bytes=entry_data.get('size_bytes', 0),
                        dependencies=entry_data.get('dependencies', []),
                        ttl_seconds=entry_data.get('ttl_seconds'),
                        compression=entry_data.get('compression', False),
                        invalidation_rules=entry_data.get('invalidation_rules', {})
                    )
                    
                    # Load binary data if needed
                    if entry.compression or entry.size_bytes > 1024:
                        binary_file = self.binary_cache_dir / f"{key}.pkl.gz"
                        if binary_file.exists():
                            with gzip.open(binary_file, 'rb') as bf:
                                entry.value = pickle.load(bf)
                    
                    self.cache[key] = entry
                
                # Load stats
                stats_data = data.get('stats', {})
                self.cache_stats = CacheStats(
                    total_requests=stats_data.get('total_requests', 0),
                    cache_hits=stats_data.get('cache_hits', 0),
                    cache_misses=stats_data.get('cache_misses', 0),
                    total_size_bytes=stats_data.get('total_size_bytes', 0),
                    entries_count=len(self.cache),
                    evictions_count=stats_data.get('evictions_count', 0),
                    average_response_time=stats_data.get('average_response_time', 0.0),
                    space_saved_bytes=stats_data.get('space_saved_bytes', 0)
                )
                
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
                self.cache = {}
                self.cache_stats = CacheStats()
    
    def _save_cache(self):
        """Save cache to persistent storage"""
        try:
            entries_data = {}
            
            for key, entry in self.cache.items():
                entry_data = {
                    'key': entry.key,
                    'created_at': entry.created_at.isoformat(),
                    'last_accessed': entry.last_accessed.isoformat(),
                    'access_count': entry.access_count,
                    'agent_name': entry.agent_name,
                    'task_signature': entry.task_signature,
                    'execution_time': entry.execution_time,
                    'size_bytes': entry.size_bytes,
                    'dependencies': entry.dependencies,
                    'ttl_seconds': entry.ttl_seconds,
                    'compression': entry.compression,
                    'invalidation_rules': entry.invalidation_rules
                }
                
                # Store small values inline, large ones as binary files
                if not entry.compression and entry.size_bytes <= 1024:
                    entry_data['value'] = entry.value
                else:
                    # Save to binary file
                    binary_file = self.binary_cache_dir / f"{key}.pkl.gz"
                    with gzip.open(binary_file, 'wb') as bf:
                        pickle.dump(entry.value, bf)
                    entry_data['value'] = None
                
                entries_data[key] = entry_data
            
            # Save main cache file
            data = {
                'entries': entries_data,
                'stats': {
                    'total_requests': self.cache_stats.total_requests,
                    'cache_hits': self.cache_stats.cache_hits,
                    'cache_misses': self.cache_stats.cache_misses,
                    'total_size_bytes': self.cache_stats.total_size_bytes,
                    'evictions_count': self.cache_stats.evictions_count,
                    'average_response_time': self.cache_stats.average_response_time,
                    'space_saved_bytes': self.cache_stats.space_saved_bytes
                },
                'last_saved': datetime.now().isoformat()
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def should_cache(self, agent: str, task: Dict[str, Any], result: Any, execution_time: float) -> bool:
        """Determine if result should be cached"""
        with self.lock:
            # Check agent-specific policies
            if agent in self.agent_policies:
                policy = self.agent_policies[agent]
                
                # Check minimum execution time
                if execution_time < policy.get('min_execution_time', 0.0):
                    return False
                
                # Check if only expensive operations should be cached
                if policy.get('cache_expensive_only', False) and execution_time < 2.0:
                    return False
            
            # Check task-specific rules
            task_type = task.get('action', 'unknown')
            if task_type in self.task_caching_rules:
                rule = self.task_caching_rules[task_type]
                if not rule.get('cacheable', True):
                    return False
            
            # Cache if expensive operation (> 5 seconds)
            if execution_time > 5.0:
                return True
            
            # Cache if frequently requested
            cache_key = self.generate_cache_key(agent, task)
            request_frequency = self._get_request_frequency(cache_key)
            if request_frequency > 3:
                return True
            
            # Cache if deterministic result
            if agent in ['codebase-research-analyst', 'schema-database-expert']:
                return True
            
            # Cache if result is large
            result_size = self._estimate_size(result)
            if result_size > 10000:  # 10KB
                return True
            
            return False
    
    def generate_cache_key(self, agent: str, task: Dict[str, Any], additional_context: str = "") -> str:
        """Generate unique cache key for agent/task combination"""
        # Create deterministic signature from task
        task_signature = {
            'agent': agent,
            'action': task.get('action', ''),
            'domain': task.get('domain', ''),
            'parameters': sorted(task.get('parameters', {}).items()) if isinstance(task.get('parameters'), dict) else [],
            'tools': sorted(task.get('tools_required', [])),
            'context': additional_context
        }
        
        signature_str = json.dumps(task_signature, sort_keys=True)
        return hashlib.sha256(signature_str.encode()).hexdigest()[:16]
    
    def get(self, cache_key: str) -> Optional[Any]:
        """Get cached value"""
        with self.lock:
            self.cache_stats.total_requests += 1
            
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                
                # Check if entry is valid
                if self._is_entry_valid(entry):
                    # Update access statistics
                    entry.last_accessed = datetime.now()
                    entry.access_count += 1
                    
                    self.cache_stats.cache_hits += 1
                    return entry.value
                else:
                    # Remove invalid entry
                    self._remove_entry(cache_key)
            
            self.cache_stats.cache_misses += 1
            return None
    
    def set(self, cache_key: str, value: Any, agent: str, task: Dict[str, Any], 
            execution_time: float, ttl_seconds: Optional[int] = None) -> bool:
        """Cache a value"""
        with self.lock:
            try:
                # Check if we should cache this
                if not self.should_cache(agent, task, value, execution_time):
                    return False
                
                # Estimate size
                value_size = self._estimate_size(value)
                
                # Check cache size limits
                if value_size > self.max_size_bytes * 0.1:  # Don't cache items > 10% of max size
                    return False
                
                # Ensure we have space
                self._ensure_space(value_size)
                
                # Determine TTL
                if ttl_seconds is None:
                    ttl_seconds = self._get_default_ttl(agent, task)
                
                # Determine if compression is needed
                should_compress = value_size > 1024 or agent in self.agent_policies and self.agent_policies[agent].get('compression', False)
                
                # Create cache entry
                entry = CacheEntry(
                    key=cache_key,
                    value=value,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    agent_name=agent,
                    task_signature=json.dumps(task, sort_keys=True),
                    execution_time=execution_time,
                    size_bytes=value_size,
                    ttl_seconds=ttl_seconds,
                    compression=should_compress,
                    dependencies=self._extract_dependencies(task),
                    invalidation_rules=self._get_invalidation_rules(agent, task)
                )
                
                # Store entry
                self.cache[cache_key] = entry
                
                # Update stats
                self.cache_stats.entries_count = len(self.cache)
                self.cache_stats.total_size_bytes += value_size
                self.cache_stats.space_saved_bytes += int(execution_time * 1000)  # Rough estimate
                
                return True
                
            except Exception as e:
                print(f"Error caching value: {e}")
                return False
    
    def get_or_execute(self, agent: str, task: Dict[str, Any], 
                      execute_func: Callable[[], Any], additional_context: str = "") -> Any:
        """Get from cache or execute function and cache result"""
        cache_key = self.generate_cache_key(agent, task, additional_context)
        
        # Try to get from cache
        cached_result = self.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Execute function and measure time
        start_time = time.time()
        result = execute_func()
        execution_time = time.time() - start_time
        
        # Cache the result
        self.set(cache_key, result, agent, task, execution_time)
        
        return result
    
    def invalidate(self, cache_key: str = None, agent: str = None, 
                  pattern: str = None, dependencies: List[str] = None) -> int:
        """Invalidate cache entries"""
        with self.lock:
            keys_to_remove = []
            
            if cache_key:
                # Invalidate specific key
                if cache_key in self.cache:
                    keys_to_remove.append(cache_key)
            
            if agent:
                # Invalidate all entries for an agent
                for key, entry in self.cache.items():
                    if entry.agent_name == agent:
                        keys_to_remove.append(key)
            
            if pattern:
                # Invalidate entries matching pattern
                for key, entry in self.cache.items():
                    if pattern in entry.task_signature:
                        keys_to_remove.append(key)
            
            if dependencies:
                # Invalidate entries with specific dependencies
                for key, entry in self.cache.items():
                    if any(dep in entry.dependencies for dep in dependencies):
                        keys_to_remove.append(key)
            
            # Remove duplicates and execute removal
            for key in set(keys_to_remove):
                self._remove_entry(key)
            
            return len(keys_to_remove)
    
    def invalidate_by_file_change(self, changed_files: List[str]) -> int:
        """Invalidate cache entries affected by file changes"""
        invalidated = 0
        
        with self.lock:
            for key, entry in list(self.cache.items()):
                should_invalidate = False
                
                # Check if any dependencies changed
                for changed_file in changed_files:
                    if any(changed_file in dep for dep in entry.dependencies):
                        should_invalidate = True
                        break
                
                # Check invalidation rules
                if entry.invalidation_rules.get('invalidate_on_code_change', False):
                    code_extensions = ['.py', '.js', '.ts', '.html', '.css']
                    if any(any(f.endswith(ext) for ext in code_extensions) for f in changed_files):
                        should_invalidate = True
                
                if should_invalidate:
                    self._remove_entry(key)
                    invalidated += 1
        
        return invalidated
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries"""
        with self.lock:
            current_time = datetime.now()
            expired_keys = []
            
            for key, entry in self.cache.items():
                if not self._is_entry_valid(entry, current_time):
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_entry(key)
            
            return len(expired_keys)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        with self.lock:
            hit_rate = (self.cache_stats.cache_hits / max(1, self.cache_stats.total_requests)) * 100
            
            return {
                'total_requests': self.cache_stats.total_requests,
                'cache_hits': self.cache_stats.cache_hits,
                'cache_misses': self.cache_stats.cache_misses,
                'hit_rate_percent': round(hit_rate, 2),
                'entries_count': len(self.cache),
                'total_size_kb': self.cache_stats.total_size_bytes / 1024,
                'max_size_kb': self.max_size_bytes / 1024,
                'space_utilization_percent': round((self.cache_stats.total_size_bytes / self.max_size_bytes) * 100, 2),
                'evictions_count': self.cache_stats.evictions_count,
                'estimated_time_saved_seconds': self.cache_stats.space_saved_bytes / 1000
            }
    
    def _is_entry_valid(self, entry: CacheEntry, current_time: datetime = None) -> bool:
        """Check if cache entry is still valid"""
        if current_time is None:
            current_time = datetime.now()
        
        # Check TTL
        if entry.ttl_seconds:
            expiry_time = entry.created_at + timedelta(seconds=entry.ttl_seconds)
            if current_time > expiry_time:
                return False
        
        # Check custom invalidation rules
        for rule_name, rule_check in self.invalidation_patterns.items():
            if rule_name in entry.invalidation_rules:
                if not rule_check(entry, current_time):
                    return False
        
        return True
    
    def _remove_entry(self, cache_key: str):
        """Remove entry from cache"""
        if cache_key in self.cache:
            entry = self.cache.pop(cache_key)
            self.cache_stats.total_size_bytes -= entry.size_bytes
            self.cache_stats.entries_count = len(self.cache)
            
            # Remove binary file if exists
            binary_file = self.binary_cache_dir / f"{cache_key}.pkl.gz"
            if binary_file.exists():
                binary_file.unlink()
    
    def _ensure_space(self, required_bytes: int):
        """Ensure we have enough space in cache"""
        while (self.cache_stats.total_size_bytes + required_bytes) > self.max_size_bytes:
            if not self._evict_least_valuable():
                break  # No more entries to evict
    
    def _evict_least_valuable(self) -> bool:
        """Evict the least valuable cache entry"""
        if not self.cache:
            return False
        
        # Score entries by value (access frequency, recency, size)
        scored_entries = []
        current_time = datetime.now()
        
        for key, entry in self.cache.items():
            age_hours = (current_time - entry.last_accessed).total_seconds() / 3600
            
            # Lower score = less valuable
            score = (
                entry.access_count * 0.4 +  # Access frequency
                (1 / max(1, age_hours)) * 0.3 +  # Recency
                (entry.execution_time / 10) * 0.2 +  # Original execution time
                (1 / max(1, entry.size_bytes / 1024)) * 0.1  # Size efficiency
            )
            
            scored_entries.append((key, score))
        
        # Remove lowest scoring entry
        scored_entries.sort(key=lambda x: x[1])
        least_valuable_key = scored_entries[0][0]
        
        self._remove_entry(least_valuable_key)
        self.cache_stats.evictions_count += 1
        
        return True
    
    def _get_default_ttl(self, agent: str, task: Dict[str, Any]) -> int:
        """Get default TTL for agent/task combination"""
        # Check agent policy
        if agent in self.agent_policies:
            return self.agent_policies[agent].get('default_ttl', 3600)
        
        # Check task rule
        task_type = task.get('action', 'unknown')
        if task_type in self.task_caching_rules:
            return self.task_caching_rules[task_type].get('ttl', 1800)
        
        # Default TTL
        return 1800  # 30 minutes
    
    def _extract_dependencies(self, task: Dict[str, Any]) -> List[str]:
        """Extract file dependencies from task"""
        dependencies = []
        
        # Extract file paths from task parameters
        for key, value in task.items():
            if isinstance(value, str):
                if '/' in value or '\\' in value:  # Likely a file path
                    dependencies.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and ('/' in item or '\\' in item):
                        dependencies.append(item)
        
        return dependencies
    
    def _get_invalidation_rules(self, agent: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get invalidation rules for agent/task"""
        rules = {}
        
        # Agent-specific rules
        if agent in self.agent_policies:
            policy = self.agent_policies[agent]
            if policy.get('invalidate_on_code_change', False):
                rules['invalidate_on_code_change'] = True
            if policy.get('dependency_tracking', False):
                rules['dependency_tracking'] = True
        
        # Task-specific rules
        task_type = task.get('action', 'unknown')
        if task_type in self.task_caching_rules:
            rule = self.task_caching_rules[task_type]
            if rule.get('invalidate_on_file_change', False):
                rules['invalidate_on_file_change'] = True
        
        return rules
    
    def _estimate_size(self, obj: Any) -> int:
        """Estimate object size in bytes"""
        try:
            if isinstance(obj, str):
                return len(obj.encode('utf-8'))
            elif isinstance(obj, (int, float)):
                return 8
            elif isinstance(obj, bool):
                return 1
            elif isinstance(obj, (list, tuple)):
                return sum(self._estimate_size(item) for item in obj)
            elif isinstance(obj, dict):
                return sum(self._estimate_size(k) + self._estimate_size(v) for k, v in obj.items())
            else:
                # Use pickle size as approximation
                return len(pickle.dumps(obj))
        except:
            return 1024  # Default estimate
    
    def _get_request_frequency(self, cache_key: str) -> int:
        """Get request frequency for cache key (simplified)"""
        if cache_key in self.cache:
            return self.cache[cache_key].access_count
        return 0
    
    def _check_file_modification(self, entry: CacheEntry, current_time: datetime) -> bool:
        """Check if dependent files have been modified"""
        for dep_path in entry.dependencies:
            file_path = Path(dep_path)
            if file_path.exists():
                modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if modified_time > entry.created_at:
                    return False
        return True
    
    def _check_time_expiry(self, entry: CacheEntry, current_time: datetime) -> bool:
        """Check time-based expiry"""
        if entry.ttl_seconds:
            expiry_time = entry.created_at + timedelta(seconds=entry.ttl_seconds)
            return current_time <= expiry_time
        return True
    
    def _check_dependency_changes(self, entry: CacheEntry, current_time: datetime) -> bool:
        """Check if dependencies have changed"""
        # Simplified implementation - in practice would check file hashes, etc.
        return True
    
    def _check_agent_updates(self, entry: CacheEntry, current_time: datetime) -> bool:
        """Check if agent has been updated"""
        # Simplified implementation - would check agent version/modification time
        return True
    
    def _check_project_changes(self, entry: CacheEntry, current_time: datetime) -> bool:
        """Check if project structure has changed"""
        # Simplified implementation - would check git commits, etc.
        return True
    
    def _start_background_maintenance(self):
        """Start background maintenance tasks"""
        def maintenance_loop():
            while True:
                try:
                    time.sleep(300)  # Run every 5 minutes
                    expired = self.cleanup_expired()
                    if expired > 0:
                        print(f"🧹 [CACHE] Cleaned up {expired} expired entries")
                    self._save_cache()
                except Exception as e:
                    print(f"Cache maintenance error: {e}")
        
        maintenance_thread = threading.Thread(target=maintenance_loop, daemon=True)
        maintenance_thread.start()


# Create cache decorator
def cache_result(agent_name: str, ttl_seconds: int = None):
    """Decorator to cache function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create task signature from function call
            task = {
                'action': func.__name__,
                'args': str(args),
                'kwargs': str(sorted(kwargs.items()))
            }
            
            def execute():
                return func(*args, **kwargs)
            
            return intelligent_cache.get_or_execute(agent_name, task, execute)
        
        return wrapper
    return decorator


# Global cache instance
intelligent_cache = IntelligentCache()

def get_or_execute(agent: str, task: Dict[str, Any], execute_func: Callable[[], Any]) -> Any:
    """Convenience function for cache-or-execute"""
    return intelligent_cache.get_or_execute(agent, task, execute_func)

def invalidate_cache(agent: str = None, pattern: str = None) -> int:
    """Convenience function for cache invalidation"""
    return intelligent_cache.invalidate(agent=agent, pattern=pattern)

def get_cache_stats() -> Dict[str, Any]:
    """Convenience function for cache stats"""
    return intelligent_cache.get_cache_stats()


if __name__ == "__main__":
    # Test the intelligent cache
    print("Testing Intelligent Caching Layer...")
    
    def expensive_operation():
        """Simulate expensive operation"""
        time.sleep(2)
        return {"result": "expensive_data", "timestamp": time.time()}
    
    # Test caching
    task = {
        'action': 'code_search',
        'domain': 'backend',
        'parameters': {'query': 'authentication'},
        'tools_required': ['grep', 'read']
    }
    
    print("🔄 First execution (should cache)...")
    start_time = time.time()
    result1 = get_or_execute('codebase-research-analyst', task, expensive_operation)
    first_duration = time.time() - start_time
    
    print("⚡ Second execution (should use cache)...")
    start_time = time.time()
    result2 = get_or_execute('codebase-research-analyst', task, expensive_operation)
    second_duration = time.time() - start_time
    
    print(f"\nResults:")
    print(f"  First execution: {first_duration:.2f}s")
    print(f"  Second execution: {second_duration:.2f}s")
    print(f"  Speedup: {first_duration / second_duration:.1f}x")
    
    # Show cache stats
    stats = get_cache_stats()
    print(f"\n📊 Cache Statistics:")
    for key, value in stats.items():
        print(f"  • {key}: {value}")
    
    # Test invalidation
    invalidated = invalidate_cache(agent='codebase-research-analyst')
    print(f"\n🗑️ Invalidated {invalidated} cache entries")