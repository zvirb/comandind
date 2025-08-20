/**
 * Circuit Breaker Authentication Flow Test
 * Tests the complete authentication flow with circuit breaker protection
 */

const fetch = require('node-fetch');

class CircuitBreakerAuthFlowTest {
  constructor() {
    this.baseUrl = 'http://localhost:8000';
    this.results = {
      tests: [],
      summary: {
        total: 0,
        passed: 0,
        failed: 0
      }
    };
  }

  async test(name, testFn) {
    this.results.summary.total++;
    console.log(`\n🧪 Testing: ${name}`);
    
    try {
      const result = await testFn();
      this.results.tests.push({ name, status: 'PASSED', result });
      this.results.summary.passed++;
      console.log(`✅ PASSED: ${name}`);
      return result;
    } catch (error) {
      this.results.tests.push({ name, status: 'FAILED', error: error.message });
      this.results.summary.failed++;
      console.log(`❌ FAILED: ${name} - ${error.message}`);
      throw error;
    }
  }

  async testCircuitBreakerStatus() {
    return await this.test('Circuit Breaker Status Check', async () => {
      const response = await fetch(`${this.baseUrl}/api/v1/auth-circuit-breaker/status`);
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(`Status check failed: ${response.status}`);
      }
      
      if (data.circuit_breaker.state !== 'closed') {
        throw new Error(`Expected circuit to be closed, got: ${data.circuit_breaker.state}`);
      }
      
      return data;
    });
  }

  async testSessionValidation() {
    return await this.test('Session Validation Still Works', async () => {
      const response = await fetch(`${this.baseUrl}/api/v1/session/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(`Session validation failed: ${response.status}`);
      }
      
      // Should return valid response (even if not authenticated)
      if (!data.hasOwnProperty('valid')) {
        throw new Error('Session validation response missing valid field');
      }
      
      return data;
    });
  }

  async testWebGLEventProcessing() {
    return await this.test('WebGL Context Lost Event Processing', async () => {
      const response = await fetch(`${this.baseUrl}/api/v1/auth-circuit-breaker/notifications/webgl-context-lost`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: 'context_lost',
          additional_info: 'Test event for flow validation'
        })
      });
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(`WebGL event processing failed: ${response.status}`);
      }
      
      if (data.status !== 'success') {
        throw new Error(`WebGL event not processed successfully: ${data.message}`);
      }
      
      if (!data.is_performance_paused) {
        throw new Error('Performance pause should be active after WebGL event');
      }
      
      return data;
    });
  }

  async testPerformanceIssueHandling() {
    return await this.test('Performance Issue Handling', async () => {
      const response = await fetch(`${this.baseUrl}/api/v1/auth-circuit-breaker/notifications/performance-issue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          issue_type: 'auth_flooding',
          severity: 'medium',
          pause_duration: 3,
          description: 'Simulated auth flooding detection'
        })
      });
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(`Performance issue handling failed: ${response.status}`);
      }
      
      if (data.status !== 'success') {
        throw new Error(`Performance issue not handled successfully: ${data.message}`);
      }
      
      return data;
    });
  }

  async testCircuitBreakerReset() {
    return await this.test('Circuit Breaker Reset', async () => {
      const response = await fetch(`${this.baseUrl}/api/v1/auth-circuit-breaker/reset`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(`Circuit breaker reset failed: ${response.status}`);
      }
      
      if (data.circuit_breaker.state !== 'closed') {
        throw new Error(`Circuit should be closed after reset, got: ${data.circuit_breaker.state}`);
      }
      
      if (data.circuit_breaker.is_performance_paused) {
        throw new Error('Performance pause should be cleared after reset');
      }
      
      return data;
    });
  }

  async testCircuitBreakerHealth() {
    return await this.test('Circuit Breaker Health Check', async () => {
      const response = await fetch(`${this.baseUrl}/api/v1/auth-circuit-breaker/health`);
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }
      
      if (data.status !== 'healthy') {
        throw new Error(`Circuit breaker not healthy: ${data.status}`);
      }
      
      return data;
    });
  }

  async testAuthFlowWithCircuitBreaker() {
    return await this.test('Complete Auth Flow with Circuit Breaker Protection', async () => {
      // Simulate auth flow that would previously cause flooding
      const authAttempts = [];
      
      for (let i = 0; i < 5; i++) {
        const response = await fetch(`${this.baseUrl}/api/v1/session/validate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        authAttempts.push({
          attempt: i + 1,
          status: response.status,
          response: data
        });
        
        // Small delay between attempts
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      // All attempts should succeed (circuit breaker shouldn't interfere with normal auth)
      const failedAttempts = authAttempts.filter(attempt => attempt.status !== 200);
      if (failedAttempts.length > 0) {
        throw new Error(`${failedAttempts.length} auth attempts failed when circuit breaker should allow them`);
      }
      
      return authAttempts;
    });
  }

  async testFrontendProxyAccess() {
    return await this.test('Frontend Proxy Access to Circuit Breaker', async () => {
      const response = await fetch('http://localhost:3001/api/v1/auth-circuit-breaker/status');
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(`Frontend proxy access failed: ${response.status}`);
      }
      
      if (data.circuit_breaker.state !== 'closed') {
        throw new Error(`Circuit should be closed via frontend proxy, got: ${data.circuit_breaker.state}`);
      }
      
      return data;
    });
  }

  async runAllTests() {
    console.log('🚀 Starting Circuit Breaker Authentication Flow Tests\n');
    
    try {
      // Test 1: Basic circuit breaker functionality
      await this.testCircuitBreakerStatus();
      
      // Test 2: Session validation still works
      await this.testSessionValidation();
      
      // Test 3: WebGL event processing
      await this.testWebGLEventProcessing();
      
      // Test 4: Performance issue handling
      await this.testPerformanceIssueHandling();
      
      // Test 5: Circuit breaker reset (clears performance pause)
      await this.testCircuitBreakerReset();
      
      // Test 6: Health check
      await this.testCircuitBreakerHealth();
      
      // Test 7: Complete auth flow protection
      await this.testAuthFlowWithCircuitBreaker();
      
      // Test 8: Frontend proxy access
      await this.testFrontendProxyAccess();
      
    } catch (error) {
      console.log(`\n💥 Test execution failed: ${error.message}`);
    }
    
    this.printSummary();
    return this.results;
  }

  printSummary() {
    console.log('\n📊 TEST SUMMARY');
    console.log('================');
    console.log(`Total Tests: ${this.results.summary.total}`);
    console.log(`✅ Passed: ${this.results.summary.passed}`);
    console.log(`❌ Failed: ${this.results.summary.failed}`);
    console.log(`Success Rate: ${((this.results.summary.passed / this.results.summary.total) * 100).toFixed(1)}%`);
    
    if (this.results.summary.failed === 0) {
      console.log('\n🎉 ALL TESTS PASSED! Circuit Breaker Authentication Flow is working correctly.');
    } else {
      console.log('\n⚠️  Some tests failed. Please review the issues above.');
    }
    
    console.log('\n📋 DETAILED RESULTS:');
    this.results.tests.forEach(test => {
      const status = test.status === 'PASSED' ? '✅' : '❌';
      console.log(`${status} ${test.name}`);
      if (test.status === 'FAILED') {
        console.log(`   Error: ${test.error}`);
      }
    });
  }
}

// Run the tests
const tester = new CircuitBreakerAuthFlowTest();
tester.runAllTests().then(results => {
  process.exit(results.summary.failed === 0 ? 0 : 1);
}).catch(error => {
  console.error('Test runner failed:', error);
  process.exit(1);
});