#!/usr/bin/env python3
"""
Orchestration Todo Manager
Handles cross-session todo coordination, context integration, and persistent state management
for the AIWFE orchestration system.

Version: 1.0
Compatible with: unified-orchestration-config.yaml v3.0
"""

import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
import argparse
from pathlib import Path


@dataclass
class OrchestrationTodo:
    """Represents a persistent orchestration todo with full metadata."""
    id: str
    content: str
    priority: str  # critical, high, medium, low, backlog
    status: str    # pending, in_progress, completed, blocked, cancelled, deferred
    context_tags: List[str]
    related_issues: List[str]
    created_date: str
    updated_date: str
    assigned_agent: Optional[str] = None
    completion_evidence: Optional[str] = None
    estimated_effort: str = "medium"  # low, medium, high
    dependencies: List[str] = None
    urgency_score: int = 50  # 0-100
    impact_score: int = 50   # 0-100
    description: Optional[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

    @property
    def priority_score(self) -> int:
        """Calculate combined priority score."""
        return int((self.urgency_score + self.impact_score) / 2)

    @property
    def is_blocking(self) -> bool:
        """Check if this todo blocks other work."""
        return self.priority in ["critical", "high"] and self.status in ["pending", "in_progress"]


class OrchestrationTodoManager:
    """Manages persistent todos across orchestration sessions."""
    
    def __init__(self, todos_file: str = ".claude/orchestration_todos.json"):
        self.todos_file = Path(todos_file).resolve()
        self.todos_file.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load_todos()

    def _load_todos(self) -> Dict[str, Any]:
        """Load todos from persistent storage."""
        if not self.todos_file.exists():
            return self._create_empty_structure()
        
        try:
            with open(self.todos_file, 'r') as f:
                data = json.load(f)
                # Migrate old format if needed
                if "metadata" not in data:
                    data = self._migrate_to_new_format(data)
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            print(f"Warning: Could not load {self.todos_file}, creating new structure")
            return self._create_empty_structure()

    def _create_empty_structure(self) -> Dict[str, Any]:
        """Create empty todo structure."""
        return {
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "total_todos": 0,
                "priority_distribution": {
                    "critical": 0, "high": 0, "medium": 0, "low": 0, "backlog": 0
                },
                "status_distribution": {
                    "pending": 0, "in_progress": 0, "blocked": 0,
                    "completed": 0, "cancelled": 0, "deferred": 0
                }
            },
            "todos": [],
            "completed_todos": [],
            "archived_todos": [],
            "recurring_patterns": {},
            "workflow_insights": {
                "common_failure_points": [],
                "successful_resolution_patterns": []
            }
        }

    def _migrate_to_new_format(self, old_data: Dict) -> Dict[str, Any]:
        """Migrate old format to new structure."""
        new_data = self._create_empty_structure()
        if "todos" in old_data:
            new_data["todos"] = old_data["todos"]
        return new_data

    def _save_todos(self):
        """Save todos to persistent storage."""
        self._update_metadata()
        with open(self.todos_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def _update_metadata(self):
        """Update metadata statistics."""
        todos = self.data["todos"]
        self.data["metadata"]["last_updated"] = datetime.now().isoformat()
        self.data["metadata"]["total_todos"] = len(todos)
        
        # Update priority distribution
        priority_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0, "backlog": 0}
        status_dist = {"pending": 0, "in_progress": 0, "blocked": 0, "completed": 0, "cancelled": 0, "deferred": 0}
        
        for todo in todos:
            priority_dist[todo.get("priority", "medium")] += 1
            status_dist[todo.get("status", "pending")] += 1
        
        self.data["metadata"]["priority_distribution"] = priority_dist
        self.data["metadata"]["status_distribution"] = status_dist

    def add_todo(self, content: str, priority: str = "medium", 
                 context_tags: List[str] = None, assigned_agent: str = None,
                 description: str = None, urgency_score: int = 50, 
                 impact_score: int = 50, dependencies: List[str] = None) -> str:
        """Add a new todo."""
        todo_id = f"{'-'.join(content.lower().split()[:3])}-{str(uuid.uuid4())[:3]}"
        
        todo = OrchestrationTodo(
            id=todo_id,
            content=content,
            priority=priority,
            status="pending",
            context_tags=context_tags or [],
            related_issues=[],
            created_date=datetime.now().isoformat(),
            updated_date=datetime.now().isoformat(),
            assigned_agent=assigned_agent,
            description=description,
            urgency_score=urgency_score,
            impact_score=impact_score,
            dependencies=dependencies or []
        )
        
        self.data["todos"].append(asdict(todo))
        self._save_todos()
        return todo_id

    def update_todo_status(self, todo_id: str, status: str, 
                          completion_evidence: str = None) -> bool:
        """Update todo status with optional evidence."""
        for todo in self.data["todos"]:
            if todo["id"] == todo_id:
                todo["status"] = status
                todo["updated_date"] = datetime.now().isoformat()
                if completion_evidence:
                    todo["completion_evidence"] = completion_evidence
                
                # Move completed todos to completed list
                if status == "completed":
                    self.data["completed_todos"].append(todo.copy())
                    self.data["todos"].remove(todo)
                
                self._save_todos()
                return True
        return False

    def get_relevant_todos(self, context_query: str, max_results: int = 10) -> List[Dict]:
        """Get todos relevant to current context."""
        query_terms = set(context_query.lower().split())
        relevant_todos = []
        
        for todo in self.data["todos"]:
            if todo["status"] in ["completed", "cancelled"]:
                continue
                
            # Calculate relevance score
            score = 0
            todo_text = f"{todo['content']} {todo.get('description', '')} {' '.join(todo['context_tags'])}".lower()
            
            # Exact matches
            for term in query_terms:
                if term in todo_text:
                    score += 10
            
            # Tag matches
            for tag in todo["context_tags"]:
                if any(term in tag.lower() for term in query_terms):
                    score += 15
            
            # Priority boost
            priority_boost = {"critical": 30, "high": 20, "medium": 10, "low": 5, "backlog": 0}
            score += priority_boost.get(todo["priority"], 0)
            
            # Urgency boost
            score += todo.get("urgency_score", 50) // 10
            
            if score > 0:
                todo_copy = todo.copy()
                todo_copy["relevance_score"] = score
                relevant_todos.append(todo_copy)
        
        # Sort by relevance and priority
        relevant_todos.sort(key=lambda x: (x["relevance_score"], x.get("urgency_score", 50)), reverse=True)
        return relevant_todos[:max_results]

    def get_high_priority_todos(self, statuses: List[str] = None) -> List[Dict]:
        """Get high-priority todos for immediate attention."""
        if statuses is None:
            statuses = ["pending", "in_progress", "blocked"]
        
        high_priority = []
        for todo in self.data["todos"]:
            if (todo["status"] in statuses and 
                todo["priority"] in ["critical", "high"] and
                todo.get("urgency_score", 50) >= 70):
                high_priority.append(todo)
        
        # Sort by priority score
        high_priority.sort(key=lambda x: x.get("urgency_score", 50) + x.get("impact_score", 50), reverse=True)
        return high_priority

    def create_orchestration_context(self, orchestration_type: str) -> Dict[str, Any]:
        """Create context package for orchestration phase."""
        context = {
            "orchestration_type": orchestration_type,
            "timestamp": datetime.now().isoformat(),
            "high_priority_todos": self.get_high_priority_todos(),
            "relevant_todos": self.get_relevant_todos(orchestration_type),
            "blocking_issues": [t for t in self.data["todos"] if t.get("urgency_score", 0) >= 85],
            "workflow_insights": self.data.get("workflow_insights", {}),
            "recurring_patterns": self.data.get("recurring_patterns", {}),
            "context_summary": self._generate_context_summary(orchestration_type)
        }
        return context

    def _generate_context_summary(self, orchestration_type: str) -> str:
        """Generate contextual summary for orchestration."""
        high_priority = len(self.get_high_priority_todos())
        relevant = len(self.get_relevant_todos(orchestration_type))
        
        summary = f"Context Summary for {orchestration_type}:\n"
        summary += f"- {high_priority} high-priority todos requiring attention\n"
        summary += f"- {relevant} todos relevant to current orchestration\n"
        
        # Add specific warnings for critical issues
        critical_todos = [t for t in self.data["todos"] if t["priority"] == "critical"]
        if critical_todos:
            summary += f"- CRITICAL: {len(critical_todos)} critical issues need immediate resolution\n"
        
        return summary

    def check_dependencies(self, todo_id: str) -> List[str]:
        """Check if todo dependencies are satisfied."""
        todo = next((t for t in self.data["todos"] if t["id"] == todo_id), None)
        if not todo or not todo.get("dependencies"):
            return []
        
        unmet_deps = []
        for dep_id in todo["dependencies"]:
            dep_todo = next((t for t in self.data["todos"] if t["id"] == dep_id), None)
            if not dep_todo or dep_todo["status"] != "completed":
                unmet_deps.append(dep_id)
        
        return unmet_deps

    def find_duplicates(self, content: str, similarity_threshold: float = 0.8) -> List[Dict]:
        """Find potential duplicate todos."""
        content_words = set(content.lower().split())
        duplicates = []
        
        for todo in self.data["todos"]:
            todo_words = set(todo["content"].lower().split())
            if len(content_words) == 0 or len(todo_words) == 0:
                continue
                
            intersection = len(content_words.intersection(todo_words))
            union = len(content_words.union(todo_words))
            similarity = intersection / union if union > 0 else 0
            
            if similarity >= similarity_threshold:
                duplicates.append({
                    "todo": todo,
                    "similarity": similarity
                })
        
        return sorted(duplicates, key=lambda x: x["similarity"], reverse=True)

    def archive_completed_todos(self, days_old: int = 30):
        """Archive old completed todos."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        archived_count = 0
        
        for todo in self.data["completed_todos"][:]:
            completed_date = datetime.fromisoformat(todo["updated_date"])
            if completed_date < cutoff_date:
                self.data["archived_todos"].append(todo)
                self.data["completed_todos"].remove(todo)
                archived_count += 1
        
        if archived_count > 0:
            self._save_todos()
        
        return archived_count

    def generate_insights(self) -> Dict[str, Any]:
        """Generate workflow insights from todo patterns."""
        insights = {
            "completion_rate": 0,
            "average_resolution_time": 0,
            "common_tags": {},
            "agent_performance": {},
            "priority_trends": {},
            "recommendations": []
        }
        
        # Calculate completion rate
        total_todos = len(self.data["todos"]) + len(self.data["completed_todos"])
        if total_todos > 0:
            insights["completion_rate"] = len(self.data["completed_todos"]) / total_todos
        
        # Analyze common tags
        for todo in self.data["todos"] + self.data["completed_todos"]:
            for tag in todo.get("context_tags", []):
                insights["common_tags"][tag] = insights["common_tags"].get(tag, 0) + 1
        
        # Generate recommendations
        if insights["completion_rate"] < 0.5:
            insights["recommendations"].append("Low completion rate - consider breaking down large todos")
        
        high_priority_count = len([t for t in self.data["todos"] if t["priority"] in ["critical", "high"]])
        if high_priority_count > 5:
            insights["recommendations"].append("High number of critical/high priority todos - consider prioritization review")
        
        return insights

def main():
    """CLI interface for orchestration todo manager."""
    parser = argparse.ArgumentParser(description="Orchestration Todo Manager")
    parser.add_argument("action", choices=["add", "update", "list", "relevant", "context", "insights", "archive"])
    parser.add_argument("--content", help="Todo content")
    parser.add_argument("--priority", choices=["critical", "high", "medium", "low", "backlog"], default="medium")
    parser.add_argument("--status", choices=["pending", "in_progress", "completed", "blocked", "cancelled", "deferred"])
    parser.add_argument("--id", help="Todo ID")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--agent", help="Assigned agent")
    parser.add_argument("--urgency", type=int, default=50, help="Urgency score (0-100)")
    parser.add_argument("--impact", type=int, default=50, help="Impact score (0-100)")
    parser.add_argument("--tags", nargs="*", help="Context tags")
    parser.add_argument("--description", help="Detailed description")
    
    args = parser.parse_args()
    
    manager = OrchestrationTodoManager()
    
    if args.action == "add":
        if not args.content:
            print("Error: --content required for add action")
            return 1
        
        todo_id = manager.add_todo(
            content=args.content,
            priority=args.priority,
            context_tags=args.tags or [],
            assigned_agent=args.agent,
            description=args.description,
            urgency_score=args.urgency,
            impact_score=args.impact
        )
        print(f"Added todo: {todo_id}")
    
    elif args.action == "update":
        if not args.id or not args.status:
            print("Error: --id and --status required for update action")
            return 1
        
        success = manager.update_todo_status(args.id, args.status)
        print(f"Updated todo {args.id}: {'success' if success else 'not found'}")
    
    elif args.action == "list":
        todos = manager.get_high_priority_todos()
        for todo in todos:
            print(f"[{todo['priority'].upper()}] {todo['content']} (ID: {todo['id']})")
    
    elif args.action == "relevant":
        if not args.query:
            print("Error: --query required for relevant action")
            return 1
        
        todos = manager.get_relevant_todos(args.query)
        for todo in todos:
            print(f"[Score: {todo['relevance_score']}] {todo['content']} (ID: {todo['id']})")
    
    elif args.action == "context":
        context_type = args.query or "general"
        context = manager.create_orchestration_context(context_type)
        print(json.dumps(context, indent=2))
    
    elif args.action == "insights":
        insights = manager.generate_insights()
        print(json.dumps(insights, indent=2))
    
    elif args.action == "archive":
        archived = manager.archive_completed_todos()
        print(f"Archived {archived} completed todos")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())