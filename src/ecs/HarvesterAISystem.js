import { System } from './System.js';
import { HarvesterComponent, ResourceNodeComponent, TransformComponent, MovementComponent, BuildingComponent, UnitComponent } from './Component.js';
import { ResourceNodeComponent as ExtendedResourceNodeComponent, EconomyComponent } from './ResourceComponents.js';
import { QuadTree, SpatialHashGrid } from '../utils/QuadTree.js';

/**
 * Harvester AI System - Manages autonomous resource gathering behavior
 * Features spatial resource lookup and optimized pathfinding integration
 * Targets: <5ms pathfinding, efficient resource allocation, authentic C&C economics
 */
export class HarvesterAISystem extends System {
    constructor(world, economyManager = null) {
        super(world);
        this.priority = 4; // Run after pathfinding but before rendering
        this.requiredComponents = [HarvesterComponent, TransformComponent, MovementComponent];
        
        // Spatial optimization for resource nodes
        this.worldBounds = { x: 0, y: 0, width: 2000, height: 2000 };
        this.resourceSpatialGrid = new SpatialHashGrid(2000, 2000, 128); // 128px grid cells
        this.refinerySpatialGrid = new SpatialHashGrid(2000, 2000, 256); // Larger cells for refineries
        
        // Resource management
        this.resourceNodes = new Map(); // entityId -> resource node data
        this.refineries = new Map(); // entityId -> refinery data
        this.economyManager = economyManager;
        
        // Performance optimization
        this.updateInterval = 200; // Update AI every 200ms (5 times per second)
        this.lastUpdate = 0;
        this.maxHarvestersPerFrame = 5; // Limit AI processing per frame
        this.harvesterUpdateQueue = [];
        
        // AI behaviors and states
        this.behaviors = {
            'resource-seeker': this.seekResourceBehavior.bind(this),
            'harvester': this.harvestBehavior.bind(this),
            'returner': this.returnBehavior.bind(this),
            'unloader': this.unloadBehavior.bind(this)
        };
        
        // Performance tracking
        this.performanceStats = {
            harvestersProcessed: 0,
            pathfindingRequests: 0,
            resourceSearches: 0,
            averageProcessingTime: 0,
            economicEfficiency: 0
        };
        
        // Economic statistics
        this.economicStats = {
            totalCreditsHarvested: 0,
            totalHarvestOperations: 0,
            averageHarvestEfficiency: 0,
            activeHarvesters: 0,
            idleHarvesters: 0
        };
        
        console.log('✅ HarvesterAISystem initialized with spatial optimization');
    }
    
    /**
     * Called when entity is added to system
     */
    onEntityAdded(entity) {
        // Register resource nodes
        if (entity.hasComponent(ResourceNodeComponent) || entity.hasComponent(ExtendedResourceNodeComponent)) {
            this.registerResourceNode(entity);
        }
        
        // Register refineries
        if (entity.hasComponent(BuildingComponent)) {
            const building = entity.getComponent(BuildingComponent);
            if (building.buildingType === 'refinery' || building.buildingType === 'construction_yard') {
                this.registerRefinery(entity);
            }
        }
        
        // Initialize harvester AI state
        if (entity.hasComponent(HarvesterComponent)) {
            const harvester = entity.getComponent(HarvesterComponent);
            if (harvester.state === 'idle') {
                harvester.state = 'seeking';
            }
            
            // Assign to nearest refinery if none assigned
            if (!harvester.homeRefineryId) {
                this.assignNearestRefinery(entity);
            }
        }
    }
    
    /**
     * Called when entity is removed from system
     */
    onEntityRemoved(entity) {
        // Unregister resource nodes
        if (this.resourceNodes.has(entity.id)) {
            this.unregisterResourceNode(entity);
        }
        
        // Unregister refineries
        if (this.refineries.has(entity.id)) {
            this.unregisterRefinery(entity);
        }
        
        // Clean up harvester references
        if (entity.hasComponent(HarvesterComponent)) {
            const harvester = entity.getComponent(HarvesterComponent);
            
            // Release any reserved resource node
            if (harvester.targetResourceNode) {
                const resourceNode = harvester.targetResourceNode;
                if (resourceNode.release) {
                    resourceNode.release(entity.id);
                }
            }
        }
    }
    
    /**
     * Register resource node in spatial grid
     */
    registerResourceNode(entity) {
        const transform = entity.getComponent(TransformComponent);
        let resourceComponent = entity.getComponent(ResourceNodeComponent) || 
                               entity.getComponent(ExtendedResourceNodeComponent);
        
        if (transform && resourceComponent) {
            const nodeData = {
                entity: entity,
                transform: transform,
                resource: resourceComponent,
                x: transform.x,
                y: transform.y,
                bounds: {
                    width: 64, // Resource node size
                    height: 64
                }
            };
            
            this.resourceNodes.set(entity.id, nodeData);
            this.resourceSpatialGrid.insert(nodeData);
            
            console.log(`Registered resource node at (${transform.x}, ${transform.y}) with ${resourceComponent.currentAmount} resources`);
        }
    }
    
    /**
     * Unregister resource node from spatial grid
     */
    unregisterResourceNode(entity) {
        const nodeData = this.resourceNodes.get(entity.id);
        if (nodeData) {
            this.resourceSpatialGrid.remove(nodeData);
            this.resourceNodes.delete(entity.id);
        }
    }
    
    /**
     * Register refinery in spatial grid
     */
    registerRefinery(entity) {
        const transform = entity.getComponent(TransformComponent);
        const building = entity.getComponent(BuildingComponent);
        
        if (transform && building) {
            const refineryData = {
                entity: entity,
                transform: transform,
                building: building,
                x: transform.x,
                y: transform.y,
                bounds: {
                    width: 96, // Refinery size
                    height: 96
                }
            };
            
            this.refineries.set(entity.id, refineryData);
            this.refinerySpatialGrid.insert(refineryData);
            
            console.log(`Registered refinery at (${transform.x}, ${transform.y})`);
        }
    }
    
    /**
     * Unregister refinery from spatial grid
     */
    unregisterRefinery(entity) {
        const refineryData = this.refineries.get(entity.id);
        if (refineryData) {
            this.refinerySpatialGrid.remove(refineryData);
            this.refineries.delete(entity.id);
        }
    }
    
    /**
     * Find nearest resource node using spatial optimization
     */
    findNearestResourceNode(entity, maxDistance = 500) {
        const startTime = performance.now();
        const transform = entity.getComponent(TransformComponent);
        
        if (!transform) return null;
        
        // Use spatial grid for fast lookup
        const nearbyNodes = this.resourceSpatialGrid.queryRadius(
            transform.x, 
            transform.y, 
            maxDistance
        );
        
        let nearestNode = null;
        let nearestDistance = Infinity;
        
        for (const nodeData of nearbyNodes) {
            const resourceComponent = nodeData.resource;
            
            // Check if node is available and has resources
            if (resourceComponent.canHarvest() && !resourceComponent.occupied) {
                const distance = Math.sqrt(
                    Math.pow(nodeData.x - transform.x, 2) + 
                    Math.pow(nodeData.y - transform.y, 2)
                );
                
                if (distance < nearestDistance) {
                    nearestDistance = distance;
                    nearestNode = nodeData;
                }
            }
        }
        
        // Update performance stats
        const searchTime = performance.now() - startTime;
        this.performanceStats.resourceSearches++;
        
        return nearestNode?.entity || null;
    }
    
    /**
     * Find nearest refinery using spatial optimization
     */
    findNearestRefinery(entity) {
        const transform = entity.getComponent(TransformComponent);
        
        if (!transform) return null;
        
        // Use spatial grid for fast lookup
        const nearbyRefineries = this.refinerySpatialGrid.queryRadius(\n            transform.x, \n            transform.y, \n            1000 // Large search radius for refineries\n        );\n        \n        let nearestRefinery = null;\n        let nearestDistance = Infinity;\n        \n        for (const refineryData of nearbyRefineries) {\n            const distance = Math.sqrt(\n                Math.pow(refineryData.x - transform.x, 2) + \n                Math.pow(refineryData.y - transform.y, 2)\n            );\n            \n            if (distance < nearestDistance) {\n                nearestDistance = distance;\n                nearestRefinery = refineryData;\n            }\n        }\n        \n        return nearestRefinery?.entity || null;\n    }\n    \n    /**\n     * Assign nearest refinery to harvester\n     */\n    assignNearestRefinery(entity) {\n        const harvester = entity.getComponent(HarvesterComponent);\n        const nearestRefinery = this.findNearestRefinery(entity);\n        \n        if (harvester && nearestRefinery) {\n            harvester.homeRefineryId = nearestRefinery.id;\n            console.log(`Assigned harvester ${entity.id} to refinery ${nearestRefinery.id}`);\n        }\n    }\n    \n    /**\n     * Resource seeking behavior\n     */\n    seekResourceBehavior(entity, deltaTime) {\n        const harvester = entity.getComponent(HarvesterComponent);\n        const transform = entity.getComponent(TransformComponent);\n        const movement = entity.getComponent(MovementComponent);\n        \n        // Skip if not ready to search\n        if (!harvester.canSearch()) {\n            return;\n        }\n        \n        // Find nearest available resource node\n        const resourceNode = this.findNearestResourceNode(entity);\n        \n        if (resourceNode) {\n            const resourceComponent = resourceNode.getComponent(ResourceNodeComponent) ||\n                                    resourceNode.getComponent(ExtendedResourceNodeComponent);\n            \n            // Reserve the resource node\n            if (resourceComponent.reserve(entity.id)) {\n                harvester.targetResourceNode = resourceComponent;\n                harvester.state = 'moving_to_resource';\n                \n                // Issue move command to resource node\n                const resourceTransform = resourceNode.getComponent(TransformComponent);\n                movement.setTarget(resourceTransform.x, resourceTransform.y);\n                \n                console.log(`Harvester ${entity.id} moving to resource at (${resourceTransform.x}, ${resourceTransform.y})`);\n            }\n        }\n        \n        harvester.updateSearchTime();\n    }\n    \n    /**\n     * Harvesting behavior\n     */\n    harvestBehavior(entity, deltaTime) {\n        const harvester = entity.getComponent(HarvesterComponent);\n        const transform = entity.getComponent(TransformComponent);\n        const movement = entity.getComponent(MovementComponent);\n        \n        // Check if we're at the resource location\n        if (harvester.targetResourceNode && !harvester.isAtResource) {\n            const resourceEntity = this.findEntityByResourceComponent(harvester.targetResourceNode);\n            if (resourceEntity) {\n                const resourceTransform = resourceEntity.getComponent(TransformComponent);\n                const distance = Math.sqrt(\n                    Math.pow(transform.x - resourceTransform.x, 2) + \n                    Math.pow(transform.y - resourceTransform.y, 2)\n                );\n                \n                // Check if close enough to start harvesting\n                if (distance <= harvester.targetResourceNode.harvestRadius) {\n                    movement.stop();\n                    harvester.startHarvesting(harvester.targetResourceNode);\n                }\n            }\n        }\n        \n        // Process harvesting\n        if (harvester.state === 'harvesting' && harvester.canHarvest()) {\n            const creditsHarvested = harvester.completeHarvest();\n            \n            if (creditsHarvested > 0) {\n                this.economicStats.totalCreditsHarvested += creditsHarvested;\n                this.economicStats.totalHarvestOperations++;\n                \n                console.log(`Harvester ${entity.id} harvested ${creditsHarvested} credits (${harvester.currentLoad}/${harvester.maxCapacity})`);\n            }\n            \n            // Check if harvester is full or resource is depleted\n            if (harvester.isFull() || !harvester.targetResourceNode.canHarvest()) {\n                harvester.state = 'returning';\n            }\n        }\n    }\n    \n    /**\n     * Return to refinery behavior\n     */\n    returnBehavior(entity, deltaTime) {\n        const harvester = entity.getComponent(HarvesterComponent);\n        const transform = entity.getComponent(TransformComponent);\n        const movement = entity.getComponent(MovementComponent);\n        \n        // Find home refinery or nearest refinery\n        let refinery = null;\n        if (harvester.homeRefineryId) {\n            refinery = this.world.getEntityById(harvester.homeRefineryId);\n        }\n        \n        if (!refinery) {\n            refinery = this.findNearestRefinery(entity);\n            if (refinery) {\n                harvester.homeRefineryId = refinery.id;\n            }\n        }\n        \n        if (refinery) {\n            const refineryTransform = refinery.getComponent(TransformComponent);\n            \n            // Move to refinery\n            if (!movement.isMoving || \n                movement.targetX !== refineryTransform.x || \n                movement.targetY !== refineryTransform.y) {\n                movement.setTarget(refineryTransform.x, refineryTransform.y);\n            }\n            \n            // Check if at refinery\n            const distance = Math.sqrt(\n                Math.pow(transform.x - refineryTransform.x, 2) + \n                Math.pow(transform.y - refineryTransform.y, 2)\n            );\n            \n            if (distance <= 64) { // Close enough to refinery\n                movement.stop();\n                harvester.startUnloading();\n            }\n        } else {\n            // No refinery found, go idle\n            harvester.state = 'idle';\n            console.warn(`Harvester ${entity.id} could not find refinery to return to`);\n        }\n    }\n    \n    /**\n     * Unloading behavior\n     */\n    unloadBehavior(entity, deltaTime) {\n        const harvester = entity.getComponent(HarvesterComponent);\n        \n        // Check if unloading is complete\n        const now = Date.now();\n        if (now - harvester.unloadStartTime >= harvester.unloadTime) {\n            const creditsDelivered = harvester.completeUnloading();\n            \n            if (creditsDelivered > 0 && this.economyManager) {\n                this.economyManager.addCredits(creditsDelivered);\n                console.log(`Harvester ${entity.id} delivered ${creditsDelivered} credits to refinery`);\n            }\n            \n            // Return to seeking resources\n            harvester.state = 'seeking';\n        }\n    }\n    \n    /**\n     * Find entity by resource component (helper method)\n     */\n    findEntityByResourceComponent(resourceComponent) {\n        for (const [entityId, nodeData] of this.resourceNodes) {\n            if (nodeData.resource === resourceComponent) {\n                return nodeData.entity;\n            }\n        }\n        return null;\n    }\n    \n    /**\n     * Update harvester AI with time-slicing optimization\n     */\n    update(deltaTime) {\n        const now = Date.now();\n        \n        // Skip update if not enough time has passed\n        if (now - this.lastUpdate < this.updateInterval) {\n            return;\n        }\n        \n        const startTime = performance.now();\n        \n        // Build update queue if empty\n        if (this.harvesterUpdateQueue.length === 0) {\n            this.harvesterUpdateQueue = Array.from(this.entities);\n        }\n        \n        // Process limited number of harvesters per frame\n        let processedCount = 0;\n        this.economicStats.activeHarvesters = 0;\n        this.economicStats.idleHarvesters = 0;\n        \n        while (this.harvesterUpdateQueue.length > 0 && processedCount < this.maxHarvestersPerFrame) {\n            const entity = this.harvesterUpdateQueue.shift();\n            \n            if (!entity.active) continue;\n            \n            const harvester = entity.getComponent(HarvesterComponent);\n            if (!harvester) continue;\n            \n            // Update economic statistics\n            if (harvester.state === 'idle') {\n                this.economicStats.idleHarvesters++;\n            } else {\n                this.economicStats.activeHarvesters++;\n            }\n            \n            // Execute behavior based on state\n            switch (harvester.state) {\n                case 'seeking':\n                    this.seekResourceBehavior(entity, deltaTime);\n                    break;\n                    \n                case 'moving_to_resource':\n                    // Check if arrived at resource\n                    const movement = entity.getComponent(MovementComponent);\n                    if (!movement.isMoving) {\n                        harvester.state = 'harvesting';\n                    }\n                    break;\n                    \n                case 'harvesting':\n                    this.harvestBehavior(entity, deltaTime);\n                    break;\n                    \n                case 'returning':\n                    this.returnBehavior(entity, deltaTime);\n                    break;\n                    \n                case 'unloading':\n                    this.unloadBehavior(entity, deltaTime);\n                    break;\n                    \n                case 'idle':\n                default:\n                    // Transition to seeking if idle\n                    harvester.state = 'seeking';\n                    break;\n            }\n            \n            processedCount++;\n        }\n        \n        // Update performance statistics\n        const processingTime = performance.now() - startTime;\n        this.performanceStats.harvestersProcessed = processedCount;\n        this.performanceStats.averageProcessingTime = \n            (this.performanceStats.averageProcessingTime * 0.9) + (processingTime * 0.1);\n        \n        // Calculate economic efficiency\n        if (this.economicStats.totalHarvestOperations > 0) {\n            this.performanceStats.economicEfficiency = \n                this.economicStats.totalCreditsHarvested / this.economicStats.totalHarvestOperations;\n        }\n        \n        this.lastUpdate = now;\n    }\n    \n    /**\n     * Get performance statistics\n     */\n    getPerformanceStats() {\n        return {\n            ...this.performanceStats,\n            economicStats: this.economicStats,\n            resourceNodes: this.resourceNodes.size,\n            refineries: this.refineries.size,\n            spatialGridStats: {\n                resourceGrid: this.resourceSpatialGrid.getStats(),\n                refineryGrid: this.refinerySpatialGrid.getStats()\n            }\n        };\n    }\n    \n    /**\n     * Get economic statistics\n     */\n    getEconomicStats() {\n        return {\n            ...this.economicStats,\n            averageCreditsPerHarvest: this.economicStats.totalHarvestOperations > 0 ?\n                this.economicStats.totalCreditsHarvested / this.economicStats.totalHarvestOperations : 0,\n            harvesterUtilization: this.economicStats.activeHarvesters / \n                (this.economicStats.activeHarvesters + this.economicStats.idleHarvesters)\n        };\n    }\n    \n    /**\n     * Reset performance counters\n     */\n    resetStats() {\n        this.performanceStats.resourceSearches = 0;\n        this.performanceStats.pathfindingRequests = 0;\n        this.resourceSpatialGrid.resetStats();\n        this.refinerySpatialGrid.resetStats();\n    }\n    \n    /**\n     * Clean up system resources\n     */\n    destroy() {\n        this.resourceSpatialGrid.clear();\n        this.refinerySpatialGrid.clear();\n        this.resourceNodes.clear();\n        this.refineries.clear();\n        this.harvesterUpdateQueue = [];\n        \n        console.log('🗑️ HarvesterAISystem destroyed');\n    }\n}