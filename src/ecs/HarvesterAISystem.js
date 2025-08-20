import { System } from "./System.js";
import { HarvesterComponent, ResourceNodeComponent, TransformComponent, MovementComponent, BuildingComponent } from "./Component.js";
import { ResourceNodeComponent as ExtendedResourceNodeComponent } from "./ResourceComponents.js";
import { SpatialHashGrid } from "../utils/QuadTree.js";

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
            "resource-seeker": this.seekResourceBehavior.bind(this),
            "harvester": this.harvestBehavior.bind(this),
            "returner": this.returnBehavior.bind(this),
            "unloader": this.unloadBehavior.bind(this)
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
        
        console.log("✅ HarvesterAISystem initialized with spatial optimization");
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
            if (building.buildingType === "refinery" || building.buildingType === "construction_yard") {
                this.registerRefinery(entity);
            }
        }
        
        // Initialize harvester AI state
        if (entity.hasComponent(HarvesterComponent)) {
            const harvester = entity.getComponent(HarvesterComponent);
            if (harvester.state === "idle") {
                harvester.state = "seeking";
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
        const nearbyRefineries = this.refinerySpatialGrid.queryRadius(
            transform.x,
            transform.y,
            1000 // Large search radius for refineries
        );

        let nearestRefinery = null;
        let nearestDistance = Infinity;

        for (const refineryData of nearbyRefineries) {
            const distance = Math.sqrt(
                Math.pow(refineryData.x - transform.x, 2) +
                Math.pow(refineryData.y - transform.y, 2)
            );

            if (distance < nearestDistance) {
                nearestDistance = distance;
                nearestRefinery = refineryData;
            }
        }

        return nearestRefinery?.entity || null;
    }

    /**
     * Assign nearest refinery to harvester
     */
    assignNearestRefinery(entity) {
        const harvester = entity.getComponent(HarvesterComponent);
        const nearestRefinery = this.findNearestRefinery(entity);

        if (harvester && nearestRefinery) {
            harvester.homeRefineryId = nearestRefinery.id;
            console.log(`Assigned harvester ${entity.id} to refinery ${nearestRefinery.id}`);
        }
    }

    /**
     * Resource seeking behavior
     */
    seekResourceBehavior(entity) {
        const harvester = entity.getComponent(HarvesterComponent);
        const movement = entity.getComponent(MovementComponent);

        // Skip if not ready to search
        if (!harvester.canSearch()) {
            return;
        }

        // Find nearest available resource node
        const resourceNode = this.findNearestResourceNode(entity);

        if (resourceNode) {
            const resourceComponent = resourceNode.getComponent(ResourceNodeComponent) ||
                                    resourceNode.getComponent(ExtendedResourceNodeComponent);

            // Reserve the resource node
            if (resourceComponent.reserve(entity.id)) {
                harvester.targetResourceNode = resourceComponent;
                harvester.state = "moving_to_resource";

                // Issue move command to resource node
                const resourceTransform = resourceNode.getComponent(TransformComponent);
                movement.setTarget(resourceTransform.x, resourceTransform.y);

                console.log(`Harvester ${entity.id} moving to resource at (${resourceTransform.x}, ${resourceTransform.y})`);
            }
        }

        harvester.updateSearchTime();
    }

    /**
     * Harvesting behavior
     */
    harvestBehavior(entity) {
        const harvester = entity.getComponent(HarvesterComponent);
        const transform = entity.getComponent(TransformComponent);
        const movement = entity.getComponent(MovementComponent);

        // Check if we're at the resource location
        if (harvester.targetResourceNode && !harvester.isAtResource) {
            const resourceEntity = this.findEntityByResourceComponent(harvester.targetResourceNode);
            if (resourceEntity) {
                const resourceTransform = resourceEntity.getComponent(TransformComponent);
                const distance = Math.sqrt(
                    Math.pow(transform.x - resourceTransform.x, 2) +
                    Math.pow(transform.y - resourceTransform.y, 2)
                );

                // Check if close enough to start harvesting
                if (distance <= harvester.targetResourceNode.harvestRadius) {
                    movement.stop();
                    harvester.startHarvesting(harvester.targetResourceNode);
                }
            }
        }

        // Process harvesting
        if (harvester.state === "harvesting" && harvester.canHarvest()) {
            const creditsHarvested = harvester.completeHarvest();

            if (creditsHarvested > 0) {
                this.economicStats.totalCreditsHarvested += creditsHarvested;
                this.economicStats.totalHarvestOperations++;

                console.log(`Harvester ${entity.id} harvested ${creditsHarvested} credits (${harvester.currentLoad}/${harvester.maxCapacity})`);
            }

            // Check if harvester is full or resource is depleted
            if (harvester.isFull() || !harvester.targetResourceNode.canHarvest()) {
                harvester.state = "returning";
            }
        }
    }

    /**
     * Return to refinery behavior
     */
    returnBehavior(entity) {
        const harvester = entity.getComponent(HarvesterComponent);
        const transform = entity.getComponent(TransformComponent);
        const movement = entity.getComponent(MovementComponent);

        // Find home refinery or nearest refinery
        let refinery = null;
        if (harvester.homeRefineryId) {
            refinery = this.world.getEntityById(harvester.homeRefineryId);
        }

        if (!refinery) {
            refinery = this.findNearestRefinery(entity);
            if (refinery) {
                harvester.homeRefineryId = refinery.id;
            }
        }

        if (refinery) {
            const refineryTransform = refinery.getComponent(TransformComponent);

            // Move to refinery
            if (!movement.isMoving ||
                movement.targetX !== refineryTransform.x ||
                movement.targetY !== refineryTransform.y) {
                movement.setTarget(refineryTransform.x, refineryTransform.y);
            }

            // Check if at refinery
            const distance = Math.sqrt(
                Math.pow(transform.x - refineryTransform.x, 2) +
                Math.pow(transform.y - refineryTransform.y, 2)
            );

            if (distance <= 64) { // Close enough to refinery
                movement.stop();
                harvester.startUnloading();
            }
        } else {
            // No refinery found, go idle
            harvester.state = "idle";
            console.warn(`Harvester ${entity.id} could not find refinery to return to`);
        }
    }

    /**
     * Unloading behavior
     */
    unloadBehavior(entity) {
        const harvester = entity.getComponent(HarvesterComponent);

        // Check if unloading is complete
        const now = Date.now();
        if (now - harvester.unloadStartTime >= harvester.unloadTime) {
            const creditsDelivered = harvester.completeUnloading();

            if (creditsDelivered > 0 && this.economyManager) {
                this.economyManager.addCredits(creditsDelivered);
                console.log(`Harvester ${entity.id} delivered ${creditsDelivered} credits to refinery`);
            }

            // Return to seeking resources
            harvester.state = "seeking";
        }
    }

    /**
     * Find entity by resource component (helper method)
     */
    findEntityByResourceComponent(resourceComponent) {
        for (const nodeData of this.resourceNodes.values()) {
            if (nodeData.resource === resourceComponent) {
                return nodeData.entity;
            }
        }
        return null;
    }

    /**
     * Update harvester AI with time-slicing optimization
     */
    update(deltaTime) {
        const now = Date.now();

        // Skip update if not enough time has passed
        if (now - this.lastUpdate < this.updateInterval) {
            return;
        }

        const startTime = performance.now();

        // Build update queue if empty
        if (this.harvesterUpdateQueue.length === 0) {
            this.harvesterUpdateQueue = Array.from(this.entities);
        }

        // Process limited number of harvesters per frame
        let processedCount = 0;
        this.economicStats.activeHarvesters = 0;
        this.economicStats.idleHarvesters = 0;

        while (this.harvesterUpdateQueue.length > 0 && processedCount < this.maxHarvestersPerFrame) {
            const entity = this.harvesterUpdateQueue.shift();

            if (!entity.active) continue;

            const harvester = entity.getComponent(HarvesterComponent);
            if (!harvester) continue;

            // Update economic statistics
            if (harvester.state === "idle") {
                this.economicStats.idleHarvesters++;
            } else {
                this.economicStats.activeHarvesters++;
            }

            // Execute behavior based on state
            switch (harvester.state) {
            case "seeking":
                this.seekResourceBehavior(entity, deltaTime);
                break;

            case "moving_to_resource": {
                // Check if arrived at resource
                const movement = entity.getComponent(MovementComponent);
                if (!movement.isMoving) {
                    harvester.state = "harvesting";
                }
                break;
            }

            case "harvesting":
                this.harvestBehavior(entity, deltaTime);
                break;

            case "returning":
                this.returnBehavior(entity, deltaTime);
                break;

            case "unloading":
                this.unloadBehavior(entity, deltaTime);
                break;

            case "idle":
            default:
                // Transition to seeking if idle
                harvester.state = "seeking";
                break;
            }

            processedCount++;
        }

        // Update performance statistics
        const processingTime = performance.now() - startTime;
        this.performanceStats.harvestersProcessed = processedCount;
        this.performanceStats.averageProcessingTime =
            (this.performanceStats.averageProcessingTime * 0.9) + (processingTime * 0.1);

        // Calculate economic efficiency
        if (this.economicStats.totalHarvestOperations > 0) {
            this.performanceStats.economicEfficiency =
                this.economicStats.totalCreditsHarvested / this.economicStats.totalHarvestOperations;
        }

        this.lastUpdate = now;
    }

    /**
     * Get performance statistics
     */
    getPerformanceStats() {
        return {
            ...this.performanceStats,
            economicStats: this.economicStats,
            resourceNodes: this.resourceNodes.size,
            refineries: this.refineries.size,
            spatialGridStats: {
                resourceGrid: this.resourceSpatialGrid.getStats(),
                refineryGrid: this.refinerySpatialGrid.getStats()
            }
        };
    }

    /**
     * Get economic statistics
     */
    getEconomicStats() {
        return {
            ...this.economicStats,
            averageCreditsPerHarvest: this.economicStats.totalHarvestOperations > 0 ?
                this.economicStats.totalCreditsHarvested / this.economicStats.totalHarvestOperations : 0,
            harvesterUtilization: this.economicStats.activeHarvesters /
                (this.economicStats.activeHarvesters + this.economicStats.idleHarvesters)
        };
    }

    /**
     * Reset performance counters
     */
    resetStats() {
        this.performanceStats.resourceSearches = 0;
        this.performanceStats.pathfindingRequests = 0;
        this.resourceSpatialGrid.resetStats();
        this.refinerySpatialGrid.resetStats();
    }

    /**
     * Clean up system resources
     */
    destroy() {
        this.resourceSpatialGrid.clear();
        this.refinerySpatialGrid.clear();
        this.resourceNodes.clear();
        this.refineries.clear();
        this.harvesterUpdateQueue = [];

        console.log("🗑️ HarvesterAISystem destroyed");
    }
}
