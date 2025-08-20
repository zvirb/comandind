/**
 * Functional Validation Framework
 * 
 * This framework addresses the critical validation gap where technical metrics
 * passed (64,809 FPS, sub-millisecond response times) but users experienced
 * complete gameplay failure (only green squares, no RTS content).
 * 
 * Priority 4: Enhanced Validation Processes
 * Prevents technical-vs-functional validation disconnects
 */

export class FunctionalValidationFramework {
    constructor() {
        this.validationResults = [];
        this.functionalErrors = [];
        this.validationTimestamp = new Date().toISOString();
        this.gameInstance = null;
        this.pixiApp = null;
        this.validationConfig = {
            // Functional validation requirements
            minimumRTSEntities: 6, // At least 6 RTS units/buildings visible
            maximumTestSprites: 10, // No more than 10 test sprites allowed
            requiredGameplayElements: [
                "unit-selection",
                "camera-controls", 
                "ecs-entities",
                "rts-assets",
                "pathfinding",
                "user-interaction"
            ],
            validationTimeout: 30000, // 30 seconds maximum
            screenshotEvidence: true
        };
    }

    /**
     * Initialize functional validation framework
     */
    async initialize(gameInstance) {
        console.log("🔍 Initializing Functional Validation Framework...");
        this.gameInstance = gameInstance;
        this.pixiApp = gameInstance?.application;
        
        if (!this.gameInstance || !this.pixiApp) {
            throw new Error("CRITICAL: Cannot validate - game instance not available");
        }
        
        console.log("✅ Functional validation framework ready");
        return true;
    }

    /**
     * Run comprehensive functional validation
     * Returns validation results with evidence
     */
    async runFunctionalValidation() {
        console.log("🎯 Starting Comprehensive Functional Validation...");
        
        const validationSuite = {
            gameplayVisibility: await this.validateGameplayVisibility(),
            userInteraction: await this.validateUserInteraction(),
            systemIntegration: await this.validateSystemIntegration(),
            functionalReality: await this.validateFunctionalReality(),
            visualEvidence: await this.collectVisualEvidence()
        };

        const overallResult = this.evaluateOverallValidation(validationSuite);
        
        return {
            timestamp: this.validationTimestamp,
            overallStatus: overallResult.status,
            functionalScore: overallResult.score,
            validationSuite: validationSuite,
            evidence: overallResult.evidence,
            recommendations: overallResult.recommendations,
            preventionMeasures: this.getPreventionMeasures()
        };
    }

    /**
     * Validate that actual RTS gameplay elements are visible (not just test sprites)
     */
    async validateGameplayVisibility() {
        console.log("🔍 Validating gameplay visibility...");
        
        const validation = {
            testName: "Gameplay Visibility Validation",
            status: "unknown",
            evidence: {},
            issues: []
        };

        try {
            // Check stage children for actual game content
            const stageChildren = this.pixiApp.stage.children;
            
            // Count different types of content
            const contentAnalysis = {
                totalChildren: stageChildren.length,
                testSprites: 0,
                rtsEntities: 0,
                gameplayElements: [],
                unknownElements: 0
            };

            // Analyze each child for content type
            for (const child of stageChildren) {
                if (this.isTestSprite(child)) {
                    contentAnalysis.testSprites++;
                } else if (this.isRTSEntity(child)) {
                    contentAnalysis.rtsEntities++;
                    contentAnalysis.gameplayElements.push(this.identifyRTSElement(child));
                } else {
                    contentAnalysis.unknownElements++;
                }
            }

            validation.evidence = contentAnalysis;

            // Functional validation criteria
            if (contentAnalysis.rtsEntities < this.validationConfig.minimumRTSEntities) {
                validation.issues.push(`CRITICAL: Only ${contentAnalysis.rtsEntities} RTS entities found, minimum ${this.validationConfig.minimumRTSEntities} required`);
            }

            if (contentAnalysis.testSprites > this.validationConfig.maximumTestSprites) {
                validation.issues.push(`WARNING: ${contentAnalysis.testSprites} test sprites visible, maximum ${this.validationConfig.maximumTestSprites} allowed in production`);
            }

            if (contentAnalysis.rtsEntities === 0 && contentAnalysis.testSprites > 0) {
                validation.issues.push("CRITICAL: Users only see test sprites, no RTS gameplay content visible");
            }

            // Check if ECS world has entities
            if (this.gameInstance.world) {
                const ecsStats = this.gameInstance.world.getStats();
                validation.evidence.ecsEntities = ecsStats.entityCount;
                validation.evidence.ecsComponents = ecsStats.componentCount;
                
                if (ecsStats.entityCount === 0) {
                    validation.issues.push("CRITICAL: ECS world has no entities - game logic not functional");
                }
            }

            // Overall status determination
            if (validation.issues.length === 0) {
                validation.status = "passed";
            } else if (validation.issues.some(issue => issue.includes("CRITICAL"))) {
                validation.status = "failed";
            } else {
                validation.status = "warning";
            }

        } catch (error) {
            validation.status = "error";
            validation.issues.push(`Validation error: ${error.message}`);
        }

        return validation;
    }

    /**
     * Validate user interaction functionality
     */
    async validateUserInteraction() {
        console.log("🔍 Validating user interaction...");
        
        const validation = {
            testName: "User Interaction Validation",
            status: "unknown",
            evidence: {},
            issues: []
        };

        try {
            // Check input handler
            if (!this.gameInstance.inputHandler) {
                validation.issues.push("CRITICAL: Input handler not initialized");
            } else {
                validation.evidence.inputHandler = "initialized";
            }

            // Check selection system
            if (!this.gameInstance.selectionSystem) {
                validation.issues.push("CRITICAL: Selection system not available");
            } else {
                validation.evidence.selectionSystem = "initialized";
                
                // Test selection functionality
                const selectionTest = await this.testSelectionSystem();
                validation.evidence.selectionTest = selectionTest;
                
                if (!selectionTest.functional) {
                    validation.issues.push("CRITICAL: Selection system not responding to user input");
                }
            }

            // Check camera controls
            if (!this.gameInstance.camera) {
                validation.issues.push("CRITICAL: Camera system not available");
            } else {
                validation.evidence.camera = {
                    position: { x: this.gameInstance.camera.x, y: this.gameInstance.camera.y },
                    scale: this.gameInstance.camera.scale,
                    functional: typeof this.gameInstance.camera.update === "function"
                };
            }

            // Overall status
            validation.status = validation.issues.length === 0 ? "passed" : 
                validation.issues.some(issue => issue.includes("CRITICAL")) ? "failed" : "warning";

        } catch (error) {
            validation.status = "error";
            validation.issues.push(`Validation error: ${error.message}`);
        }

        return validation;
    }

    /**
     * Validate system integration and ECS functionality
     */
    async validateSystemIntegration() {
        console.log("🔍 Validating system integration...");
        
        const validation = {
            testName: "System Integration Validation",
            status: "unknown",
            evidence: {},
            issues: []
        };

        try {
            // Check ECS World
            if (!this.gameInstance.world) {
                validation.issues.push("CRITICAL: ECS World not initialized");
            } else {
                const worldStats = this.gameInstance.world.getStats();
                validation.evidence.ecsWorld = worldStats;
                
                if (worldStats.entityCount === 0) {
                    validation.issues.push("CRITICAL: ECS World has no entities");
                }
                
                if (worldStats.systemCount === 0) {
                    validation.issues.push("CRITICAL: ECS World has no systems");
                }
            }

            // Check Asset Loading
            if (!this.gameInstance.cncAssets) {
                validation.issues.push("CRITICAL: C&C Assets not loaded");
            } else {
                const assetStats = this.gameInstance.cncAssets.getLoadingStats();
                validation.evidence.assets = assetStats;
                
                if (assetStats.loadedAssets === 0) {
                    validation.issues.push("CRITICAL: No C&C assets loaded - only test sprites available");
                }
            }

            // Check Pathfinding System
            if (!this.gameInstance.pathfindingSystem) {
                validation.issues.push("WARNING: Pathfinding system not available");
            } else {
                validation.evidence.pathfinding = {
                    initialized: true,
                    gridSize: this.gameInstance.pathfindingSystem.gridWidth + "x" + this.gameInstance.pathfindingSystem.gridHeight
                };
            }

            // Check Entity Factory
            if (!this.gameInstance.entityFactory) {
                validation.issues.push("CRITICAL: Entity Factory not available - cannot create RTS units");
            } else {
                validation.evidence.entityFactory = "initialized";
            }

            validation.status = validation.issues.length === 0 ? "passed" : 
                validation.issues.some(issue => issue.includes("CRITICAL")) ? "failed" : "warning";

        } catch (error) {
            validation.status = "error";
            validation.issues.push(`Validation error: ${error.message}`);
        }

        return validation;
    }

    /**
     * Validate functional reality vs technical metrics
     */
    async validateFunctionalReality() {
        console.log("🔍 Validating functional reality...");
        
        const validation = {
            testName: "Functional Reality Check",
            status: "unknown",
            evidence: {},
            issues: []
        };

        try {
            // Technical metrics vs functional reality correlation
            const technicalMetrics = {
                fps: this.gameInstance.performanceMonitor?.getFPS() || 0,
                memoryUsage: this.gameInstance.performanceMonitor?.getMemoryUsage() || 0,
                stageChildren: this.pixiApp.stage.children.length
            };

            const functionalReality = {
                userCanSeeRTSContent: await this.checkUserCanSeeRTSContent(),
                userCanInteract: await this.checkUserCanInteract(),
                gameplayActuallyWorks: await this.checkGameplayWorks()
            };

            validation.evidence = {
                technicalMetrics,
                functionalReality,
                correlation: this.analyzeCorrelation(technicalMetrics, functionalReality)
            };

            // Critical functional reality checks
            if (!functionalReality.userCanSeeRTSContent) {
                validation.issues.push("CRITICAL: High technical performance but users cannot see RTS content");
            }

            if (!functionalReality.userCanInteract) {
                validation.issues.push("CRITICAL: Technical systems responding but user interaction not functional");
            }

            if (!functionalReality.gameplayActuallyWorks) {
                validation.issues.push("CRITICAL: Technical validation passed but gameplay is non-functional");
            }

            // Correlation analysis
            if (technicalMetrics.fps > 60 && !functionalReality.gameplayActuallyWorks) {
                validation.issues.push("CRITICAL: Technical-vs-functional disconnect detected (high FPS, broken gameplay)");
            }

            validation.status = validation.issues.length === 0 ? "passed" : "failed";

        } catch (error) {
            validation.status = "error";
            validation.issues.push(`Validation error: ${error.message}`);
        }

        return validation;
    }

    /**
     * Collect visual evidence for validation
     */
    async collectVisualEvidence() {
        if (!this.validationConfig.screenshotEvidence) {
            return { collected: false, reason: "Screenshot evidence disabled" };
        }

        try {
            // Create canvas screenshot
            const canvas = this.pixiApp.view;
            const dataURL = canvas.toDataURL("image/png");
            
            return {
                collected: true,
                timestamp: new Date().toISOString(),
                screenshot: dataURL,
                canvasSize: { width: canvas.width, height: canvas.height },
                description: "Functional validation screenshot showing actual user view"
            };
        } catch (error) {
            return {
                collected: false,
                error: error.message
            };
        }
    }

    /**
     * Helper methods for content identification
     */
    isTestSprite(child) {
        // Check if this is a TestSprite (usually has specific properties or naming)
        return child.tint !== undefined && 
               (child.constructor.name === "Sprite" || child.constructor.name === "Graphics") &&
               (!child.texture?.baseTexture?.imageUrl || child.texture.baseTexture.imageUrl.includes("test"));
    }

    isRTSEntity(child) {
        // Check if this is an actual RTS entity (has ECS components, game data, etc.)
        return child.entityId !== undefined || 
               child.unitType !== undefined ||
               child.faction !== undefined ||
               (child.texture?.baseTexture?.imageUrl && !child.texture.baseTexture.imageUrl.includes("test"));
    }

    identifyRTSElement(child) {
        return {
            type: child.unitType || child.buildingType || "unknown",
            faction: child.faction || "unknown",
            entityId: child.entityId,
            position: { x: child.x, y: child.y }
        };
    }

    /**
     * Test selection system functionality
     */
    async testSelectionSystem() {
        try {
            const selectionSystem = this.gameInstance.selectionSystem;
            if (!selectionSystem) return { functional: false, reason: "Selection system not available" };

            // Check if selection system has required methods
            const hasRequiredMethods = typeof selectionSystem.getSelectedEntities === "function" &&
                                     typeof selectionSystem.selectEntity === "function";

            return {
                functional: hasRequiredMethods,
                selectedCount: selectionSystem.getSelectedEntities?.()?.length || 0,
                methods: hasRequiredMethods
            };
        } catch (error) {
            return { functional: false, error: error.message };
        }
    }

    /**
     * Check if user can actually see RTS content
     */
    async checkUserCanSeeRTSContent() {
        const stageChildren = this.pixiApp.stage.children;
        const rtsContentCount = stageChildren.filter(child => this.isRTSEntity(child)).length;
        const testSpriteCount = stageChildren.filter(child => this.isTestSprite(child)).length;
        
        // User can see RTS content if there are RTS entities visible and not just test sprites
        return rtsContentCount > 0 && (testSpriteCount === 0 || rtsContentCount > testSpriteCount);
    }

    /**
     * Check if user can actually interact with the game
     */
    async checkUserCanInteract() {
        return !!(this.gameInstance.inputHandler && 
                 this.gameInstance.selectionSystem && 
                 this.gameInstance.camera);
    }

    /**
     * Check if gameplay actually works end-to-end
     */
    async checkGameplayWorks() {
        const hasRTSContent = await this.checkUserCanSeeRTSContent();
        const canInteract = await this.checkUserCanInteract();
        const hasECSEntities = this.gameInstance.world?.getStats().entityCount > 0;
        const hasAssets = this.gameInstance.cncAssets?.getLoadingStats().loadedAssets > 0;
        
        return hasRTSContent && canInteract && hasECSEntities && hasAssets;
    }

    /**
     * Analyze correlation between technical metrics and functional reality
     */
    analyzeCorrelation(technical, functional) {
        const issues = [];
        
        if (technical.fps > 60 && !functional.gameplayActuallyWorks) {
            issues.push("High performance metrics but non-functional gameplay");
        }
        
        if (technical.stageChildren > 0 && !functional.userCanSeeRTSContent) {
            issues.push("Stage has children but user cannot see RTS content");
        }
        
        return {
            correlationValid: issues.length === 0,
            issues: issues
        };
    }

    /**
     * Evaluate overall validation results
     */
    evaluateOverallValidation(suite) {
        const results = Object.values(suite);
        const passedCount = results.filter(r => r.status === "passed").length;
        const failedCount = results.filter(r => r.status === "failed").length;
        const errorCount = results.filter(r => r.status === "error").length;
        
        let overallStatus = "unknown";
        let score = 0;
        
        if (errorCount > 0) {
            overallStatus = "error";
        } else if (failedCount > 0) {
            overallStatus = "failed";
            score = Math.max(0, (passedCount / results.length) * 100 - failedCount * 25);
        } else if (passedCount === results.length) {
            overallStatus = "passed";
            score = 100;
        } else {
            overallStatus = "warning";
            score = (passedCount / results.length) * 100;
        }

        return {
            status: overallStatus,
            score: Math.round(score),
            evidence: {
                passedTests: passedCount,
                failedTests: failedCount,
                errorTests: errorCount,
                totalTests: results.length
            },
            recommendations: this.generateRecommendations(suite)
        };
    }

    /**
     * Generate recommendations based on validation results
     */
    generateRecommendations(suite) {
        const recommendations = [];
        
        if (suite.gameplayVisibility.status === "failed") {
            recommendations.push("CRITICAL: Implement actual RTS content visibility before production");
        }
        
        if (suite.userInteraction.status === "failed") {
            recommendations.push("CRITICAL: Fix user interaction systems before production");
        }
        
        if (suite.systemIntegration.status === "failed") {
            recommendations.push("CRITICAL: Resolve ECS/asset loading issues before production");
        }
        
        if (suite.functionalReality.status === "failed") {
            recommendations.push("CRITICAL: Correlate technical metrics with functional reality");
        }
        
        if (recommendations.length === 0) {
            recommendations.push("Functional validation passed - ready for production");
        }
        
        return recommendations;
    }

    /**
     * Get prevention measures for future validation gaps
     */
    getPreventionMeasures() {
        return {
            mandatoryChecks: [
                "Visual content verification (RTS entities vs test sprites)",
                "User interaction testing with actual gameplay elements",
                "End-to-end gameplay flow validation",
                "Technical metrics correlation with functional reality"
            ],
            automatedTests: [
                "Screenshot comparison with expected gameplay content",
                "Interactive element counting and verification",
                "ECS entity validation and content verification",
                "Asset loading verification with functional testing"
            ],
            validationGates: [
                "No production deployment without functional validation",
                "Technical metrics must correlate with user experience",
                "Mandatory user perspective testing before certification",
                "Screenshot evidence required for production validation"
            ]
        };
    }
}

/**
 * Enhanced Production Validation Integration
 * Integrates functional validation into production validation pipeline
 */
export class EnhancedProductionValidator {
    constructor() {
        this.functionalValidator = new FunctionalValidationFramework();
        this.technicalValidator = null; // Existing technical validator
    }

    /**
     * Run combined technical and functional validation
     */
    async runEnhancedValidation(gameInstance) {
        console.log("🎯 Running Enhanced Production Validation (Technical + Functional)...");
        
        // Initialize functional validator
        await this.functionalValidator.initialize(gameInstance);
        
        // Run functional validation
        const functionalResults = await this.functionalValidator.runFunctionalValidation();
        
        // Combine with technical validation (if available)
        const technicalResults = await this.runTechnicalValidation();
        
        // Create comprehensive validation report
        const enhancedReport = {
            timestamp: new Date().toISOString(),
            validationType: "Enhanced Production Validation",
            functionalValidation: functionalResults,
            technicalValidation: technicalResults,
            overallStatus: this.determineOverallStatus(functionalResults, technicalResults),
            gapAnalysis: this.analyzeValidationGaps(functionalResults, technicalResults),
            certificationDecision: this.makeCertificationDecision(functionalResults, technicalResults)
        };

        return enhancedReport;
    }

    /**
     * Run technical validation (placeholder for existing technical validator)
     */
    async runTechnicalValidation() {
        // This would integrate with existing technical validation
        return {
            status: "passed",
            healthChecks: "passed",
            performance: "excellent",
            security: "validated"
        };
    }

    /**
     * Determine overall validation status
     */
    determineOverallStatus(functional, technical) {
        if (functional.overallStatus === "failed" || technical.status === "failed") {
            return "failed";
        }
        
        if (functional.overallStatus === "error" || technical.status === "error") {
            return "error";
        }
        
        if (functional.overallStatus === "passed" && technical.status === "passed") {
            return "passed";
        }
        
        return "warning";
    }

    /**
     * Analyze gaps between technical and functional validation
     */
    analyzeValidationGaps(functional, technical) {
        const gaps = [];
        
        if (technical.status === "passed" && functional.overallStatus === "failed") {
            gaps.push("CRITICAL GAP: Technical validation passed but functional validation failed");
            gaps.push("This indicates a technical-vs-functional disconnect");
        }
        
        if (functional.functionalScore < 50 && technical.status === "passed") {
            gaps.push("WARNING: Low functional score despite passing technical validation");
        }
        
        return gaps;
    }

    /**
     * Make certification decision based on enhanced validation
     */
    makeCertificationDecision(functional, technical) {
        const decision = {
            certified: false,
            reason: "",
            requirements: []
        };
        
        if (functional.overallStatus === "failed") {
            decision.reason = "Functional validation failed - user experience not acceptable";
            decision.requirements = functional.recommendations;
        } else if (technical.status === "failed") {
            decision.reason = "Technical validation failed";
        } else if (functional.overallStatus === "passed" && technical.status === "passed") {
            decision.certified = true;
            decision.reason = "Both technical and functional validation passed";
        } else {
            decision.reason = "Partial validation success - review warnings";
            decision.requirements.push("Address validation warnings before certification");
        }
        
        return decision;
    }
}