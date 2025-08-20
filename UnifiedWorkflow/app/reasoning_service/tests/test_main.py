"""Tests for the main Reasoning Service application."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from ..models.responses import EvidenceValidationResponse, EvidenceAssessment


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check_healthy(self, client):
        """Test health check when all services are healthy."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data
        assert "version" in data


class TestEvidenceValidationEndpoint:
    """Tests for evidence validation endpoint."""
    
    def test_evidence_validation_success(self, client, sample_evidence, mock_services):
        """Test successful evidence validation."""
        # Mock the evidence validator response
        mock_response = EvidenceValidationResponse(
            overall_validity=0.89,
            meets_threshold=True,
            assessments=[
                EvidenceAssessment(
                    evidence_id="test_001",
                    validity_score=0.89,
                    reliability_score=0.91,
                    confidence=0.87,
                    strengths=["Strong source credibility"],
                    weaknesses=["Limited timeframe"],
                    recommendations=["Extend data collection period"]
                )
            ],
            summary="Evidence meets high-confidence validation threshold",
            processing_time_ms=1250.5,
            validation_method="multi_criteria_analysis",
            confidence_score=0.87
        )
        
        mock_services["evidence_validator"].validate_evidence_batch.return_value = mock_response
        
        request_data = {
            "evidence": sample_evidence,
            "context": "Testing evidence validation",
            "require_high_confidence": True
        }
        
        response = client.post("/validate/evidence", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["overall_validity"] == 0.89
        assert data["meets_threshold"] is True
        assert len(data["assessments"]) == 1
        assert data["validation_method"] == "multi_criteria_analysis"
    
    def test_evidence_validation_invalid_input(self, client):
        """Test evidence validation with invalid input."""
        request_data = {
            "evidence": [],  # Empty evidence list
            "require_high_confidence": True
        }
        
        response = client.post("/validate/evidence", json=request_data)
        
        assert response.status_code == 422  # Validation error


class TestMultiCriteriaDecisionEndpoint:
    """Tests for multi-criteria decision endpoint."""
    
    def test_multi_criteria_decision_success(self, client, sample_decision_request, mock_services):
        """Test successful multi-criteria decision analysis."""
        # Mock the decision analyzer response
        from ..models.responses import MultiCriteriaDecisionResponse, DecisionEvaluation
        
        mock_response = MultiCriteriaDecisionResponse(
            recommended_option="Microservices",
            confidence_score=0.82,
            evaluations=[
                DecisionEvaluation(
                    option_name="Microservices",
                    overall_score=0.78,
                    criteria_scores={"Scalability": 0.9, "Cost": 0.7, "Complexity": 0.6},
                    strengths=["Scalable", "Flexible"],
                    weaknesses=["Complex"],
                    risk_factors=["Operational complexity"],
                    implementation_considerations=["Team training needed"]
                )
            ],
            decision_rationale="Best balance of scalability and long-term benefits",
            sensitivity_analysis={"weight_changes": "Recommendation stable"},
            risk_mitigation=["Gradual migration", "Invest in monitoring tools"],
            processing_time_ms=2150.3
        )
        
        mock_services["decision_analyzer"].analyze_decision.return_value = mock_response
        
        response = client.post("/decide/multi-criteria", json=sample_decision_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["recommended_option"] == "Microservices"
        assert data["confidence_score"] == 0.82
        assert len(data["evaluations"]) == 1


class TestHypothesisTestingEndpoint:
    """Tests for hypothesis testing endpoint."""
    
    def test_hypothesis_testing_success(self, client, sample_hypothesis_request, mock_services):
        """Test successful hypothesis testing."""
        from ..models.responses import HypothesisTestingResponse, HypothesisResult
        
        mock_response = HypothesisTestingResponse(
            hypothesis="New feature will increase user engagement by 15%",
            result=HypothesisResult(
                test_result="supported",
                confidence_score=0.83,
                p_value=0.023,
                supporting_evidence=["Positive A/B test results"],
                contradicting_evidence=["Limited test duration"],
                alternative_hypotheses=["Novelty effect may decline"]
            ),
            methodology="Statistical analysis with Bayesian inference",
            evidence_analysis="Evidence shows consistent positive trend",
            recommendations=["Extend test duration", "Monitor long-term effects"],
            processing_time_ms=1875.2
        )
        
        mock_services["hypothesis_tester"].test_hypothesis.return_value = mock_response
        
        response = client.post("/test/hypothesis", json=sample_hypothesis_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["hypothesis"] == "New feature will increase user engagement by 15%"
        assert data["result"]["test_result"] == "supported"
        assert data["result"]["confidence_score"] == 0.83


class TestReasoningChainEndpoint:
    """Tests for reasoning chain endpoint."""
    
    def test_reasoning_chain_success(self, client, sample_reasoning_request, mock_services):
        """Test successful reasoning chain processing."""
        from ..models.responses import ReasoningChainResponse, ReasoningChainResult
        
        mock_response = ReasoningChainResponse(
            initial_premise="System shows high CPU usage and memory leaks",
            goal="Determine root cause and solution",
            result=ReasoningChainResult(
                steps=[
                    {
                        "step": 1,
                        "premise": "System shows memory leaks",
                        "inference": "Memory not properly released",
                        "conclusion": "Code has resource management issues",
                        "confidence": 0.9
                    }
                ],
                final_conclusion="Root cause is improper resource disposal in async operations",
                overall_confidence=0.87,
                logical_consistency=0.93,
                key_assumptions=["Monitoring data is accurate"],
                potential_flaws=["Limited test scenarios"],
                alternative_paths=["Network bottlenecks", "Database issues"]
            ),
            reasoning_type="abductive",
            validation_checks=["Logical consistency check passed"],
            processing_time_ms=3200.7
        )
        
        mock_services["reasoning_engine"].process_reasoning_chain.return_value = mock_response
        
        response = client.post("/reasoning/chain", json=sample_reasoning_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["initial_premise"] == "System shows high CPU usage and memory leaks"
        assert data["reasoning_type"] == "abductive"
        assert data["result"]["overall_confidence"] == 0.87
        assert len(data["result"]["steps"]) == 1


class TestErrorHandling:
    """Tests for error handling in the application."""
    
    def test_404_endpoint(self, client):
        """Test 404 for non-existent endpoint."""
        response = client.get("/non-existent")
        assert response.status_code == 404
    
    def test_invalid_json(self, client):
        """Test invalid JSON handling."""
        response = client.post(
            "/validate/evidence", 
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_method_not_allowed(self, client):
        """Test method not allowed."""
        response = client.put("/health")
        assert response.status_code == 405


class TestMetricsEndpoint:
    """Tests for metrics endpoint."""
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"] or response.headers["content-type"] == "text/plain; charset=utf-8"
        
        # Check for some expected metric names
        content = response.content.decode()
        assert "reasoning_requests_total" in content or "python_info" in content  # At least some metric should be present