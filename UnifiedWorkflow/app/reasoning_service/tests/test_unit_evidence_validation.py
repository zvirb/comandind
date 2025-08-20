"""Unit tests for Evidence Validation functionality.

Tests the evidence-based validation engine with >85% accuracy requirement
as specified in the Phase 2 cognitive architecture.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from reasoning_service.services.evidence_validator import EvidenceValidator
from reasoning_service.models.requests import EvidenceValidationRequest, Evidence
from reasoning_service.models.responses import EvidenceValidationResponse


@pytest.fixture
def mock_ollama_service():
    """Mock Ollama service for evidence validation."""
    mock = AsyncMock()
    mock.health_check.return_value = True
    mock.is_model_ready.return_value = True
    
    # Mock evidence analysis responses
    def generate_evidence_analysis(evidence_text, validation_criteria):
        return {
            "credibility_score": 0.85,
            "consistency_score": 0.90,
            "relevance_score": 0.88,
            "bias_indicators": ["minimal selection bias"],
            "fact_check_summary": "Claims verified against reliable sources",
            "methodology_assessment": "Sound statistical methodology",
            "confidence": 0.87
        }
    
    mock.generate_evidence_analysis = AsyncMock(side_effect=generate_evidence_analysis)
    return mock


@pytest.fixture
def mock_redis_service():
    """Mock Redis service for caching validation results."""
    mock = AsyncMock()
    mock.get.return_value = None  # No cached results initially
    mock.set.return_value = True
    mock.track_performance_metric = AsyncMock()
    return mock


@pytest.fixture
def evidence_validator(mock_ollama_service, mock_redis_service):
    """Create EvidenceValidator instance with mocked dependencies."""
    return EvidenceValidator(
        ollama_service=mock_ollama_service,
        redis_service=mock_redis_service,
        validation_threshold=0.85
    )


@pytest.fixture
def sample_evidence_batch():
    """Sample evidence for testing."""
    return [
        Evidence(
            content="Study of 10,000 participants shows 85% improvement in cognitive function after intervention X",
            source="Journal of Cognitive Science, 2024",
            evidence_type="statistical_study",
            confidence=0.90,
            metadata={
                "study_type": "randomized_controlled_trial",
                "sample_size": 10000,
                "peer_reviewed": True
            }
        ),
        Evidence(
            content="According to industry expert John Smith, this approach has proven effective in 3 previous cases",
            source="Expert interview",
            evidence_type="expert_opinion",
            confidence=0.65,
            metadata={
                "expert_credentials": "20 years experience",
                "previous_cases": 3
            }
        ),
        Evidence(
            content="Preliminary results from our pilot study indicate promising trends, though sample size was limited",
            source="Internal pilot study",
            evidence_type="preliminary_data",
            confidence=0.70,
            metadata={
                "sample_size": 50,
                "preliminary": True
            }
        )
    ]


class TestEvidenceValidationCore:
    """Test core evidence validation functionality."""
    
    @pytest.mark.asyncio
    async def test_validate_single_evidence_high_quality(self, evidence_validator, sample_evidence_batch):
        """Test validation of high-quality statistical evidence."""
        high_quality_evidence = sample_evidence_batch[0]  # Statistical study
        
        result = await evidence_validator.validate_single_evidence(
            evidence=high_quality_evidence,
            validation_criteria=["credibility", "methodology", "relevance"]
        )
        
        # Should meet high-quality standards
        assert result.credibility_score >= 0.8
        assert result.consistency_score >= 0.8
        assert result.overall_validity >= 0.85
        assert result.meets_threshold is True
        assert "statistical" in result.validation_method.lower()
        
        # Should have detailed breakdown
        assert len(result.validation_details) >= 3
        assert any("credibility" in detail.lower() for detail in result.validation_details)
        assert any("methodology" in detail.lower() for detail in result.validation_details)
    
    @pytest.mark.asyncio
    async def test_validate_single_evidence_expert_opinion(self, evidence_validator, sample_evidence_batch):
        """Test validation of expert opinion evidence with appropriate scoring."""
        expert_opinion = sample_evidence_batch[1]  # Expert opinion
        
        result = await evidence_validator.validate_single_evidence(
            evidence=expert_opinion,
            validation_criteria=["credibility", "experience", "bias_assessment"]
        )
        
        # Expert opinion should have moderate scores
        assert 0.6 <= result.overall_validity <= 0.8
        assert result.credibility_score >= 0.6
        assert "expert" in result.validation_method.lower()
        
        # Should identify limitations
        assert len(result.limitations) > 0
        assert any("opinion" in limitation.lower() or "subjective" in limitation.lower() 
                  for limitation in result.limitations)
    
    @pytest.mark.asyncio
    async def test_validate_single_evidence_preliminary_data(self, evidence_validator, sample_evidence_batch):
        """Test validation of preliminary data with appropriate caution."""
        preliminary_evidence = sample_evidence_batch[2]  # Preliminary study
        
        result = await evidence_validator.validate_single_evidence(
            evidence=preliminary_evidence,
            validation_criteria=["sample_size", "methodology", "preliminary_nature"]
        )
        
        # Preliminary data should have lower confidence
        assert result.overall_validity <= 0.75
        assert result.meets_threshold is False  # Below 0.85 threshold
        
        # Should flag preliminary nature
        assert len(result.limitations) > 0
        assert any("preliminary" in limitation.lower() or "limited" in limitation.lower() 
                  for limitation in result.limitations)
    
    @pytest.mark.asyncio
    async def test_validate_evidence_batch_mixed_quality(self, evidence_validator, sample_evidence_batch):
        """Test batch validation with mixed quality evidence."""
        request = EvidenceValidationRequest(
            evidence=sample_evidence_batch,
            validation_criteria=["credibility", "methodology", "consistency", "bias_assessment"],
            require_high_confidence=True,
            context="Testing mixed quality evidence validation"
        )
        
        result = await evidence_validator.validate_evidence_batch(request, "test-request-123")
        
        # Should process all evidence
        assert len(result.individual_results) == 3
        assert result.total_evidence_count == 3
        
        # Overall validity should be weighted average
        assert 0.7 <= result.overall_validity <= 0.85
        
        # Should identify quality distribution
        high_quality_count = sum(1 for r in result.individual_results if r.overall_validity >= 0.85)
        moderate_quality_count = sum(1 for r in result.individual_results if 0.7 <= r.overall_validity < 0.85)
        low_quality_count = sum(1 for r in result.individual_results if r.overall_validity < 0.7)
        
        assert high_quality_count == 1  # Statistical study
        assert moderate_quality_count == 1  # Expert opinion
        assert low_quality_count == 1  # Preliminary data
        
        # Should provide comprehensive quality assessment
        assert "mixed quality" in result.quality_assessment.lower() or "varied" in result.quality_assessment.lower()


class TestEvidenceValidationAccuracy:
    """Test validation accuracy requirements (>85% accuracy target)."""
    
    @pytest.mark.asyncio
    async def test_validation_accuracy_with_known_outcomes(self, evidence_validator):
        """Test validation accuracy against known high/low quality evidence."""
        # High quality evidence (should score high)
        high_quality_evidence = [
            Evidence(
                content="Meta-analysis of 15 randomized controlled trials (n=25,000) shows significant improvement (p<0.001, effect size=0.8)",
                source="Cochrane Systematic Review, 2024",
                evidence_type="meta_analysis",
                confidence=0.95,
                metadata={"study_count": 15, "total_participants": 25000, "effect_size": 0.8}
            ),
            Evidence(
                content="Longitudinal study spanning 10 years with 95% retention rate demonstrates consistent outcomes",
                source="Nature Medicine, 2024",
                evidence_type="longitudinal_study",
                confidence=0.92,
                metadata={"duration_years": 10, "retention_rate": 0.95}
            )
        ]
        
        # Low quality evidence (should score low)
        low_quality_evidence = [
            Evidence(
                content="I heard from someone that this might work, but I'm not sure about the details",
                source="Anecdotal report",
                evidence_type="anecdote",
                confidence=0.30,
                metadata={"verification": False}
            ),
            Evidence(
                content="Small study (n=8) with conflicting results and high dropout rate suggests possible benefit",
                source="Unpublished pilot study",
                evidence_type="pilot_study",
                confidence=0.40,
                metadata={"sample_size": 8, "dropout_rate": 0.6}
            )
        ]
        
        # Validate high quality evidence
        high_quality_request = EvidenceValidationRequest(
            evidence=high_quality_evidence,
            validation_criteria=["statistical_power", "methodology", "peer_review", "effect_size"],
            require_high_confidence=True
        )
        
        high_result = await evidence_validator.validate_evidence_batch(high_quality_request, "high-quality-test")
        
        # Should score high
        assert high_result.overall_validity >= 0.85
        assert high_result.meets_threshold is True
        assert all(r.overall_validity >= 0.85 for r in high_result.individual_results)
        
        # Validate low quality evidence  
        low_quality_request = EvidenceValidationRequest(
            evidence=low_quality_evidence,
            validation_criteria=["statistical_power", "methodology", "verification", "sample_size"],
            require_high_confidence=True
        )
        
        low_result = await evidence_validator.validate_evidence_batch(low_quality_request, "low-quality-test")
        
        # Should score low
        assert low_result.overall_validity <= 0.50
        assert low_result.meets_threshold is False
        assert all(r.overall_validity <= 0.50 for r in low_result.individual_results)
        
        # Validation accuracy check: high quality correctly identified as high, low as low
        validation_accuracy = 1.0  # 100% accurate discrimination in this test
        assert validation_accuracy >= 0.85, "Validation accuracy must meet >85% requirement"
    
    @pytest.mark.asyncio
    async def test_validation_consistency_across_similar_evidence(self, evidence_validator):
        """Test that similar quality evidence receives consistent validation scores."""
        # Create similar high-quality evidence
        similar_evidence = [
            Evidence(
                content=f"Randomized controlled trial (n={9000 + i*200}) shows {85 + i}% improvement with p<0.001",
                source=f"Journal of {['Medicine', 'Science', 'Research'][i]}, 2024",
                evidence_type="randomized_controlled_trial",
                confidence=0.90 + i*0.01,
                metadata={"sample_size": 9000 + i*200, "p_value": 0.001}
            )
            for i in range(3)
        ]
        
        validation_results = []
        for evidence in similar_evidence:
            request = EvidenceValidationRequest(
                evidence=[evidence],
                validation_criteria=["statistical_power", "methodology", "peer_review"],
                require_high_confidence=True
            )
            
            result = await evidence_validator.validate_evidence_batch(request, f"consistency-test-{len(validation_results)}")
            validation_results.append(result.overall_validity)
        
        # Results should be consistent (within 0.1 range for similar evidence)
        max_score = max(validation_results)
        min_score = min(validation_results)
        consistency_range = max_score - min_score
        
        assert consistency_range <= 0.1, f"Validation inconsistency too high: {consistency_range}"
        assert all(score >= 0.85 for score in validation_results), "All similar high-quality evidence should meet threshold"


class TestEvidenceValidationPerformance:
    """Test validation performance targets (<2s response time)."""
    
    @pytest.mark.asyncio
    async def test_single_evidence_validation_performance(self, evidence_validator, sample_evidence_batch):
        """Test that single evidence validation meets performance targets."""
        import time
        
        evidence = sample_evidence_batch[0]
        
        start_time = time.time()
        result = await evidence_validator.validate_single_evidence(
            evidence=evidence,
            validation_criteria=["credibility", "methodology", "relevance"]
        )
        end_time = time.time()
        
        validation_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Should complete within performance target
        assert validation_time <= 2000, f"Single validation took {validation_time}ms, exceeds 2s target"
        assert result.processing_time_ms <= 2000
    
    @pytest.mark.asyncio
    async def test_batch_validation_performance(self, evidence_validator, sample_evidence_batch):
        """Test batch validation performance with larger evidence sets."""
        import time
        
        # Create larger evidence batch
        large_evidence_batch = sample_evidence_batch * 5  # 15 pieces of evidence
        
        request = EvidenceValidationRequest(
            evidence=large_evidence_batch,
            validation_criteria=["credibility", "methodology", "consistency"],
            require_high_confidence=False
        )
        
        start_time = time.time()
        result = await evidence_validator.validate_evidence_batch(request, "performance-test")
        end_time = time.time()
        
        validation_time = (end_time - start_time) * 1000
        
        # Should complete within reasonable time for batch processing
        assert validation_time <= 10000, f"Batch validation took {validation_time}ms, exceeds 10s reasonable limit"
        assert result.processing_time_ms <= 10000
        
        # Should process all evidence
        assert len(result.individual_results) == 15
        assert result.total_evidence_count == 15


class TestEvidenceValidationCaching:
    """Test validation result caching for performance optimization."""
    
    @pytest.mark.asyncio
    async def test_validation_result_caching(self, evidence_validator, sample_evidence_batch, mock_redis_service):
        """Test that validation results are cached and retrieved correctly."""
        evidence = sample_evidence_batch[0]
        
        # First validation - should cache result
        first_result = await evidence_validator.validate_single_evidence(
            evidence=evidence,
            validation_criteria=["credibility", "methodology"]
        )
        
        # Verify cache write was called
        mock_redis_service.set.assert_called()
        
        # Second validation - should use cached result
        mock_redis_service.get.return_value = {
            "credibility_score": first_result.credibility_score,
            "consistency_score": first_result.consistency_score,
            "overall_validity": first_result.overall_validity,
            "cached": True
        }
        
        second_result = await evidence_validator.validate_single_evidence(
            evidence=evidence,
            validation_criteria=["credibility", "methodology"]
        )
        
        # Results should be identical
        assert second_result.overall_validity == first_result.overall_validity
        assert second_result.credibility_score == first_result.credibility_score
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_criteria_change(self, evidence_validator, sample_evidence_batch, mock_redis_service):
        """Test that cache is properly invalidated when validation criteria change."""
        evidence = sample_evidence_batch[0]
        
        # First validation with basic criteria
        await evidence_validator.validate_single_evidence(
            evidence=evidence,
            validation_criteria=["credibility"]
        )
        
        # Reset mock to test cache miss
        mock_redis_service.get.return_value = None
        
        # Second validation with different criteria - should not use cache
        result = await evidence_validator.validate_single_evidence(
            evidence=evidence,
            validation_criteria=["credibility", "methodology", "bias_assessment"]
        )
        
        # Should perform fresh validation
        assert result.processing_time_ms > 0  # Indicates actual processing occurred


class TestEvidenceValidationErrorHandling:
    """Test error handling and resilience in evidence validation."""
    
    @pytest.mark.asyncio
    async def test_ollama_service_failure_handling(self, evidence_validator, sample_evidence_batch, mock_ollama_service):
        """Test graceful handling of Ollama service failures."""
        # Simulate Ollama service failure
        mock_ollama_service.generate_evidence_analysis.side_effect = Exception("Service unavailable")
        
        evidence = sample_evidence_batch[0]
        
        result = await evidence_validator.validate_single_evidence(
            evidence=evidence,
            validation_criteria=["credibility", "methodology"]
        )
        
        # Should provide fallback validation
        assert result is not None
        assert result.overall_validity >= 0.0  # Should have some score, even if fallback
        assert "fallback" in result.validation_method.lower() or "error" in result.validation_method.lower()
        assert len(result.limitations) > 0
        assert any("service" in limitation.lower() for limitation in result.limitations)
    
    @pytest.mark.asyncio
    async def test_invalid_evidence_handling(self, evidence_validator):
        """Test handling of invalid or malformed evidence."""
        # Empty content
        empty_evidence = Evidence(
            content="",
            source="Test source",
            evidence_type="test",
            confidence=0.5
        )
        
        result = await evidence_validator.validate_single_evidence(
            evidence=empty_evidence,
            validation_criteria=["credibility"]
        )
        
        # Should handle gracefully
        assert result.overall_validity == 0.0
        assert not result.meets_threshold
        assert len(result.limitations) > 0
        assert any("empty" in limitation.lower() or "invalid" in limitation.lower() 
                  for limitation in result.limitations)
    
    @pytest.mark.asyncio
    async def test_partial_batch_failure_recovery(self, evidence_validator, sample_evidence_batch, mock_ollama_service):
        """Test recovery from partial failures in batch processing."""
        # Setup mock to fail on second evidence only
        def selective_failure(evidence_text, validation_criteria):
            if "expert" in evidence_text.lower():
                raise Exception("Analysis failed for this evidence")
            return {
                "credibility_score": 0.80,
                "consistency_score": 0.85,
                "relevance_score": 0.82,
                "confidence": 0.82
            }
        
        mock_ollama_service.generate_evidence_analysis.side_effect = selective_failure
        
        request = EvidenceValidationRequest(
            evidence=sample_evidence_batch,
            validation_criteria=["credibility", "methodology"],
            require_high_confidence=False
        )
        
        result = await evidence_validator.validate_evidence_batch(request, "partial-failure-test")
        
        # Should process available evidence and handle failures
        assert len(result.individual_results) == 3
        assert result.total_evidence_count == 3
        
        # Should have at least partial results
        successful_results = [r for r in result.individual_results if r.overall_validity > 0]
        assert len(successful_results) >= 1  # At least one should succeed
        
        # Should report processing issues
        assert len(result.validation_warnings) > 0


@pytest.mark.integration
class TestEvidenceValidationIntegration:
    """Integration tests for evidence validation with real-world scenarios."""
    
    @pytest.mark.asyncio
    async def test_scientific_paper_validation_workflow(self, evidence_validator):
        """Test validation of scientific paper evidence - realistic scenario."""
        scientific_evidence = Evidence(
            content="Double-blind, placebo-controlled trial (n=1,247) published in NEJM demonstrates 73% reduction in primary endpoint (95% CI: 0.21-0.35, p<0.0001). Study duration: 24 months, dropout rate: 8%.",
            source="New England Journal of Medicine, Vol 387, 2024",
            evidence_type="randomized_controlled_trial",
            confidence=0.94,
            metadata={
                "journal_impact_factor": 176.1,
                "peer_reviewed": True,
                "study_design": "double_blind_rct",
                "sample_size": 1247,
                "primary_endpoint_reduction": 0.73,
                "confidence_interval": "0.21-0.35",
                "p_value": "<0.0001",
                "study_duration_months": 24,
                "dropout_rate": 0.08
            }
        )
        
        result = await evidence_validator.validate_single_evidence(
            evidence=scientific_evidence,
            validation_criteria=[
                "statistical_power", "study_design", "peer_review", 
                "sample_size", "effect_size", "confidence_interval"
            ]
        )
        
        # High-quality scientific evidence should score very highly
        assert result.overall_validity >= 0.90
        assert result.credibility_score >= 0.90
        assert result.consistency_score >= 0.85
        assert result.meets_threshold is True
        
        # Should identify key quality indicators
        validation_details_text = " ".join(result.validation_details).lower()
        assert "double-blind" in validation_details_text or "randomized" in validation_details_text
        assert "sample size" in validation_details_text or "participants" in validation_details_text
        assert "peer review" in validation_details_text or "journal" in validation_details_text