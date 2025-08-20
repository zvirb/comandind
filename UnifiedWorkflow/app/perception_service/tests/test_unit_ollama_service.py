"""Unit tests for Perception Service OllamaService.

Tests the core image processing and vector generation functionality
with comprehensive mocking of Ollama API interactions.
"""

import asyncio
import base64
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import numpy as np
from aioresponses import aioresponses

from perception_service.services.ollama_service import OllamaService


class TestOllamaServiceInit:
    """Test OllamaService initialization and configuration."""
    
    def test_service_initialization(self):
        """Test proper service initialization with default settings."""
        service = OllamaService("http://localhost:11434")
        
        assert service.base_url == "http://localhost:11434"
        assert service.model == "llava"
        assert service.timeout == 30.0
        assert service.max_retries == 3
        assert service._session is None
    
    def test_service_initialization_with_custom_params(self):
        """Test service initialization with custom parameters."""
        service = OllamaService(
            base_url="http://custom:8080",
            model="llava:13b",
            timeout=60.0,
            max_retries=5
        )
        
        assert service.base_url == "http://custom:8080"
        assert service.model == "llava:13b"
        assert service.timeout == 60.0
        assert service.max_retries == 5


class TestOllamaServiceHealthCheck:
    """Test health check functionality."""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_httpx_client):
        """Test successful health check."""
        service = OllamaService("http://localhost:11434")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock successful health response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_instance.get.return_value = mock_response
            
            result = await service.health_check()
            
            assert result is True
            mock_instance.get.assert_called_once_with(
                "http://localhost:11434/api/tags",
                timeout=30.0
            )
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure handling."""
        service = OllamaService("http://localhost:11434")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock failed health response
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_instance.get.return_value = mock_response
            
            result = await service.health_check()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_network_error(self):
        """Test health check with network error."""
        service = OllamaService("http://localhost:11434")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock network error
            mock_instance.get.side_effect = Exception("Network error")
            
            result = await service.health_check()
            
            assert result is False


class TestOllamaServiceModelManagement:
    """Test model management functionality."""
    
    @pytest.mark.asyncio
    async def test_is_model_ready_success(self):
        """Test successful model readiness check."""
        service = OllamaService("http://localhost:11434")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock successful model list response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "llava:latest", "size": 4000000000},
                    {"name": "llama2:latest", "size": 3800000000}
                ]
            }
            mock_instance.get.return_value = mock_response
            
            result = await service.is_model_ready()
            
            assert result is True
            mock_instance.get.assert_called_once_with(
                "http://localhost:11434/api/tags",
                timeout=30.0
            )
    
    @pytest.mark.asyncio
    async def test_is_model_ready_model_not_available(self):
        """Test model readiness check when model is not available."""
        service = OllamaService("http://localhost:11434")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock response with different models
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "llama2:latest", "size": 3800000000}
                ]
            }
            mock_instance.get.return_value = mock_response
            
            result = await service.is_model_ready()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_ensure_model_ready_already_available(self):
        """Test ensure model ready when model is already available."""
        service = OllamaService("http://localhost:11434")
        
        with patch.object(service, 'is_model_ready', return_value=True):
            # Should not raise any exception
            await service.ensure_model_ready()
    
    @pytest.mark.asyncio
    async def test_ensure_model_ready_needs_pull(self):
        """Test ensure model ready when model needs to be pulled."""
        service = OllamaService("http://localhost:11434")
        
        with patch.object(service, 'is_model_ready', side_effect=[False, True]):
            with patch('httpx.AsyncClient') as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_instance
                
                # Mock successful pull response
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_instance.post.return_value = mock_response
                
                await service.ensure_model_ready()
                
                # Verify pull was called
                mock_instance.post.assert_called_once()


class TestOllamaServiceVectorGeneration:
    """Test vector generation functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_concept_vector_success(self, create_test_image):
        """Test successful concept vector generation."""
        service = OllamaService("http://localhost:11434")
        test_image = create_test_image(256, 256, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock successful generation response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "This is a test image with geometric patterns.",
                "done": True,
                "context": list(range(100)),
                "created_at": "2024-01-15T10:30:00Z",
                "model": "llava",
                "total_duration": 2500000000,
                "load_duration": 100000000,
                "prompt_eval_duration": 800000000,
                "eval_duration": 1600000000
            }
            mock_instance.post.return_value = mock_response
            
            # Mock embedding generation
            with patch.object(service, '_generate_text_embeddings', 
                            return_value=np.random.rand(1536).tolist()) as mock_embed:
                
                vector = await service.generate_concept_vector(
                    image_data=image_b64,
                    image_format="jpeg",
                    prompt="Describe this image",
                    request_id="test-123"
                )
                
                assert len(vector) == 1536
                assert all(isinstance(v, (int, float)) for v in vector)
                mock_embed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_concept_vector_with_custom_prompt(self, create_test_image):
        """Test vector generation with custom prompt."""
        service = OllamaService("http://localhost:11434")
        test_image = create_test_image(128, 128, "PNG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        custom_prompt = "What objects are visible in this image?"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "I can see geometric patterns and colored shapes.",
                "done": True
            }
            mock_instance.post.return_value = mock_response
            
            with patch.object(service, '_generate_text_embeddings',
                            return_value=np.random.rand(1536).tolist()):
                
                vector = await service.generate_concept_vector(
                    image_data=image_b64,
                    image_format="png",
                    prompt=custom_prompt,
                    request_id="test-456"
                )
                
                assert len(vector) == 1536
                
                # Verify the custom prompt was used
                call_args = mock_instance.post.call_args
                request_data = json.loads(call_args[1]['content'])
                assert custom_prompt in str(request_data)
    
    @pytest.mark.asyncio
    async def test_generate_concept_vector_invalid_image_data(self):
        """Test vector generation with invalid image data."""
        service = OllamaService("http://localhost:11434")
        
        with pytest.raises(ValueError, match="Invalid image data"):
            await service.generate_concept_vector(
                image_data="not-valid-base64",
                image_format="jpeg"
            )
    
    @pytest.mark.asyncio
    async def test_generate_concept_vector_unsupported_format(self, create_test_image):
        """Test vector generation with unsupported image format."""
        service = OllamaService("http://localhost:11434")
        test_image = create_test_image(100, 100, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        with pytest.raises(ValueError, match="Unsupported image format"):
            await service.generate_concept_vector(
                image_data=image_b64,
                image_format="bmp"  # Unsupported format
            )
    
    @pytest.mark.asyncio
    async def test_generate_concept_vector_ollama_error(self, create_test_image):
        """Test vector generation with Ollama API error."""
        service = OllamaService("http://localhost:11434")
        test_image = create_test_image(200, 200, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock Ollama error response
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.json.return_value = {"error": "Model not loaded"}
            mock_instance.post.return_value = mock_response
            
            with pytest.raises(RuntimeError, match="Ollama API error"):
                await service.generate_concept_vector(
                    image_data=image_b64,
                    image_format="jpeg"
                )


class TestOllamaServiceEmbeddings:
    """Test text embedding functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_text_embeddings_success(self):
        """Test successful text embeddings generation."""
        service = OllamaService("http://localhost:11434")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock successful embedding response
            test_embeddings = np.random.rand(1536).tolist()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "embedding": test_embeddings
            }
            mock_instance.post.return_value = mock_response
            
            embeddings = await service._generate_text_embeddings("Test text")
            
            assert embeddings == test_embeddings
            assert len(embeddings) == 1536
    
    @pytest.mark.asyncio
    async def test_generate_text_embeddings_api_error(self):
        """Test text embeddings generation with API error."""
        service = OllamaService("http://localhost:11434")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock API error
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_response.text = "Model not found"
            mock_instance.post.return_value = mock_response
            
            with pytest.raises(RuntimeError, match="Failed to generate embeddings"):
                await service._generate_text_embeddings("Test text")


class TestOllamaServiceRetryLogic:
    """Test retry logic and error handling."""
    
    @pytest.mark.asyncio
    async def test_retry_on_temporary_failure(self, create_test_image):
        """Test retry logic on temporary API failures."""
        service = OllamaService("http://localhost:11434", max_retries=3)
        test_image = create_test_image(150, 150, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock temporary failures followed by success
            failure_response = AsyncMock()
            failure_response.status_code = 503  # Service unavailable
            
            success_response = AsyncMock()
            success_response.status_code = 200
            success_response.json.return_value = {
                "response": "Test description",
                "done": True
            }
            
            # First two calls fail, third succeeds
            mock_instance.post.side_effect = [
                failure_response, failure_response, success_response
            ]
            
            with patch.object(service, '_generate_text_embeddings',
                            return_value=np.random.rand(1536).tolist()):
                
                vector = await service.generate_concept_vector(
                    image_data=image_b64,
                    image_format="jpeg"
                )
                
                assert len(vector) == 1536
                assert mock_instance.post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, create_test_image):
        """Test behavior when max retries are exceeded."""
        service = OllamaService("http://localhost:11434", max_retries=2)
        test_image = create_test_image(150, 150, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock continuous failures
            failure_response = AsyncMock()
            failure_response.status_code = 500
            failure_response.json.return_value = {"error": "Server error"}
            mock_instance.post.return_value = failure_response
            
            with pytest.raises(RuntimeError, match="Ollama API error"):
                await service.generate_concept_vector(
                    image_data=image_b64,
                    image_format="jpeg"
                )
                
            # Should have tried max_retries + 1 times
            assert mock_instance.post.call_count == 3


class TestOllamaServiceResourceManagement:
    """Test resource management and cleanup."""
    
    @pytest.mark.asyncio
    async def test_close_session(self):
        """Test proper session cleanup."""
        service = OllamaService("http://localhost:11434")
        
        # Mock session
        mock_session = AsyncMock()
        service._session = mock_session
        
        await service.close()
        
        mock_session.aclose.assert_called_once()
        assert service._session is None
    
    @pytest.mark.asyncio
    async def test_close_no_session(self):
        """Test closing when no session exists."""
        service = OllamaService("http://localhost:11434")
        
        # Should not raise any exceptions
        await service.close()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using service as async context manager."""
        async with OllamaService("http://localhost:11434") as service:
            assert service is not None
            assert hasattr(service, 'generate_concept_vector')
        
        # Session should be closed after context exit
        assert service._session is None


@pytest.mark.unit
@pytest.mark.vector
class TestVectorDimensions:
    """Test vector dimension consistency."""
    
    @pytest.mark.asyncio
    async def test_vector_dimensions_consistency(self, create_test_image):
        """Test that all generated vectors have consistent dimensions."""
        service = OllamaService("http://localhost:11434")
        
        with patch('httpx.AsyncClient'):
            with patch.object(service, '_generate_text_embeddings') as mock_embed:
                # Test different image sizes produce same vector dimensions
                test_vectors = [
                    np.random.rand(1536).tolist(),
                    np.random.rand(1536).tolist(),
                    np.random.rand(1536).tolist()
                ]
                mock_embed.side_effect = test_vectors
                
                # Test with different image sizes
                image_sizes = [(64, 64), (256, 256), (512, 512)]
                vectors = []
                
                for width, height in image_sizes:
                    test_image = create_test_image(width, height, "JPEG")
                    image_b64 = base64.b64encode(test_image).decode("utf-8")
                    
                    with patch('httpx.AsyncClient') as mock_client:
                        mock_instance = AsyncMock()
                        mock_client.return_value.__aenter__.return_value = mock_instance
                        
                        mock_response = AsyncMock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = {
                            "response": f"Image of size {width}x{height}",
                            "done": True
                        }
                        mock_instance.post.return_value = mock_response
                        
                        vector = await service.generate_concept_vector(
                            image_data=image_b64,
                            image_format="jpeg"
                        )
                        vectors.append(vector)
                
                # All vectors should have the same dimensions
                dimensions = [len(v) for v in vectors]
                assert all(d == 1536 for d in dimensions), f"Inconsistent dimensions: {dimensions}"