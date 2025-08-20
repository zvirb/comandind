/**
 * PHASE 11: Production Validation & Health Monitoring
 * POST-TEXTURE-ATLAS-FIX COMPREHENSIVE VALIDATION
 * 
 * This script validates:
 * 1. Application Flow: Loading → Menu → Game
 * 2. Infrastructure Health & Performance
 * 3. Texture Atlas Manager with PIXI.js v7+ compatibility
 * 4. Error Handling & Recovery Mechanisms
 */

import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';
import { exec } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class ProductionValidator {
    constructor() {
        this.results = {
            timestamp: new Date().toISOString(),
            applicationFlow: {},
            infrastructure: {},
            performance: {},
            textureAtlas: {},
            errors: [],
            screenshots: [],
            overallScore: 0
        };
        this.evidenceDir = path.join(__dirname, 'evidence-collection', 'phase11-validation');
        this.ensureEvidenceDir();
    }

    ensureEvidenceDir() {
        if (!fs.existsSync(this.evidenceDir)) {
            fs.mkdirSync(this.evidenceDir, { recursive: true });
        }
    }

    async saveScreenshot(page, name) {
        const screenshotPath = path.join(this.evidenceDir, `${name}-${Date.now()}.png`);
        await page.screenshot({ 
            path: screenshotPath, 
            fullPage: true,
            type: 'png'
        });
        this.results.screenshots.push({
            name,
            path: screenshotPath,
            timestamp: new Date().toISOString()
        });
        console.log(`📸 Screenshot saved: ${screenshotPath}`);
        return screenshotPath;
    }

    async validateApplicationFlow() {
        console.log('\n🎮 VALIDATING APPLICATION FLOW POST-FIX...');
        
        const browser = await puppeteer.launch({
            headless: false,
            defaultViewport: { width: 1280, height: 720 },
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });

        try {
            const page = await browser.newPage();
            
            // Collect console logs and errors
            const consoleLogs = [];
            const errors = [];
            
            page.on('console', msg => {
                const text = msg.text();
                consoleLogs.push({
                    type: msg.type(),
                    text,
                    timestamp: new Date().toISOString()
                });
                console.log(`🔧 Console ${msg.type()}: ${text}`);
            });
            
            page.on('pageerror', err => {
                const error = {
                    message: err.message,
                    stack: err.stack,
                    timestamp: new Date().toISOString()
                };
                errors.push(error);
                console.log(`❌ Page Error: ${err.message}`);
            });

            // Navigate to application
            console.log('🌐 Loading application...');
            const response = await page.goto('http://localhost:3000', {
                waitUntil: 'domcontentloaded',
                timeout: 30000
            });

            this.results.applicationFlow.responseStatus = response.status();
            console.log(`📡 Response Status: ${response.status()}`);

            // Screenshot initial load
            await this.saveScreenshot(page, 'initial-load');

            // Wait for loading screen
            console.log('⏳ Waiting for loading screen...');
            await page.waitForSelector('.loading-screen, #loading-screen, .loader', {
                timeout: 10000
            }).catch(() => console.log('No loading screen found'));

            await this.saveScreenshot(page, 'loading-screen');

            // Wait for main menu to appear (critical path post-fix)
            console.log('🎯 Waiting for main menu transition...');
            const mainMenuFound = await page.waitForSelector('.main-menu, #main-menu, .menu-container', {
                timeout: 15000
            }).then(() => {
                console.log('✅ Main menu appeared successfully!');
                return true;
            }).catch(() => {
                console.log('❌ Main menu did not appear within timeout');
                return false;
            });

            this.results.applicationFlow.mainMenuTransition = mainMenuFound;

            if (mainMenuFound) {
                await this.saveScreenshot(page, 'main-menu-success');
                
                // Test menu interaction
                console.log('🖱️ Testing menu interactions...');
                const playButton = await page.$('.start-button, #start-button, button:contains("Play")').catch(() => null);
                
                if (playButton) {
                    await playButton.click();
                    await page.waitForTimeout(2000);
                    await this.saveScreenshot(page, 'game-start-attempt');
                    this.results.applicationFlow.gameStart = true;
                } else {
                    console.log('⚠️ No play button found');
                    this.results.applicationFlow.gameStart = false;
                }
            }

            // Check for texture atlas specific elements
            console.log('🖼️ Validating texture atlas loading...');
            const textureAtlasCheck = await page.evaluate(() => {
                // Look for PIXI application
                if (window.PIXI && window.app) {
                    return {
                        pixiVersion: PIXI.VERSION || 'unknown',
                        appExists: !!window.app,
                        rendererType: window.app.renderer?.type || 'unknown',
                        texturesLoaded: Object.keys(PIXI.utils.TextureCache || {}).length
                    };
                }
                return { error: 'PIXI not found' };
            });

            this.results.textureAtlas = textureAtlasCheck;
            console.log('📊 Texture Atlas Status:', JSON.stringify(textureAtlasCheck, null, 2));

            // Final screenshot
            await this.saveScreenshot(page, 'final-state');

            this.results.applicationFlow.consoleLogs = consoleLogs;
            this.results.errors = errors;

            // Calculate flow score
            let flowScore = 0;
            if (this.results.applicationFlow.responseStatus === 200) flowScore += 2;
            if (this.results.applicationFlow.mainMenuTransition) flowScore += 4;
            if (this.results.applicationFlow.gameStart) flowScore += 2;
            if (errors.length === 0) flowScore += 2;
            
            this.results.applicationFlow.score = flowScore;

        } finally {
            await browser.close();
        }
    }

    async validateInfrastructure() {
        console.log('\n🏗️ VALIDATING INFRASTRUCTURE HEALTH...');
        
        const infraChecks = {};
        
        // Memory usage
        console.log('🧠 Checking memory usage...');
        const memInfo = await this.runCommand('free -h');
        infraChecks.memory = memInfo;
        
        // CPU usage
        console.log('💻 Checking CPU usage...');
        const cpuInfo = await this.runCommand('top -bn1 | head -5');
        infraChecks.cpu = cpuInfo;
        
        // Disk space
        console.log('💽 Checking disk space...');
        const diskInfo = await this.runCommand('df -h /');
        infraChecks.disk = diskInfo;
        
        // Node.js process health
        console.log('🚀 Checking Node.js processes...');
        const nodeProcesses = await this.runCommand('ps aux | grep node | grep -v grep');
        infraChecks.nodeProcesses = nodeProcesses;
        
        // Port accessibility
        console.log('🌐 Checking port accessibility...');
        const portCheck = await this.runCommand('ss -tlnp | grep ":3000"');
        infraChecks.portCheck = portCheck;

        this.results.infrastructure = infraChecks;
        
        // Calculate infrastructure score
        let infraScore = 0;
        if (infraChecks.memory.includes('available')) infraScore += 2;
        if (infraChecks.nodeProcesses.includes('node')) infraScore += 2;
        if (infraChecks.portCheck.includes('3000')) infraScore += 2;
        
        this.results.infrastructure.score = infraScore;
    }

    async validatePerformance() {
        console.log('\n⚡ VALIDATING PERFORMANCE METRICS...');
        
        const performanceMetrics = {};
        
        // Response time test
        console.log('⏱️ Testing response times...');
        const startTime = Date.now();
        const curlResult = await this.runCommand('curl -o /dev/null -s -w "%{http_code},%{time_total},%{size_download}" http://localhost:3000');
        performanceMetrics.responseTime = curlResult;
        
        // Load test (simple)
        console.log('📊 Running basic load test...');
        const loadTestResults = [];
        for (let i = 0; i < 5; i++) {
            const testStart = Date.now();
            await this.runCommand('curl -s http://localhost:3000 > /dev/null');
            loadTestResults.push(Date.now() - testStart);
        }
        performanceMetrics.loadTest = {
            requests: 5,
            times: loadTestResults,
            average: loadTestResults.reduce((a, b) => a + b, 0) / loadTestResults.length
        };

        this.results.performance = performanceMetrics;
        
        // Calculate performance score
        let perfScore = 0;
        if (curlResult.includes('200')) perfScore += 2;
        if (performanceMetrics.loadTest.average < 1000) perfScore += 2;
        
        this.results.performance.score = perfScore;
    }

    async runCommand(command) {
        return new Promise((resolve) => {
            exec(command, (error, stdout, stderr) => {
                if (error) {
                    resolve(`Error: ${error.message}`);
                } else {
                    resolve(stdout || stderr || 'No output');
                }
            });
        });
    }

    async generateReport() {
        console.log('\n📊 GENERATING COMPREHENSIVE VALIDATION REPORT...');
        
        // Calculate overall score
        const scores = [
            this.results.applicationFlow.score || 0,
            this.results.infrastructure.score || 0,
            this.results.performance.score || 0
        ];
        
        this.results.overallScore = (scores.reduce((a, b) => a + b, 0) / 10) * 10; // Scale to 10
        
        const report = {
            ...this.results,
            summary: {
                totalErrors: this.results.errors.length,
                screenshotCount: this.results.screenshots.length,
                productionReady: this.results.overallScore >= 9.0,
                recommendations: this.generateRecommendations()
            }
        };
        
        const reportPath = path.join(this.evidenceDir, 'validation-report.json');
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
        
        console.log(`\n📋 VALIDATION REPORT SAVED: ${reportPath}`);
        console.log(`🏆 OVERALL SCORE: ${this.results.overallScore}/10`);
        console.log(`🚀 PRODUCTION READY: ${report.summary.productionReady ? 'YES' : 'NO'}`);
        
        return report;
    }
    
    generateRecommendations() {
        const recommendations = [];
        
        if (this.results.errors.length > 0) {
            recommendations.push('Address JavaScript errors found during validation');
        }
        
        if (!this.results.applicationFlow.mainMenuTransition) {
            recommendations.push('Critical: Main menu transition is failing - investigate texture atlas loading');
        }
        
        if (this.results.overallScore < 9.0) {
            recommendations.push('System not ready for production deployment - address validation failures');
        } else {
            recommendations.push('System validated - ready for production deployment');
        }
        
        return recommendations;
    }
}

// Main execution
async function main() {
    console.log('🚀 PHASE 11: PRODUCTION VALIDATION & HEALTH MONITORING');
    console.log('=' .repeat(60));
    
    const validator = new ProductionValidator();
    
    try {
        // Run all validations
        await validator.validateApplicationFlow();
        await validator.validateInfrastructure();
        await validator.validatePerformance();
        
        // Generate final report
        const report = await validator.generateReport();
        
        console.log('\n' + '='.repeat(60));
        console.log('🎯 PHASE 11 VALIDATION COMPLETE');
        console.log('=' .repeat(60));
        
        if (report.summary.productionReady) {
            console.log('✅ READY FOR PRODUCTION DEPLOYMENT');
            console.log('✅ PROCEED TO PHASE 12: TODO LOOP CONTROL');
        } else {
            console.log('❌ NOT READY FOR PRODUCTION');
            console.log('❌ RETURN TO PHASE 0 WITH FAILURE CONTEXT');
        }
        
        process.exit(report.summary.productionReady ? 0 : 1);
        
    } catch (error) {
        console.error('💥 VALIDATION FAILED:', error.message);
        process.exit(1);
    }
}

if (import.meta.url === `file://${process.argv[1]}`) {
    main();
}

export default ProductionValidator;