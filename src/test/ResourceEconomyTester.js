/**
 * Resource Economy Testing Framework
 * Validates harvester AI, resource node pathfinding, and economy balance
 */

export class ResourceEconomyTester {
    constructor(world, economySystem) {
        this.world = world;
        this.economySystem = economySystem;
        
        // Test configuration
        this.config = {
            maxHarvesterPathTime: 10, // ms - pathfinding to resource nodes
            minEfficiencyRate: 0.75, // 75% efficiency expected
            maxIdleTime: 2000, // ms - harvesters shouldn't be idle too long
            resourceBalanceThreshold: 0.2, // 20% variance acceptable
            
            // Economy balance targets
            resourceTypes: ['minerals', 'energy', 'research'],
            baseHarvestRate: 10, // resources per second per harvester
            expectedROI: 1.5, // return on investment for harvesters
            maxHarvesters: 20, // maximum concurrent harvesters for testing
        };
        
        // Test scenarios
        this.testScenarios = [
            {
                name: 'Single Harvester Efficiency',
                harvesters: 1,
                resourceNodes: 3,
                duration: 30000, // 30 seconds
                expectedEfficiency: 0.80
            },
            {
                name: 'Multi-Harvester Coordination',
                harvesters: 5,
                resourceNodes: 3,
                duration: 45000,
                expectedEfficiency: 0.75
            },
            {
                name: 'High Load Harvesting',
                harvesters: 10,
                resourceNodes: 5,
                duration: 60000,
                expectedEfficiency: 0.70
            },
            {
                name: 'Resource Competition',
                harvesters: 15,
                resourceNodes: 3,
                duration: 45000,
                expectedEfficiency: 0.65
            },
            {
                name: 'Scalability Stress Test',
                harvesters: 20,
                resourceNodes: 8,
                duration: 90000,
                expectedEfficiency: 0.60
            }
        ];
        
        this.testResults = [];
        this.evidenceData = [];
    }
    
    /**
     * Run comprehensive resource economy tests
     */
    async runEconomyTests() {
        console.log('💰 Starting Resource Economy Tests');
        console.log('=' .repeat(70));
        
        const overallStartTime = performance.now();
        
        try {
            // Test 1: Harvester AI efficiency
            const harvesterAIResults = await this.testHarvesterAIEfficiency();
            
            // Test 2: Resource pathfinding performance
            const pathfindingResults = await this.testResourcePathfinding();
            
            // Test 3: Economy balance validation
            const balanceResults = await this.testEconomyBalance();
            
            // Test 4: Multi-harvester coordination
            const coordinationResults = await this.testHarvesterCoordination();
            
            // Test 5: Resource node optimization
            const optimizationResults = await this.testResourceNodeOptimization();
            
            // Compile comprehensive results
            const allResults = {
                timestamp: new Date().toISOString(),
                duration: performance.now() - overallStartTime,
                tests: {
                    harvesterAI: harvesterAIResults,
                    pathfinding: pathfindingResults,
                    balance: balanceResults,
                    coordination: coordinationResults,
                    optimization: optimizationResults
                },
                evidence: this.evidenceData,
                overallSuccess: this.determineOverallSuccess([
                    harvesterAIResults, pathfindingResults, balanceResults,
                    coordinationResults, optimizationResults
                ])
            };
            
            this.printEconomyTestReport(allResults);
            return allResults;
            
        } catch (error) {
            console.error('❌ Resource economy testing failed:', error);
            throw error;
        }
    }
    
    /**
     * Test harvester AI efficiency across different scenarios
     */
    async testHarvesterAIEfficiency() {
        console.log('\n🤖 Testing Harvester AI Efficiency...');
        
        const results = [];
        
        for (const scenario of this.testScenarios) {
            console.log(`  📋 Running: ${scenario.name}`);
            console.log(`    Harvesters: ${scenario.harvesters}, Nodes: ${scenario.resourceNodes}`);
            
            const scenarioResult = await this.runEconomyScenario(scenario);
            results.push(scenarioResult);
            
            // Collect evidence
            this.collectEvidence('harvester_ai', scenario.name, scenarioResult);
            
            // Brief pause between tests
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        
        return {
            testType: 'Harvester AI Efficiency',
            scenarios: results,
            success: results.every(r => r.success),
            averageEfficiency: results.reduce((sum, r) => sum + r.efficiency, 0) / results.length,
            summary: this.generateHarvesterAISummary(results)
        };
    }
    
    /**
     * Run individual economy scenario
     */
    async runEconomyScenario(scenario) {
        const testEnvironment = this.createEconomyTestEnvironment(scenario);
        const { harvesters, resourceNodes, depot } = testEnvironment;
        
        try {
            // Initialize tracking
            const tracking = {
                totalResourcesHarvested: 0,
                totalHarvestingTime: 0,
                idleTime: 0,
                pathfindingTime: 0,
                harvesterStates: new Map(),
                resourceDepletions: 0,
                collisions: 0,
                frameCount: 0
            };
            
            // Initialize harvester states
            harvesters.forEach(harvester => {
                tracking.harvesterStates.set(harvester.id, {
                    currentState: 'idle',
                    lastStateChange: performance.now(),
                    totalHarvested: 0,
                    trips: 0,
                    pathfindingAttempts: 0
                });
            });
            
            // Run scenario simulation
            const startTime = performance.now();
            const frameTime = 50; // 20 FPS for economy simulation
            let elapsedTime = 0;
            
            while (elapsedTime < scenario.duration) {
                const frameStart = performance.now();
                
                // Update harvester AI
                await this.updateHarvesterAI(harvesters, resourceNodes, depot, tracking);
                
                // Update resource nodes
                this.updateResourceNodes(resourceNodes);
                
                // Collect frame metrics
                tracking.frameCount++;
                elapsedTime += frameTime;
                
                // Simulate frame delay
                await new Promise(resolve => setTimeout(resolve, frameTime));
            }
            
            // Calculate final metrics
            const totalDuration = performance.now() - startTime;
            const efficiency = this.calculateEfficiency(tracking, scenario);
            const averageIdleTime = tracking.idleTime / harvesters.length;
            const averageHarvesterOutput = tracking.totalResourcesHarvested / harvesters.length;
            
            return {
                scenario: scenario.name,
                harvesters: scenario.harvesters,
                resourceNodes: scenario.resourceNodes,
                duration: totalDuration,
                efficiency,
                success: efficiency >= scenario.expectedEfficiency,
                metrics: {
                    totalResourcesHarvested: tracking.totalResourcesHarvested,
                    averageHarvesterOutput,
                    averageIdleTime,
                    resourceDepletions: tracking.resourceDepletions,
                    collisions: tracking.collisions,
                    pathfindingTime: tracking.pathfindingTime,
                    frames: tracking.frameCount
                },
                details: {
                    expectedEfficiency: scenario.expectedEfficiency,
                    actualEfficiency: efficiency,
                    performanceMargin: efficiency - scenario.expectedEfficiency,
                    harvesterStates: Array.from(tracking.harvesterStates.entries())
                }
            };
            
        } finally {
            // Cleanup
            this.cleanupEconomyTestEnvironment(testEnvironment);
        }
    }
    
    /**
     * Create test environment for economy scenario
     */
    createEconomyTestEnvironment(scenario) {
        // Create resource depot
        const depot = this.createResourceDepot();
        
        // Create resource nodes
        const resourceNodes = [];
        for (let i = 0; i < scenario.resourceNodes; i++) {
            const node = this.createResourceNode(i);
            resourceNodes.push(node);
        }
        
        // Create harvesters
        const harvesters = [];
        for (let i = 0; i < scenario.harvesters; i++) {
            const harvester = this.createHarvester(i, depot);
            harvesters.push(harvester);
        }
        
        return { harvesters, resourceNodes, depot };
    }
    
    createResourceDepot() {
        return {
            id: 'depot_0',
            type: 'depot',
            position: { x: 600, y: 350 }, // Center of map
            capacity: 10000,
            currentResources: 0,
            
            depositResources(amount) {
                this.currentResources += amount;
                return amount;
            }
        };
    }
    
    createResourceNode(index) {
        const positions = [
            { x: 200, y: 200 },
            { x: 1000, y: 200 },
            { x: 200, y: 500 },
            { x: 1000, y: 500 },
            { x: 600, y: 100 },
            { x: 600, y: 600 },
            { x: 100, y: 350 },
            { x: 1100, y: 350 }
        ];
        
        const position = positions[index % positions.length];
        
        return {
            id: `resource_node_${index}`,
            type: 'resource_node',
            position,
            resourceType: this.config.resourceTypes[index % this.config.resourceTypes.length],
            maxResources: 1000,
            currentResources: 1000,
            harvestersAssigned: new Set(),
            depleted: false,
            
            harvest(amount) {
                const harvested = Math.min(amount, this.currentResources);
                this.currentResources -= harvested;
                
                if (this.currentResources <= 0) {
                    this.depleted = true;
                }
                
                return harvested;
            },
            
            assignHarvester(harvesterId) {
                this.harvestersAssigned.add(harvesterId);
            },
            
            unassignHarvester(harvesterId) {
                this.harvestersAssigned.delete(harvesterId);
            }
        };
    }
    
    createHarvester(index, depot) {
        return {
            id: `harvester_${index}`,
            type: 'harvester',
            position: { x: depot.position.x + (index * 20), y: depot.position.y + (index * 20) },
            state: 'idle', // idle, moving_to_resource, harvesting, moving_to_depot, depositing
            targetNode: null,
            currentResources: 0,
            capacity: 50,
            speed: 100, // pixels per second
            harvestRate: 10, // resources per second
            lastStateChange: performance.now(),
            
            // AI state machine
            setState(newState, tracking) {
                if (this.state !== newState) {
                    const now = performance.now();
                    const stateTime = now - this.lastStateChange;
                    
                    // Track state-specific metrics
                    const harvesterTracking = tracking.harvesterStates.get(this.id);
                    
                    switch (this.state) {
                        case 'idle':
                            tracking.idleTime += stateTime;
                            break;
                        case 'harvesting':
                            tracking.totalHarvestingTime += stateTime;
                            break;
                    }
                    
                    this.state = newState;
                    this.lastStateChange = now;
                }
            }
        };
    }
    
    /**
     * Update harvester AI logic
     */
    async updateHarvesterAI(harvesters, resourceNodes, depot, tracking) {
        for (const harvester of harvesters) {
            const deltaTime = 0.05; // 50ms frame time
            
            switch (harvester.state) {
                case 'idle':
                    await this.handleIdleState(harvester, resourceNodes, tracking);
                    break;
                    
                case 'moving_to_resource':
                    await this.handleMovingToResourceState(harvester, resourceNodes, deltaTime, tracking);
                    break;
                    
                case 'harvesting':
                    await this.handleHarvestingState(harvester, deltaTime, tracking);
                    break;
                    
                case 'moving_to_depot':
                    await this.handleMovingToDepotState(harvester, depot, deltaTime, tracking);
                    break;
                    
                case 'depositing':
                    await this.handleDepositingState(harvester, depot, tracking);
                    break;
            }
        }
    }
    
    async handleIdleState(harvester, resourceNodes, tracking) {
        // Find nearest resource node with resources
        const availableNodes = resourceNodes.filter(node => 
            !node.depleted && 
            node.harvestersAssigned.size < 3 // Limit harvesters per node
        );
        
        if (availableNodes.length > 0) {
            // Find nearest node
            const nearestNode = availableNodes.reduce((nearest, node) => {
                const distanceToNearest = this.calculateDistance(harvester.position, nearest.position);
                const distanceToNode = this.calculateDistance(harvester.position, node.position);
                return distanceToNode < distanceToNearest ? node : nearest;
            });
            
            harvester.targetNode = nearestNode;
            nearestNode.assignHarvester(harvester.id);
            harvester.setState('moving_to_resource', tracking);
        }
    }
    
    async handleMovingToResourceState(harvester, resourceNodes, deltaTime, tracking) {
        if (!harvester.targetNode) {
            harvester.setState('idle', tracking);
            return;
        }
        
        // Simulate pathfinding time
        const pathfindingStart = performance.now();
        await new Promise(resolve => setTimeout(resolve, 1)); // Simulate pathfinding delay
        tracking.pathfindingTime += performance.now() - pathfindingStart;
        
        // Move towards target
        const distance = this.calculateDistance(harvester.position, harvester.targetNode.position);
        
        if (distance <= 32) { // Reached node
            harvester.setState('harvesting', tracking);
        } else {
            // Move closer
            const moveDistance = harvester.speed * deltaTime;
            const direction = this.normalizeVector({
                x: harvester.targetNode.position.x - harvester.position.x,
                y: harvester.targetNode.position.y - harvester.position.y
            });
            
            harvester.position.x += direction.x * moveDistance;
            harvester.position.y += direction.y * moveDistance;
        }
    }
    
    async handleHarvestingState(harvester, deltaTime, tracking) {
        if (!harvester.targetNode || harvester.targetNode.depleted) {
            if (harvester.targetNode) {
                harvester.targetNode.unassignHarvester(harvester.id);
            }
            harvester.targetNode = null;
            harvester.setState('idle', tracking);
            return;
        }
        
        // Harvest resources
        const harvestAmount = harvester.harvestRate * deltaTime;
        const harvested = harvester.targetNode.harvest(harvestAmount);
        
        harvester.currentResources += harvested;
        tracking.totalResourcesHarvested += harvested;
        
        // Check if harvester is full or node is depleted
        if (harvester.currentResources >= harvester.capacity) {
            harvester.targetNode.unassignHarvester(harvester.id);
            harvester.targetNode = null;
            harvester.setState('moving_to_depot', tracking);
            
            // Track harvester stats
            const harvesterStats = tracking.harvesterStates.get(harvester.id);
            harvesterStats.trips++;
            harvesterStats.totalHarvested += harvester.currentResources;
        } else if (harvester.targetNode.depleted) {
            tracking.resourceDepletions++;
            harvester.targetNode.unassignHarvester(harvester.id);
            harvester.targetNode = null;
            
            if (harvester.currentResources > 0) {
                harvester.setState('moving_to_depot', tracking);
            } else {
                harvester.setState('idle', tracking);
            }
        }
    }
    
    async handleMovingToDepotState(harvester, depot, deltaTime, tracking) {
        // Move towards depot
        const distance = this.calculateDistance(harvester.position, depot.position);
        
        if (distance <= 48) { // Reached depot
            harvester.setState('depositing', tracking);
        } else {
            // Move closer
            const moveDistance = harvester.speed * deltaTime;
            const direction = this.normalizeVector({
                x: depot.position.x - harvester.position.x,
                y: depot.position.y - harvester.position.y
            });
            
            harvester.position.x += direction.x * moveDistance;
            harvester.position.y += direction.y * moveDistance;
        }
    }
    
    async handleDepositingState(harvester, depot, tracking) {
        // Deposit resources
        const deposited = depot.depositResources(harvester.currentResources);
        harvester.currentResources = 0;
        
        // Return to idle state
        harvester.setState('idle', tracking);
    }
    
    updateResourceNodes(resourceNodes) {
        // Optionally regenerate resources slowly
        resourceNodes.forEach(node => {
            if (node.depleted && node.harvestersAssigned.size === 0) {
                // Slow regeneration for testing
                if (Math.random() < 0.001) { // 0.1% chance per frame
                    node.currentResources = Math.min(node.maxResources, node.currentResources + 100);
                    if (node.currentResources > 0) {
                        node.depleted = false;
                    }
                }
            }
        });
    }
    
    /**
     * Test resource pathfinding performance
     */
    async testResourcePathfinding() {
        console.log('\n🛣️ Testing Resource Pathfinding Performance...');
        
        const results = [];
        const pathfindingTests = [
            { harvesters: 5, nodes: 3, complexity: 'simple' },
            { harvesters: 10, nodes: 5, complexity: 'moderate' },
            { harvesters: 15, nodes: 8, complexity: 'complex' }
        ];
        
        for (const test of pathfindingTests) {
            console.log(`  🎯 Testing ${test.harvesters} harvesters to ${test.nodes} nodes`);
            
            const testResult = await this.runPathfindingTest(test);
            results.push(testResult);
        }
        
        return {
            testType: 'Resource Pathfinding Performance',
            results,
            success: results.every(r => r.success),
            averagePathTime: results.reduce((sum, r) => sum + r.averagePathTime, 0) / results.length,
            summary: this.generatePathfindingSummary(results)
        };
    }
    
    async runPathfindingTest(testConfig) {
        const harvesters = [];
        const resourceNodes = [];
        
        // Create test entities
        for (let i = 0; i < testConfig.harvesters; i++) {
            harvesters.push(this.createHarvester(i, { position: { x: 600, y: 350 } }));
        }
        
        for (let i = 0; i < testConfig.nodes; i++) {
            resourceNodes.push(this.createResourceNode(i));
        }
        
        // Measure pathfinding performance
        const pathfindingTimes = [];
        const iterations = 50;
        
        for (let i = 0; i < iterations; i++) {
            const harvester = harvesters[i % harvesters.length];
            const targetNode = resourceNodes[i % resourceNodes.length];
            
            const startTime = performance.now();
            
            // Simulate pathfinding calculation
            await this.simulatePathfindingCalculation(harvester.position, targetNode.position, testConfig.complexity);
            
            const endTime = performance.now();
            pathfindingTimes.push(endTime - startTime);
        }
        
        const averagePathTime = pathfindingTimes.reduce((sum, time) => sum + time, 0) / pathfindingTimes.length;
        const maxPathTime = Math.max(...pathfindingTimes);
        
        return {
            harvesters: testConfig.harvesters,
            nodes: testConfig.nodes,
            complexity: testConfig.complexity,
            averagePathTime,
            maxPathTime,
            success: averagePathTime <= this.config.maxHarvesterPathTime,
            details: {
                iterations,
                target: this.config.maxHarvesterPathTime,
                pathfindingTimes
            }
        };
    }
    
    async simulatePathfindingCalculation(start, end, complexity) {
        // Simulate pathfinding complexity
        let delay = 2; // Base delay
        
        switch (complexity) {
            case 'simple':
                delay += Math.random() * 2;
                break;
            case 'moderate':
                delay += Math.random() * 5;
                break;
            case 'complex':
                delay += Math.random() * 8;
                break;
        }
        
        await new Promise(resolve => setTimeout(resolve, delay));
    }
    
    /**
     * Test economy balance
     */
    async testEconomyBalance() {
        console.log('\n⚖️ Testing Economy Balance...');
        
        const testEnvironment = this.createEconomyTestEnvironment({
            harvesters: 10,
            resourceNodes: 5,
            duration: 60000
        });
        
        try {
            // Run balanced economy test
            const balanceResult = await this.runEconomyBalanceTest(testEnvironment);
            
            return {
                testType: 'Economy Balance',
                success: balanceResult.balanced,
                metrics: balanceResult,
                summary: this.generateBalanceSummary(balanceResult)
            };
            
        } finally {
            this.cleanupEconomyTestEnvironment(testEnvironment);
        }
    }
    
    async runEconomyBalanceTest(testEnvironment) {
        const { harvesters, resourceNodes } = testEnvironment;
        const resourceProduction = new Map();
        
        // Initialize tracking
        this.config.resourceTypes.forEach(type => {
            resourceProduction.set(type, 0);
        });
        
        // Simulate economy for 60 seconds
        const duration = 60000;
        const startTime = performance.now();
        
        while (performance.now() - startTime < duration) {
            // Simulate resource production
            resourceNodes.forEach(node => {
                if (!node.depleted && node.harvestersAssigned.size > 0) {
                    const production = node.harvestersAssigned.size * this.config.baseHarvestRate * 0.05;
                    const currentProduction = resourceProduction.get(node.resourceType) || 0;
                    resourceProduction.set(node.resourceType, currentProduction + production);
                }
            });
            
            await new Promise(resolve => setTimeout(resolve, 50));
        }
        
        // Analyze balance
        const productions = Array.from(resourceProduction.values());
        const averageProduction = productions.reduce((sum, prod) => sum + prod, 0) / productions.length;
        const maxDeviation = Math.max(...productions.map(prod => Math.abs(prod - averageProduction))) / averageProduction;
        
        return {
            resourceProduction: Object.fromEntries(resourceProduction),
            averageProduction,
            maxDeviation,
            balanced: maxDeviation <= this.config.resourceBalanceThreshold,
            recommendations: maxDeviation > this.config.resourceBalanceThreshold ? 
                ['Rebalance resource node distribution', 'Adjust harvester efficiency per resource type'] : []
        };
    }
    
    /**
     * Test harvester coordination
     */
    async testHarvesterCoordination() {
        console.log('\n🤝 Testing Harvester Coordination...');
        
        const coordinationResult = await this.runCoordinationTest();
        
        return {
            testType: 'Harvester Coordination',
            success: coordinationResult.efficient,
            metrics: coordinationResult,
            summary: this.generateCoordinationSummary(coordinationResult)
        };
    }
    
    async runCoordinationTest() {
        const testEnvironment = this.createEconomyTestEnvironment({
            harvesters: 12,
            resourceNodes: 3, // Few nodes to force coordination
            duration: 45000
        });
        
        try {
            const { harvesters, resourceNodes } = testEnvironment;
            const collisionCount = { value: 0 };
            const idleTime = { value: 0 };
            
            // Simulate coordination scenario
            const startTime = performance.now();
            
            while (performance.now() - startTime < 45000) {
                // Check for coordination issues
                this.detectCoordinationIssues(harvesters, resourceNodes, collisionCount, idleTime);
                
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            
            const totalTime = performance.now() - startTime;
            const avgIdleTime = idleTime.value / harvesters.length;
            const collisionRate = (collisionCount.value / totalTime) * 1000; // per second
            
            return {
                collisions: collisionCount.value,
                collisionRate,
                averageIdleTime: avgIdleTime,
                efficient: collisionRate < 0.1 && avgIdleTime < 5000, // Less than 0.1 collisions/sec and 5s idle
                recommendations: collisionRate >= 0.1 ? 
                    ['Implement harvester reservation system', 'Add coordination protocols'] : []
            };
            
        } finally {
            this.cleanupEconomyTestEnvironment(testEnvironment);
        }
    }
    
    detectCoordinationIssues(harvesters, resourceNodes, collisionCount, idleTime) {
        // Detect harvesters competing for same node
        resourceNodes.forEach(node => {
            if (node.harvestersAssigned.size > 3) {
                collisionCount.value += node.harvestersAssigned.size - 3;
            }
        });
        
        // Detect idle harvesters when resources available
        const idleHarvesters = harvesters.filter(h => h.state === 'idle');
        const availableNodes = resourceNodes.filter(n => !n.depleted);
        
        if (idleHarvesters.length > 0 && availableNodes.length > 0) {
            idleTime.value += idleHarvesters.length * 100; // 100ms penalty per idle harvester
        }
    }
    
    /**
     * Test resource node optimization
     */
    async testResourceNodeOptimization() {
        console.log('\n🎯 Testing Resource Node Optimization...');
        
        const optimizationTests = [
            { nodes: 3, harvesters: 10, layout: 'clustered' },
            { nodes: 5, harvesters: 10, layout: 'distributed' },
            { nodes: 8, harvesters: 15, layout: 'scattered' }
        ];
        
        const results = [];
        
        for (const test of optimizationTests) {
            const result = await this.runOptimizationTest(test);
            results.push(result);
        }
        
        return {
            testType: 'Resource Node Optimization',
            results,
            success: results.every(r => r.efficient),
            summary: this.generateOptimizationSummary(results)
        };
    }
    
    async runOptimizationTest(testConfig) {
        // Create optimized layout based on config
        const resourceNodes = this.createOptimizedNodeLayout(testConfig);
        const harvesters = [];
        
        for (let i = 0; i < testConfig.harvesters; i++) {
            harvesters.push(this.createHarvester(i, { position: { x: 600, y: 350 } }));
        }
        
        // Measure efficiency metrics
        const totalDistance = this.calculateTotalTravelDistance(harvesters, resourceNodes);
        const distributionScore = this.calculateNodeDistribution(resourceNodes);
        
        return {
            layout: testConfig.layout,
            nodes: testConfig.nodes,
            harvesters: testConfig.harvesters,
            totalTravelDistance: totalDistance,
            distributionScore,
            efficient: totalDistance < 10000 && distributionScore > 0.7,
            recommendations: totalDistance >= 10000 ? 
                ['Reduce node distances', 'Add strategic depot placement'] : []
        };
    }
    
    // Helper methods
    
    calculateEfficiency(tracking, scenario) {
        const theoreticalMax = scenario.harvesters * this.config.baseHarvestRate * (scenario.duration / 1000);
        return Math.min(1.0, tracking.totalResourcesHarvested / theoreticalMax);
    }
    
    calculateDistance(pos1, pos2) {
        const dx = pos2.x - pos1.x;
        const dy = pos2.y - pos1.y;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    normalizeVector(vector) {
        const magnitude = Math.sqrt(vector.x * vector.x + vector.y * vector.y);
        if (magnitude === 0) return { x: 0, y: 0 };
        return { x: vector.x / magnitude, y: vector.y / magnitude };
    }
    
    createOptimizedNodeLayout(testConfig) {
        // Create different layouts based on config
        const nodes = [];
        
        switch (testConfig.layout) {
            case 'clustered':
                // Nodes close together
                for (let i = 0; i < testConfig.nodes; i++) {
                    nodes.push(this.createResourceNode(i));
                    nodes[i].position.x = 500 + (i * 100);
                    nodes[i].position.y = 300 + ((i % 2) * 100);
                }
                break;
                
            case 'distributed':
                // Evenly distributed
                for (let i = 0; i < testConfig.nodes; i++) {
                    nodes.push(this.createResourceNode(i));
                    const angle = (i / testConfig.nodes) * 2 * Math.PI;
                    nodes[i].position.x = 600 + Math.cos(angle) * 300;
                    nodes[i].position.y = 350 + Math.sin(angle) * 200;
                }
                break;
                
            case 'scattered':
                // Random distribution
                for (let i = 0; i < testConfig.nodes; i++) {
                    nodes.push(this.createResourceNode(i));
                    nodes[i].position.x = 200 + Math.random() * 800;
                    nodes[i].position.y = 150 + Math.random() * 400;
                }
                break;
        }
        
        return nodes;
    }
    
    calculateTotalTravelDistance(harvesters, resourceNodes) {
        let totalDistance = 0;
        
        harvesters.forEach(harvester => {
            // Calculate distance to nearest resource node
            const distances = resourceNodes.map(node => 
                this.calculateDistance(harvester.position, node.position)
            );
            const minDistance = Math.min(...distances);
            totalDistance += minDistance;
        });
        
        return totalDistance;
    }
    
    calculateNodeDistribution(resourceNodes) {
        // Calculate how well distributed the nodes are
        if (resourceNodes.length < 2) return 1.0;
        
        const distances = [];
        for (let i = 0; i < resourceNodes.length; i++) {
            for (let j = i + 1; j < resourceNodes.length; j++) {
                const distance = this.calculateDistance(resourceNodes[i].position, resourceNodes[j].position);
                distances.push(distance);
            }
        }
        
        const averageDistance = distances.reduce((sum, d) => sum + d, 0) / distances.length;
        const variance = distances.reduce((sum, d) => sum + Math.pow(d - averageDistance, 2), 0) / distances.length;
        const standardDeviation = Math.sqrt(variance);
        
        // Lower variance means more even distribution
        const distributionScore = Math.max(0, 1 - (standardDeviation / averageDistance));
        return distributionScore;
    }
    
    cleanupEconomyTestEnvironment(testEnvironment) {
        // Cleanup test entities
        const { harvesters, resourceNodes, depot } = testEnvironment;
        
        harvesters.forEach(harvester => {
            if (this.world && this.world.removeEntity) {
                this.world.removeEntity(harvester);
            }
        });
        
        resourceNodes.forEach(node => {
            if (this.world && this.world.removeEntity) {
                this.world.removeEntity(node);
            }
        });
    }
    
    // Evidence and reporting methods
    
    collectEvidence(testType, testName, result) {
        this.evidenceData.push({
            timestamp: new Date().toISOString(),
            testType,
            testName,
            result,
            metrics: result.metrics
        });
    }
    
    generateHarvesterAISummary(results) {
        const avgEfficiency = results.reduce((sum, r) => sum + r.efficiency, 0) / results.length;
        const passedTests = results.filter(r => r.success).length;
        
        return {
            averageEfficiency: `${(avgEfficiency * 100).toFixed(1)}%`,
            passedTests: `${passedTests}/${results.length}`,
            status: passedTests === results.length ? 'EFFICIENT' : 'NEEDS OPTIMIZATION'
        };
    }
    
    generatePathfindingSummary(results) {
        const avgTime = results.reduce((sum, r) => sum + r.averagePathTime, 0) / results.length;
        const allPassed = results.every(r => r.success);
        
        return {
            averagePathfindingTime: `${avgTime.toFixed(2)}ms`,
            target: `${this.config.maxHarvesterPathTime}ms`,
            status: allPassed ? 'WITHIN TARGETS' : 'EXCEEDS TARGETS'
        };
    }
    
    generateBalanceSummary(result) {
        return {
            balanced: result.balanced ? 'YES' : 'NO',
            maxDeviation: `${(result.maxDeviation * 100).toFixed(1)}%`,
            threshold: `${(this.config.resourceBalanceThreshold * 100).toFixed(1)}%`,
            status: result.balanced ? 'BALANCED' : 'IMBALANCED'
        };
    }
    
    generateCoordinationSummary(result) {
        return {
            collisionRate: `${result.collisionRate.toFixed(2)}/sec`,
            averageIdleTime: `${(result.averageIdleTime / 1000).toFixed(1)}s`,
            status: result.efficient ? 'COORDINATED' : 'NEEDS IMPROVEMENT'
        };
    }
    
    generateOptimizationSummary(results) {
        const efficientLayouts = results.filter(r => r.efficient).length;
        
        return {
            efficientLayouts: `${efficientLayouts}/${results.length}`,
            bestLayout: results.reduce((best, current) => 
                current.distributionScore > best.distributionScore ? current : best
            ).layout,
            status: efficientLayouts === results.length ? 'OPTIMIZED' : 'NEEDS ADJUSTMENT'
        };
    }
    
    determineOverallSuccess(testResults) {
        return testResults.every(result => result.success);
    }
    
    /**
     * Print comprehensive economy test report
     */
    printEconomyTestReport(results) {
        console.log('\n' + '=' .repeat(80));
        console.log('💰 RESOURCE ECONOMY TEST REPORT');
        console.log('=' .repeat(80));
        
        console.log(`\n📊 Overall Results:`);
        console.log(`   Duration: ${(results.duration / 1000).toFixed(2)}s`);
        console.log(`   Overall Success: ${results.overallSuccess ? '✅ PASSED' : '❌ FAILED'}`);
        
        // Print individual test results
        Object.entries(results.tests).forEach(([testName, testResult]) => {
            console.log(`\n💡 ${testResult.testType}:`);
            console.log(`   Status: ${testResult.success ? '✅ PASSED' : '❌ FAILED'}`);
            
            if (testResult.summary) {
                Object.entries(testResult.summary).forEach(([key, value]) => {
                    console.log(`   ${key}: ${value}`);
                });
            }
        });
        
        // Economic targets
        console.log(`\n🎯 Economic Targets:`);
        console.log(`   Minimum Efficiency: ${(this.config.minEfficiencyRate * 100).toFixed(1)}%`);
        console.log(`   Max Harvester Path Time: ${this.config.maxHarvesterPathTime}ms`);
        console.log(`   Resource Balance Threshold: ${(this.config.resourceBalanceThreshold * 100).toFixed(1)}%`);
        
        console.log('\n' + '=' .repeat(80));
    }
}