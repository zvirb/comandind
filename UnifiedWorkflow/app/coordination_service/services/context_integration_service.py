"""Context Integration Service - Merge supplemental findings back to requesting agents.

This service handles the integration of new findings from dynamically spawned agents
back into the context of the requesting agent, ensuring seamless knowledge transfer.
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


class IntegrationStrategy(str, Enum):
    """Context integration strategies."""
    MERGE = "merge"
    APPEND = "append"
    REPLACE = "replace"
    SELECTIVE = "selective"
    PRIORITIZE_NEW = "prioritize_new"
    PRIORITIZE_ORIGINAL = "prioritize_original"


class IntegrationStatus(str, Enum):
    """Integration processing statuses."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    INTEGRATING = "integrating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ContextIntegration:
    """Represents a context integration operation."""
    integration_id: str
    requesting_agent: str
    workflow_id: str
    request_id: str
    status: IntegrationStatus = IntegrationStatus.PENDING
    
    # Context data
    original_context: Dict[str, Any] = field(default_factory=dict)
    new_findings: Dict[str, Any] = field(default_factory=dict)
    integrated_context: Dict[str, Any] = field(default_factory=dict)
    
    # Integration metadata
    integration_strategy: IntegrationStrategy = IntegrationStrategy.MERGE
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    # Results
    integration_summary: Dict[str, Any] = field(default_factory=dict)
    confidence_improvement: float = 0.0
    updated_context_package_id: Optional[str] = None
    error_message: Optional[str] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if integration is complete."""
        return self.status in [IntegrationStatus.COMPLETED, IntegrationStatus.FAILED]
    
    @property
    def duration(self) -> Optional[float]:
        """Get integration duration."""
        if self.completed_at:
            return self.completed_at - self.created_at
        return None


class ContextAnalyzer:
    """Analyzes context for optimal integration strategies."""
    
    def __init__(self):
        self.conflict_patterns = {
            "contradictory_findings": [
                "contradicts", "conflicts with", "opposite of",
                "disagrees with", "refutes"
            ],
            "supplementary_information": [
                "adds to", "supplements", "expands on",
                "provides additional", "enhances"
            ],
            "corrective_information": [
                "corrects", "fixes", "updates", "revises",
                "replaces previous"
            ]
        }
    
    async def analyze_context_compatibility(
        self,
        original_context: Dict[str, Any],
        new_findings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze compatibility between original context and new findings."""
        try:
            analysis = {
                "compatibility_score": 0.0,
                "conflicts": [],
                "supplements": [],
                "corrections": [],
                "overlaps": [],
                "gaps_filled": [],
                "recommended_strategy": IntegrationStrategy.MERGE
            }
            
            # Analyze for conflicts
            conflicts = await self._detect_conflicts(original_context, new_findings)
            analysis["conflicts"] = conflicts
            
            # Analyze for supplements
            supplements = await self._detect_supplements(original_context, new_findings)
            analysis["supplements"] = supplements
            
            # Analyze for corrections
            corrections = await self._detect_corrections(original_context, new_findings)
            analysis["corrections"] = corrections
            
            # Analyze overlaps
            overlaps = await self._detect_overlaps(original_context, new_findings)
            analysis["overlaps"] = overlaps
            
            # Detect filled gaps
            gaps_filled = await self._detect_filled_gaps(original_context, new_findings)
            analysis["gaps_filled"] = gaps_filled
            
            # Calculate compatibility score
            analysis["compatibility_score"] = await self._calculate_compatibility_score(analysis)
            
            # Recommend integration strategy
            analysis["recommended_strategy"] = await self._recommend_strategy(analysis)
            
            logger.info(
                "Context compatibility analyzed",
                compatibility_score=analysis["compatibility_score"],
                conflicts_count=len(conflicts),
                supplements_count=len(supplements),
                recommended_strategy=analysis["recommended_strategy"]
            )
            
            return analysis
            
        except Exception as e:
            logger.error("Context compatibility analysis failed", error=str(e))
            return {
                "compatibility_score": 0.5,
                "conflicts": [],
                "supplements": [],
                "corrections": [],
                "overlaps": [],
                "gaps_filled": [],
                "recommended_strategy": IntegrationStrategy.MERGE
            }
    
    async def _detect_conflicts(
        self,
        original_context: Dict[str, Any],
        new_findings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between contexts."""
        conflicts = []
        
        # Compare key-value pairs for contradictions
        for key in new_findings:
            if key in original_context:
                original_value = original_context[key]
                new_value = new_findings[key]
                
                # Check for direct contradictions
                if await self._are_contradictory(original_value, new_value):
                    conflicts.append({
                        "field": key,
                        "original_value": original_value,
                        "new_value": new_value,
                        "conflict_type": "direct_contradiction"
                    })
        
        return conflicts
    
    async def _detect_supplements(
        self,
        original_context: Dict[str, Any],
        new_findings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect supplementary information."""
        supplements = []
        
        for key in new_findings:
            if key not in original_context:
                supplements.append({
                    "field": key,
                    "new_value": new_findings[key],
                    "supplement_type": "new_information"
                })
            elif await self._is_supplementary(original_context[key], new_findings[key]):
                supplements.append({
                    "field": key,
                    "original_value": original_context[key],
                    "new_value": new_findings[key],
                    "supplement_type": "additional_detail"
                })
        
        return supplements
    
    async def _detect_corrections(
        self,
        original_context: Dict[str, Any],
        new_findings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect corrective information."""
        corrections = []
        
        for key in new_findings:
            if key in original_context:
                if await self._is_correction(original_context[key], new_findings[key]):
                    corrections.append({
                        "field": key,
                        "original_value": original_context[key],
                        "corrected_value": new_findings[key],
                        "correction_type": "data_correction"
                    })
        
        return corrections
    
    async def _detect_overlaps(
        self,
        original_context: Dict[str, Any],
        new_findings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect overlapping information."""
        overlaps = []
        
        for key in new_findings:
            if key in original_context:
                similarity = await self._calculate_similarity(
                    original_context[key], new_findings[key]
                )
                
                if similarity > 0.8:  # High similarity threshold
                    overlaps.append({
                        "field": key,
                        "similarity_score": similarity,
                        "overlap_type": "high_similarity"
                    })
        
        return overlaps
    
    async def _detect_filled_gaps(
        self,
        original_context: Dict[str, Any],
        new_findings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect gaps that were filled by new findings."""
        gaps_filled = []
        
        # Look for fields that were missing or incomplete in original context
        for key in new_findings:
            if key not in original_context:
                gaps_filled.append({
                    "field": key,
                    "gap_type": "missing_field",
                    "filled_value": new_findings[key]
                })
            elif await self._was_incomplete(original_context[key]):
                gaps_filled.append({
                    "field": key,
                    "gap_type": "incomplete_data",
                    "original_value": original_context[key],
                    "completed_value": new_findings[key]
                })
        
        return gaps_filled
    
    async def _are_contradictory(self, value1: Any, value2: Any) -> bool:
        """Check if two values are contradictory."""
        if isinstance(value1, bool) and isinstance(value2, bool):
            return value1 != value2
        
        if isinstance(value1, str) and isinstance(value2, str):
            for pattern in self.conflict_patterns["contradictory_findings"]:
                if pattern in value2.lower():
                    return True
        
        return False
    
    async def _is_supplementary(self, original: Any, new: Any) -> bool:
        """Check if new value supplements the original."""
        if isinstance(original, str) and isinstance(new, str):
            for pattern in self.conflict_patterns["supplementary_information"]:
                if pattern in new.lower():
                    return True
        
        if isinstance(original, list) and isinstance(new, list):
            # Check if new list adds to original
            return len(set(new) - set(original)) > 0
        
        return False
    
    async def _is_correction(self, original: Any, new: Any) -> bool:
        """Check if new value corrects the original."""
        if isinstance(original, str) and isinstance(new, str):
            for pattern in self.conflict_patterns["corrective_information"]:
                if pattern in new.lower():
                    return True
        
        return False
    
    async def _calculate_similarity(self, value1: Any, value2: Any) -> float:
        """Calculate similarity between two values."""
        if value1 == value2:
            return 1.0
        
        if isinstance(value1, str) and isinstance(value2, str):
            # Simple similarity based on common words
            words1 = set(value1.lower().split())
            words2 = set(value2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
        
        return 0.0
    
    async def _was_incomplete(self, value: Any) -> bool:
        """Check if a value appears incomplete."""
        if value is None:
            return True
        
        if isinstance(value, str):
            incomplete_indicators = ["todo", "tbd", "incomplete", "partial", "unknown"]
            return any(indicator in value.lower() for indicator in incomplete_indicators)
        
        if isinstance(value, list):
            return len(value) == 0
        
        if isinstance(value, dict):
            return len(value) == 0
        
        return False
    
    async def _calculate_compatibility_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate overall compatibility score."""
        score = 1.0
        
        # Penalties for conflicts
        conflict_penalty = len(analysis["conflicts"]) * 0.2
        score -= min(conflict_penalty, 0.8)  # Max 80% penalty
        
        # Bonuses for supplements and gap filling
        supplement_bonus = len(analysis["supplements"]) * 0.1
        gap_bonus = len(analysis["gaps_filled"]) * 0.15
        
        score += min(supplement_bonus + gap_bonus, 0.5)  # Max 50% bonus
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
    
    async def _recommend_strategy(self, analysis: Dict[str, Any]) -> IntegrationStrategy:
        """Recommend integration strategy based on analysis."""
        conflicts = len(analysis["conflicts"])
        supplements = len(analysis["supplements"])
        corrections = len(analysis["corrections"])
        compatibility_score = analysis["compatibility_score"]
        
        # High conflicts suggest selective integration
        if conflicts > 3 or compatibility_score < 0.3:
            return IntegrationStrategy.SELECTIVE
        
        # Many corrections suggest prioritizing new findings
        if corrections > 2:
            return IntegrationStrategy.PRIORITIZE_NEW
        
        # Many supplements suggest merging
        if supplements > 2:
            return IntegrationStrategy.MERGE
        
        # Low compatibility suggests append strategy
        if compatibility_score < 0.7:
            return IntegrationStrategy.APPEND
        
        # Default to merge for compatible contexts
        return IntegrationStrategy.MERGE


class ContextIntegrator:
    """Handles the actual integration of contexts."""
    
    def __init__(self):
        self.integration_strategies = {
            IntegrationStrategy.MERGE: self._merge_strategy,
            IntegrationStrategy.APPEND: self._append_strategy,
            IntegrationStrategy.REPLACE: self._replace_strategy,
            IntegrationStrategy.SELECTIVE: self._selective_strategy,
            IntegrationStrategy.PRIORITIZE_NEW: self._prioritize_new_strategy,
            IntegrationStrategy.PRIORITIZE_ORIGINAL: self._prioritize_original_strategy
        }
    
    async def integrate_contexts(
        self,
        original_context: Dict[str, Any],
        new_findings: Dict[str, Any],
        strategy: IntegrationStrategy,
        analysis: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Integrate contexts using the specified strategy."""
        try:
            integration_func = self.integration_strategies.get(strategy, self._merge_strategy)
            
            integrated_context, integration_summary = await integration_func(
                original_context, new_findings, analysis
            )
            
            logger.info(
                "Contexts integrated",
                strategy=strategy,
                original_fields=len(original_context),
                new_fields=len(new_findings),
                integrated_fields=len(integrated_context)
            )
            
            return integrated_context, integration_summary
            
        except Exception as e:
            logger.error("Context integration failed", strategy=strategy, error=str(e))
            # Fallback to simple merge
            return await self._merge_strategy(original_context, new_findings, analysis)
    
    async def _merge_strategy(
        self,
        original: Dict[str, Any],
        new: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Merge contexts by combining non-conflicting information."""
        integrated = original.copy()
        changes = {"added": [], "updated": [], "conflicts_resolved": []}
        
        for key, value in new.items():
            if key not in integrated:
                integrated[key] = value
                changes["added"].append(key)
            else:
                # Check if this is a known conflict
                is_conflict = any(
                    conflict["field"] == key
                    for conflict in analysis.get("conflicts", [])
                )
                
                if not is_conflict:
                    # Safe to merge/update
                    if isinstance(integrated[key], dict) and isinstance(value, dict):
                        integrated[key] = {**integrated[key], **value}
                    elif isinstance(integrated[key], list) and isinstance(value, list):
                        integrated[key] = list(set(integrated[key] + value))
                    else:
                        integrated[key] = value
                    changes["updated"].append(key)
                else:
                    # Handle conflict by creating a conflict resolution structure
                    integrated[f"{key}_conflict"] = {
                        "original": integrated[key],
                        "new": value,
                        "resolution_needed": True
                    }
                    changes["conflicts_resolved"].append(key)
        
        summary = {
            "strategy_used": "merge",
            "changes_made": changes,
            "fields_merged": len(changes["added"]) + len(changes["updated"]),
            "conflicts_deferred": len(changes["conflicts_resolved"])
        }
        
        return integrated, summary
    
    async def _append_strategy(
        self,
        original: Dict[str, Any],
        new: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Append new findings to original context."""
        integrated = original.copy()
        integrated["supplemental_findings"] = new
        integrated["supplemental_metadata"] = {
            "appended_at": time.time(),
            "source": "dynamic_agent_request",
            "analysis_summary": analysis
        }
        
        summary = {
            "strategy_used": "append",
            "changes_made": {"appended_section": "supplemental_findings"},
            "fields_added": len(new),
            "preservation": "original_context_preserved"
        }
        
        return integrated, summary
    
    async def _replace_strategy(
        self,
        original: Dict[str, Any],
        new: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Replace original context with new findings."""
        integrated = new.copy()
        integrated["replaced_context"] = {
            "original": original,
            "replacement_metadata": {
                "replaced_at": time.time(),
                "reason": "new_findings_preferred",
                "analysis_summary": analysis
            }
        }
        
        summary = {
            "strategy_used": "replace",
            "changes_made": {"replaced": "entire_context"},
            "fields_replaced": len(original),
            "fields_new": len(new)
        }
        
        return integrated, summary
    
    async def _selective_strategy(
        self,
        original: Dict[str, Any],
        new: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Selectively integrate based on analysis."""
        integrated = original.copy()
        changes = {"selected_additions": [], "avoided_conflicts": [], "merged_supplements": []}
        
        # Add non-conflicting new information
        conflicts = {conflict["field"] for conflict in analysis.get("conflicts", [])}
        
        for key, value in new.items():
            if key not in conflicts:
                if key not in integrated:
                    integrated[key] = value
                    changes["selected_additions"].append(key)
                else:
                    # Check if it's a supplement
                    is_supplement = any(
                        supp["field"] == key
                        for supp in analysis.get("supplements", [])
                    )
                    
                    if is_supplement:
                        # Merge supplementary information
                        if isinstance(integrated[key], dict) and isinstance(value, dict):
                            integrated[key] = {**integrated[key], **value}
                        elif isinstance(integrated[key], list) and isinstance(value, list):
                            integrated[key] = list(set(integrated[key] + value))
                        else:
                            integrated[f"{key}_supplemental"] = value
                        changes["merged_supplements"].append(key)
            else:
                changes["avoided_conflicts"].append(key)
        
        # Store avoided conflicts for manual review
        if changes["avoided_conflicts"]:
            integrated["_conflict_review"] = {
                field: new[field] for field in changes["avoided_conflicts"]
                if field in new
            }
        
        summary = {
            "strategy_used": "selective",
            "changes_made": changes,
            "fields_added": len(changes["selected_additions"]),
            "supplements_merged": len(changes["merged_supplements"]),
            "conflicts_avoided": len(changes["avoided_conflicts"])
        }
        
        return integrated, summary
    
    async def _prioritize_new_strategy(
        self,
        original: Dict[str, Any],
        new: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Prioritize new findings over original context."""
        integrated = original.copy()
        changes = {"prioritized_new": [], "preserved_original": []}
        
        # Prioritize new values, but preserve original as backup
        for key, value in new.items():
            if key in integrated:
                # Save original value
                integrated[f"{key}_original"] = integrated[key]
                integrated[key] = value
                changes["prioritized_new"].append(key)
            else:
                integrated[key] = value
                changes["prioritized_new"].append(key)
        
        # Preserve unique original fields
        for key in integrated:
            if key not in new and not key.endswith("_original"):
                changes["preserved_original"].append(key)
        
        summary = {
            "strategy_used": "prioritize_new",
            "changes_made": changes,
            "new_values_prioritized": len(changes["prioritized_new"]),
            "original_values_preserved": len(changes["preserved_original"])
        }
        
        return integrated, summary
    
    async def _prioritize_original_strategy(
        self,
        original: Dict[str, Any],
        new: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Prioritize original context over new findings."""
        integrated = original.copy()
        changes = {"added_new": [], "preserved_original": []}
        
        # Only add new fields that don't exist in original
        for key, value in new.items():
            if key not in integrated:
                integrated[key] = value
                changes["added_new"].append(key)
        
        # Store new findings as supplemental
        integrated["_supplemental_findings"] = {
            key: value for key, value in new.items()
            if key in integrated
        }
        
        changes["preserved_original"] = list(original.keys())
        
        summary = {
            "strategy_used": "prioritize_original",
            "changes_made": changes,
            "original_preserved": len(changes["preserved_original"]),
            "new_added": len(changes["added_new"]),
            "supplemental_stored": len(integrated.get("_supplemental_findings", {}))
        }
        
        return integrated, summary


class ContextIntegrationService:
    """Main service for context integration operations."""
    
    def __init__(self, context_generator=None, redis_service=None):
        self.context_generator = context_generator
        self.redis_service = redis_service
        
        # Initialize components
        self.context_analyzer = ContextAnalyzer()
        self.context_integrator = ContextIntegrator()
        
        # Active integrations
        self.active_integrations: Dict[str, ContextIntegration] = {}
        
        # Metrics
        self.metrics = {
            "total_integrations": 0,
            "successful_integrations": 0,
            "failed_integrations": 0,
            "avg_integration_time": 0.0,
            "confidence_improvements": []
        }
    
    async def initialize(self) -> None:
        """Initialize the context integration service."""
        logger.info("Initializing Context Integration Service...")
        logger.info("Context Integration Service initialized")
    
    async def create_integration(
        self,
        requesting_agent: str,
        workflow_id: str,
        request_id: str,
        original_context: Dict[str, Any],
        new_findings: Dict[str, Any],
        integration_strategy: str = "merge"
    ) -> str:
        """Create a new context integration operation."""
        try:
            integration_id = str(uuid.uuid4())
            
            integration = ContextIntegration(
                integration_id=integration_id,
                requesting_agent=requesting_agent,
                workflow_id=workflow_id,
                request_id=request_id,
                original_context=original_context,
                new_findings=new_findings,
                integration_strategy=IntegrationStrategy(integration_strategy)
            )
            
            # Store integration
            self.active_integrations[integration_id] = integration
            
            # Start integration process
            await self._process_integration(integration)
            
            # Update metrics
            self.metrics["total_integrations"] += 1
            
            logger.info(
                "Created context integration",
                integration_id=integration_id,
                requesting_agent=requesting_agent,
                strategy=integration_strategy
            )
            
            return integration_id
            
        except Exception as e:
            logger.error("Failed to create integration", error=str(e))
            raise
    
    async def get_integration_status(self, integration_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a context integration."""
        integration = self.active_integrations.get(integration_id)
        if not integration:
            return None
        
        return {
            "integration_id": integration_id,
            "status": integration.status,
            "requesting_agent": integration.requesting_agent,
            "workflow_id": integration.workflow_id,
            "request_id": integration.request_id,
            "integration_strategy": integration.integration_strategy,
            "created_at": integration.created_at,
            "completed_at": integration.completed_at,
            "confidence_improvement": integration.confidence_improvement,
            "is_complete": integration.is_complete
        }
    
    async def get_integration_result(self, integration_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a completed integration."""
        integration = self.active_integrations.get(integration_id)
        if not integration or not integration.is_complete:
            return None
        
        return {
            "integration_id": integration_id,
            "status": integration.status,
            "integrated_context": integration.integrated_context,
            "integration_summary": integration.integration_summary,
            "confidence_improvement": integration.confidence_improvement,
            "updated_context_package_id": integration.updated_context_package_id,
            "processing_duration": integration.duration,
            "error_message": integration.error_message
        }
    
    async def _process_integration(self, integration: ContextIntegration) -> None:
        """Process a context integration."""
        try:
            integration.status = IntegrationStatus.ANALYZING
            
            # Analyze context compatibility
            analysis = await self.context_analyzer.analyze_context_compatibility(
                integration.original_context,
                integration.new_findings
            )
            
            # Use recommended strategy if not explicitly set
            if integration.integration_strategy == IntegrationStrategy.MERGE:
                integration.integration_strategy = analysis["recommended_strategy"]
            
            integration.status = IntegrationStatus.INTEGRATING
            
            # Perform integration
            integrated_context, integration_summary = await self.context_integrator.integrate_contexts(
                integration.original_context,
                integration.new_findings,
                integration.integration_strategy,
                analysis
            )
            
            # Calculate confidence improvement
            confidence_improvement = await self._calculate_confidence_improvement(
                integration.original_context,
                integrated_context,
                analysis
            )
            
            # Update integration
            integration.integrated_context = integrated_context
            integration.integration_summary = {
                **integration_summary,
                "compatibility_analysis": analysis,
                "confidence_improvement": confidence_improvement
            }
            integration.confidence_improvement = confidence_improvement
            integration.status = IntegrationStatus.COMPLETED
            integration.completed_at = time.time()
            
            # Generate updated context package if context generator available
            if self.context_generator:
                try:
                    updated_package_id = await self.context_generator.generate_context_package(
                        agent_name=integration.requesting_agent,
                        workflow_id=integration.workflow_id,
                        task_context=integrated_context,
                        requirements={"max_tokens": 4000, "source": "context_integration"}
                    )
                    integration.updated_context_package_id = updated_package_id
                except Exception as e:
                    logger.warning("Failed to generate updated context package", error=str(e))
            
            # Update metrics
            self.metrics["successful_integrations"] += 1
            self.metrics["confidence_improvements"].append(confidence_improvement)
            
            # Update average integration time
            if integration.duration:
                total_time = self.metrics["avg_integration_time"] * (self.metrics["successful_integrations"] - 1)
                self.metrics["avg_integration_time"] = (total_time + integration.duration) / self.metrics["successful_integrations"]
            
            logger.info(
                "Context integration completed",
                integration_id=integration.integration_id,
                strategy=integration.integration_strategy,
                confidence_improvement=confidence_improvement,
                duration_seconds=integration.duration
            )
            
        except Exception as e:
            integration.status = IntegrationStatus.FAILED
            integration.error_message = str(e)
            integration.completed_at = time.time()
            
            # Update metrics
            self.metrics["failed_integrations"] += 1
            
            logger.error(
                "Context integration failed",
                integration_id=integration.integration_id,
                error=str(e)
            )
    
    async def _calculate_confidence_improvement(
        self,
        original_context: Dict[str, Any],
        integrated_context: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> float:
        """Calculate confidence improvement from integration."""
        try:
            # Base improvement from compatibility score
            base_improvement = analysis.get("compatibility_score", 0.5) * 0.3
            
            # Improvement from filled gaps
            gaps_filled = len(analysis.get("gaps_filled", []))
            gap_improvement = min(gaps_filled * 0.1, 0.4)  # Max 40% from gaps
            
            # Improvement from supplements
            supplements = len(analysis.get("supplements", []))
            supplement_improvement = min(supplements * 0.05, 0.2)  # Max 20% from supplements
            
            # Penalty for unresolved conflicts
            conflicts = len(analysis.get("conflicts", []))
            conflict_penalty = min(conflicts * 0.05, 0.3)  # Max 30% penalty
            
            # Calculate total improvement
            total_improvement = base_improvement + gap_improvement + supplement_improvement - conflict_penalty
            
            # Ensure improvement is between 0 and 1
            return max(0.0, min(1.0, total_improvement))
            
        except Exception as e:
            logger.error("Failed to calculate confidence improvement", error=str(e))
            return 0.0
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get context integration metrics."""
        active_count = len([i for i in self.active_integrations.values() if not i.is_complete])
        
        # Calculate average confidence improvement
        avg_confidence_improvement = (
            sum(self.metrics["confidence_improvements"]) / len(self.metrics["confidence_improvements"])
            if self.metrics["confidence_improvements"] else 0.0
        )
        
        return {
            **self.metrics,
            "active_integrations": active_count,
            "success_rate": (
                self.metrics["successful_integrations"] / self.metrics["total_integrations"]
                if self.metrics["total_integrations"] > 0 else 0.0
            ),
            "avg_confidence_improvement": avg_confidence_improvement
        }
    
    async def shutdown(self) -> None:
        """Shutdown the context integration service."""
        logger.info("Shutting down Context Integration Service...")
        logger.info("Context Integration Service shutdown complete")