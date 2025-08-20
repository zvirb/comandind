/**
 * Performance Benchmark Suite for Command and Independent Thought
 * Simulates high-load scenarios to identify bottlenecks and optimization opportunities
 */

export class PerformanceBenchmark {
    constructor(world, renderer) {
        this.world = world;
        this.renderer = renderer;
        this.isRunning = false;
        this.benchmarkData = [];
        this.testScenarios = new Map();
        
        // Performance tracking
        this.frameTimeHistory = [];
        this.memoryHistory = [];
        this.drawCallHistory = [];
        this.entityCountHistory = [];
        
        // Benchmark configuration
        this.config = {
            maxEntities: 100,
            testDuration: 30000, // 30 seconds
            sampleInterval: 100, // Sample every 100ms
            targetFPS: 60,
            memoryWarningThreshold: 400, // MB
            memoryErrorThreshold: 600 // MB
        };
        
        this.setupTestScenarios();
    }
    
    setupTestScenarios() {
        // 50+ Unit Combat Scenario
        this.testScenarios.set("combat_50_units", {
            name: "Combat with 50+ Units",
            description: "Simulates 50 units engaging in combat with pathfinding and AI",
            entityCount: 50,
            setup: this.setupCombatScenario.bind(this),
            requirements: ["60+ FPS", "<400MB memory", "<50 draw calls"]
        });
        
        // Stress Test - 100 Units
        this.testScenarios.set("stress_100_units", {
            name: "Stress Test - 100 Units",
            description: "Maximum load test with 100 units for scalability assessment",
            entityCount: 100,
            setup: this.setupStressScenario.bind(this),
            requirements: ["45+ FPS", "<600MB memory", "<80 draw calls"]
        });
        
        // Memory Leak Detection
        this.testScenarios.set("memory_leak_test", {
            name: "Memory Leak Detection",
            description: "Creates and destroys entities repeatedly to detect memory leaks",
            entityCount: 25,
            setup: this.setupMemoryLeakTest.bind(this),
            requirements: ["Stable memory usage", "No continuous growth"]
        });
        
        // Rendering Performance
        this.testScenarios.set("rendering_stress", {
            name: "Rendering Stress Test",
            description: "Tests sprite batching efficiency with varied textures",
            entityCount: 75,
            setup: this.setupRenderingStress.bind(this),
            requirements: ["60+ FPS", "Efficient sprite batching", "<100 draw calls"]
        });
    }
    
    /**
     * Run a specific benchmark scenario
     */
    async runBenchmark(scenarioName) {
        const scenario = this.testScenarios.get(scenarioName);
        if (!scenario) {
            throw new Error(`Unknown scenario: ${scenarioName}`);
        }
        
        console.log(`🚀 Starting benchmark: ${scenario.name}`);
        console.log(`📝 Description: ${scenario.description}`);
        console.log(`🎯 Requirements: ${scenario.requirements.join(", ")}`);
        
        this.isRunning = true;
        this.clearHistory();
        
        // Setup scenario
        const testEntities = await scenario.setup();
        
        // Record baseline performance
        const baselineData = this.capturePerformanceSnapshot("baseline");
        
        // Run benchmark for configured duration
        const startTime = performance.now();
        let lastSampleTime = startTime;
        
        while (performance.now() - startTime < this.config.testDuration && this.isRunning) {
            const currentTime = performance.now();
            
            // Sample performance data
            if (currentTime - lastSampleTime >= this.config.sampleInterval) {
                this.samplePerformanceData();
                lastSampleTime = currentTime;
            }
            
            // Allow for frame processing
            await new Promise(resolve => setTimeout(resolve, 16)); // ~60 FPS
        }
        
        // Cleanup test entities
        this.cleanupTestEntities(testEntities);
        
        // Analyze results
        const results = this.analyzeResults(scenario, baselineData);
        
        console.log(`✅ Benchmark completed: ${scenario.name}`);
        this.printResults(results);
        
        this.isRunning = false;
        return results;
    }
    
    /**
     * Run all benchmark scenarios
     */
    async runAllBenchmarks() {
        const allResults = [];
        
        for (const [scenarioName, scenario] of this.testScenarios) {
            try {
                const results = await this.runBenchmark(scenarioName);
                allResults.push(results);
                
                // Wait between tests for cleanup
                await new Promise(resolve => setTimeout(resolve, 2000));
            } catch (error) {
                console.error(`❌ Benchmark failed: ${scenario.name}`, error);
                allResults.push({
                    scenario: scenarioName,
                    success: false,
                    error: error.message
                });
            }
        }
        
        this.generateComprehensiveReport(allResults);
        return allResults;
    }
    
    setupCombatScenario() {
        const entities = [];
        const unitCount = 50;
        
        // Create units in two opposing forces
        for (let i = 0; i < unitCount; i++) {
            const isPlayerUnit = i < unitCount / 2;
            const entity = this.world.createEntity();
            
            // Add required components for combat testing
            entity.addComponent("TransformComponent", {
                x: isPlayerUnit ? Math.random() * 200 + 50 : Math.random() * 200 + 600,
                y: Math.random() * 400 + 100,
                rotation: 0
            });
            
            entity.addComponent("VelocityComponent", {
                vx: 0,
                vy: 0,
                maxSpeed: 100,
                friction: 0.95
            });
            
            entity.addComponent("SpriteComponent", {
                textureName: isPlayerUnit ? "player_unit" : "enemy_unit",
                visible: true,
                alpha: 1.0
            });
            
            entity.addComponent("HealthComponent", {
                maxHealth: 100,
                currentHealth: 100
            });
            
            entity.addComponent("MovementComponent", {
                speed: 50 + Math.random() * 50,
                isMoving: false,
                path: []
            });
            
            entity.addComponent("CombatComponent", {
                damage: 25,
                range: 100,
                attackSpeed: 2.0,
                damageType: "kinetic"
            });
            
            entity.addComponent("AIComponent", {
                behaviorType: "attack",
                alertRadius: 150,
                leashRadius: 300,
                thinkInterval: 250
            });
            
            entities.push(entity);
        }
        
        return entities;
    }
    
    setupStressScenario() {
        const entities = [];
        const unitCount = 100;
        
        // Create maximum load scenario
        for (let i = 0; i < unitCount; i++) {
            const entity = this.world.createEntity();
            
            entity.addComponent("TransformComponent", {
                x: Math.random() * 1200,
                y: Math.random() * 700,
                rotation: Math.random() * Math.PI * 2
            });
            
            entity.addComponent("VelocityComponent", {
                vx: (Math.random() - 0.5) * 100,
                vy: (Math.random() - 0.5) * 100,
                maxSpeed: 100,
                friction: 0.98
            });
            
            entity.addComponent("SpriteComponent", {
                textureName: `unit_type_${Math.floor(Math.random() * 5)}`,
                visible: true,
                alpha: 0.8 + Math.random() * 0.2
            });
            
            entity.addComponent("AIComponent", {
                behaviorType: "patrol",
                alertRadius: 100,
                leashRadius: 200,
                thinkInterval: 200 + Math.random() * 300
            });
            
            entities.push(entity);
        }
        
        return entities;
    }
    
    setupMemoryLeakTest() {
        const entities = [];
        let createdEntities = 0;
        const maxEntities = 25;
        
        // Create entities and periodically destroy/recreate them
        const createDestroyInterval = setInterval(() => {
            if (!this.isRunning) {
                clearInterval(createDestroyInterval);
                return;
            }
            
            // Destroy random entities
            const toDestroy = Math.floor(Math.random() * 5) + 1;
            for (let i = 0; i < toDestroy && entities.length > 0; i++) {
                const randomIndex = Math.floor(Math.random() * entities.length);
                const entity = entities.splice(randomIndex, 1)[0];
                this.world.removeEntity(entity);
            }
            
            // Create new entities
            const toCreate = Math.floor(Math.random() * 8) + 2;
            for (let i = 0; i < toCreate && entities.length < maxEntities; i++) {
                const entity = this.world.createEntity();
                
                entity.addComponent("TransformComponent", {
                    x: Math.random() * 1200,
                    y: Math.random() * 700
                });
                
                entity.addComponent("SpriteComponent", {
                    textureName: "test_unit",
                    visible: true
                });
                
                entities.push(entity);
                createdEntities++;
            }
        }, 1000);
        
        return entities;
    }
    
    setupRenderingStress() {
        const entities = [];
        const unitCount = 75;
        const textureVariants = ["unit_a", "unit_b", "unit_c", "unit_d", "unit_e"];
        
        for (let i = 0; i < unitCount; i++) {
            const entity = this.world.createEntity();
            
            entity.addComponent("TransformComponent", {
                x: Math.random() * 1200,
                y: Math.random() * 700,
                rotation: Math.random() * Math.PI * 2,
                scaleX: 0.5 + Math.random() * 1.0,
                scaleY: 0.5 + Math.random() * 1.0
            });
            
            entity.addComponent("VelocityComponent", {
                vx: (Math.random() - 0.5) * 50,
                vy: (Math.random() - 0.5) * 50,
                maxSpeed: 75
            });
            
            entity.addComponent("SpriteComponent", {
                textureName: textureVariants[Math.floor(Math.random() * textureVariants.length)],
                visible: true,
                alpha: 0.7 + Math.random() * 0.3,
                tint: Math.floor(Math.random() * 0xFFFFFF)
            });
            
            entities.push(entity);
        }
        
        return entities;
    }
    
    samplePerformanceData() {
        const now = performance.now();
        
        // Get performance metrics
        const stats = this.world.getStats();
        const rendererStats = this.renderer.getStats();
        
        // Memory usage
        let memoryUsage = 0;
        if (performance.memory) {
            memoryUsage = performance.memory.usedJSHeapSize / 1048576; // MB
        }
        
        // Record data points
        this.frameTimeHistory.push({
            timestamp: now,
            frameTime: performance.now() - this.lastFrameTime || 16.67,
            fps: 1000 / (performance.now() - this.lastFrameTime || 16.67)
        });
        
        this.memoryHistory.push({
            timestamp: now,
            memory: memoryUsage
        });
        
        this.drawCallHistory.push({
            timestamp: now,
            drawCalls: rendererStats.drawCalls || 0
        });
        
        this.entityCountHistory.push({
            timestamp: now,
            entityCount: stats.entityCount || 0
        });
        
        this.lastFrameTime = now;
        
        // Check for performance warnings
        this.checkPerformanceWarnings(memoryUsage, rendererStats);
    }
    
    checkPerformanceWarnings(memoryUsage, rendererStats) {
        // Memory warnings
        if (memoryUsage > this.config.memoryErrorThreshold) {
            console.error(`🚨 CRITICAL: Memory usage exceeded ${this.config.memoryErrorThreshold}MB: ${memoryUsage.toFixed(1)}MB`);
        } else if (memoryUsage > this.config.memoryWarningThreshold) {
            console.warn(`⚠️  WARNING: High memory usage: ${memoryUsage.toFixed(1)}MB`);
        }
        
        // FPS warnings
        const currentFPS = this.frameTimeHistory.length > 0 ? 
            this.frameTimeHistory[this.frameTimeHistory.length - 1].fps : 60;
        
        if (currentFPS < 30) {
            console.error(`🚨 CRITICAL: FPS dropped below 30: ${currentFPS.toFixed(1)}`);
        } else if (currentFPS < 45) {
            console.warn(`⚠️  WARNING: FPS below target: ${currentFPS.toFixed(1)}`);
        }
    }
    
    capturePerformanceSnapshot(label) {
        const stats = this.world.getStats();
        const rendererStats = this.renderer.getStats();
        
        return {
            label,
            timestamp: performance.now(),
            entityCount: stats.entityCount,
            systemCount: stats.systemCount,
            drawCalls: rendererStats.drawCalls,
            spriteCount: rendererStats.spriteCount,
            textureCount: rendererStats.textureCount,
            memory: performance.memory ? performance.memory.usedJSHeapSize / 1048576 : 0
        };
    }
    
    analyzeResults(scenario, baselineData) {
        const results = {
            scenario: scenario.name,
            success: true,
            metrics: {},
            analysis: {},
            recommendations: []
        };
        
        // Analyze FPS performance
        if (this.frameTimeHistory.length > 0) {
            const avgFPS = this.frameTimeHistory.reduce((sum, data) => sum + data.fps, 0) / this.frameTimeHistory.length;
            const minFPS = Math.min(...this.frameTimeHistory.map(data => data.fps));
            const maxFPS = Math.max(...this.frameTimeHistory.map(data => data.fps));
            
            results.metrics.fps = {
                average: avgFPS,
                minimum: minFPS,
                maximum: maxFPS,
                target: this.config.targetFPS,
                metTarget: avgFPS >= this.config.targetFPS * 0.9
            };
        }
        
        // Analyze memory performance
        if (this.memoryHistory.length > 0) {
            const avgMemory = this.memoryHistory.reduce((sum, data) => sum + data.memory, 0) / this.memoryHistory.length;
            const maxMemory = Math.max(...this.memoryHistory.map(data => data.memory));
            const minMemory = Math.min(...this.memoryHistory.map(data => data.memory));
            
            results.metrics.memory = {
                average: avgMemory,
                maximum: maxMemory,
                minimum: minMemory,
                growth: maxMemory - minMemory,
                withinLimits: maxMemory < this.config.memoryWarningThreshold
            };
        }
        
        // Analyze rendering performance
        if (this.drawCallHistory.length > 0) {
            const avgDrawCalls = this.drawCallHistory.reduce((sum, data) => sum + data.drawCalls, 0) / this.drawCallHistory.length;
            const maxDrawCalls = Math.max(...this.drawCallHistory.map(data => data.drawCalls));
            
            results.metrics.rendering = {
                averageDrawCalls: avgDrawCalls,
                maximumDrawCalls: maxDrawCalls,
                efficient: avgDrawCalls < scenario.entityCount * 0.5 // Rough efficiency metric
            };
        }
        
        // Generate recommendations
        this.generateRecommendations(results);
        
        return results;
    }
    
    generateRecommendations(results) {
        const { metrics } = results;
        
        // FPS recommendations
        if (metrics.fps && !metrics.fps.metTarget) {
            if (metrics.fps.average < 45) {
                results.recommendations.push({
                    priority: "high",
                    category: "performance",
                    issue: "Low FPS performance",
                    suggestion: "Consider implementing object pooling, spatial partitioning, or reducing entity update frequency"
                });
            }
        }
        
        // Memory recommendations
        if (metrics.memory && !metrics.memory.withinLimits) {
            results.recommendations.push({
                priority: "high",
                category: "memory",
                issue: "High memory usage",
                suggestion: "Implement entity pooling, texture atlasing, and aggressive garbage collection"
            });
        }
        
        if (metrics.memory && metrics.memory.growth > 50) {
            results.recommendations.push({
                priority: "critical",
                category: "memory",
                issue: "Potential memory leak detected",
                suggestion: "Review entity cleanup and component destruction patterns"
            });
        }
        
        // Rendering recommendations
        if (metrics.rendering && !metrics.rendering.efficient) {
            results.recommendations.push({
                priority: "medium",
                category: "rendering",
                issue: "Inefficient sprite batching",
                suggestion: "Optimize sprite batching by grouping similar textures and reducing state changes"
            });
        }
    }
    
    printResults(results) {
        console.log(`\n📊 Benchmark Results: ${results.scenario}`);
        console.log("=====================================");
        
        if (results.metrics.fps) {
            const fps = results.metrics.fps;
            console.log("🎯 FPS Performance:");
            console.log(`   Average: ${fps.average.toFixed(1)} FPS`);
            console.log(`   Range: ${fps.minimum.toFixed(1)} - ${fps.maximum.toFixed(1)} FPS`);
            console.log(`   Target Met: ${fps.metTarget ? "✅" : "❌"}`);
        }
        
        if (results.metrics.memory) {
            const mem = results.metrics.memory;
            console.log("🧠 Memory Performance:");
            console.log(`   Average: ${mem.average.toFixed(1)} MB`);
            console.log(`   Peak: ${mem.maximum.toFixed(1)} MB`);
            console.log(`   Growth: ${mem.growth.toFixed(1)} MB`);
            console.log(`   Within Limits: ${mem.withinLimits ? "✅" : "❌"}`);
        }
        
        if (results.metrics.rendering) {
            const render = results.metrics.rendering;
            console.log("🎨 Rendering Performance:");
            console.log(`   Average Draw Calls: ${render.averageDrawCalls.toFixed(1)}`);
            console.log(`   Peak Draw Calls: ${render.maximumDrawCalls}`);
            console.log(`   Efficient Batching: ${render.efficient ? "✅" : "❌"}`);
        }
        
        if (results.recommendations.length > 0) {
            console.log("\n💡 Recommendations:");
            results.recommendations.forEach((rec, index) => {
                const priority = rec.priority === "critical" ? "🚨" : 
                    rec.priority === "high" ? "⚠️" : "💡";
                console.log(`   ${priority} ${rec.suggestion}`);
            });
        }
        
        console.log("\n=====================================\n");
    }
    
    generateComprehensiveReport(allResults) {
        console.log("\n🏆 COMPREHENSIVE PERFORMANCE REPORT");
        console.log("=========================================");
        
        const successfulTests = allResults.filter(r => r.success);
        const failedTests = allResults.filter(r => !r.success);
        
        console.log("📈 Test Summary:");
        console.log(`   Successful: ${successfulTests.length}/${allResults.length}`);
        console.log(`   Failed: ${failedTests.length}/${allResults.length}`);
        
        if (successfulTests.length > 0) {
            // Overall performance assessment
            const avgFPS = successfulTests
                .filter(r => r.metrics.fps)
                .reduce((sum, r) => sum + r.metrics.fps.average, 0) / 
                successfulTests.filter(r => r.metrics.fps).length;
            
            const maxMemory = Math.max(...successfulTests
                .filter(r => r.metrics.memory)
                .map(r => r.metrics.memory.maximum));
            
            console.log("\n📊 Overall Performance:");
            console.log(`   Average FPS: ${avgFPS.toFixed(1)}`);
            console.log(`   Peak Memory: ${maxMemory.toFixed(1)} MB`);
            console.log(`   60+ FPS Target: ${avgFPS >= 54 ? "✅" : "❌"}`);
            console.log(`   Memory Target (<400MB): ${maxMemory < 400 ? "✅" : "❌"}`);
        }
        
        // Critical issues
        const criticalIssues = allResults
            .flatMap(r => r.recommendations || [])
            .filter(rec => rec.priority === "critical");
        
        if (criticalIssues.length > 0) {
            console.log("\n🚨 CRITICAL ISSUES DETECTED:");
            criticalIssues.forEach(issue => {
                console.log(`   • ${issue.issue}: ${issue.suggestion}`);
            });
        }
        
        console.log("\n=========================================\n");
    }
    
    clearHistory() {
        this.frameTimeHistory = [];
        this.memoryHistory = [];
        this.drawCallHistory = [];
        this.entityCountHistory = [];
    }
    
    cleanupTestEntities(entities) {
        entities.forEach(entity => {
            if (entity && entity.active) {
                this.world.removeEntity(entity);
            }
        });
    }
    
    stopBenchmark() {
        this.isRunning = false;
    }
}