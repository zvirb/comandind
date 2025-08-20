#!/usr/bin/env python3
"""
Context Inheritance and Propagation System
Maintains intelligent context flow throughout the execution chain
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
import hashlib
from copy import deepcopy


@dataclass
class ContextItem:
    """Individual context item with metadata"""
    key: str
    value: Any
    source_agent: str
    timestamp: datetime
    relevance_score: float = 1.0
    expiry: Optional[datetime] = None
    access_count: int = 0
    tags: Set[str] = field(default_factory=set)


@dataclass
class SynthesisPoint:
    """Point where synthesis is needed"""
    trigger_agent: str
    context_required: List[str]  # Context keys needed
    synthesis_type: str  # 'architectural', 'cross-domain', 'integration'
    priority: int = 5
    created: datetime = field(default_factory=datetime.now)
    resolved: bool = False


class ContextFilter:
    """Filters for context propagation"""
    
    @staticmethod
    def security_filter(context: Dict) -> Dict:
        """Filter sensitive security information"""
        filtered = {}
        sensitive_keys = ['password', 'token', 'key', 'secret', 'credential']
        
        for k, v in context.items():
            if not any(sens in k.lower() for sens in sensitive_keys):
                filtered[k] = v
            else:
                filtered[k] = "[REDACTED]"
        
        return filtered
    
    @staticmethod
    def domain_filter(target_domain: str) -> Callable[[Dict], Dict]:
        """Create domain-specific filter"""
        def filter_func(context: Dict) -> Dict:
            filtered = {}
            
            # Domain-specific relevance
            domain_keywords = {
                'frontend': ['ui', 'component', 'style', 'render', 'dom', 'browser'],
                'backend': ['api', 'service', 'endpoint', 'server', 'database'],
                'security': ['auth', 'permission', 'validate', 'encrypt', 'secure'],
                'database': ['schema', 'table', 'query', 'index', 'migration']
            }
            
            relevant_keywords = domain_keywords.get(target_domain, [])
            
            for k, v in context.items():
                # Include if key contains domain-relevant keywords
                if any(keyword in k.lower() for keyword in relevant_keywords):
                    filtered[k] = v
                # Include general context
                elif k in ['project_structure', 'current_phase', 'user_requirements']:
                    filtered[k] = v
            
            return filtered
        
        return filter_func
    
    @staticmethod
    def complexity_filter(max_items: int = 10) -> Callable[[Dict], Dict]:
        """Limit context size based on relevance"""
        def filter_func(context: Dict) -> Dict:
            if len(context) <= max_items:
                return context
            
            # Score items by relevance (simplified)
            scored_items = []
            for k, v in context.items():
                score = 1.0
                if isinstance(v, dict) and 'relevance_score' in v:
                    score = v['relevance_score']
                elif k in ['error_patterns', 'user_feedback']:
                    score = 0.9
                elif k.startswith('_'):
                    score = 0.3
                
                scored_items.append((k, v, score))
            
            # Keep top items
            scored_items.sort(key=lambda x: x[2], reverse=True)
            return {k: v for k, v, _ in scored_items[:max_items]}
        
        return filter_func


class ContextChain:
    """Maintains context throughout the execution chain"""
    
    def __init__(self):
        self.global_context = {}  # Shared by all agents
        self.agent_contexts = {}  # Agent-specific contexts
        self.synthesis_points = []  # Where synthesis is needed
        self.context_history = []  # Historical context states
        self.access_patterns = {}  # Track what context is accessed when
        
        # Context persistence
        self.context_file = Path(".claude/logs/context_chain.json")
        self.load_persistent_context()
        
        # Relevance decay settings
        self.relevance_decay_rate = 0.1  # Per hour
        self.max_context_age_hours = 24
        
    def load_persistent_context(self):
        """Load context from persistent storage"""
        if self.context_file.exists():
            try:
                with open(self.context_file, 'r') as f:
                    data = json.load(f)
                    
                # Restore global context
                self.global_context = data.get('global_context', {})
                
                # Restore synthesis points
                synthesis_data = data.get('synthesis_points', [])
                for sp_data in synthesis_data:
                    sp = SynthesisPoint(
                        trigger_agent=sp_data['trigger_agent'],
                        context_required=sp_data['context_required'],
                        synthesis_type=sp_data['synthesis_type'],
                        priority=sp_data['priority'],
                        created=datetime.fromisoformat(sp_data['created']),
                        resolved=sp_data['resolved']
                    )
                    self.synthesis_points.append(sp)
                    
            except Exception as e:
                print(f"Warning: Could not load persistent context: {e}")
    
    def save_persistent_context(self):
        """Save context to persistent storage"""
        try:
            self.context_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare serializable data
            data = {
                'global_context': self.global_context,
                'synthesis_points': [
                    {
                        'trigger_agent': sp.trigger_agent,
                        'context_required': sp.context_required,
                        'synthesis_type': sp.synthesis_type,
                        'priority': sp.priority,
                        'created': sp.created.isoformat(),
                        'resolved': sp.resolved
                    } for sp in self.synthesis_points
                ],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.context_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not save persistent context: {e}")
    
    def add_context(self, key: str, value: Any, source_agent: str, 
                   tags: Set[str] = None, relevance_score: float = 1.0,
                   expiry_hours: Optional[int] = None) -> str:
        """Add context item with metadata"""
        timestamp = datetime.now()
        expiry = timestamp + timedelta(hours=expiry_hours) if expiry_hours else None
        
        context_item = ContextItem(
            key=key,
            value=value,
            source_agent=source_agent,
            timestamp=timestamp,
            relevance_score=relevance_score,
            expiry=expiry,
            tags=tags or set()
        )
        
        # Store in global context
        context_id = f"{key}_{source_agent}_{int(timestamp.timestamp())}"
        self.global_context[context_id] = context_item
        
        # Also store in agent's context
        if source_agent not in self.agent_contexts:
            self.agent_contexts[source_agent] = {}
        
        self.agent_contexts[source_agent][key] = context_item
        
        # Save to persistence
        self.save_persistent_context()
        
        return context_id
    
    def get_context(self, requesting_agent: str, keys: List[str] = None, 
                   tags: Set[str] = None) -> Dict[str, Any]:
        """Get relevant context for an agent"""
        current_time = datetime.now()
        relevant_context = {}
        
        # Clean expired context first
        self._clean_expired_context(current_time)
        
        # Get all context items
        all_items = list(self.global_context.values())
        
        # Filter by keys if specified
        if keys:
            all_items = [item for item in all_items if item.key in keys]
        
        # Filter by tags if specified
        if tags:
            all_items = [item for item in all_items if tags.intersection(item.tags)]
        
        # Calculate relevance for requesting agent
        for item in all_items:
            relevance = self._calculate_relevance(item, requesting_agent, current_time)
            
            if relevance > 0.1:  # Minimum relevance threshold
                relevant_context[item.key] = {
                    'value': item.value,
                    'source': item.source_agent,
                    'relevance': relevance,
                    'timestamp': item.timestamp.isoformat()
                }
                
                # Track access
                item.access_count += 1
                self._track_access(requesting_agent, item.key)
        
        # Sort by relevance
        sorted_context = dict(sorted(relevant_context.items(), 
                                   key=lambda x: x[1]['relevance'], reverse=True))
        
        return sorted_context
    
    def propagate_context(self, from_agent: str, to_agent: str, 
                         context_filter: Optional[Callable] = None,
                         specific_keys: List[str] = None) -> Dict[str, Any]:
        """Intelligently propagate relevant context between agents"""
        
        # Get source agent's context
        if from_agent not in self.agent_contexts:
            return {}
        
        source_context = {}
        for key, item in self.agent_contexts[from_agent].items():
            if specific_keys and key not in specific_keys:
                continue
                
            source_context[key] = item.value
        
        # Apply filter if provided
        if context_filter:
            filtered_context = context_filter(source_context)
        else:
            # Apply default domain filter
            to_agent_domain = self._infer_agent_domain(to_agent)
            domain_filter = ContextFilter.domain_filter(to_agent_domain)
            filtered_context = domain_filter(source_context)
        
        # Add inheritance metadata
        for key, value in filtered_context.items():
            if key not in filtered_context:
                continue
                
            self.add_context(
                key=key,
                value=value,
                source_agent=f"{from_agent}->{to_agent}",
                tags={'inherited'},
                relevance_score=0.8  # Slightly lower relevance for inherited context
            )
        
        # Add to target agent's context
        if to_agent not in self.agent_contexts:
            self.agent_contexts[to_agent] = {}
        
        for key, value in filtered_context.items():
            self.agent_contexts[to_agent][f"inherited_{key}"] = ContextItem(
                key=f"inherited_{key}",
                value=value,
                source_agent=from_agent,
                timestamp=datetime.now(),
                relevance_score=0.8,
                tags={'inherited'}
            )
        
        return filtered_context
    
    def add_synthesis_point(self, trigger_agent: str, context_required: List[str],
                          synthesis_type: str = 'general', priority: int = 5):
        """Add a point where synthesis is needed"""
        synthesis_point = SynthesisPoint(
            trigger_agent=trigger_agent,
            context_required=context_required,
            synthesis_type=synthesis_type,
            priority=priority
        )
        
        self.synthesis_points.append(synthesis_point)
        
        # Log synthesis requirement
        self.add_context(
            key=f"synthesis_required_{synthesis_type}",
            value={
                'trigger_agent': trigger_agent,
                'context_required': context_required,
                'type': synthesis_type,
                'priority': priority
            },
            source_agent='context-chain',
            tags={'synthesis', synthesis_type},
            relevance_score=0.95
        )
        
        print(f"🧠 [SYNTHESIS] {trigger_agent} requires {synthesis_type} synthesis")
        return synthesis_point
    
    def get_pending_synthesis_points(self) -> List[SynthesisPoint]:
        """Get all unresolved synthesis points"""
        return [sp for sp in self.synthesis_points if not sp.resolved]
    
    def resolve_synthesis_point(self, synthesis_point: SynthesisPoint, result: Any):
        """Mark synthesis point as resolved with result"""
        synthesis_point.resolved = True
        
        # Add synthesis result to context
        self.add_context(
            key=f"synthesis_result_{synthesis_point.synthesis_type}",
            value=result,
            source_agent='nexus-synthesis-agent',
            tags={'synthesis_result', synthesis_point.synthesis_type},
            relevance_score=0.9
        )
        
        print(f"✅ [SYNTHESIS] {synthesis_point.synthesis_type} synthesis completed")
    
    def create_context_snapshot(self, phase_name: str) -> str:
        """Create a snapshot of current context"""
        snapshot_id = f"snapshot_{phase_name}_{int(datetime.now().timestamp())}"
        
        snapshot = {
            'id': snapshot_id,
            'phase': phase_name,
            'timestamp': datetime.now().isoformat(),
            'global_context': deepcopy(self.global_context),
            'agent_contexts': deepcopy(self.agent_contexts),
            'synthesis_points': deepcopy(self.synthesis_points)
        }
        
        self.context_history.append(snapshot)
        
        # Limit history size
        if len(self.context_history) > 20:
            self.context_history = self.context_history[-10:]
        
        return snapshot_id
    
    def restore_context_snapshot(self, snapshot_id: str) -> bool:
        """Restore context from a snapshot"""
        for snapshot in self.context_history:
            if snapshot['id'] == snapshot_id:
                self.global_context = deepcopy(snapshot['global_context'])
                self.agent_contexts = deepcopy(snapshot['agent_contexts'])
                self.synthesis_points = deepcopy(snapshot['synthesis_points'])
                print(f"📥 [CONTEXT] Restored snapshot: {snapshot_id}")
                return True
        
        print(f"❌ [CONTEXT] Snapshot not found: {snapshot_id}")
        return False
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get high-level summary of current context"""
        current_time = datetime.now()
        
        # Count items by type
        context_types = {}
        agent_contributions = {}
        
        for item in self.global_context.values():
            # Count by source agent
            agent = item.source_agent
            if agent not in agent_contributions:
                agent_contributions[agent] = 0
            agent_contributions[agent] += 1
            
            # Count by tags
            for tag in item.tags:
                if tag not in context_types:
                    context_types[tag] = 0
                context_types[tag] += 1
        
        pending_synthesis = len(self.get_pending_synthesis_points())
        
        return {
            'total_context_items': len(self.global_context),
            'active_agents': len(self.agent_contexts),
            'context_by_type': context_types,
            'agent_contributions': agent_contributions,
            'pending_synthesis_points': pending_synthesis,
            'last_updated': current_time.isoformat()
        }
    
    def _calculate_relevance(self, item: ContextItem, requesting_agent: str, 
                           current_time: datetime) -> float:
        """Calculate relevance score for context item"""
        base_relevance = item.relevance_score
        
        # Time-based decay
        age_hours = (current_time - item.timestamp).total_seconds() / 3600
        decay_factor = max(0.1, 1.0 - (age_hours * self.relevance_decay_rate))
        
        # Source agent similarity boost
        source_boost = 1.0
        if item.source_agent == requesting_agent:
            source_boost = 1.2
        elif self._agents_in_same_domain(item.source_agent, requesting_agent):
            source_boost = 1.1
        
        # Access frequency boost
        access_boost = 1.0 + (item.access_count * 0.1)
        
        # Tag-based relevance
        tag_boost = 1.0
        requesting_domain = self._infer_agent_domain(requesting_agent)
        if requesting_domain in item.tags:
            tag_boost = 1.3
        
        total_relevance = (base_relevance * decay_factor * source_boost * 
                          access_boost * tag_boost)
        
        return min(1.0, total_relevance)
    
    def _clean_expired_context(self, current_time: datetime):
        """Remove expired context items"""
        expired_keys = []
        
        for key, item in self.global_context.items():
            # Check expiry
            if item.expiry and current_time > item.expiry:
                expired_keys.append(key)
                continue
            
            # Check age limit
            age_hours = (current_time - item.timestamp).total_seconds() / 3600
            if age_hours > self.max_context_age_hours:
                expired_keys.append(key)
        
        # Remove expired items
        for key in expired_keys:
            del self.global_context[key]
    
    def _infer_agent_domain(self, agent_name: str) -> str:
        """Infer domain from agent name"""
        domain_keywords = {
            'frontend': ['ui', 'webui', 'regression', 'playwright'],
            'backend': ['gateway', 'service', 'api'],
            'security': ['security', 'validator', 'auth'],
            'database': ['schema', 'database', 'db'],
            'analysis': ['research', 'analyst', 'codebase'],
            'orchestration': ['orchestrator', 'project']
        }
        
        agent_lower = agent_name.lower()
        for domain, keywords in domain_keywords.items():
            if any(keyword in agent_lower for keyword in keywords):
                return domain
        
        return 'general'
    
    def _agents_in_same_domain(self, agent1: str, agent2: str) -> bool:
        """Check if two agents are in the same domain"""
        domain1 = self._infer_agent_domain(agent1)
        domain2 = self._infer_agent_domain(agent2)
        return domain1 == domain2
    
    def _track_access(self, agent: str, context_key: str):
        """Track context access patterns"""
        if agent not in self.access_patterns:
            self.access_patterns[agent] = {}
        
        if context_key not in self.access_patterns[agent]:
            self.access_patterns[agent][context_key] = 0
        
        self.access_patterns[agent][context_key] += 1


# Global context chain instance
context_chain = ContextChain()

def add_context(key: str, value: Any, source_agent: str, **kwargs) -> str:
    """Convenience function for adding context"""
    return context_chain.add_context(key, value, source_agent, **kwargs)

def get_context(requesting_agent: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for getting context"""
    return context_chain.get_context(requesting_agent, **kwargs)

def propagate_context(from_agent: str, to_agent: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for propagating context"""
    return context_chain.propagate_context(from_agent, to_agent, **kwargs)

def add_synthesis_point(trigger_agent: str, context_required: List[str], **kwargs):
    """Convenience function for adding synthesis points"""
    return context_chain.add_synthesis_point(trigger_agent, context_required, **kwargs)


if __name__ == "__main__":
    # Test the context chain system
    print("Testing Context Inheritance and Propagation...")
    
    # Add some test context
    add_context("project_structure", 
                {"type": "full-stack", "frontend": "svelte", "backend": "python"},
                "codebase-research-analyst",
                tags={'architectural', 'structure'},
                relevance_score=0.9)
    
    add_context("security_issues", 
                ["auth_vulnerability", "xss_risk"],
                "security-validator",
                tags={'security', 'critical'},
                relevance_score=0.95)
    
    # Test context retrieval
    frontend_context = get_context("ui-regression-debugger")
    print(f"\n📋 Frontend Agent Context ({len(frontend_context)} items):")
    for key, item in frontend_context.items():
        print(f"  • {key}: relevance {item['relevance']:.2f}")
    
    # Test context propagation
    propagated = propagate_context("security-validator", "backend-gateway-expert")
    print(f"\n🔄 Propagated Context ({len(propagated)} items):")
    for key, value in propagated.items():
        print(f"  • {key}: {value}")
    
    # Test synthesis point
    add_synthesis_point("backend-gateway-expert", 
                       ["project_structure", "security_issues"],
                       synthesis_type="architectural",
                       priority=8)
    
    pending = context_chain.get_pending_synthesis_points()
    print(f"\n🧠 Pending Synthesis Points: {len(pending)}")
    for sp in pending:
        print(f"  • {sp.synthesis_type} synthesis for {sp.trigger_agent}")
    
    # Test context summary
    summary = context_chain.get_context_summary()
    print(f"\n📊 Context Summary:")
    print(f"  • Total items: {summary['total_context_items']}")
    print(f"  • Active agents: {summary['active_agents']}")
    print(f"  • Pending synthesis: {summary['pending_synthesis_points']}")