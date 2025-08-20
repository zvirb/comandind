#!/usr/bin/env python3
"""
Simple Authentication Performance Test
Quick test of authentication response times
"""

import asyncio
import httpx
import time
import statistics

async def test_auth_performance():
    """Test authentication performance with health endpoint"""
    response_times = []
    
    async with httpx.AsyncClient() as client:
        for i in range(10):
            start_time = time.time()
            
            try:
                response = await client.get("http://localhost:8000/health", timeout=5.0)
                end_time = time.time()
                
                response_time_ms = (end_time - start_time) * 1000
                response_times.append(response_time_ms)
                
                print(f"Request {i+1}: {response_time_ms:.1f}ms (Status: {response.status_code})")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Request {i+1} failed: {e}")
    
    if response_times:
        avg = statistics.mean(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        print(f"\n📊 Performance Summary:")
        print(f"   Average: {avg:.1f}ms")
        print(f"   Min: {min_time:.1f}ms") 
        print(f"   Max: {max_time:.1f}ms")
        print(f"   Target: <50ms")
        
        if avg < 50:
            print(f"   ✅ TARGET ACHIEVED!")
        else:
            print(f"   ⚠️  Above target ({avg:.1f}ms vs 50ms)")

if __name__ == "__main__":
    asyncio.run(test_auth_performance())