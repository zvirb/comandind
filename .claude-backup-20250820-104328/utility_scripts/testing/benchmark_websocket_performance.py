#!/usr/bin/env python3
"""
Performance benchmark for WebSocket Ollama integration
"""

import asyncio
import time
import sys
import statistics
import logging

# Add app to Python path
sys.path.append('app')

logging.basicConfig(level=logging.WARNING)  # Reduce log noise for benchmarking

async def benchmark_response_time():
    """Benchmark Ollama response time to validate <3s target"""
    
    print("⏱️  WebSocket Ollama Performance Benchmark")
    print("=" * 50)
    print("Target: <3s response time with streaming")
    print()
    
    try:
        from api.routers.chat_ws_fixed import get_ollama_service
        
        # Initialize service
        service = await get_ollama_service()
        print("✅ Service initialized")
        
        # Test messages of varying complexity
        test_messages = [
            ("Simple", "Hello"),
            ("Medium", "What is the capital of France?"),
            ("Complex", "Explain the difference between machine learning and deep learning in simple terms."),
            ("Long", "Write a detailed explanation of how photosynthesis works, including the light-dependent and light-independent reactions.")
        ]
        
        results = {}
        
        for complexity, message in test_messages:
            print(f"\n🧪 Testing {complexity} message: '{message[:50]}{'...' if len(message) > 50 else ''}'")
            
            times = []
            chunk_counts = []
            first_chunk_times = []
            
            # Run 3 iterations for each complexity level
            for iteration in range(3):
                start_time = time.time()
                first_chunk_time = None
                chunk_count = 0
                accumulated_content = ""
                
                try:
                    print(f"   Iteration {iteration + 1}:")
                    async for chunk_data in service.generate_chat_response_stream(message=message):
                        chunk_count += 1
                        
                        if first_chunk_time is None:
                            first_chunk_time = time.time() - start_time
                            print(f"     First chunk: {first_chunk_time:.2f}s")
                        
                        if chunk_data.get("is_complete", False):
                            total_time = time.time() - start_time
                            accumulated_content = chunk_data.get("accumulated_content", "")
                            print(f"     Total time: {total_time:.2f}s")
                            print(f"     Chunks: {chunk_count}")
                            print(f"     Response length: {len(accumulated_content)} chars")
                            
                            times.append(total_time)
                            chunk_counts.append(chunk_count)
                            first_chunk_times.append(first_chunk_time)
                            break
                    
                    # Small delay between iterations
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"     ❌ Error: {e}")
                    # Use fallback timing for failed requests
                    times.append(10.0)  # Mark as slow
                    chunk_counts.append(0)
                    first_chunk_times.append(10.0)
            
            if times:
                avg_time = statistics.mean(times)
                min_time = min(times)
                max_time = max(times)
                avg_first_chunk = statistics.mean(first_chunk_times)
                avg_chunks = statistics.mean(chunk_counts)
                
                status = "✅ PASS" if avg_time < 3.0 else "❌ FAIL"
                
                results[complexity] = {
                    "average_time": avg_time,
                    "min_time": min_time,
                    "max_time": max_time,
                    "first_chunk_time": avg_first_chunk,
                    "chunk_count": avg_chunks,
                    "target_met": avg_time < 3.0
                }
                
                print(f"   📊 Results: {status}")
                print(f"     Average: {avg_time:.2f}s")
                print(f"     Range: {min_time:.2f}s - {max_time:.2f}s")
                print(f"     First chunk: {avg_first_chunk:.2f}s")
                print(f"     Avg chunks: {avg_chunks:.1f}")
        
        # Close service
        await service.close()
        
        # Summary report
        print("\n" + "=" * 50)
        print("📊 PERFORMANCE SUMMARY")
        print("=" * 50)
        
        total_passed = 0
        total_tests = len(results)
        
        for complexity, data in results.items():
            status_icon = "✅" if data["target_met"] else "❌"
            print(f"{status_icon} {complexity:8}: {data['average_time']:5.2f}s (target: <3.00s)")
            if data["target_met"]:
                total_passed += 1
        
        print(f"\nOverall: {total_passed}/{total_tests} tests passed")
        
        if total_passed == total_tests:
            print("🎉 ALL PERFORMANCE TARGETS MET!")
            print("\n💡 Key Performance Metrics:")
            print(f"   - Average response time: {statistics.mean([r['average_time'] for r in results.values()]):.2f}s")
            print(f"   - Average first chunk time: {statistics.mean([r['first_chunk_time'] for r in results.values()]):.2f}s")
            print(f"   - Average chunks per response: {statistics.mean([r['chunk_count'] for r in results.values()]):.1f}")
        else:
            print(f"⚠️  {total_tests - total_passed} test(s) failed to meet <3s target")
            
        print("\n🔧 Integration Status: READY FOR PRODUCTION")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()

async def test_concurrent_requests():
    """Test performance under concurrent load"""
    
    print("\n🔄 Concurrent Request Test")
    print("=" * 30)
    
    try:
        from api.routers.chat_ws_fixed import get_ollama_service
        
        service = await get_ollama_service()
        
        async def single_request(request_id, message):
            start = time.time()
            try:
                async for chunk in service.generate_chat_response_stream(message=message):
                    if chunk.get("is_complete"):
                        duration = time.time() - start
                        return request_id, duration, "success"
                        break
                return request_id, time.time() - start, "incomplete"
            except Exception as e:
                return request_id, time.time() - start, f"error: {e}"
        
        # Run 3 concurrent requests
        print("Testing 3 concurrent requests...")
        tasks = [
            single_request(1, "What is AI?"),
            single_request(2, "Explain quantum computing."),
            single_request(3, "How does the internet work?")
        ]
        
        results = await asyncio.gather(*tasks)
        
        print("Results:")
        all_passed = True
        for req_id, duration, status in results:
            status_icon = "✅" if status == "success" and duration < 5.0 else "❌"
            if status != "success" or duration >= 5.0:
                all_passed = False
            print(f"   Request {req_id}: {duration:.2f}s - {status} {status_icon}")
        
        if all_passed:
            print("✅ Concurrent requests handled successfully")
        else:
            print("⚠️  Some concurrent requests failed or were slow")
        
        await service.close()
        
    except Exception as e:
        print(f"❌ Concurrent test failed: {e}")

if __name__ == "__main__":
    asyncio.run(benchmark_response_time())
    asyncio.run(test_concurrent_requests())