"""Performance benchmarking tests for Perception Service.

Tests performance characteristics including P95 latency targets,
throughput under load, and resource utilization patterns.
"""

import asyncio
import base64
import time
import statistics
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from unittest.mock import AsyncMock
import pytest
from httpx import AsyncClient
import numpy as np
from PIL import Image
import io
import psutil
import gc

from perception_service.main import create_app


class PerformanceMetrics:
    """Utility class for collecting and analyzing performance metrics."""
    
    def __init__(self):
        self.response_times = []
        self.processing_times = []
        self.memory_usage = []
        self.cpu_usage = []
        self.error_count = 0
        self.success_count = 0
    
    def add_response(self, response_time_ms: float, processing_time_ms: float = None, success: bool = True):
        """Add a response measurement."""
        self.response_times.append(response_time_ms)
        if processing_time_ms:
            self.processing_times.append(processing_time_ms)
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def add_system_metrics(self):
        """Add current system resource usage."""
        process = psutil.Process()
        self.memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
        self.cpu_usage.append(process.cpu_percent())
    
    def calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate performance percentiles."""
        if not values:
            return {}
        
        sorted_values = sorted(values)
        return {
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": np.percentile(sorted_values, 95),
            "p99": np.percentile(sorted_values, 99),
            "std": statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            "response_times": self.calculate_percentiles(self.response_times),
            "processing_times": self.calculate_percentiles(self.processing_times),
            "memory_usage": self.calculate_percentiles(self.memory_usage),
            "cpu_usage": self.calculate_percentiles(self.cpu_usage),
            "success_rate": self.success_count / (self.success_count + self.error_count) if (self.success_count + self.error_count) > 0 else 0,
            "total_requests": self.success_count + self.error_count,
            "error_rate": self.error_count / (self.success_count + self.error_count) if (self.success_count + self.error_count) > 0 else 0
        }


@pytest.fixture
def performance_test_images():
    """Create test images of various sizes for performance testing."""
    def _create_performance_image(width: int, height: int, complexity: str = "medium"):
        """Create test image with specified complexity."""
        image = Image.new("RGB", (width, height), (255, 255, 255))
        pixels = image.load()
        
        if complexity == "simple":
            # Simple solid color blocks
            for x in range(width):
                for y in range(height):
                    pixels[x, y] = ((x // 100) * 50, (y // 100) * 50, 128)
        
        elif complexity == "medium":
            # Medium complexity patterns
            for x in range(width):
                for y in range(height):
                    r = int(128 + 127 * np.sin(x / 50))
                    g = int(128 + 127 * np.cos(y / 50))
                    b = int(128 + 127 * np.sin((x + y) / 75))
                    pixels[x, y] = (r, g, b)
        
        elif complexity == "complex":
            # High complexity with detailed patterns
            for x in range(width):
                for y in range(height):
                    r = int(128 + 127 * np.sin(x / 10) * np.cos(y / 15))
                    g = int(128 + 127 * np.cos(x / 20) * np.sin(y / 25))
                    b = int(128 + 127 * np.sin((x * y) / 100))
                    pixels[x, y] = (r, g, b)
        
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=95)
        return buffer.getvalue()
    
    return {
        "tiny_simple": _create_performance_image(64, 64, "simple"),
        "small_medium": _create_performance_image(256, 256, "medium"), 
        "medium_complex": _create_performance_image(512, 512, "complex"),
        "large_medium": _create_performance_image(1024, 768, "medium"),
        "xlarge_simple": _create_performance_image(2048, 1536, "simple")
    }


@pytest.mark.performance
@pytest.mark.slow
class TestPerceptionP95LatencyTargets:
    """Test P95 latency targets for perception service under various conditions."""
    
    @pytest.mark.asyncio
    async def test_p95_latency_standard_images(self, performance_test_images):
        """Test P95 latency < 2s for standard image sizes (256x256 to 1024x768)."""
        app = create_app()
        
        # Mock Ollama service with realistic variable response times
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        async def realistic_processing(*args, **kwargs):
            # Simulate variable processing time (800ms to 1800ms)
            base_time = 0.8
            variation = np.random.uniform(0, 1.0)  # 0-1s variation
            await asyncio.sleep(base_time + variation)
            return np.random.rand(1536).tolist()
        
        mock_ollama_service.generate_concept_vector.side_effect = realistic_processing
        app.state.ollama_service = mock_ollama_service
        
        metrics = PerformanceMetrics()
        
        # Test standard image sizes
        test_cases = [
            ("small_medium", "256x256 medium complexity"),
            ("medium_complex", "512x512 complex patterns"),
            ("large_medium", "1024x768 medium complexity")
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for image_key, description in test_cases:
                print(f"Testing P95 latency for {description}...")
                
                image_data = performance_test_images[image_key]
                image_b64 = base64.b64encode(image_data).decode("utf-8")
                
                # Run 100 requests to get good P95 statistics
                tasks = []
                for i in range(100):
                    request_data = {
                        "image_data": image_b64,
                        "format": "jpeg",
                        "prompt": f"Performance test {i} for {description}"
                    }
                    tasks.append(self._timed_request(client, request_data))
                
                # Execute requests with some concurrency (batches of 20)
                for batch_start in range(0, 100, 20):
                    batch_tasks = tasks[batch_start:batch_start + 20]
                    batch_results = await asyncio.gather(*batch_tasks)
                    
                    for response_time, processing_time, success in batch_results:
                        metrics.add_response(response_time, processing_time, success)
                        metrics.add_system_metrics()
                    
                    # Brief pause between batches to avoid overwhelming
                    await asyncio.sleep(0.1)
        
        # Analyze performance results
        summary = metrics.get_summary()
        
        print(f"\nP95 Latency Test Results:")
        print(f"  Total Requests: {summary['total_requests']}")
        print(f"  Success Rate: {summary['success_rate']:.2%}")
        print(f"  Response Times (ms):")
        print(f"    Mean: {summary['response_times']['mean']:.0f}")
        print(f"    P95: {summary['response_times']['p95']:.0f}")
        print(f"    P99: {summary['response_times']['p99']:.0f}")
        print(f"    Max: {summary['response_times']['max']:.0f}")
        
        # Assert P95 target
        p95_latency = summary['response_times']['p95']
        assert p95_latency <= 2000, f"P95 latency {p95_latency:.0f}ms exceeds 2000ms target"
        
        # Assert success rate
        assert summary['success_rate'] >= 0.99, f"Success rate {summary['success_rate']:.2%} below 99% target"
    
    @pytest.mark.asyncio
    async def test_p95_latency_under_load(self, performance_test_images):
        """Test P95 latency under concurrent load."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        async def consistent_processing(*args, **kwargs):
            # More consistent processing time under load
            await asyncio.sleep(1.2)  # 1.2s baseline
            return np.random.rand(1536).tolist()
        
        mock_ollama_service.generate_concept_vector.side_effect = consistent_processing
        app.state.ollama_service = mock_ollama_service
        
        metrics = PerformanceMetrics()
        image_b64 = base64.b64encode(performance_test_images["small_medium"]).decode("utf-8")
        
        # Concurrent load test: 50 concurrent requests
        concurrent_requests = 50
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            tasks = []
            for i in range(concurrent_requests):
                request_data = {
                    "image_data": image_b64,
                    "format": "jpeg",
                    "prompt": f"Concurrent load test {i}"
                }
                tasks.append(self._timed_request(client, request_data))
            
            # Execute all requests concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            for response_time, processing_time, success in results:
                metrics.add_response(response_time, processing_time, success)
        
        summary = metrics.get_summary()
        throughput = concurrent_requests / total_time
        
        print(f"\nConcurrent Load Test Results:")
        print(f"  Concurrent Requests: {concurrent_requests}")
        print(f"  Total Time: {total_time:.1f}s")
        print(f"  Throughput: {throughput:.1f} req/s")
        print(f"  P95 Latency: {summary['response_times']['p95']:.0f}ms")
        print(f"  Success Rate: {summary['success_rate']:.2%}")
        
        # Under load, allow slightly higher P95 (2.5s)
        assert summary['response_times']['p95'] <= 2500, "P95 latency under load exceeds 2.5s"
        assert summary['success_rate'] >= 0.95, "Success rate under load below 95%"
    
    async def _timed_request(self, client, request_data):
        """Execute a timed request and return metrics."""
        start_time = time.time()
        try:
            response = await client.post("/conceptualize", json=request_data)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            processing_time = None
            success = response.status_code == 200
            
            if success:
                result = response.json()
                processing_time = result.get("processing_time_ms")
            
            return response_time, processing_time, success
            
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            return response_time, None, False


@pytest.mark.performance
@pytest.mark.slow
class TestThroughputBenchmarks:
    """Test throughput characteristics under various load patterns."""
    
    @pytest.mark.asyncio
    async def test_sustained_throughput(self, performance_test_images):
        """Test sustained throughput over extended period."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        async def fast_processing(*args, **kwargs):
            await asyncio.sleep(0.5)  # Fast processing for throughput test
            return np.random.rand(1536).tolist()
        
        mock_ollama_service.generate_concept_vector.side_effect = fast_processing
        app.state.ollama_service = mock_ollama_service
        
        metrics = PerformanceMetrics()
        image_b64 = base64.b64encode(performance_test_images["small_medium"]).decode("utf-8")
        
        # Sustained load: 200 requests over 60 seconds with steady rate
        total_requests = 200
        duration_seconds = 60
        batch_size = 10
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            start_time = time.time()
            completed_requests = 0
            
            while completed_requests < total_requests:
                batch_start = time.time()
                
                # Submit batch of requests
                tasks = []
                batch_actual_size = min(batch_size, total_requests - completed_requests)
                
                for i in range(batch_actual_size):
                    request_data = {
                        "image_data": image_b64,
                        "format": "jpeg",
                        "prompt": f"Sustained throughput test {completed_requests + i}"
                    }
                    tasks.append(self._timed_request_with_metrics(client, request_data, metrics))
                
                # Execute batch
                await asyncio.gather(*tasks)
                completed_requests += batch_actual_size
                
                # Rate limiting to achieve target duration
                batch_time = time.time() - batch_start
                target_batch_time = (duration_seconds / total_requests) * batch_size
                
                if batch_time < target_batch_time:
                    await asyncio.sleep(target_batch_time - batch_time)
            
            total_time = time.time() - start_time
        
        summary = metrics.get_summary()
        actual_throughput = total_requests / total_time
        
        print(f"\nSustained Throughput Test Results:")
        print(f"  Total Requests: {total_requests}")
        print(f"  Duration: {total_time:.1f}s")
        print(f"  Average Throughput: {actual_throughput:.1f} req/s")
        print(f"  Mean Response Time: {summary['response_times']['mean']:.0f}ms")
        print(f"  P95 Response Time: {summary['response_times']['p95']:.0f}ms")
        print(f"  Success Rate: {summary['success_rate']:.2%}")
        
        # Throughput targets
        assert actual_throughput >= 2.0, f"Throughput {actual_throughput:.1f} req/s below 2.0 req/s minimum"
        assert summary['success_rate'] >= 0.98, "Success rate in sustained test below 98%"
    
    @pytest.mark.asyncio
    async def test_burst_throughput(self, performance_test_images):
        """Test system behavior under burst load patterns."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        async def variable_processing(*args, **kwargs):
            # Variable processing time to simulate real conditions
            await asyncio.sleep(np.random.uniform(0.3, 1.5))
            return np.random.rand(1536).tolist()
        
        mock_ollama_service.generate_concept_vector.side_effect = variable_processing
        app.state.ollama_service = mock_ollama_service
        
        metrics = PerformanceMetrics()
        image_b64 = base64.b64encode(performance_test_images["small_medium"]).decode("utf-8")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Burst pattern: 3 bursts of 30 requests each with 10s gaps
            for burst in range(3):
                print(f"Executing burst {burst + 1}/3...")
                
                burst_start = time.time()
                
                # Submit burst of 30 concurrent requests
                tasks = []
                for i in range(30):
                    request_data = {
                        "image_data": image_b64,
                        "format": "jpeg", 
                        "prompt": f"Burst {burst} request {i}"
                    }
                    tasks.append(self._timed_request_with_metrics(client, request_data, metrics))
                
                # Execute burst concurrently
                await asyncio.gather(*tasks)
                
                burst_time = time.time() - burst_start
                burst_throughput = 30 / burst_time
                
                print(f"  Burst {burst + 1} completed in {burst_time:.1f}s ({burst_throughput:.1f} req/s)")
                
                # Wait between bursts (except after last burst)
                if burst < 2:
                    await asyncio.sleep(10)
        
        summary = metrics.get_summary()
        
        print(f"\nBurst Throughput Test Results:")
        print(f"  Total Requests: {summary['total_requests']}")
        print(f"  Overall Success Rate: {summary['success_rate']:.2%}")
        print(f"  Response Time P95: {summary['response_times']['p95']:.0f}ms")
        print(f"  Response Time P99: {summary['response_times']['p99']:.0f}ms")
        
        # Burst load should handle spikes gracefully
        assert summary['success_rate'] >= 0.90, "Success rate during bursts below 90%"
        assert summary['response_times']['p95'] <= 5000, "P95 response time during bursts exceeds 5s"
    
    async def _timed_request_with_metrics(self, client, request_data, metrics):
        """Execute a timed request and add to metrics."""
        start_time = time.time()
        try:
            response = await client.post("/conceptualize", json=request_data)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            processing_time = None
            success = response.status_code == 200
            
            if success:
                result = response.json()
                processing_time = result.get("processing_time_ms")
            
            metrics.add_response(response_time, processing_time, success)
            return response_time, processing_time, success
            
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            metrics.add_response(response_time, None, False)
            return response_time, None, False


@pytest.mark.performance
class TestResourceUtilization:
    """Test resource utilization patterns and memory management."""
    
    @pytest.mark.asyncio
    async def test_memory_usage_patterns(self, performance_test_images):
        """Test memory usage patterns under load."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        mock_ollama_service.generate_concept_vector.return_value = np.random.rand(1536).tolist()
        
        app.state.ollama_service = mock_ollama_service
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_measurements = []
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Process images of different sizes to test memory usage
            for size_key, description in [
                ("tiny_simple", "64x64"),
                ("small_medium", "256x256"), 
                ("medium_complex", "512x512"),
                ("large_medium", "1024x768"),
                ("xlarge_simple", "2048x1536")
            ]:
                print(f"Testing memory usage for {description} images...")
                
                image_b64 = base64.b64encode(performance_test_images[size_key]).decode("utf-8")
                
                # Process 20 images of this size
                for i in range(20):
                    request_data = {
                        "image_data": image_b64,
                        "format": "jpeg",
                        "prompt": f"Memory test {i} for {description}"
                    }
                    
                    response = await client.post("/conceptualize", json=request_data)
                    assert response.status_code == 200
                    
                    # Measure memory after each request
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_measurements.append({
                        "size": description,
                        "request": i,
                        "memory_mb": current_memory,
                        "memory_delta": current_memory - initial_memory
                    })
                
                # Force garbage collection between sizes
                gc.collect()
                await asyncio.sleep(0.1)
        
        # Analyze memory usage patterns
        final_memory = process.memory_info().rss / 1024 / 1024
        max_memory = max(m["memory_mb"] for m in memory_measurements)
        memory_growth = final_memory - initial_memory
        
        print(f"\nMemory Usage Analysis:")
        print(f"  Initial Memory: {initial_memory:.1f} MB")
        print(f"  Final Memory: {final_memory:.1f} MB")
        print(f"  Peak Memory: {max_memory:.1f} MB")
        print(f"  Memory Growth: {memory_growth:.1f} MB")
        
        # Memory usage should be reasonable
        assert memory_growth <= 100, f"Memory growth {memory_growth:.1f} MB exceeds 100 MB limit"
        assert max_memory <= initial_memory + 150, f"Peak memory usage exceeds reasonable limits"
    
    @pytest.mark.asyncio
    async def test_performance_scaling_with_image_size(self, performance_test_images):
        """Test how performance scales with image size."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        # Mock processing time that scales with image size
        async def size_based_processing(*args, **kwargs):
            # Extract image size from base64 data length as proxy
            image_data = kwargs.get("image_data", "")
            data_size = len(image_data)
            
            # Scale processing time based on data size
            base_time = 0.5
            size_factor = min(data_size / 100000, 3.0)  # Cap at 3x
            processing_time = base_time + (size_factor * 0.5)
            
            await asyncio.sleep(processing_time)
            return np.random.rand(1536).tolist()
        
        mock_ollama_service.generate_concept_vector.side_effect = size_based_processing
        app.state.ollama_service = mock_ollama_service
        
        scaling_results = []
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            size_tests = [
                ("tiny_simple", "64x64"),
                ("small_medium", "256x256"),
                ("medium_complex", "512x512"), 
                ("large_medium", "1024x768"),
                ("xlarge_simple", "2048x1536")
            ]
            
            for size_key, description in size_tests:
                image_data = performance_test_images[size_key]
                image_b64 = base64.b64encode(image_data).decode("utf-8")
                data_size_kb = len(image_data) / 1024
                
                # Run 10 requests for each size
                response_times = []
                
                for i in range(10):
                    start_time = time.time()
                    response = await client.post("/conceptualize", json={
                        "image_data": image_b64,
                        "format": "jpeg",
                        "prompt": f"Size scaling test {i}"
                    })
                    end_time = time.time()
                    
                    assert response.status_code == 200
                    response_time = (end_time - start_time) * 1000
                    response_times.append(response_time)
                
                mean_response_time = statistics.mean(response_times)
                scaling_results.append({
                    "size": description,
                    "data_size_kb": data_size_kb,
                    "mean_response_time_ms": mean_response_time
                })
        
        print(f"\nPerformance Scaling Results:")
        for result in scaling_results:
            print(f"  {result['size']}: {result['data_size_kb']:.0f}KB → {result['mean_response_time_ms']:.0f}ms")
        
        # Verify reasonable scaling (larger images should not be disproportionately slow)
        tiny_time = scaling_results[0]["mean_response_time_ms"]
        xlarge_time = scaling_results[-1]["mean_response_time_ms"]
        scaling_factor = xlarge_time / tiny_time
        
        print(f"  Scaling Factor (XLarge/Tiny): {scaling_factor:.1f}x")
        
        # Performance should not degrade more than 4x for largest vs smallest images
        assert scaling_factor <= 4.0, f"Performance scaling factor {scaling_factor:.1f}x exceeds 4x limit"