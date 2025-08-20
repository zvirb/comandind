const { test, expect } = require('@playwright/test');
const { chromium } = require('playwright');

// Performance tracking utility
class PerformanceTracker {
  constructor() {
    this.metrics = {
      pageLoadTime: null,
      chatInteractionTime: null,
      renderTime: null,
      networkRequests: []
    };
  }

  trackPageLoad(loadTime) {
    this.metrics.pageLoadTime = loadTime;
  }

  trackChatInteraction(interactionTime) {
    this.metrics.chatInteractionTime = interactionTime;
  }

  trackRenderPerformance(renderTime) {
    this.metrics.renderTime = renderTime;
  }

  recordNetworkRequests(requests) {
    this.metrics.networkRequests = requests;
  }

  generateReport() {
    return {
      pageLoadPerformance: this.metrics.pageLoadTime,
      chatInteractionPerformance: this.metrics.chatInteractionTime,
      renderPerformance: this.metrics.renderTime,
      networkHealthy: this.metrics.networkRequests.every(req => req.status < 400)
    };
  }
}

// User Experience Validation Test Suite
test.describe('AI Workflow Engine User Experience Validation', () => {
  let browser, page, performanceTracker;

  test.beforeAll(async () => {
    browser = await chromium.launch();
    performanceTracker = new PerformanceTracker();
  });

  test.afterAll(async () => {
    await browser.close();
  });

  test('Authentication Flow', async () => {
    const startTime = Date.now();
    page = await browser.newPage();
    
    // Navigate to login page
    await page.goto('https://aiwfe.com/login');
    
    // Validate login page elements
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    
    // Perform login
    await page.fill('input[name="username"]', process.env.TEST_USERNAME);
    await page.fill('input[name="password"]', process.env.TEST_PASSWORD);
    await page.click('button[type="submit"]');
    
    // Wait for dashboard to load
    await page.waitForSelector('.dashboard-container');
    
    const loginTime = Date.now() - startTime;
    performanceTracker.trackPageLoad(loginTime);
    
    // Validate dashboard access
    await expect(page.locator('.dashboard-container')).toBeVisible();
  });

  test('Chat Interface Functionality', async () => {
    const startTime = Date.now();
    
    // Navigate to chat interface
    await page.goto('https://aiwfe.com/chat');
    
    // Validate chat input and send functionality
    const chatInput = await page.locator('textarea[name="chat-input"]');
    await chatInput.fill('Hello, test message');
    await page.click('button[name="send-message"]');
    
    // Wait for message to be sent and response received
    await page.waitForSelector('.message-list .user-message');
    await page.waitForSelector('.message-list .ai-response');
    
    const chatInteractionTime = Date.now() - startTime;
    performanceTracker.trackChatInteraction(chatInteractionTime);
    
    // Validate message presence
    const messages = await page.locator('.message-list .message').all();
    expect(messages.length).toBeGreaterThan(1);
  });

  test('Performance and Rendering', async () => {
    const startTime = Date.now();
    
    // Navigate to dashboard with complex rendering
    await page.goto('https://aiwfe.com/dashboard');
    
    // Wait for WebGL/Three.js components to render
    await page.waitForSelector('.galaxy-constellation');
    
    const renderTime = Date.now() - startTime;
    performanceTracker.trackRenderPerformance(renderTime);
    
    // Capture network requests
    const networkRequests = await page.context().requests();
    performanceTracker.recordNetworkRequests(networkRequests);
  });

  test('Error Handling and Recovery', async () => {
    // Simulate intentional error scenarios
    await page.goto('https://aiwfe.com/error-test');
    
    // Validate error page elements
    await expect(page.locator('.error-container')).toBeVisible();
    
    // Test error recovery mechanism
    await page.click('button[name="retry"]');
    await page.waitForSelector('.dashboard-container');
  });

  test('Performance Report Generation', async () => {
    const performanceReport = performanceTracker.generateReport();
    
    // Log performance metrics
    console.log('Performance Report:', performanceReport);
    
    // Assertions on performance metrics
    expect(performanceReport.pageLoadPerformance).toBeLessThan(3000); // < 3 seconds
    expect(performanceReport.chatInteractionPerformance).toBeLessThan(2000); // < 2 seconds
    expect(performanceReport.networkHealthy).toBe(true);
  });
});

module.exports = { PerformanceTracker };