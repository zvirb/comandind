/**
 * ResourceEconomyUI - Comprehensive resource economy interface
 * 
 * Advanced resource management UI that provides real-time tracking of credits,
 * harvester operations, income rates, and economic forecasting. Integrates
 * with the UIUpdateManager for smooth 10Hz updates and efficient DOM manipulation.
 * 
 * Features:
 * - Real-time credit counter with smooth animations
 * - Harvester status monitoring and efficiency tracking
 * - Income rate calculation and trend analysis
 * - Resource flow visualization
 * - Economic health indicators
 * - Power grid status and consumption
 * - Production building status
 * - Resource shortage warnings
 */

import { UIUpdateManager } from '../core/UIUpdateManager.js';

export class ResourceEconomyUI {
    constructor(world, uiUpdateManager, options = {}) {
        this.world = world;
        this.uiUpdateManager = uiUpdateManager || new UIUpdateManager();
        
        // Configuration
        this.config = {
            updateInterval: options.updateInterval || 100, // ms
            animationDuration: options.animationDuration || 500,
            enableAnimations: options.enableAnimations !== false,
            enablePredictions: options.enablePredictions !== false,
            warningThresholds: {
                lowCredits: options.lowCreditsThreshold || 500,
                lowPower: options.lowPowerThreshold || 50,
                lowIncome: options.lowIncomeThreshold || 5
            },
            formatOptions: {
                useThousandsSeparator: true,
                showDecimals: false,
                currency: '$'
            }
        };
        
        // Resource tracking state
        this.resources = {
            credits: 1000,
            power: 100,
            powerUsed: 0,
            income: 0,
            expenses: 0,
            netIncome: 0
        };
        
        // Historical data for trend analysis
        this.history = {
            credits: [],
            income: [],
            expenses: [],
            maxHistory: 60 // Keep 60 data points (1 minute at 1Hz)
        };
        
        // Harvester tracking
        this.harvesters = new Map(); // entityId -> harvester data
        this.harvestStats = {
            total: 0,
            active: 0,
            idle: 0,
            returning: 0,
            efficiency: 100,
            totalIncome: 0,
            incomeRate: 0
        };
        
        // Building tracking
        this.buildings = {
            powerPlants: 0,
            refineries: 0,
            factories: 0,
            defense: 0
        };
        
        // UI state
        this.isVisible = true;
        this.lastUpdateTime = 0;
        this.animationTargets = new Map();
        this.warnings = new Set();
        
        // Performance tracking
        this.stats = {
            updates: 0,
            averageUpdateTime: 0,
            maxUpdateTime: 0,
            domUpdates: 0
        };
        
        this.isDestroyed = false;
        
        this.init();
    }
    
    /**
     * Initialize the resource economy UI
     */
    init() {
        console.log('💰 Initializing ResourceEconomyUI...');
        
        // Create DOM elements
        this.createUI();
        
        // Start update loop
        this.startUpdateLoop();
        
        // Setup event listeners
        this.setupEventListeners();
        
        console.log('✅ ResourceEconomyUI initialized');
    }
    
    /**
     * Create UI DOM elements
     */
    createUI() {
        // Create main container
        const container = document.createElement('div');
        container.id = 'resource-economy-ui';
        container.className = 'resource-ui';
        container.innerHTML = this.getUIHTML();
        
        // Add styles
        const styles = document.createElement('style');
        styles.textContent = this.getUICSS();
        document.head.appendChild(styles);
        
        // Insert into page
        document.body.appendChild(container);
        
        // Cache DOM elements
        this.cacheUIElements();
        
        console.log('🎨 Resource UI DOM elements created');
    }
    
    /**
     * Get UI HTML structure
     */
    getUIHTML() {
        return `
            <div class="resource-panel">
                <div class="resource-header">
                    <h3>Economic Status</h3>
                    <button id="resource-minimize" class="minimize-btn">−</button>
                </div>
                
                <div class="resource-content">
                    <!-- Credits Section -->
                    <div class="resource-section credits-section">
                        <div class="resource-icon">💰</div>
                        <div class="resource-info">
                            <div class="resource-label">Credits</div>
                            <div class="resource-value" id="credits-value">$0</div>
                            <div class="resource-trend" id="credits-trend">+$0/min</div>
                        </div>
                        <div class="resource-status" id="credits-status">●</div>
                    </div>
                    
                    <!-- Power Section -->
                    <div class="resource-section power-section">
                        <div class="resource-icon">⚡</div>
                        <div class="resource-info">
                            <div class="resource-label">Power</div>
                            <div class="resource-value" id="power-value">0/0</div>
                            <div class="resource-bar">
                                <div class="power-bar-fill" id="power-bar-fill"></div>
                            </div>
                        </div>
                        <div class="resource-status" id="power-status">●</div>
                    </div>
                    
                    <!-- Income Section -->
                    <div class="resource-section income-section">
                        <div class="resource-icon">📈</div>
                        <div class="resource-info">
                            <div class="resource-label">Income</div>
                            <div class="resource-value" id="income-value">+$0/min</div>
                            <div class="resource-breakdown">
                                <span id="income-breakdown">Harvesters: $0</span>
                            </div>
                        </div>
                        <div class="resource-status" id="income-status">●</div>
                    </div>
                    
                    <!-- Harvester Section -->
                    <div class="resource-section harvesters-section">
                        <div class="resource-icon">🚛</div>
                        <div class="resource-info">
                            <div class="resource-label">Harvesters</div>
                            <div class="resource-value" id="harvesters-count">0/0</div>
                            <div class="harvester-status">
                                <span class="harvester-stat">Active: <span id="harvesters-active">0</span></span>
                                <span class="harvester-stat">Idle: <span id="harvesters-idle">0</span></span>
                                <span class="harvester-stat">Efficiency: <span id="harvesters-efficiency">100%</span></span>
                            </div>
                        </div>
                        <div class="resource-status" id="harvesters-status">●</div>
                    </div>
                    
                    <!-- Buildings Section -->
                    <div class="resource-section buildings-section">
                        <div class="resource-icon">🏭</div>
                        <div class="resource-info">
                            <div class="resource-label">Buildings</div>
                            <div class="building-counts">
                                <span class="building-count">Power: <span id="power-plants-count">0</span></span>
                                <span class="building-count">Refineries: <span id="refineries-count">0</span></span>
                                <span class="building-count">Factories: <span id="factories-count">0</span></span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Warnings Section -->
                <div class="warnings-section" id="warnings-section" style="display: none;">
                    <div class="warning-header">⚠️ Warnings</div>
                    <div class="warning-list" id="warning-list"></div>
                </div>
                
                <!-- Predictions Section (Optional) -->
                <div class="predictions-section" id="predictions-section" style="display: none;">
                    <div class="predictions-header">📊 Forecast</div>
                    <div class="prediction-item">
                        <span>Credits in 5min:</span>
                        <span id="credits-prediction">$0</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Get UI CSS styles
     */
    getUICSS() {
        return `
            .resource-ui {
                position: fixed;
                top: 80px;
                left: 10px;
                background: rgba(0, 20, 40, 0.95);
                border: 2px solid #00ff00;
                border-radius: 8px;
                color: #00ff00;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                min-width: 280px;
                z-index: 1000;
                user-select: none;
                backdrop-filter: blur(5px);
            }
            
            .resource-panel {
                padding: 0;
            }
            
            .resource-header {
                background: rgba(0, 255, 0, 0.2);
                padding: 8px 12px;
                border-bottom: 1px solid #00ff00;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .resource-header h3 {
                margin: 0;
                font-size: 14px;
                font-weight: bold;
            }
            
            .minimize-btn {
                background: none;
                border: 1px solid #00ff00;
                color: #00ff00;
                width: 20px;
                height: 20px;
                cursor: pointer;
                border-radius: 3px;
                font-size: 14px;
                line-height: 1;
            }
            
            .minimize-btn:hover {
                background: rgba(0, 255, 0, 0.2);
            }
            
            .resource-content {
                padding: 12px;
            }
            
            .resource-section {
                display: flex;
                align-items: center;
                margin-bottom: 12px;
                padding: 8px;
                border: 1px solid transparent;
                border-radius: 4px;
                transition: all 0.2s ease;
            }
            
            .resource-section:hover {
                background: rgba(0, 255, 0, 0.1);
                border-color: #00ff00;
            }
            
            .resource-icon {
                font-size: 16px;
                width: 24px;
                text-align: center;
                margin-right: 10px;
            }
            
            .resource-info {
                flex: 1;
            }
            
            .resource-label {
                font-size: 10px;
                opacity: 0.8;
                margin-bottom: 2px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .resource-value {
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 2px;
                color: #ffffff;
            }
            
            .resource-trend, .resource-breakdown, .harvester-status, .building-counts {
                font-size: 10px;
                opacity: 0.7;
                line-height: 1.2;
            }
            
            .resource-status {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin-left: 8px;
            }
            
            .resource-status.good { color: #00ff00; }
            .resource-status.warning { color: #ffff00; }
            .resource-status.critical { color: #ff0000; }
            
            .resource-bar {
                width: 100%;
                height: 4px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 2px;
                margin-top: 2px;
                overflow: hidden;
            }
            
            .power-bar-fill {
                height: 100%;
                background: linear-gradient(90deg, #00ff00, #ffff00);
                border-radius: 2px;
                transition: width 0.3s ease;
                width: 0%;
            }
            
            .harvester-stat {
                display: inline-block;
                margin-right: 8px;
            }
            
            .building-count {
                display: inline-block;
                margin-right: 8px;
                font-size: 10px;
            }
            
            .warnings-section {
                border-top: 1px solid #ff0000;
                background: rgba(255, 0, 0, 0.1);
            }
            
            .warning-header {
                padding: 8px 12px;
                font-weight: bold;
                color: #ff0000;
                font-size: 11px;
            }
            
            .warning-list {
                padding: 0 12px 8px;
                color: #ff0000;
                font-size: 10px;
                line-height: 1.4;
            }
            
            .predictions-section {
                border-top: 1px solid #00ffff;
                background: rgba(0, 255, 255, 0.1);
                padding: 8px 12px;
            }
            
            .predictions-header {
                font-weight: bold;
                color: #00ffff;
                font-size: 11px;
                margin-bottom: 4px;
            }
            
            .prediction-item {
                display: flex;
                justify-content: space-between;
                font-size: 10px;
                margin-bottom: 2px;
            }
            
            /* Animation classes */
            .resource-value.updating {
                animation: pulse 0.5s ease-in-out;
            }
            
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            
            /* Minimized state */
            .resource-ui.minimized .resource-content,
            .resource-ui.minimized .warnings-section,
            .resource-ui.minimized .predictions-section {
                display: none;
            }
        `;
    }
    
    /**
     * Cache UI DOM elements for efficient access
     */
    cacheUIElements() {
        this.elements = {
            // Main elements
            container: document.getElementById('resource-economy-ui'),
            minimizeBtn: document.getElementById('resource-minimize'),
            
            // Resource values
            creditsValue: document.getElementById('credits-value'),
            creditsTrend: document.getElementById('credits-trend'),
            creditsStatus: document.getElementById('credits-status'),
            
            powerValue: document.getElementById('power-value'),
            powerBarFill: document.getElementById('power-bar-fill'),
            powerStatus: document.getElementById('power-status'),
            
            incomeValue: document.getElementById('income-value'),
            incomeBreakdown: document.getElementById('income-breakdown'),
            incomeStatus: document.getElementById('income-status'),
            
            // Harvester elements
            harvestersCount: document.getElementById('harvesters-count'),
            harvestersActive: document.getElementById('harvesters-active'),
            harvestersIdle: document.getElementById('harvesters-idle'),
            harvestersEfficiency: document.getElementById('harvesters-efficiency'),
            harvestersStatus: document.getElementById('harvesters-status'),
            
            // Building counts
            powerPlantsCount: document.getElementById('power-plants-count'),
            refineriesCount: document.getElementById('refineries-count'),
            factoriesCount: document.getElementById('factories-count'),
            
            // Warnings and predictions
            warningsSection: document.getElementById('warnings-section'),
            warningList: document.getElementById('warning-list'),
            predictionsSection: document.getElementById('predictions-section'),
            creditsPrediction: document.getElementById('credits-prediction')
        };
    }
    
    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Minimize/maximize toggle
        if (this.elements.minimizeBtn) {
            this.elements.minimizeBtn.addEventListener('click', () => {
                this.toggleMinimize();
            });
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            if (event.key === 'F4') {
                event.preventDefault();
                this.toggleVisibility();
            }
        });
    }
    
    /**
     * Start the update loop
     */
    startUpdateLoop() {
        const updateLoop = () => {
            if (this.isDestroyed) return;
            
            const now = Date.now();
            if (now - this.lastUpdateTime >= this.config.updateInterval) {
                this.updateResources();
                this.lastUpdateTime = now;
            }
            
            requestAnimationFrame(updateLoop);
        };
        
        requestAnimationFrame(updateLoop);
    }
    
    /**
     * Update all resource data and UI
     */
    updateResources() {
        const startTime = performance.now();
        
        try {
            // Gather resource data from world
            this.gatherResourceData();
            
            // Update harvester data
            this.updateHarvesterData();
            
            // Update building data
            this.updateBuildingData();
            
            // Calculate trends and predictions
            this.calculateTrends();
            
            // Check for warnings
            this.checkWarnings();
            
            // Update UI elements
            this.updateUI();
            
            // Update performance stats
            const updateTime = performance.now() - startTime;
            this.stats.updates++;
            this.stats.averageUpdateTime = (this.stats.averageUpdateTime + updateTime) / 2;
            this.stats.maxUpdateTime = Math.max(this.stats.maxUpdateTime, updateTime);
            
        } catch (error) {
            console.error('❌ Error updating resource UI:', error);
        }
    }
    
    /**
     * Gather resource data from world entities
     */
    gatherResourceData() {
        if (!this.world) return;
        
        // Reset counters
        let totalPower = 0;
        let usedPower = 0;
        let totalIncome = 0;
        let totalExpenses = 0;
        
        // Get all entities with resource components
        const entities = this.world.entities.filter(entity => entity.active);
        
        for (const entity of entities) {
            // Power generation
            const powerGen = entity.getComponent('PowerGeneratorComponent');
            if (powerGen) {
                totalPower += powerGen.output;
            }
            
            // Power consumption
            const powerCons = entity.getComponent('PowerConsumerComponent');
            if (powerCons) {
                usedPower += powerCons.consumption;
            }
            
            // Income generation
            const income = entity.getComponent('IncomeComponent');
            if (income) {
                totalIncome += income.rate;
            }
            
            // Expenses
            const expense = entity.getComponent('ExpenseComponent');
            if (expense) {
                totalExpenses += expense.rate;
            }
        }
        
        // Update resource state
        this.resources.power = totalPower;
        this.resources.powerUsed = usedPower;
        this.resources.income = totalIncome;
        this.resources.expenses = totalExpenses;
        this.resources.netIncome = totalIncome - totalExpenses;
        
        // Update credits based on net income (simplified)
        const timeDelta = this.config.updateInterval / 1000; // Convert to seconds
        const incomePerSecond = this.resources.netIncome / 60; // Convert per-minute to per-second
        this.resources.credits += incomePerSecond * timeDelta;
        
        // Ensure credits don't go negative
        this.resources.credits = Math.max(0, this.resources.credits);
    }
    
    /**
     * Update harvester-specific data
     */
    updateHarvesterData() {
        if (!this.world) return;
        
        // Find all harvester entities
        const harvesters = this.world.entities.filter(entity => 
            entity.hasComponent('HarvesterComponent') && entity.active
        );
        
        // Reset stats
        this.harvestStats.total = harvesters.length;
        this.harvestStats.active = 0;
        this.harvestStats.idle = 0;
        this.harvestStats.returning = 0;
        this.harvestStats.totalIncome = 0;
        
        // Analyze each harvester
        for (const harvester of harvesters) {
            const harvesterComp = harvester.getComponent('HarvesterComponent');
            const movement = harvester.getComponent('MovementComponent');
            
            if (harvesterComp) {
                // Update harvester tracking
                const entityId = harvester.id;
                const harvesterData = {
                    id: entityId,
                    state: harvesterComp.state || 'idle',
                    cargo: harvesterComp.cargo || 0,
                    maxCargo: harvesterComp.maxCargo || 100,
                    efficiency: harvesterComp.efficiency || 100,
                    incomeGenerated: harvesterComp.totalIncome || 0
                };
                
                this.harvesters.set(entityId, harvesterData);
                
                // Count states
                switch (harvesterData.state) {
                    case 'harvesting':
                    case 'moving_to_resource':
                        this.harvestStats.active++;
                        break;
                    case 'returning':
                    case 'moving_to_refinery':
                        this.harvestStats.returning++;
                        break;
                    default:
                        this.harvestStats.idle++;
                }
                
                this.harvestStats.totalIncome += harvesterData.incomeGenerated;
            }
        }
        
        // Calculate overall efficiency
        if (this.harvestStats.total > 0) {
            const workingHarvesters = this.harvestStats.active + this.harvestStats.returning;
            this.harvestStats.efficiency = Math.round((workingHarvesters / this.harvestStats.total) * 100);
        }
        
        // Calculate income rate (credits per minute)
        this.harvestStats.incomeRate = this.harvestStats.totalIncome * 60 / (this.stats.updates || 1);
    }
    
    /**
     * Update building counts
     */
    updateBuildingData() {
        if (!this.world) return;
        
        // Reset building counts
        this.buildings.powerPlants = 0;
        this.buildings.refineries = 0;
        this.buildings.factories = 0;
        this.buildings.defense = 0;
        
        // Count buildings by type
        const buildings = this.world.entities.filter(entity => 
            entity.hasComponent('BuildingComponent') && entity.active
        );
        
        for (const building of buildings) {
            const buildingComp = building.getComponent('BuildingComponent');
            if (buildingComp) {
                switch (buildingComp.type) {
                    case 'power-plant':
                        this.buildings.powerPlants++;
                        break;
                    case 'refinery':
                        this.buildings.refineries++;
                        break;
                    case 'factory':
                    case 'barracks':
                    case 'vehicle-factory':
                        this.buildings.factories++;
                        break;
                    case 'turret':
                    case 'defense':
                        this.buildings.defense++;
                        break;
                }
            }
        }
    }
    
    /**
     * Calculate trends and add to history
     */
    calculateTrends() {
        const now = Date.now();
        
        // Add current data to history
        this.history.credits.push({
            value: this.resources.credits,
            time: now
        });
        
        this.history.income.push({
            value: this.resources.income,
            time: now
        });
        
        this.history.expenses.push({
            value: this.resources.expenses,
            time: now
        });
        
        // Limit history size
        const maxHistory = this.history.maxHistory;
        if (this.history.credits.length > maxHistory) {
            this.history.credits = this.history.credits.slice(-maxHistory);
        }
        if (this.history.income.length > maxHistory) {
            this.history.income = this.history.income.slice(-maxHistory);
        }
        if (this.history.expenses.length > maxHistory) {
            this.history.expenses = this.history.expenses.slice(-maxHistory);
        }
    }
    
    /**
     * Check for resource warnings
     */
    checkWarnings() {
        this.warnings.clear();
        
        // Low credits warning
        if (this.resources.credits < this.config.warningThresholds.lowCredits) {
            this.warnings.add(`Low credits: ${this.formatCredits(this.resources.credits)}`);
        }
        
        // Low power warning
        const powerPercent = this.resources.power > 0 ? 
            (this.resources.powerUsed / this.resources.power) * 100 : 100;
        if (powerPercent > 80) {
            this.warnings.add(`High power usage: ${powerPercent.toFixed(0)}%`);
        }
        
        // Low income warning
        if (this.resources.netIncome < this.config.warningThresholds.lowIncome) {
            this.warnings.add(`Low income: ${this.formatCredits(this.resources.netIncome)}/min`);
        }
        
        // No harvesters warning
        if (this.harvestStats.total === 0) {
            this.warnings.add('No harvesters deployed');
        } else if (this.harvestStats.active === 0) {
            this.warnings.add('All harvesters idle');
        }
        
        // Power shortage warning
        if (this.resources.powerUsed > this.resources.power) {
            this.warnings.add('Power shortage detected');
        }
    }
    
    /**
     * Update all UI elements
     */
    updateUI() {
        if (!this.isVisible || this.isDestroyed) return;
        
        // Update credits
        this.updateCreditsDisplay();
        
        // Update power display
        this.updatePowerDisplay();
        
        // Update income display
        this.updateIncomeDisplay();
        
        // Update harvester display
        this.updateHarvesterDisplay();
        
        // Update building counts
        this.updateBuildingDisplay();
        
        // Update warnings
        this.updateWarningsDisplay();
        
        // Update predictions if enabled
        if (this.config.enablePredictions) {
            this.updatePredictionsDisplay();
        }
        
        this.stats.domUpdates++;
    }
    
    /**
     * Update credits display
     */
    updateCreditsDisplay() {
        if (!this.elements.creditsValue) return;
        
        const formattedCredits = this.formatCredits(this.resources.credits);
        
        // Use UIUpdateManager for smooth updates
        this.uiUpdateManager.queueTextUpdate('credits-value', formattedCredits);
        
        // Update trend
        if (this.elements.creditsTrend) {
            const trend = this.resources.netIncome >= 0 ? '+' : '';
            const formattedTrend = `${trend}${this.formatCredits(this.resources.netIncome)}/min`;
            this.uiUpdateManager.queueTextUpdate('credits-trend', formattedTrend);
        }
        
        // Update status indicator
        this.updateStatusIndicator('credits-status', this.getCreditsStatus());
        
        // Add pulse animation if credits changed significantly
        if (this.config.enableAnimations) {
            this.animateValueChange('credits-value');
        }
    }
    
    /**
     * Update power display
     */
    updatePowerDisplay() {
        if (!this.elements.powerValue) return;
        
        const powerText = `${this.resources.powerUsed}/${this.resources.power}`;
        this.uiUpdateManager.queueTextUpdate('power-value', powerText);
        
        // Update power bar
        const powerPercent = this.resources.power > 0 ? 
            (this.resources.powerUsed / this.resources.power) * 100 : 0;
        
        if (this.elements.powerBarFill) {
            this.uiUpdateManager.queueStyleChange('power-bar-fill', {
                width: `${Math.min(100, powerPercent)}%`
            });
        }
        
        // Update status
        this.updateStatusIndicator('power-status', this.getPowerStatus());
    }
    
    /**
     * Update income display
     */
    updateIncomeDisplay() {
        if (!this.elements.incomeValue) return;
        
        const formattedIncome = `+${this.formatCredits(this.resources.income)}/min`;
        this.uiUpdateManager.queueTextUpdate('income-value', formattedIncome);
        
        // Update breakdown
        if (this.elements.incomeBreakdown) {
            const harvesterIncome = this.formatCredits(this.harvestStats.incomeRate);
            this.uiUpdateManager.queueTextUpdate('income-breakdown', `Harvesters: ${harvesterIncome}`);
        }
        
        // Update status
        this.updateStatusIndicator('income-status', this.getIncomeStatus());
    }
    
    /**
     * Update harvester display
     */
    updateHarvesterDisplay() {
        if (!this.elements.harvestersCount) return;
        
        this.uiUpdateManager.queueTextUpdate('harvesters-count', 
            `${this.harvestStats.active + this.harvestStats.returning}/${this.harvestStats.total}`);
        
        this.uiUpdateManager.queueTextUpdate('harvesters-active', 
            this.harvestStats.active.toString());
        
        this.uiUpdateManager.queueTextUpdate('harvesters-idle', 
            this.harvestStats.idle.toString());
        
        this.uiUpdateManager.queueTextUpdate('harvesters-efficiency', 
            `${this.harvestStats.efficiency}%`);
        
        // Update status
        this.updateStatusIndicator('harvesters-status', this.getHarvestersStatus());
    }
    
    /**
     * Update building display
     */
    updateBuildingDisplay() {
        this.uiUpdateManager.queueTextUpdate('power-plants-count', 
            this.buildings.powerPlants.toString());
        
        this.uiUpdateManager.queueTextUpdate('refineries-count', 
            this.buildings.refineries.toString());
        
        this.uiUpdateManager.queueTextUpdate('factories-count', 
            this.buildings.factories.toString());
    }
    
    /**
     * Update warnings display
     */
    updateWarningsDisplay() {
        if (!this.elements.warningsSection) return;
        
        if (this.warnings.size > 0) {
            this.elements.warningsSection.style.display = 'block';
            
            const warningText = Array.from(this.warnings).join('<br>');
            this.uiUpdateManager.queueTextUpdate('warning-list', warningText);
        } else {
            this.elements.warningsSection.style.display = 'none';
        }
    }
    
    /**
     * Update predictions display
     */
    updatePredictionsDisplay() {
        if (!this.elements.predictionsSection) return;
        
        // Calculate credit prediction for 5 minutes
        const creditsIn5Min = this.resources.credits + (this.resources.netIncome * 5);
        
        this.uiUpdateManager.queueTextUpdate('credits-prediction', 
            this.formatCredits(creditsIn5Min));
        
        this.elements.predictionsSection.style.display = 'block';
    }
    
    /**
     * Update status indicator
     */
    updateStatusIndicator(elementId, status) {
        const statusClass = status === 'good' ? 'good' : 
                           status === 'warning' ? 'warning' : 'critical';
        
        this.uiUpdateManager.queueClassChange(elementId, {
            remove: ['good', 'warning', 'critical'],
            add: [statusClass]
        });
    }
    
    /**
     * Animate value change
     */
    animateValueChange(elementId) {
        this.uiUpdateManager.queueClassChange(elementId, {
            add: ['updating']
        });
        
        setTimeout(() => {
            this.uiUpdateManager.queueClassChange(elementId, {
                remove: ['updating']
            });
        }, 500);
    }
    
    /**
     * Get credits status
     */
    getCreditsStatus() {
        if (this.resources.credits < this.config.warningThresholds.lowCredits) {
            return 'critical';
        } else if (this.resources.netIncome < 0) {
            return 'warning';
        } else {
            return 'good';
        }
    }
    
    /**
     * Get power status
     */
    getPowerStatus() {
        if (this.resources.powerUsed > this.resources.power) {
            return 'critical';
        } else if ((this.resources.powerUsed / this.resources.power) > 0.8) {
            return 'warning';
        } else {
            return 'good';
        }
    }
    
    /**
     * Get income status
     */
    getIncomeStatus() {
        if (this.resources.netIncome < 0) {
            return 'critical';
        } else if (this.resources.netIncome < this.config.warningThresholds.lowIncome) {
            return 'warning';
        } else {
            return 'good';
        }
    }
    
    /**
     * Get harvesters status
     */
    getHarvestersStatus() {
        if (this.harvestStats.total === 0) {
            return 'critical';
        } else if (this.harvestStats.efficiency < 50) {
            return 'warning';
        } else {
            return 'good';
        }
    }
    
    /**
     * Format credits with thousands separator
     */
    formatCredits(amount) {
        const { currency, useThousandsSeparator, showDecimals } = this.config.formatOptions;
        
        let formatted = showDecimals ? 
            amount.toFixed(2) : 
            Math.round(amount).toString();
        
        if (useThousandsSeparator) {
            formatted = formatted.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        }
        
        return `${currency}${formatted}`;
    }
    
    /**
     * Toggle minimize state
     */
    toggleMinimize() {
        const isMinimized = this.elements.container.classList.contains('minimized');
        
        if (isMinimized) {
            this.elements.container.classList.remove('minimized');
            this.elements.minimizeBtn.textContent = '−';
        } else {
            this.elements.container.classList.add('minimized');
            this.elements.minimizeBtn.textContent = '+';
        }
    }
    
    /**
     * Toggle visibility
     */
    toggleVisibility() {
        this.isVisible = !this.isVisible;
        this.elements.container.style.display = this.isVisible ? 'block' : 'none';
    }
    
    /**
     * Get current performance statistics
     */
    getStats() {
        return {
            ...this.stats,
            warnings: this.warnings.size,
            harvesters: this.harvestStats.total,
            buildings: Object.values(this.buildings).reduce((a, b) => a + b, 0)
        };
    }
    
    /**
     * Update configuration
     */
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        console.log('⚙️  ResourceEconomyUI config updated');
    }
    
    /**
     * Force immediate update
     */
    forceUpdate() {
        this.updateResources();
    }
    
    /**
     * Destroy and cleanup
     */
    destroy() {
        if (this.isDestroyed) return;
        
        console.log('🗑️ Destroying ResourceEconomyUI...');
        this.isDestroyed = true;
        
        // Remove DOM elements
        if (this.elements.container) {
            this.elements.container.remove();
        }
        
        // Clear data structures
        this.harvesters.clear();
        this.warnings.clear();
        this.history.credits = [];
        this.history.income = [];
        this.history.expenses = [];
        
        console.log('✅ ResourceEconomyUI destroyed successfully');
    }
}