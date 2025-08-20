/**
 * Production Health Check System
 * Provides comprehensive application health monitoring for deployment validation
 */

export class HealthCheck {
    constructor() {
        this.checks = new Map();
        this.status = {
            healthy: true,
            version: "0.1.0",
            timestamp: new Date().toISOString(),
            uptime: 0,
            environment: "production"
        };
        this.startTime = Date.now();
    
        this.registerDefaultChecks();
        this.startHealthEndpoint();
    }

    registerDefaultChecks() {
    // WebGL Health Check
        this.registerCheck("webgl", () => {
            const canvas = document.createElement("canvas");
            const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
            return {
                healthy: !!gl,
                details: {
                    webgl_supported: !!gl,
                    extensions: gl ? gl.getSupportedExtensions().length : 0
                }
            };
        });

        // Memory Health Check  
        this.registerCheck("memory", () => {
            if (performance.memory) {
                const memory = performance.memory;
                const memoryUsage = memory.usedJSHeapSize / memory.totalJSHeapSize;
                return {
                    healthy: memoryUsage < 0.9, // Alert if >90% memory usage
                    details: {
                        used_mb: Math.round(memory.usedJSHeapSize / 1048576),
                        total_mb: Math.round(memory.totalJSHeapSize / 1048576),
                        usage_percent: Math.round(memoryUsage * 100)
                    }
                };
            }
            return { healthy: true, details: { memory_api: "unavailable" } };
        });

        // Core Systems Health Check
        this.registerCheck("core_systems", () => {
            return {
                healthy: true,
                details: {
                    application: window.gameApplication ? "loaded" : "missing",
                    renderer: window.gameRenderer ? "loaded" : "missing",
                    input_handler: window.gameInputHandler ? "loaded" : "missing"
                }
            };
        });

        // Asset Loading Health Check
        this.registerCheck("assets", () => {
            return {
                healthy: true,
                details: {
                    textures_loaded: window.loadedTextures ? Object.keys(window.loadedTextures).length : 0,
                    audio_ready: window.audioContext ? window.audioContext.state : "unknown"
                }
            };
        });

        // Performance Health Check
        this.registerCheck("performance", () => {
            const now = performance.now();
            const fps = this.calculateFPS();
            return {
                healthy: fps > 30, // Alert if FPS drops below 30
                details: {
                    fps: fps,
                    frame_time_ms: window.lastFrameTime || 0,
                    performance_now: Math.round(now)
                }
            };
        });
    }

    registerCheck(name, checkFunction) {
        this.checks.set(name, checkFunction);
    }

    async runHealthCheck() {
        const results = {};
        let overallHealthy = true;
    
        this.status.uptime = Math.round((Date.now() - this.startTime) / 1000);
        this.status.timestamp = new Date().toISOString();

        for (const [name, checkFunction] of this.checks) {
            try {
                const result = await checkFunction();
                results[name] = result;
                if (!result.healthy) {
                    overallHealthy = false;
                }
            } catch (error) {
                results[name] = {
                    healthy: false,
                    error: error.message,
                    details: {}
                };
                overallHealthy = false;
            }
        }

        this.status.healthy = overallHealthy;
        this.status.checks = results;

        return this.status;
    }

    calculateFPS() {
        if (!window.fpsHistory) {
            window.fpsHistory = [];
        }
    
        const now = performance.now();
        window.fpsHistory.push(now);
    
        // Keep only last 60 frames
        if (window.fpsHistory.length > 60) {
            window.fpsHistory.shift();
        }
    
        if (window.fpsHistory.length < 2) {
            return 60; // Default assumption
        }
    
        const timeDelta = now - window.fpsHistory[0];
        const frameCount = window.fpsHistory.length - 1;
    
        return Math.round(frameCount / (timeDelta / 1000));
    }

    startHealthEndpoint() {
    // Create health check endpoint for monitoring systems
        if (typeof window !== "undefined") {
            window.healthCheck = this;
      
            // Expose health endpoint for external monitoring
            window.getHealthStatus = () => this.runHealthCheck();
        }

        // Set up periodic health checks
        setInterval(() => {
            this.runHealthCheck().then(status => {
                if (!status.healthy) {
                    console.warn("Health check failed:", status);
                }
            });
        }, 30000); // Check every 30 seconds
    }

    // Readiness probe - checks if app is ready to serve traffic
    async readinessProbe() {
        const health = await this.runHealthCheck();
        const criticalSystems = ["webgl", "core_systems"];
    
        const criticalHealthy = criticalSystems.every(system => 
            health.checks[system] && health.checks[system].healthy
        );

        return {
            ready: criticalHealthy,
            timestamp: new Date().toISOString(),
            checks: Object.fromEntries(
                criticalSystems.map(system => [system, health.checks[system]])
            )
        };
    }

    // Liveness probe - checks if app is still alive
    async livenessProbe() {
        const now = Date.now();
        const timeSinceStart = now - this.startTime;
    
        // Simple liveness check - app is alive if it can respond
        return {
            alive: true,
            uptime_seconds: Math.round(timeSinceStart / 1000),
            timestamp: new Date().toISOString()
        };
    }
}

// Initialize health check system
export const healthCheck = new HealthCheck();

// Export for external monitoring integration
if (typeof window !== "undefined") {
    window.HealthCheck = HealthCheck;
    window.healthCheck = healthCheck;
}