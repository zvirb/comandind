"""Tests for the Ollama service integration."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
import httpx
import numpy as np

from services.ollama_service import OllamaService, OllamaError, OllamaConnectionError, OllamaModelError


@pytest.fixture
def ollama_service():
    """Create OllamaService instance for testing."""
    return OllamaService("http://test-ollama:11434")


@pytest.fixture
def mock_httpx_response():
    """Mock HTTPX response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"models": [{"name": "llava:latest"}]}
    return mock_response


class TestOllamaService:
    """Test OllamaService functionality."""
    
    @pytest.mark.asyncio
    async def test_init(self, ollama_service):
        """Test service initialization."""
        assert ollama_service.ollama_url == "http://test-ollama:11434"
        assert ollama_service.model_name == "llava"  # default from settings
        assert ollama_service.client is not None
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_service):
        """Test successful health check."""
        with patch.object(ollama_service.client, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_get.return_value = mock_response
            
            result = await ollama_service.health_check()
            
            assert result is True
            mock_get.assert_called_once_with("http://test-ollama:11434/api/tags")
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, ollama_service):
        """Test health check failure."""
        with patch.object(ollama_service.client, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Server error"
            mock_get.return_value = mock_response
            
            result = await ollama_service.health_check()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, ollama_service):
        """Test health check with connection error."""
        with patch.object(ollama_service.client, 'get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection failed")
            
            with pytest.raises(OllamaConnectionError):
                await ollama_service.health_check()
    
    @pytest.mark.asyncio
    async def test_is_model_ready_success(self, ollama_service):
        """Test model readiness check when model is available."""
        with patch.object(ollama_service.client, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [{"name": "llava:latest"}, {"name": "other:latest"}]
            }
            mock_get.return_value = mock_response
            
            result = await ollama_service.is_model_ready()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_is_model_ready_not_found(self, ollama_service):
        """Test model readiness check when model is not available."""
        with patch.object(ollama_service.client, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [{"name": "other:latest"}]
            }
            mock_get.return_value = mock_response
            
            result = await ollama_service.is_model_ready()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_ensure_model_ready_already_ready(self, ollama_service):
        """Test ensure_model_ready when model is already available."""
        with patch.object(ollama_service, 'is_model_ready') as mock_ready:
            mock_ready.return_value = True
            
            await ollama_service.ensure_model_ready()
            
            mock_ready.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_model_ready_pull_needed(self, ollama_service):
        """Test ensure_model_ready when model needs to be pulled."""
        with patch.object(ollama_service, 'is_model_ready') as mock_ready:
            mock_ready.return_value = False
            
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                mock_response = Mock()
                mock_response.status_code = 200
                mock_client.post.return_value = mock_response
                
                await ollama_service.ensure_model_ready()
                
                mock_client.post.assert_called_once()
                assert ollama_service._model_ready is True
    
    @pytest.mark.asyncio
    async def test_generate_description_success(self, ollama_service):
        """Test successful description generation."""
        test_image_data = "base64_image_data"
        expected_response = "A detailed description of the image"
        
        with patch.object(ollama_service, 'is_model_ready') as mock_ready:
            mock_ready.return_value = True
            
            with patch.object(ollama_service.client, 'post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "response": expected_response,
                    "model": "llava",
                    "created_at": "2024-01-01T00:00:00Z",
                    "done": True,
                    "total_duration": 1000000000  # 1 second in nanoseconds
                }
                mock_post.return_value = mock_response
                
                result = await ollama_service.generate_description(test_image_data)
                
                assert result == expected_response
                mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_description_model_not_ready(self, ollama_service):
        """Test description generation when model is not ready."""
        test_image_data = "base64_image_data"
        
        with patch.object(ollama_service, 'is_model_ready') as mock_ready:
            mock_ready.return_value = False
            
            with patch.object(ollama_service, 'ensure_model_ready') as mock_ensure:
                mock_ensure.return_value = None
                
                with patch.object(ollama_service.client, 'post') as mock_post:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "response": "test response",
                        "model": "llava",
                        "created_at": "2024-01-01T00:00:00Z",
                        "done": True
                    }
                    mock_post.return_value = mock_response
                    
                    await ollama_service.generate_description(test_image_data)
                    
                    mock_ensure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_description_http_error(self, ollama_service):
        """Test description generation with HTTP error."""
        test_image_data = "base64_image_data"
        
        with patch.object(ollama_service, 'is_model_ready') as mock_ready:
            mock_ready.return_value = True
            
            with patch.object(ollama_service.client, 'post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.text = "Server error"
                mock_post.return_value = mock_response
                
                with pytest.raises(OllamaModelError):
                    await ollama_service.generate_description(test_image_data)
    
    @pytest.mark.asyncio
    async def test_generate_description_timeout(self, ollama_service):
        """Test description generation with timeout."""
        test_image_data = "base64_image_data"
        
        with patch.object(ollama_service, 'is_model_ready') as mock_ready:
            mock_ready.return_value = True
            
            with patch.object(ollama_service.client, 'post') as mock_post:
                mock_post.side_effect = httpx.TimeoutException("Timeout")
                
                with pytest.raises(OllamaError, match="timed out"):
                    await ollama_service.generate_description(test_image_data)
    
    def test_text_to_vector(self, ollama_service):
        """Test text to vector conversion."""
        test_text = "A person standing in a park with trees and blue sky"
        
        vector = ollama_service._text_to_vector(test_text)
        
        # Check vector properties
        assert len(vector) == 1536
        assert all(isinstance(v, (int, float)) for v in vector)
        assert all(-1e10 < v < 1e10 for v in vector)  # All finite values
        
        # Check that different texts produce different vectors
        different_text = "A red car driving on a road"
        different_vector = ollama_service._text_to_vector(different_text)
        
        assert vector != different_vector
    
    def test_text_to_vector_empty_text(self, ollama_service):
        """Test text to vector conversion with empty text."""
        vector = ollama_service._text_to_vector("")
        
        assert len(vector) == 1536
        assert all(isinstance(v, (int, float)) for v in vector)
    
    def test_text_to_vector_normalization(self, ollama_service):
        """Test that vectors are properly normalized."""
        test_text = "Test text for normalization"
        
        vector = ollama_service._text_to_vector(test_text)
        
        # Calculate vector norm
        norm = np.linalg.norm(vector)
        
        # Should be normalized (close to 1.0, allowing for floating point precision)
        assert abs(norm - 1.0) < 1e-6 or norm == 0.0
    
    @pytest.mark.asyncio
    async def test_generate_concept_vector_success(self, ollama_service):
        """Test successful concept vector generation."""
        test_image_data = "base64_image_data"
        test_description = "A detailed description"
        
        with patch.object(ollama_service, 'generate_description') as mock_desc:
            mock_desc.return_value = test_description
            
            vector = await ollama_service.generate_concept_vector(
                image_data=test_image_data,
                image_format="png"
            )
            
            assert len(vector) == 1536
            assert all(isinstance(v, (int, float)) for v in vector)
            mock_desc.assert_called_once_with(
                image_data=test_image_data,
                prompt=None,
                request_id=None
            )
    
    @pytest.mark.asyncio
    async def test_generate_concept_vector_with_custom_prompt(self, ollama_service):
        """Test concept vector generation with custom prompt."""
        test_image_data = "base64_image_data"
        custom_prompt = "Custom analysis prompt"
        test_description = "Custom description"
        request_id = 12345
        
        with patch.object(ollama_service, 'generate_description') as mock_desc:
            mock_desc.return_value = test_description
            
            await ollama_service.generate_concept_vector(
                image_data=test_image_data,
                image_format="jpeg",
                prompt=custom_prompt,
                request_id=request_id
            )
            
            mock_desc.assert_called_once_with(
                image_data=test_image_data,
                prompt=custom_prompt,
                request_id=request_id
            )
    
    @pytest.mark.asyncio
    async def test_generate_concept_vector_description_error(self, ollama_service):
        """Test concept vector generation when description fails."""
        test_image_data = "base64_image_data"
        
        with patch.object(ollama_service, 'generate_description') as mock_desc:
            mock_desc.side_effect = OllamaError("Description failed")
            
            with pytest.raises(OllamaError):
                await ollama_service.generate_concept_vector(
                    image_data=test_image_data,
                    image_format="png"
                )
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with OllamaService("http://test:11434") as service:
            assert service.client is not None
            
        # Client should be closed after exiting context