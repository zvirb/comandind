#!/usr/bin/env python3
"""
GPU Stress Test for Performance Optimization Validation
High-intensity concurrent requests to maximize GPU utilization
"""

import asyncio
import aiohttp
import json
import time
import sys
from datetime import datetime

async def gpu_workload_request(session, request_id):
    """Single GPU workload request"""
    payload = {
        "model": "llama3.2:3b",
        "prompt": f"Request {request_id}: Perform complex mathematical analysis including matrix operations, statistical computations, deep learning model training steps, gradient calculations, backpropagation algorithms, neural network architectures, optimization functions, memory management techniques, parallel processing strategies, and multi-threaded computational workflows. Include detailed calculations and comprehensive explanations with at least 2000 words of technical content.",
        "stream": False
    }
    
    try:
        async with session.post('http://localhost:11434/api/generate', json=payload) as response:
            if response.status == 200:
                result = await response.json()
                tokens = result.get('eval_count', 0)
                duration = result.get('eval_duration', 0) / 1e9  # Convert to seconds
                print(f"Request {request_id}: {tokens} tokens in {duration:.2f}s = {tokens/duration:.1f} tokens/sec")
                return tokens, duration
            else:
                print(f"Request {request_id}: HTTP {response.status}")
                return 0, 0
    except Exception as e:
        print(f"Request {request_id}: Error - {str(e)}")
        return 0, 0

async def run_gpu_stress_test(concurrent_requests=12, duration_minutes=2):
    """Run high-intensity GPU stress test"""
    print(f"Starting GPU Stress Test:")
    print(f"- Concurrent Requests: {concurrent_requests}")
    print(f"- Duration: {duration_minutes} minutes")
    print(f"- Target: >50% GPU utilization")
    print("="*60)
    
    end_time = time.time() + (duration_minutes * 60)
    request_id = 0
    total_tokens = 0
    total_duration = 0
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as session:
        while time.time() < end_time:
            # Launch concurrent requests
            tasks = []
            for _ in range(concurrent_requests):
                request_id += 1
                task = asyncio.create_task(gpu_workload_request(session, request_id))
                tasks.append(task)
            
            # Wait for batch completion
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aggregate results
            for result in results:
                if isinstance(result, tuple):
                    tokens, duration = result
                    total_tokens += tokens
                    total_duration += duration
            
            print(f"Batch completed at {datetime.now().strftime('%H:%M:%S')}")
            
            # Brief pause to prevent overwhelming the system
            await asyncio.sleep(1)
    
    # Calculate final statistics
    avg_throughput = total_tokens / total_duration if total_duration > 0 else 0
    print("="*60)
    print(f"GPU Stress Test Complete:")
    print(f"- Total Tokens: {total_tokens:,}")
    print(f"- Total Duration: {total_duration:.2f}s")
    print(f"- Average Throughput: {avg_throughput:.1f} tokens/sec")
    print(f"- Requests Completed: {request_id}")

if __name__ == "__main__":
    # Run stress test with high concurrency
    asyncio.run(run_gpu_stress_test(concurrent_requests=16, duration_minutes=3))