import { OptimizedSelectionSystem } from './OptimizedSelectionSystem.js';
import { HarvesterAISystem } from './HarvesterAISystem.js';
import { ResourceNodeComponent, HarvesterComponent, EconomyComponent } from './ResourceComponents.js';
import { QuadTree } from '../utils/QuadTree.js';
import { PerformanceValidator } from '../utils/PerformanceValidator.js';

/**
 * Backend System Integrator - Coordinates all optimized backend systems
 * Ensures proper initialization, integration, and performance validation
 */
export class BackendSystemIntegrator {
    constructor(world, inputHandler, camera, stage) {
        this.world = world;
        this.inputHandler = inputHandler;
        this.camera = camera;
        this.stage = stage;
        
        // System instances
        this.optimizedSelectionSystem = null;
        this.harvesterAISystem = null;
        this.economyManager = null;
        this.performanceValidator = null;
        
        // Integration state
        this.initialized = false;
        this.systemsRegistered = false;
        
        // Performance monitoring
        this.performanceMonitor = {
            frameCount: 0,
            lastPerformanceCheck: Date.now(),
            performanceHistory: []
        };
        
        console.log('🔧 BackendSystemIntegrator created');
    }
    
    /**
     * Initialize all optimized backend systems
     */
    async initialize() {
        try {
            console.log('🚀 Initializing optimized backend systems...');
            
            // 1. Create economy manager
            await this.initializeEconomyManager();
            
            // 2. Initialize optimized selection system
            await this.initializeOptimizedSelection();
            
            // 3. Initialize harvester AI system
            await this.initializeHarvesterAI();
            
            // 4. Register systems with world
            await this.registerSystems();
            
            // 5. Initialize performance validator
            await this.initializePerformanceValidator();
            
            // 6. Setup integration bindings
            await this.setupSystemIntegration();
            
            this.initialized = true;
            console.log('✅ All optimized backend systems initialized successfully');
            
            return true;
            
        } catch (error) {
            console.error('❌ Failed to initialize backend systems:', error);
            return false;
        }
    }
    
    /**
     * Initialize economy management system
     */
    async initializeEconomyManager() {
        console.log('💰 Initializing economy manager...');

        // Create global economy entity
        const economyEntity = this.world.createEntity();
        this.economyManager = new EconomyComponent(2000); // Start with 2000 credits
        economyEntity.addComponent(this.economyManager);

        // Store reference for easy access
        this.world.economyEntity = economyEntity;

        console.log('✅ Economy manager initialized with 2000 starting credits');
    }

    /**
     * Initialize optimized selection system
     */
    async initializeOptimizedSelection() {
        console.log('🎯 Initializing optimized selection system...');

        this.optimizedSelectionSystem = new OptimizedSelectionSystem(
            this.world,
            this.inputHandler,
            this.camera,
            this.stage
        );

        console.log('✅ Optimized selection system initialized with QuadTree spatial partitioning');
    }

    /**
     * Initialize harvester AI system
     */
    async initializeHarvesterAI() {
        console.log('🤖 Initializing harvester AI system...');

        this.harvesterAISystem = new HarvesterAISystem(
            this.world,
            this.economyManager
        );

        console.log('✅ Harvester AI system initialized with spatial resource lookup');
    }

    /**
     * Register all systems with the world
     */
    async registerSystems() {
        console.log('📋 Registering systems with world...');

        // Add systems to world
        if (this.optimizedSelectionSystem) {
            this.world.addSystem(this.optimizedSelectionSystem);
            console.log('  ✓ Optimized selection system registered');
        }

        if (this.harvesterAISystem) {
            this.world.addSystem(this.harvesterAISystem);
            console.log('  ✓ Harvester AI system registered');
        }

        this.systemsRegistered = true;
        console.log('✅ All systems registered with world');
    }

    /**
     * Initialize performance validator
     */
    async initializePerformanceValidator() {
        console.log('📊 Initializing performance validator...');

        this.performanceValidator = new PerformanceValidator();

        console.log('✅ Performance validator ready for testing');
    }

    /**
     * Setup integration between systems
     */
    async setupSystemIntegration() {
        console.log('🔗 Setting up system integration...');

        // Bind economy manager to harvester AI
        if (this.harvesterAISystem && this.economyManager) {
            this.harvesterAISystem.economyManager = this.economyManager;
            console.log('  ✓ Economy manager linked to harvester AI');
        }

        // Setup performance monitoring hooks
        this.setupPerformanceMonitoring();

        console.log('✅ System integration complete');
    }

    /**
     * Setup performance monitoring
     */
    setupPerformanceMonitoring() {
        // Monitor selection system performance
        if (this.optimizedSelectionSystem) {
            const originalGetEntityAtPosition = this.optimizedSelectionSystem.getEntityAtPosition.bind(this.optimizedSelectionSystem);
            this.optimizedSelectionSystem.getEntityAtPosition = (x, y) => {
                const startTime = performance.now();
                const result = originalGetEntityAtPosition(x, y);
                const endTime = performance.now();

                this.recordPerformanceMetric('selection', endTime - startTime);
                return result;
            };
        }

        // Monitor pathfinding system performance if available
        const pathfindingSystem = this.world.systems.find(s => s.constructor.name === 'PathfindingSystem');
        if (pathfindingSystem && pathfindingSystem.calculatePath) {
            const originalCalculatePath = pathfindingSystem.calculatePath.bind(pathfindingSystem);
            pathfindingSystem.calculatePath = (entity) => {
                const startTime = performance.now();
                const result = originalCalculatePath(entity);
                const endTime = performance.now();

                this.recordPerformanceMetric('pathfinding', endTime - startTime);
                return result;
            };
        }
    }

    /**
     * Record performance metric
     */
    recordPerformanceMetric(type, time) {
        const now = Date.now();
        this.performanceMonitor.performanceHistory.push({
            type,
            time,
            timestamp: now
        });

        // Clean old entries (keep last 100)
        if (this.performanceMonitor.performanceHistory.length > 100) {
            this.performanceMonitor.performanceHistory.shift();
        }
    }

    /**
     * Create test scenario with entities
     */
    createTestScenario() {
        console.log('🎭 Creating test scenario...');

        const entities = {
            harvesters: [],
            resourceNodes: [],
            refineries: []
        };

        try {
            // Import required components
            const { TransformComponent, SelectableComponent, UnitComponent, BuildingComponent, MovementComponent } = require('./Component.js');

            // Create resource nodes
            for (let i = 0; i < 10; i++) {
                const resourceEntity = this.world.createEntity();

                const x = 200 + (i % 5) * 300;
                const y = 200 + Math.floor(i / 5) * 300;

                resourceEntity.addComponent(new TransformComponent(x, y));
                resourceEntity.addComponent(new ResourceNodeComponent('tiberium', 1000, 25));
                resourceEntity.addComponent(new SelectableComponent());

                entities.resourceNodes.push(resourceEntity);
                console.log(`  ✓ Created resource node at (${x}, ${y})`);
            }

            // Create refineries
            for (let i = 0; i < 2; i++) {
                const refineryEntity = this.world.createEntity();

                const x = 100 + i * 800;
                const y = 600;

                refineryEntity.addComponent(new TransformComponent(x, y));
                refineryEntity.addComponent(new BuildingComponent('refinery', 'player', 2000));
                refineryEntity.addComponent(new SelectableComponent());

                entities.refineries.push(refineryEntity);
                console.log(`  ✓ Created refinery at (${x}, ${y})`);
            }

            // Create harvesters
            for (let i = 0; i < 5; i++) {
                const harvesterEntity = this.world.createEntity();

                const x = 150 + i * 100;
                const y = 500;

                harvesterEntity.addComponent(new TransformComponent(x, y));
                harvesterEntity.addComponent(new UnitComponent('harvester', 'player', 1400));
                harvesterEntity.addComponent(new HarvesterComponent(700, 3000));
                harvesterEntity.addComponent(new MovementComponent());
                harvesterEntity.addComponent(new SelectableComponent());

                entities.harvesters.push(harvesterEntity);
                console.log(`  ✓ Created harvester at (${x}, ${y})`);
            }

            console.log(`✅ Test scenario created: ${entities.resourceNodes.length} resource nodes, ${entities.refineries.length} refineries, ${entities.harvesters.length} harvesters`);

        } catch (error) {
            console.warn('⚠️ Could not create full test scenario (components may not be available):', error.message);

            // Create minimal test entities
            for (let i = 0; i < 50; i++) {
                const entity = this.world.createEntity();
                // Add minimal components if available
                entity.testEntity = true;
                entities.harvesters.push(entity);
            }

            console.log('✅ Created minimal test scenario with 50 test entities');
        }

        return entities;
    }

    /**
     * Run performance validation tests
     */
    async runPerformanceValidation() {
        if (!this.performanceValidator) {
            console.error('❌ Performance validator not initialized');
            return false;
        }

        console.log('🧪 Running performance validation tests...');

        // Create test scenario
        const testEntities = this.createTestScenario();

        // Start validation
        this.performanceValidator.startValidation(
            this.world,
            this.optimizedSelectionSystem,
            this.world.systems.find(s => s.constructor.name === 'PathfindingSystem')
        );

        // Wait for validation to complete
        return new Promise((resolve) => {
            const checkComplete = () => {
                this.performanceValidator.update();

                if (!this.performanceValidator.isRunning) {
                    const results = this.performanceValidator.completeValidation();
                    resolve(results);
                } else {
                    setTimeout(checkComplete, 100);
                }
            };

            checkComplete();
        });
    }

    /**
     * Get comprehensive system statistics
     */
    getSystemStats() {
        const stats = {
            initialized: this.initialized,
            systemsRegistered: this.systemsRegistered,
            entityCount: this.world.entities.size,
            systemCount: this.world.systems.length
        };

        // Selection system stats
        if (this.optimizedSelectionSystem) {
            stats.selection = this.optimizedSelectionSystem.getPerformanceStats();
        }

        // Harvester AI stats
        if (this.harvesterAISystem) {
            stats.harvesterAI = this.harvesterAISystem.getPerformanceStats();
            stats.economy = this.harvesterAISystem.getEconomicStats();
        }

        // Economy stats
        if (this.economyManager) {
            stats.economyManager = this.economyManager.getStats();
        }

        // Performance monitoring stats
        stats.performance = this.getPerformanceStats();

        return stats;
    }

    /**
     * Get performance monitoring statistics
     */
    getPerformanceStats() {
        const recent = this.performanceMonitor.performanceHistory.slice(-50); // Last 50 entries

        const selectionTimes = recent.filter(entry => entry.type === 'selection').map(entry => entry.time);
        const pathfindingTimes = recent.filter(entry => entry.type === 'pathfinding').map(entry => entry.time);

        return {
            recentEntries: recent.length,
            selection: {
                count: selectionTimes.length,
                average: selectionTimes.length > 0 ? selectionTimes.reduce((sum, time) => sum + time, 0) / selectionTimes.length : 0,
                max: selectionTimes.length > 0 ? Math.max(...selectionTimes) : 0
            },
            pathfinding: {
                count: pathfindingTimes.length,
                average: pathfindingTimes.length > 0 ? pathfindingTimes.reduce((sum, time) => sum + time, 0) / pathfindingTimes.length : 0,
                max: pathfindingTimes.length > 0 ? Math.max(...pathfindingTimes) : 0
            }
        };
    }

    /**
     * Update integrator (call every frame)
     */
    update(deltaTime) {
        if (!this.initialized) return;

        this.performanceMonitor.frameCount++;

        // Update performance validator if running
        if (this.performanceValidator && this.performanceValidator.isRunning) {
            this.performanceValidator.update();
        }

        // Periodic performance reporting
        const now = Date.now();
        if (now - this.performanceMonitor.lastPerformanceCheck > 5000) { // Every 5 seconds
            this.reportPerformanceStatus();
            this.performanceMonitor.lastPerformanceCheck = now;
        }
    }

    /**
     * Report current performance status
     */
    reportPerformanceStatus() {
        const stats = this.getSystemStats();

        console.log('📊 Performance Status Report:');
        console.log(`  Entities: ${stats.entityCount}`);

        if (stats.selection) {
            console.log(`  Selection: ${stats.selection.averageSelectionTime?.toFixed(2)}ms avg, ${stats.selection.spatialQueries} spatial queries`);
        }

        if (stats.performance) {
            const perf = stats.performance;
            console.log(`  Recent Performance: Selection ${perf.selection.average?.toFixed(2)}ms, Pathfinding ${perf.pathfinding.average?.toFixed(2)}ms`);
        }

        if (stats.economy) {
            console.log(`  Economy: ${stats.economyManager?.credits || 0} credits, ${stats.economy.activeHarvesters || 0} active harvesters`);
        }
    }

    /**
     * Cleanup all systems
     */
    destroy() {
        console.log('🗑️ Destroying backend system integrator...');

        if (this.optimizedSelectionSystem) {
            this.optimizedSelectionSystem.destroy();
        }

        if (this.harvesterAISystem) {
            this.harvesterAISystem.destroy();
        }

        this.performanceMonitor.performanceHistory = [];

        console.log('✅ Backend system integrator destroyed');
    }
}
