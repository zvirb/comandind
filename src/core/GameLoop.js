export class GameLoop {
    constructor(updateCallback, renderCallback, targetFPS = 60) {
        this.updateCallback = updateCallback;
        this.renderCallback = renderCallback;
        this.targetFPS = targetFPS;
        
        // Fixed timestep configuration
        this.fixedDeltaTime = 1000 / targetFPS; // In milliseconds
        this.maxUpdateSteps = 5; // Maximum updates per frame to prevent spiral of death
        
        // Timing variables
        this.lastTime = 0;
        this.accumulator = 0;
        this.currentTime = 0;
        this.frameCount = 0;
        
        // Performance tracking
        this.fps = 0;
        this.frameTime = 0;
        this.lastFPSUpdate = 0;
        this.framesThisSecond = 0;
        
        // State
        this.isRunning = false;
        this.rafId = null;
        
        // Bind methods
        this.loop = this.loop.bind(this);
    }
    
    start() {
        if (this.isRunning) {
            console.warn('Game loop is already running');
            return;
        }
        
        this.isRunning = true;
        this.lastTime = performance.now();
        this.lastFPSUpdate = this.lastTime;
        this.accumulator = 0;
        
        console.log(`Starting game loop with target ${this.targetFPS} FPS`);
        this.rafId = requestAnimationFrame(this.loop);
    }
    
    stop() {
        if (!this.isRunning) {
            console.warn('Game loop is not running');
            return;
        }
        
        this.isRunning = false;
        if (this.rafId) {
            cancelAnimationFrame(this.rafId);
            this.rafId = null;
        }
        
        console.log('Game loop stopped');
    }
    
    loop(timestamp) {
        if (!this.isRunning) return;
        
        try {
            // Calculate delta time
            const deltaTime = Math.min(timestamp - this.lastTime, 250); // Cap at 250ms to prevent huge jumps
            this.lastTime = timestamp;
            
            // Update FPS counter
            this.updateFPS(timestamp);
            
            // Add to accumulator
            this.accumulator += deltaTime;
            
            // Fixed timestep update loop
            let updateSteps = 0;
            while (this.accumulator >= this.fixedDeltaTime && updateSteps < this.maxUpdateSteps) {
                try {
                    // Call update with fixed delta time
                    this.updateCallback(this.fixedDeltaTime / 1000); // Convert to seconds
                } catch (updateError) {
                    console.error('Error in update callback:', updateError);
                    console.error('Stack trace:', updateError.stack);
                    this.stop();
                    return;
                }
                
                this.accumulator -= this.fixedDeltaTime;
                updateSteps++;
            }
            
            // Warn if we're falling behind
            if (updateSteps >= this.maxUpdateSteps) {
                console.warn(`Game loop is falling behind! ${updateSteps} updates in one frame`);
                // Reset accumulator to prevent spiral of death
                this.accumulator = 0;
            }
            
            // Calculate interpolation value for smooth rendering
            const interpolation = this.accumulator / this.fixedDeltaTime;
            
            try {
                // Render with interpolation
                this.renderCallback(interpolation);
            } catch (renderError) {
                console.error('Error in render callback:', renderError);
                console.error('Stack trace:', renderError.stack);
                this.stop();
                return;
            }
            
            // Increment frame counter
            this.frameCount++;
            
            // Request next frame
            this.rafId = requestAnimationFrame(this.loop);
            
        } catch (loopError) {
            console.error('Critical error in game loop:', loopError);
            console.error('Stack trace:', loopError.stack);
            this.stop();
            
            // Prevent endless error loops
            throw loopError;
        }
    }
    
    updateFPS(timestamp) {
        this.framesThisSecond++;
        
        // Update FPS every second
        if (timestamp >= this.lastFPSUpdate + 1000) {
            this.fps = this.framesThisSecond;
            this.frameTime = 1000 / this.framesThisSecond;
            this.framesThisSecond = 0;
            this.lastFPSUpdate = timestamp;
        }
    }
    
    // Get current FPS
    getFPS() {
        return this.fps;
    }
    
    // Get average frame time in ms
    getFrameTime() {
        return this.frameTime;
    }
    
    // Get total frames rendered
    getFrameCount() {
        return this.frameCount;
    }
    
    // Change target FPS
    setTargetFPS(fps) {
        this.targetFPS = fps;
        this.fixedDeltaTime = 1000 / fps;
        console.log(`Target FPS changed to ${fps}`);
    }
    
    // Pause/resume functionality
    pause() {
        if (this.isRunning) {
            this.stop();
            console.log('Game loop paused');
        }
    }
    
    resume() {
        if (!this.isRunning) {
            this.start();
            console.log('Game loop resumed');
        }
    }
    
    // Reset timing (useful after long pauses)
    resetTiming() {
        this.lastTime = performance.now();
        this.accumulator = 0;
        this.lastFPSUpdate = this.lastTime;
        this.framesThisSecond = 0;
    }
}