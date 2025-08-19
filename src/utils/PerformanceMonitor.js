export class PerformanceMonitor {
    constructor() {
        this.fps = 0;
        this.frameTime = 0;
        this.memoryUsage = 0;
        
        // FPS calculation
        this.frameCount = 0;
        this.lastTime = performance.now();
        this.lastFPSUpdate = this.lastTime;
        
        // Frame time tracking
        this.frameTimes = new Array(60).fill(16.67);
        this.frameTimeIndex = 0;
        
        // Memory tracking (if available)
        this.supportsMemory = performance.memory !== undefined;
    }
    
    update() {
        const now = performance.now();
        const delta = now - this.lastTime;
        this.lastTime = now;
        
        // Track frame time
        this.frameTimes[this.frameTimeIndex] = delta;
        this.frameTimeIndex = (this.frameTimeIndex + 1) % this.frameTimes.length;
        
        // Calculate average frame time
        this.frameTime = this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length;
        
        // Update FPS
        this.frameCount++;
        if (now >= this.lastFPSUpdate + 1000) {
            this.fps = this.frameCount;
            this.frameCount = 0;
            this.lastFPSUpdate = now;
            
            // Update memory usage
            if (this.supportsMemory) {
                this.memoryUsage = performance.memory.usedJSHeapSize / 1048576; // Convert to MB
            }
        }
    }
    
    getFPS() {
        return this.fps;
    }
    
    getFrameTime() {
        return this.frameTime;
    }
    
    getMemoryUsage() {
        return this.memoryUsage;
    }
    
    getStats() {
        return {
            fps: this.fps,
            frameTime: this.frameTime.toFixed(2),
            memory: this.memoryUsage.toFixed(2)
        };
    }
    
    stop() {
        // Reset performance tracking
        this.frameCount = 0;
        this.fps = 0;
        this.frameTime = 0;
        this.memoryUsage = 0;
        this.frameTimes.fill(16.67);
        this.frameTimeIndex = 0;
        console.log('📊 PerformanceMonitor stopped and reset');
    }
}