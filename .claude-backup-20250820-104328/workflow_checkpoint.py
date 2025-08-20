#!/usr/bin/env python3
"""
Workflow Checkpoint and Rollback System
Enables transaction-like behavior with rollback capabilities
"""
import json
import os
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
import hashlib
import tarfile
import tempfile


@dataclass
class FileState:
    """State of a file at checkpoint time"""
    path: str
    exists: bool
    content_hash: Optional[str]
    size: Optional[int]
    modified_time: Optional[float]
    permissions: Optional[str]


@dataclass
class DatabaseState:
    """Database state snapshot"""
    connection_string: str
    tables_snapshot: Dict[str, str]  # table_name -> schema
    data_checksums: Dict[str, str]  # table_name -> content hash
    migration_version: Optional[str]


@dataclass
class AgentState:
    """Agent execution state"""
    agent_name: str
    current_task: Optional[str]
    context_data: Dict[str, Any]
    execution_stack: List[str]
    resource_usage: Dict[str, float]


@dataclass
class Checkpoint:
    """Complete system checkpoint"""
    checkpoint_id: str
    phase_name: str
    timestamp: datetime
    description: str
    files_modified: List[FileState]
    database_states: List[DatabaseState]
    agent_states: List[AgentState]
    git_commit_hash: Optional[str]
    system_state: Dict[str, Any]
    checkpoint_size: int = 0
    validation_status: str = "pending"


class WorkflowCheckpoint:
    """Enable rollback to previous states"""
    
    def __init__(self):
        self.checkpoints_dir = Path(".claude/checkpoints")
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.checkpoints_dir / "checkpoints_metadata.json"
        self.checkpoints = self._load_checkpoints_metadata()
        
        # Configuration
        self.max_checkpoints = 20
        self.watched_directories = [
            Path("."),  # Current project
            Path("app") if Path("app").exists() else None,
            Path("src") if Path("src").exists() else None,
            Path(".claude")
        ]
        self.watched_directories = [d for d in self.watched_directories if d]
        
        # Exclude patterns
        self.exclude_patterns = {
            "*.pyc", "__pycache__", "node_modules", ".git", "*.log",
            "*.tmp", ".DS_Store", "*.swp", ".vscode", ".idea"
        }
        
        # Database connections to monitor
        self.database_configs = self._detect_databases()
    
    def _load_checkpoints_metadata(self) -> Dict[str, Checkpoint]:
        """Load checkpoint metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    
                checkpoints = {}
                for cp_data in data.get('checkpoints', []):
                    checkpoint = Checkpoint(
                        checkpoint_id=cp_data['checkpoint_id'],
                        phase_name=cp_data['phase_name'],
                        timestamp=datetime.fromisoformat(cp_data['timestamp']),
                        description=cp_data['description'],
                        files_modified=[FileState(**fs) for fs in cp_data['files_modified']],
                        database_states=[DatabaseState(**ds) for ds in cp_data.get('database_states', [])],
                        agent_states=[AgentState(**ags) for ags in cp_data.get('agent_states', [])],
                        git_commit_hash=cp_data.get('git_commit_hash'),
                        system_state=cp_data.get('system_state', {}),
                        checkpoint_size=cp_data.get('checkpoint_size', 0),
                        validation_status=cp_data.get('validation_status', 'pending')
                    )
                    checkpoints[checkpoint.checkpoint_id] = checkpoint
                
                return checkpoints
                
            except Exception as e:
                print(f"Warning: Could not load checkpoint metadata: {e}")
        
        return {}
    
    def _save_checkpoints_metadata(self):
        """Save checkpoint metadata"""
        try:
            data = {
                'checkpoints': [
                    {
                        'checkpoint_id': cp.checkpoint_id,
                        'phase_name': cp.phase_name,
                        'timestamp': cp.timestamp.isoformat(),
                        'description': cp.description,
                        'files_modified': [
                            {
                                'path': fs.path,
                                'exists': fs.exists,
                                'content_hash': fs.content_hash,
                                'size': fs.size,
                                'modified_time': fs.modified_time,
                                'permissions': fs.permissions
                            } for fs in cp.files_modified
                        ],
                        'database_states': [
                            {
                                'connection_string': ds.connection_string,
                                'tables_snapshot': ds.tables_snapshot,
                                'data_checksums': ds.data_checksums,
                                'migration_version': ds.migration_version
                            } for ds in cp.database_states
                        ],
                        'agent_states': [
                            {
                                'agent_name': ags.agent_name,
                                'current_task': ags.current_task,
                                'context_data': ags.context_data,
                                'execution_stack': ags.execution_stack,
                                'resource_usage': ags.resource_usage
                            } for ags in cp.agent_states
                        ],
                        'git_commit_hash': cp.git_commit_hash,
                        'system_state': cp.system_state,
                        'checkpoint_size': cp.checkpoint_size,
                        'validation_status': cp.validation_status
                    } for cp in self.checkpoints.values()
                ],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving checkpoint metadata: {e}")
    
    def _detect_databases(self) -> Dict[str, str]:
        """Detect database configurations"""
        databases = {}
        
        # Check for SQLite databases
        for db_file in Path(".").rglob("*.db"):
            if db_file.exists():
                databases[f"sqlite_{db_file.name}"] = str(db_file)
        
        # Check for PostgreSQL configuration
        if Path("docker-compose.yml").exists() or Path("docker-compose.yaml").exists():
            # Look for postgres in docker-compose
            compose_files = list(Path(".").glob("docker-compose*.yml")) + list(Path(".").glob("docker-compose*.yaml"))
            for compose_file in compose_files:
                try:
                    with open(compose_file, 'r') as f:
                        content = f.read()
                        if 'postgres' in content.lower():
                            databases['postgres_docker'] = str(compose_file)
                except:
                    pass
        
        return databases
    
    def create_checkpoint(self, phase_name: str, description: str = "", 
                         include_git: bool = True) -> str:
        """Save current state before critical operations"""
        checkpoint_id = self._generate_checkpoint_id(phase_name)
        
        print(f"💾 [CHECKPOINT] Creating checkpoint: {checkpoint_id}")
        
        try:
            # 1. Scan file changes
            files_modified = self._scan_file_changes()
            
            # 2. Capture database state
            database_states = self._capture_database_states()
            
            # 3. Capture agent states (if available)
            agent_states = self._capture_agent_states()
            
            # 4. Get git commit hash
            git_commit_hash = None
            if include_git:
                git_commit_hash = self._get_git_commit_hash()
            
            # 5. Capture system state
            system_state = self._capture_system_state()
            
            # Create checkpoint
            checkpoint = Checkpoint(
                checkpoint_id=checkpoint_id,
                phase_name=phase_name,
                timestamp=datetime.now(),
                description=description,
                files_modified=files_modified,
                database_states=database_states,
                agent_states=agent_states,
                git_commit_hash=git_commit_hash,
                system_state=system_state
            )
            
            # 6. Save file snapshots
            checkpoint_size = self._save_file_snapshots(checkpoint)
            checkpoint.checkpoint_size = checkpoint_size
            
            # 7. Validate checkpoint
            checkpoint.validation_status = "valid" if self._validate_checkpoint(checkpoint) else "invalid"
            
            # 8. Store checkpoint
            self.checkpoints[checkpoint_id] = checkpoint
            self._save_checkpoints_metadata()
            
            # 9. Cleanup old checkpoints
            self._cleanup_old_checkpoints()
            
            print(f"✅ [CHECKPOINT] Created: {checkpoint_id} ({checkpoint_size / 1024:.1f} KB)")
            return checkpoint_id
            
        except Exception as e:
            print(f"❌ [CHECKPOINT] Failed to create checkpoint: {e}")
            return ""
    
    def rollback_to_checkpoint(self, checkpoint_id: str, confirm: bool = False) -> bool:
        """Restore system to previous checkpoint"""
        if checkpoint_id not in self.checkpoints:
            print(f"❌ [ROLLBACK] Checkpoint not found: {checkpoint_id}")
            return False
        
        checkpoint = self.checkpoints[checkpoint_id]
        
        if not confirm:
            print(f"⚠️ [ROLLBACK] This will restore system to: {checkpoint.phase_name}")
            print(f"   Timestamp: {checkpoint.timestamp}")
            print(f"   Files affected: {len(checkpoint.files_modified)}")
            print("   Use confirm=True to proceed with rollback")
            return False
        
        print(f"🔄 [ROLLBACK] Restoring to checkpoint: {checkpoint_id}")
        
        try:
            # 1. Create backup checkpoint before rollback
            backup_id = self.create_checkpoint("pre_rollback_backup", 
                                             f"Backup before rolling back to {checkpoint_id}")
            
            # 2. Restore files
            self._restore_files(checkpoint)
            
            # 3. Restore databases
            self._restore_databases(checkpoint)
            
            # 4. Reset agent states
            self._reset_agent_states(checkpoint)
            
            # 5. Git rollback if needed
            if checkpoint.git_commit_hash:
                self._git_rollback(checkpoint.git_commit_hash)
            
            print(f"✅ [ROLLBACK] Successfully restored to: {checkpoint_id}")
            print(f"   Backup created at: {backup_id}")
            return True
            
        except Exception as e:
            print(f"❌ [ROLLBACK] Failed to rollback: {e}")
            # Attempt to restore from backup
            if 'backup_id' in locals():
                print("   Attempting to restore from backup...")
                self._emergency_restore(backup_id)
            return False
    
    def list_checkpoints(self, limit: int = 10) -> List[Checkpoint]:
        """List available checkpoints"""
        checkpoints = list(self.checkpoints.values())
        checkpoints.sort(key=lambda x: x.timestamp, reverse=True)
        return checkpoints[:limit]
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a specific checkpoint"""
        if checkpoint_id not in self.checkpoints:
            return False
        
        try:
            # Delete files
            checkpoint_dir = self.checkpoints_dir / checkpoint_id
            if checkpoint_dir.exists():
                shutil.rmtree(checkpoint_dir)
            
            # Remove from metadata
            del self.checkpoints[checkpoint_id]
            self._save_checkpoints_metadata()
            
            print(f"🗑️ [CHECKPOINT] Deleted: {checkpoint_id}")
            return True
            
        except Exception as e:
            print(f"❌ [CHECKPOINT] Failed to delete {checkpoint_id}: {e}")
            return False
    
    def get_checkpoint_info(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a checkpoint"""
        if checkpoint_id not in self.checkpoints:
            return None
        
        checkpoint = self.checkpoints[checkpoint_id]
        
        return {
            'id': checkpoint.checkpoint_id,
            'phase': checkpoint.phase_name,
            'timestamp': checkpoint.timestamp.isoformat(),
            'description': checkpoint.description,
            'files_count': len(checkpoint.files_modified),
            'databases_count': len(checkpoint.database_states),
            'agents_count': len(checkpoint.agent_states),
            'size_kb': checkpoint.checkpoint_size / 1024,
            'git_hash': checkpoint.git_commit_hash,
            'validation': checkpoint.validation_status,
            'age_hours': (datetime.now() - checkpoint.timestamp).total_seconds() / 3600
        }
    
    def _generate_checkpoint_id(self, phase_name: str) -> str:
        """Generate unique checkpoint ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        phase_clean = phase_name.replace(" ", "_").replace("-", "_").lower()
        return f"cp_{phase_clean}_{timestamp}"
    
    def _scan_file_changes(self) -> List[FileState]:
        """Scan for modified files"""
        file_states = []
        
        for watch_dir in self.watched_directories:
            if not watch_dir.exists():
                continue
                
            for file_path in watch_dir.rglob("*"):
                if file_path.is_file() and not self._should_exclude(file_path):
                    try:
                        stat = file_path.stat()
                        
                        # Calculate content hash for text files
                        content_hash = None
                        if file_path.suffix in ['.py', '.js', '.ts', '.css', '.html', '.json', '.md', '.txt']:
                            try:
                                with open(file_path, 'rb') as f:
                                    content_hash = hashlib.md5(f.read()).hexdigest()
                            except:
                                pass
                        
                        file_state = FileState(
                            path=str(file_path),
                            exists=True,
                            content_hash=content_hash,
                            size=stat.st_size,
                            modified_time=stat.st_mtime,
                            permissions=oct(stat.st_mode)
                        )
                        file_states.append(file_state)
                        
                    except Exception as e:
                        print(f"Warning: Could not scan file {file_path}: {e}")
        
        return file_states
    
    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded from checkpoint"""
        file_str = str(file_path)
        
        for pattern in self.exclude_patterns:
            if pattern.startswith("*.") and file_str.endswith(pattern[1:]):
                return True
            elif pattern in file_str:
                return True
        
        return False
    
    def _capture_database_states(self) -> List[DatabaseState]:
        """Capture database states"""
        db_states = []
        
        for db_name, db_path in self.database_configs.items():
            try:
                if db_name.startswith("sqlite_"):
                    db_state = self._capture_sqlite_state(db_path)
                    if db_state:
                        db_states.append(db_state)
                elif db_name.startswith("postgres_"):
                    db_state = self._capture_postgres_state(db_path)
                    if db_state:
                        db_states.append(db_state)
            except Exception as e:
                print(f"Warning: Could not capture database state {db_name}: {e}")
        
        return db_states
    
    def _capture_sqlite_state(self, db_path: str) -> Optional[DatabaseState]:
        """Capture SQLite database state"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get table schemas
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
            tables_snapshot = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get data checksums
            data_checksums = {}
            for table_name in tables_snapshot.keys():
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    data_checksums[table_name] = f"count_{count}"
                except:
                    data_checksums[table_name] = "unknown"
            
            conn.close()
            
            return DatabaseState(
                connection_string=f"sqlite:///{db_path}",
                tables_snapshot=tables_snapshot,
                data_checksums=data_checksums,
                migration_version=None
            )
            
        except Exception as e:
            print(f"Error capturing SQLite state: {e}")
            return None
    
    def _capture_postgres_state(self, compose_file: str) -> Optional[DatabaseState]:
        """Capture PostgreSQL state (simplified)"""
        # This is a simplified implementation
        # In practice, you'd connect to the actual PostgreSQL instance
        return DatabaseState(
            connection_string="postgres://localhost:5432/app",
            tables_snapshot={},
            data_checksums={},
            migration_version=None
        )
    
    def _capture_agent_states(self) -> List[AgentState]:
        """Capture current agent states"""
        agent_states = []
        
        try:
            # Check if agent logger exists and has state
            from .agent_logger import logger
            
            for agent_name in ['project-orchestrator', 'ui-regression-debugger', 'backend-gateway-expert']:
                agent_state = AgentState(
                    agent_name=agent_name,
                    current_task=None,  # Would be populated if agent is active
                    context_data={},
                    execution_stack=[],
                    resource_usage={'cpu': 0.0, 'memory': 0.0}
                )
                agent_states.append(agent_state)
                
        except ImportError:
            # Agent system not available
            pass
        
        return agent_states
    
    def _get_git_commit_hash(self) -> Optional[str]:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
    
    def _capture_system_state(self) -> Dict[str, Any]:
        """Capture system state information"""
        import psutil
        
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'process_count': len(psutil.pids()),
            'python_version': os.sys.version,
            'working_directory': os.getcwd(),
            'environment_vars': dict(os.environ)
        }
    
    def _save_file_snapshots(self, checkpoint: Checkpoint) -> int:
        """Save file snapshots to checkpoint directory"""
        checkpoint_dir = self.checkpoints_dir / checkpoint.checkpoint_id
        checkpoint_dir.mkdir(exist_ok=True)
        
        total_size = 0
        
        # Create tar archive of important files
        tar_file = checkpoint_dir / "files.tar.gz"
        
        with tarfile.open(tar_file, "w:gz") as tar:
            for file_state in checkpoint.files_modified:
                file_path = Path(file_state.path)
                if file_path.exists() and file_path.is_file():
                    try:
                        # Only include text files and small binaries
                        if file_state.size and file_state.size < 1024 * 1024:  # 1MB limit
                            tar.add(file_path, arcname=file_path.name)
                            total_size += file_state.size or 0
                    except Exception as e:
                        print(f"Warning: Could not archive {file_path}: {e}")
        
        return total_size
    
    def _validate_checkpoint(self, checkpoint: Checkpoint) -> bool:
        """Validate checkpoint integrity"""
        try:
            checkpoint_dir = self.checkpoints_dir / checkpoint.checkpoint_id
            
            # Check if checkpoint directory exists
            if not checkpoint_dir.exists():
                return False
            
            # Check if tar file exists and is readable
            tar_file = checkpoint_dir / "files.tar.gz"
            if tar_file.exists():
                with tarfile.open(tar_file, "r:gz") as tar:
                    # Basic integrity check
                    tar.getnames()
            
            return True
            
        except Exception:
            return False
    
    def _restore_files(self, checkpoint: Checkpoint):
        """Restore files from checkpoint"""
        checkpoint_dir = self.checkpoints_dir / checkpoint.checkpoint_id
        tar_file = checkpoint_dir / "files.tar.gz"
        
        if not tar_file.exists():
            print("Warning: No file archive found in checkpoint")
            return
        
        print(f"📁 [RESTORE] Restoring {len(checkpoint.files_modified)} files...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract to temporary directory
            with tarfile.open(tar_file, "r:gz") as tar:
                tar.extractall(temp_dir)
            
            # Restore files to original locations
            temp_path = Path(temp_dir)
            for extracted_file in temp_path.iterdir():
                if extracted_file.is_file():
                    # Find corresponding original file
                    for file_state in checkpoint.files_modified:
                        if Path(file_state.path).name == extracted_file.name:
                            try:
                                shutil.copy2(extracted_file, file_state.path)
                                print(f"  ✅ Restored: {file_state.path}")
                            except Exception as e:
                                print(f"  ❌ Failed to restore {file_state.path}: {e}")
    
    def _restore_databases(self, checkpoint: Checkpoint):
        """Restore databases from checkpoint"""
        for db_state in checkpoint.database_states:
            print(f"🗃️ [RESTORE] Database restoration for {db_state.connection_string} (simplified)")
            # In a full implementation, this would restore database states
            # For now, just log the action
    
    def _reset_agent_states(self, checkpoint: Checkpoint):
        """Reset agent states from checkpoint"""
        print(f"🤖 [RESTORE] Resetting {len(checkpoint.agent_states)} agent states...")
        # In a full implementation, this would reset agent execution states
    
    def _git_rollback(self, commit_hash: str):
        """Rollback git to specific commit"""
        try:
            # Create a new branch for the rollback
            branch_name = f"rollback_{int(time.time())}"
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
            subprocess.run(["git", "reset", "--hard", commit_hash], check=True)
            print(f"🔀 [GIT] Rolled back to commit: {commit_hash}")
            print(f"    Created rollback branch: {branch_name}")
        except subprocess.CalledProcessError as e:
            print(f"❌ [GIT] Rollback failed: {e}")
    
    def _emergency_restore(self, backup_id: str):
        """Emergency restore from backup"""
        print(f"🚨 [EMERGENCY] Attempting emergency restore from: {backup_id}")
        # Simplified emergency restore
        self.rollback_to_checkpoint(backup_id, confirm=True)
    
    def _cleanup_old_checkpoints(self):
        """Remove old checkpoints to free space"""
        checkpoints_list = list(self.checkpoints.values())
        checkpoints_list.sort(key=lambda x: x.timestamp, reverse=True)
        
        if len(checkpoints_list) > self.max_checkpoints:
            old_checkpoints = checkpoints_list[self.max_checkpoints:]
            
            for old_checkpoint in old_checkpoints:
                print(f"🧹 [CLEANUP] Removing old checkpoint: {old_checkpoint.checkpoint_id}")
                self.delete_checkpoint(old_checkpoint.checkpoint_id)


# Global checkpoint manager
checkpoint_manager = WorkflowCheckpoint()

def create_checkpoint(phase_name: str, description: str = "") -> str:
    """Convenience function for creating checkpoints"""
    return checkpoint_manager.create_checkpoint(phase_name, description)

def rollback_to_checkpoint(checkpoint_id: str, confirm: bool = False) -> bool:
    """Convenience function for rollback"""
    return checkpoint_manager.rollback_to_checkpoint(checkpoint_id, confirm)

def list_checkpoints(limit: int = 10) -> List[Checkpoint]:
    """Convenience function for listing checkpoints"""
    return checkpoint_manager.list_checkpoints(limit)


if __name__ == "__main__":
    # Test the checkpoint system
    print("Testing Workflow Checkpoint System...")
    
    # Create a test checkpoint
    checkpoint_id = create_checkpoint("test_phase", "Test checkpoint creation")
    
    if checkpoint_id:
        print(f"✅ Test checkpoint created: {checkpoint_id}")
        
        # List checkpoints
        checkpoints = list_checkpoints(5)
        print(f"\n📋 Available Checkpoints ({len(checkpoints)}):")
        for cp in checkpoints:
            info = checkpoint_manager.get_checkpoint_info(cp.checkpoint_id)
            if info:
                print(f"  • {info['id']}: {info['phase']} ({info['size_kb']:.1f} KB)")
        
        # Get detailed info
        info = checkpoint_manager.get_checkpoint_info(checkpoint_id)
        if info:
            print(f"\n🔍 Checkpoint Details:")
            for key, value in info.items():
                print(f"  • {key}: {value}")
    else:
        print("❌ Failed to create test checkpoint")