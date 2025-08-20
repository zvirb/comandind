import { Component } from "./Component.js";

/**
 * Resource Node Component - Tiberium fields and resource deposits
 */
export class ResourceNodeComponent extends Component {
    constructor(resourceType = "tiberium", amount = 1000, harvestRate = 25) {
        super();
        this.resourceType = resourceType; // tiberium, ore, gems
        this.maxAmount = amount;
        this.currentAmount = amount;
        this.harvestRate = harvestRate; // Credits per harvest action (25 for tiberium)
        this.harvestTime = 3000; // 3 seconds per harvest
        this.depleted = false;
        this.regenerationRate = 0; // Some nodes regenerate
        this.lastRegenTime = Date.now();
        
        // Spatial optimization
        this.harvestRadius = 32; // Radius for harvester positioning
        this.occupied = false;
        this.reservedBy = null; // Entity ID that reserved this node
    }
    
    /**
     * Harvest resources from this node
     */
    harvest(amount = null) {
        if (this.depleted || this.currentAmount <= 0) {
            return 0;
        }
        
        const harvestAmount = amount || this.harvestRate;
        const actualHarvest = Math.min(harvestAmount, this.currentAmount);
        
        this.currentAmount -= actualHarvest;
        
        if (this.currentAmount <= 0) {
            this.currentAmount = 0;
            this.depleted = true;
            this.occupied = false;
            this.reservedBy = null;
        }
        
        return actualHarvest;
    }
    
    /**
     * Check if node can be harvested
     */
    canHarvest() {
        return !this.depleted && this.currentAmount > 0;
    }
    
    /**
     * Reserve this node for a harvester
     */
    reserve(entityId) {
        if (!this.occupied && this.canHarvest()) {
            this.occupied = true;
            this.reservedBy = entityId;
            return true;
        }
        return false;
    }
    
    /**
     * Release reservation
     */
    release(entityId) {
        if (this.reservedBy === entityId) {
            this.occupied = false;
            this.reservedBy = null;
            return true;
        }
        return false;
    }
    
    /**
     * Get resource percentage remaining
     */
    getResourcePercentage() {
        return this.currentAmount / this.maxAmount;
    }
    
    /**
     * Update regeneration (if applicable)
     */
    updateRegeneration(deltaTime) {
        if (this.regenerationRate > 0 && !this.depleted) {
            const now = Date.now();
            if (now - this.lastRegenTime >= 5000) { // Regenerate every 5 seconds
                this.currentAmount = Math.min(
                    this.maxAmount, 
                    this.currentAmount + this.regenerationRate
                );
                this.lastRegenTime = now;
                
                if (this.currentAmount > 0) {
                    this.depleted = false;
                }
            }
        }
    }
}

/**
 * Harvester Component - Resource gathering units
 */
export class HarvesterComponent extends Component {
    constructor(capacity = 700, harvestSpeed = 3000) {
        super();
        this.maxCapacity = capacity; // 700 credits capacity like C&C
        this.currentLoad = 0;
        this.harvestSpeed = harvestSpeed; // 3 seconds per harvest
        this.lastHarvestTime = 0;
        
        // AI State
        this.state = "idle"; // idle, seeking, harvesting, returning, unloading
        this.targetResourceNode = null;
        this.homeRefineryId = null;
        this.harvestStartTime = 0;
        
        // Performance optimization
        this.searchRadius = 200; // Radius to search for resources
        this.lastSearchTime = 0;
        this.searchCooldown = 2000; // 2 seconds between searches
        
        // Movement state
        this.moveToResourceTime = 0;
        this.isAtResource = false;
        this.unloadStartTime = 0;
        this.unloadTime = 3000; // 3 seconds to unload
    }
    
    /**
     * Start harvesting from a resource node
     */
    startHarvesting(resourceNode) {
        if (this.isFull() || !resourceNode || !resourceNode.canHarvest()) {
            return false;
        }
        
        this.state = "harvesting";
        this.targetResourceNode = resourceNode;
        this.harvestStartTime = Date.now();
        this.isAtResource = true;
        
        // Reserve the resource node
        if (resourceNode.reserve) {
            resourceNode.reserve(this.entity?.id);
        }
        
        return true;
    }
    
    /**
     * Complete harvesting action
     */
    completeHarvest() {
        if (!this.targetResourceNode || this.state !== "harvesting") {
            return 0;
        }
        
        const availableCapacity = this.maxCapacity - this.currentLoad;
        const harvestAmount = Math.min(
            availableCapacity,
            this.targetResourceNode.harvestRate || 25
        );
        
        const actualHarvest = this.targetResourceNode.harvest(harvestAmount);
        this.currentLoad += actualHarvest;
        this.lastHarvestTime = Date.now();
        
        // Check if node is depleted or we're full
        if (this.targetResourceNode.depleted || this.isFull()) {
            this.finishHarvesting();
        } else {
            // Continue harvesting - reset timer
            this.harvestStartTime = Date.now();
        }
        
        return actualHarvest;
    }
    
    /**
     * Finish harvesting and change state
     */
    finishHarvesting() {
        if (this.targetResourceNode && this.targetResourceNode.release) {
            this.targetResourceNode.release(this.entity?.id);
        }
        
        this.targetResourceNode = null;
        this.isAtResource = false;
        
        if (this.isFull()) {
            this.state = "returning";
        } else {
            this.state = "seeking";
        }
    }
    
    /**
     * Start unloading at refinery
     */
    startUnloading() {
        if (this.isEmpty()) {
            return false;
        }
        
        this.state = "unloading";
        this.unloadStartTime = Date.now();
        return true;
    }
    
    /**
     * Complete unloading and return credits
     */
    completeUnloading() {
        const credits = this.currentLoad;
        this.currentLoad = 0;
        this.state = "seeking";
        return credits;
    }
    
    /**
     * Check if harvester is full
     */
    isFull() {
        return this.currentLoad >= this.maxCapacity;
    }
    
    /**
     * Check if harvester is empty
     */
    isEmpty() {
        return this.currentLoad <= 0;
    }
    
    /**
     * Check if ready to harvest (cooldown)
     */
    canHarvest() {
        const now = Date.now();
        return (now - this.lastHarvestTime) >= this.harvestSpeed;
    }
    
    /**
     * Check if ready to search for resources
     */
    canSearch() {
        const now = Date.now();
        return (now - this.lastSearchTime) >= this.searchCooldown;
    }
    
    /**
     * Update search timer
     */
    updateSearchTime() {
        this.lastSearchTime = Date.now();
    }
    
    /**
     * Get load percentage
     */
    getLoadPercentage() {
        return this.currentLoad / this.maxCapacity;
    }
    
    /**
     * Reset to idle state
     */
    reset() {
        this.state = "idle";
        this.targetResourceNode = null;
        this.isAtResource = false;
        this.harvestStartTime = 0;
        this.unloadStartTime = 0;
    }
}

/**
 * Economy Component - Manages player resources and income
 */
export class EconomyComponent extends Component {
    constructor(startingCredits = 2000) {
        super();
        this.credits = startingCredits;
        this.creditsPerSecond = 0;
        this.totalEarned = startingCredits;
        this.totalSpent = 0;
        
        // Income tracking
        this.lastIncomeUpdate = Date.now();
        this.incomeHistory = [];
        this.maxHistoryLength = 60; // Track 60 seconds of income
        
        // Resource storage
        this.refineries = new Set(); // Track refinery buildings
        this.harvesters = new Set(); // Track harvester units
        
        // Performance metrics
        this.harvestEfficiency = 1.0; // Multiplier for harvest rates
        this.lastEconomyUpdate = Date.now();
    }
    
    /**
     * Add credits to economy
     */
    addCredits(amount) {
        this.credits += amount;
        this.totalEarned += amount;
        
        // Update income tracking
        const now = Date.now();
        this.incomeHistory.push({
            amount,
            timestamp: now
        });
        
        // Clean old history
        this.cleanIncomeHistory();
        
        return this.credits;
    }
    
    /**
     * Spend credits if available
     */
    spendCredits(amount) {
        if (this.credits >= amount) {
            this.credits -= amount;
            this.totalSpent += amount;
            return true;
        }
        return false;
    }
    
    /**
     * Get current income per second
     */
    getIncomePerSecond() {
        const now = Date.now();
        const oneSecondAgo = now - 1000;
        
        let recentIncome = 0;
        for (const income of this.incomeHistory) {
            if (income.timestamp >= oneSecondAgo) {
                recentIncome += income.amount;
            }
        }
        
        return recentIncome;
    }
    
    /**
     * Clean old income history
     */
    cleanIncomeHistory() {
        const now = Date.now();
        const maxAge = this.maxHistoryLength * 1000; // Convert to milliseconds
        
        this.incomeHistory = this.incomeHistory.filter(
            income => (now - income.timestamp) < maxAge
        );
    }
    
    /**
     * Register a refinery building
     */
    addRefinery(buildingId) {
        this.refineries.add(buildingId);
    }
    
    /**
     * Remove a refinery building
     */
    removeRefinery(buildingId) {
        this.refineries.delete(buildingId);
    }
    
    /**
     * Register a harvester unit
     */
    addHarvester(unitId) {
        this.harvesters.add(unitId);
    }
    
    /**
     * Remove a harvester unit
     */
    removeHarvester(unitId) {
        this.harvesters.delete(unitId);
    }
    
    /**
     * Get economy statistics
     */
    getStats() {
        return {
            credits: this.credits,
            incomePerSecond: this.getIncomePerSecond(),
            totalEarned: this.totalEarned,
            totalSpent: this.totalSpent,
            refineryCount: this.refineries.size,
            harvesterCount: this.harvesters.size,
            harvestEfficiency: this.harvestEfficiency
        };
    }
}