#!/usr/bin/env node

/**
 * Test Runner for Map Generation System
 * 
 * This script provides a simple interface to run the comprehensive
 * map generation test suite with various options.
 * 
 * Usage:
 *   node runTests.js [options]
 * 
 * Options:
 *   --all              Run all tests (default)
 *   --wfc              Run only WFC tests
 *   --symmetric        Run only symmetric map tests
 *   --resources        Run only resource distribution tests
 *   --performance      Run only performance tests
 *   --quality          Run only quality tests
 *   --demo             Run demonstration examples
 *   --quick            Run a quick subset of tests
 *   --export-results   Export results to JSON file
 *   --verbose          Enable verbose output
 *   --help             Show this help message
 */

import MapGenerationTests, { MapGenerationDemo } from './MapGenerationTests.js';
import { writeFileSync } from 'fs';
import { join } from 'path';

class TestRunner {
    constructor() {
        this.args = process.argv.slice(2);
        this.options = this.parseArguments();
    }

    parseArguments() {
        const options = {
            runAll: true,
            runWFC: false,
            runSymmetric: false,
            runResources: false,
            runPerformance: false,
            runQuality: false,
            runDemo: false,
            quick: false,
            exportResults: false,
            verbose: false,
            help: false
        };

        for (const arg of this.args) {
            switch (arg) {
                case '--all':
                    options.runAll = true;
                    break;
                case '--wfc':
                    options.runAll = false;
                    options.runWFC = true;
                    break;
                case '--symmetric':
                    options.runAll = false;
                    options.runSymmetric = true;
                    break;
                case '--resources':
                    options.runAll = false;
                    options.runResources = true;
                    break;
                case '--performance':
                    options.runAll = false;
                    options.runPerformance = true;
                    break;
                case '--quality':
                    options.runAll = false;
                    options.runQuality = true;
                    break;
                case '--demo':
                    options.runDemo = true;
                    break;
                case '--quick':
                    options.quick = true;
                    options.runAll = false;
                    break;
                case '--export-results':
                    options.exportResults = true;
                    break;
                case '--verbose':
                    options.verbose = true;
                    break;
                case '--help':
                    options.help = true;
                    break;
                default:
                    console.warn(`Unknown option: ${arg}`);
            }
        }

        return options;
    }

    showHelp() {
        console.log(`
Map Generation Test Runner
==========================

Usage: node runTests.js [options]

Options:
  --all              Run all tests (default)
  --wfc              Run only Wave Function Collapse tests
  --symmetric        Run only symmetric map balance tests
  --resources        Run only resource distribution tests
  --performance      Run only performance benchmarks
  --quality          Run only map quality tests
  --demo             Run demonstration examples
  --quick            Run a quick subset of tests
  --export-results   Export results to JSON file
  --verbose          Enable verbose output
  --help             Show this help message

Examples:
  node runTests.js                    # Run all tests
  node runTests.js --wfc --resources  # Run specific test suites
  node runTests.js --demo             # Run demonstration
  node runTests.js --quick            # Quick test run
  node runTests.js --performance --export-results  # Performance tests + export
`);
    }

    async runSelectedTests() {
        const testOptions = {
            enablePerformanceTesting: this.options.runAll || this.options.runPerformance,
            generateExampleMaps: this.options.runAll || this.options.runDemo,
            enableVisualization: false, // Disable for CLI
        };

        // Adjust for quick tests
        if (this.options.quick) {
            testOptions.testMapSizes = [{ width: 20, height: 15, name: 'small' }];
            testOptions.playerCountTests = [2, 4];
            testOptions.algorithmTests = ['wfc', 'symmetric'];
            testOptions.climateTests = ['temperate'];
        }

        const tester = new MapGenerationTests(testOptions);
        let results;

        if (this.options.runAll) {
            console.log('🚀 Running Complete Test Suite');
            results = await tester.runAllTests();
        } else {
            console.log('🚀 Running Selected Test Suites');
            
            if (this.options.runWFC) {
                await tester.runWFCTests();
            }
            
            if (this.options.runSymmetric) {
                await tester.runSymmetricMapTests();
            }
            
            if (this.options.runResources) {
                await tester.runResourceDistributionTests();
            }
            
            if (this.options.runPerformance) {
                await tester.runPerformanceTests();
            }
            
            if (this.options.runQuality) {
                await tester.runMapQualityTests();
            }

            if (this.options.quick) {
                // Run a subset of each test suite
                await tester.runWFCTests();
                await tester.runSymmetricMapTests();
                await tester.runResourceDistributionTests();
            }

            await tester.generateTestReport();
            results = tester.testResults;
        }

        return results;
    }

    async runDemo() {
        console.log('🎮 Running Map Generation Demonstration');
        const demo = new MapGenerationDemo();
        await demo.runQuickDemo();
    }

    exportResults(results) {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `test-results-${timestamp}.json`;
        const filepath = join(process.cwd(), filename);
        
        const exportData = {
            timestamp: new Date().toISOString(),
            testResults: results,
            systemInfo: {
                nodeVersion: process.version,
                platform: process.platform,
                arch: process.arch,
                memory: process.memoryUsage()
            }
        };

        try {
            writeFileSync(filepath, JSON.stringify(exportData, null, 2));
            console.log(`\n📄 Results exported to: ${filename}`);
        } catch (error) {
            console.error(`❌ Failed to export results: ${error.message}`);
        }
    }

    async run() {
        try {
            if (this.options.help) {
                this.showHelp();
                return;
            }

            if (this.options.runDemo) {
                await this.runDemo();
                return;
            }

            const results = await this.runSelectedTests();

            if (this.options.exportResults) {
                this.exportResults(results);
            }

            // Exit with appropriate code
            const totalTests = results.overall.passed + results.overall.failed;
            const hasFailures = results.overall.failed > 0;
            
            if (hasFailures) {
                console.log('\n⚠️  Some tests failed. Check the output above for details.');
                process.exit(1);
            } else {
                console.log('\n🎉 All tests passed successfully!');
                process.exit(0);
            }

        } catch (error) {
            console.error('\n❌ Test runner failed:', error);
            console.error(error.stack);
            process.exit(1);
        }
    }
}

// Performance monitoring
function setupPerformanceMonitoring() {
    const startTime = process.hrtime();
    const startMemory = process.memoryUsage();

    process.on('exit', () => {
        const [seconds, nanoseconds] = process.hrtime(startTime);
        const endMemory = process.memoryUsage();
        const totalTime = seconds + nanoseconds / 1e9;

        console.log('\n📊 Performance Summary:');
        console.log(`Total execution time: ${totalTime.toFixed(3)}s`);
        console.log(`Peak memory usage: ${(endMemory.heapUsed / 1024 / 1024).toFixed(2)}MB`);
        console.log(`Memory growth: ${((endMemory.heapUsed - startMemory.heapUsed) / 1024 / 1024).toFixed(2)}MB`);
    });
}

// Main execution
if (import.meta.url === `file://${process.argv[1]}`) {
    setupPerformanceMonitoring();
    
    const runner = new TestRunner();
    runner.run().catch(error => {
        console.error('Unhandled error:', error);
        process.exit(1);
    });
}

export default TestRunner;