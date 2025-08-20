#!/usr/bin/env python3
"""
GPU Performance Monitor for Ollama Optimization
Real-time monitoring of GPU utilization, memory usage, and inference performance
"""

import subprocess
import json
import time
import statistics
import threading
import requests
from datetime import datetime
from typing import Dict, List, Optional
import argparse

class GPUPerformanceMonitor:
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.ollama_base_url = ollama_base_url
        self.metrics_history = []
        self.monitoring = False
        
    def get_gpu_metrics(self) -> Dict:
        """Get current GPU metrics using nvidia-smi"""
        try:
            cmd = [
                "nvidia-smi", 
                "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            gpu_metrics = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = [p.strip() for p in line.split(',')]
                    gpu_metrics.append({
                        'gpu_id': int(parts[0]),
                        'name': parts[1],
                        'utilization_percent': float(parts[2]) if parts[2] != '[Not Supported]' else 0,
                        'memory_used_mb': float(parts[3]),
                        'memory_total_mb': float(parts[4]),
                        'memory_utilization_percent': (float(parts[3]) / float(parts[4])) * 100,
                        'temperature_c': float(parts[5]) if parts[5] != '[Not Supported]' else 0,
                        'power_draw_w': float(parts[6]) if parts[6] != '[Not Supported]' else 0
                    })
            
            return {
                'timestamp': datetime.now().isoformat(),
                'gpus': gpu_metrics,
                'total_gpus': len(gpu_metrics),
                'avg_utilization': statistics.mean([gpu['utilization_percent'] for gpu in gpu_metrics]),
                'avg_memory_utilization': statistics.mean([gpu['memory_utilization_percent'] for gpu in gpu_metrics]),
                'total_memory_used_gb': sum([gpu['memory_used_mb'] for gpu in gpu_metrics]) / 1024,
                'total_memory_available_gb': sum([gpu['memory_total_mb'] for gpu in gpu_metrics]) / 1024
            }
        except subprocess.CalledProcessError as e:
            print(f"Error getting GPU metrics: {e}")
            return {}
    
    def get_ollama_metrics(self) -> Dict:
        """Get Ollama service metrics"""
        try:
            # Get loaded models
            models_response = requests.get(f"{self.ollama_base_url}/api/ps", timeout=5)
            models_data = models_response.json() if models_response.status_code == 200 else {}
            
            # Get service health
            health_response = requests.get(f"{self.ollama_base_url}/", timeout=5)
            health_status = health_response.status_code == 200
            
            return {
                'timestamp': datetime.now().isoformat(),
                'health': health_status,
                'loaded_models': models_data.get('models', []),
                'model_count': len(models_data.get('models', [])),
                'response_time_ms': health_response.elapsed.total_seconds() * 1000 if health_status else None
            }
        except Exception as e:
            print(f"Error getting Ollama metrics: {e}")
            return {'health': False, 'error': str(e)}
    
    def benchmark_inference(self, model: str = "llama3.2:3b", prompt: str = "Hello, how are you?") -> Dict:
        """Benchmark inference performance"""
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 50,  # Limit tokens for consistent benchmarking
                        "temperature": 0.1
                    }
                },
                timeout=30
            )
            
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                inference_time = end_time - start_time
                tokens_generated = len(data.get('response', '').split())
                tokens_per_second = tokens_generated / inference_time if inference_time > 0 else 0
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'model': model,
                    'inference_time_seconds': inference_time,
                    'tokens_generated': tokens_generated,
                    'tokens_per_second': tokens_per_second,
                    'prompt_length': len(prompt.split()),
                    'success': True
                }
            else:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'model': model,
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'model': model,
                'success': False,
                'error': str(e)
            }
    
    def concurrent_benchmark(self, num_concurrent: int = 4, model: str = "llama3.2:3b") -> Dict:
        """Test concurrent inference performance"""
        results = []
        threads = []
        
        def run_inference():
            result = self.benchmark_inference(model, f"Generate a creative story about AI. Request {threading.current_thread().ident}")
            results.append(result)
        
        start_time = time.time()
        
        # Start concurrent requests
        for i in range(num_concurrent):
            thread = threading.Thread(target=run_inference)
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        successful_results = [r for r in results if r.get('success', False)]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'concurrent_requests': num_concurrent,
            'total_time_seconds': end_time - start_time,
            'successful_requests': len(successful_results),
            'failed_requests': len(results) - len(successful_results),
            'avg_tokens_per_second': statistics.mean([r['tokens_per_second'] for r in successful_results]) if successful_results else 0,
            'results': results
        }
    
    def start_monitoring(self, interval: int = 5, duration: int = 60):
        """Start continuous monitoring"""
        self.monitoring = True
        self.metrics_history = []
        
        print(f"Starting GPU performance monitoring for {duration} seconds (interval: {interval}s)")
        print("=" * 80)
        
        start_time = time.time()
        
        while self.monitoring and (time.time() - start_time) < duration:
            gpu_metrics = self.get_gpu_metrics()
            ollama_metrics = self.get_ollama_metrics()
            
            combined_metrics = {
                'timestamp': datetime.now().isoformat(),
                'gpu': gpu_metrics,
                'ollama': ollama_metrics
            }
            
            self.metrics_history.append(combined_metrics)
            
            # Display current metrics
            if gpu_metrics:
                print(f"[{combined_metrics['timestamp']}]")
                print(f"  GPU Avg Utilization: {gpu_metrics.get('avg_utilization', 0):.1f}%")
                print(f"  GPU Avg Memory: {gpu_metrics.get('avg_memory_utilization', 0):.1f}%")
                print(f"  Total Memory Used: {gpu_metrics.get('total_memory_used_gb', 0):.1f}GB")
                print(f"  Ollama Health: {'✓' if ollama_metrics.get('health', False) else '✗'}")
                print(f"  Loaded Models: {ollama_metrics.get('model_count', 0)}")
                print("-" * 40)
            
            time.sleep(interval)
        
        self.monitoring = False
        return self.metrics_history
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
    
    def generate_report(self) -> Dict:
        """Generate comprehensive performance report"""
        if not self.metrics_history:
            return {'error': 'No metrics collected'}
        
        gpu_utilizations = []
        memory_utilizations = []
        
        for metric in self.metrics_history:
            if 'gpu' in metric and metric['gpu']:
                gpu_utilizations.append(metric['gpu'].get('avg_utilization', 0))
                memory_utilizations.append(metric['gpu'].get('avg_memory_utilization', 0))
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'monitoring_duration_seconds': len(self.metrics_history) * 5,  # Assuming 5s intervals
            'gpu_performance': {
                'avg_utilization_percent': statistics.mean(gpu_utilizations) if gpu_utilizations else 0,
                'max_utilization_percent': max(gpu_utilizations) if gpu_utilizations else 0,
                'min_utilization_percent': min(gpu_utilizations) if gpu_utilizations else 0,
                'avg_memory_utilization_percent': statistics.mean(memory_utilizations) if memory_utilizations else 0,
                'utilization_consistency': statistics.stdev(gpu_utilizations) if len(gpu_utilizations) > 1 else 0
            },
            'total_metrics_collected': len(self.metrics_history)
        }
        
        return report

def main():
    parser = argparse.ArgumentParser(description='GPU Performance Monitor for Ollama')
    parser.add_argument('--action', choices=['monitor', 'benchmark', 'concurrent', 'report'], 
                       default='monitor', help='Action to perform')
    parser.add_argument('--duration', type=int, default=60, help='Monitoring duration in seconds')
    parser.add_argument('--interval', type=int, default=5, help='Monitoring interval in seconds')
    parser.add_argument('--concurrent', type=int, default=4, help='Number of concurrent requests for benchmark')
    parser.add_argument('--model', default='llama3.2:3b', help='Model to use for benchmarking')
    parser.add_argument('--ollama-url', default='http://localhost:11434', help='Ollama base URL')
    
    args = parser.parse_args()
    
    monitor = GPUPerformanceMonitor(args.ollama_url)
    
    if args.action == 'monitor':
        metrics = monitor.start_monitoring(args.interval, args.duration)
        report = monitor.generate_report()
        print("\n" + "=" * 80)
        print("PERFORMANCE REPORT")
        print("=" * 80)
        print(json.dumps(report, indent=2))
        
    elif args.action == 'benchmark':
        print("Running single inference benchmark...")
        result = monitor.benchmark_inference(args.model)
        print(json.dumps(result, indent=2))
        
    elif args.action == 'concurrent':
        print(f"Running concurrent benchmark with {args.concurrent} requests...")
        result = monitor.concurrent_benchmark(args.concurrent, args.model)
        print(json.dumps(result, indent=2))
        
    elif args.action == 'report':
        gpu_metrics = monitor.get_gpu_metrics()
        ollama_metrics = monitor.get_ollama_metrics()
        print("Current System Status:")
        print(json.dumps({
            'gpu': gpu_metrics,
            'ollama': ollama_metrics
        }, indent=2))

if __name__ == "__main__":
    main()