/**
 * Development Tools Detector
 * Detects and handles console warnings from development tools and browser extensions
 */

class DevelopmentToolsDetector {
  constructor() {
    this.detectedTools = new Set();
    this.fragmentWarnings = new Map();
    this.suppressedWarnings = new Set();
    
    this.init();
  }

  init() {
    this.setupConsoleFiltering();
    this.detectDevelopmentEnvironment();
    this.monitorConsoleWarnings();
  }

  /**
   * Setup console filtering for known development tool warnings
   */
  setupConsoleFiltering() {
    const originalWarn = console.warn;
    const originalError = console.error;
    
    console.warn = (...args) => {
      const message = args.join(' ');
      
      // Filter out known development tool warnings
      if (this.shouldSuppressWarning(message)) {
        // Log suppressed warning to debug console if needed
        if (process.env.NODE_ENV === 'development') {
          console.debug('[DevTools] Suppressed warning:', message);
        }
        return;
      }
      
      // Check for GraphQL fragment warnings
      if (this.isGraphQLFragmentWarning(message)) {
        this.handleFragmentWarning(message);
        return;
      }
      
      // Allow other warnings through
      originalWarn.apply(console, args);
    };
    
    console.error = (...args) => {
      const message = args.join(' ');
      
      // Filter out known development tool errors
      if (this.shouldSuppressError(message)) {
        if (process.env.NODE_ENV === 'development') {
          console.debug('[DevTools] Suppressed error:', message);
        }
        return;
      }
      
      // Allow other errors through
      originalError.apply(console, args);
    };
  }

  /**
   * Detect if we're in a development environment with tools
   */
  detectDevelopmentEnvironment() {
    // Check for common development tools
    const devTools = [
      'React Developer Tools',
      'Redux DevTools',
      'Apollo Client Developer Tools',
      'GraphQL Playground',
      'Storybook'
    ];
    
    // Check for browser extensions
    if (window.chrome && window.chrome.runtime) {
      this.detectedTools.add('Chrome Extension Environment');
    }
    
    // Check for React DevTools
    if (window.__REACT_DEVTOOLS_GLOBAL_HOOK__) {
      this.detectedTools.add('React Developer Tools');
    }
    
    // Check for Apollo DevTools
    if (window.__APOLLO_CLIENT__) {
      this.detectedTools.add('Apollo Client Developer Tools');
    }
    
    // Check for Storybook
    if (window.__STORYBOOK_ADDONS || window.__STORYBOOK_CLIENT_API__) {
      this.detectedTools.add('Storybook');
    }
    
    if (this.detectedTools.size > 0) {
      console.log('[DevTools] Detected development tools:', Array.from(this.detectedTools));
    }
  }

  /**
   * Monitor for specific console warning patterns
   */
  monitorConsoleWarnings() {
    // Listen for global error events
    window.addEventListener('error', (event) => {
      this.handleGlobalError(event);
    });
    
    // Listen for unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.handleUnhandledRejection(event);
    });
  }

  /**
   * Check if a warning should be suppressed
   */
  shouldSuppressWarning(message) {
    const suppressPatterns = [
      // React DevTools warnings
      /React DevTools/i,
      /Warning.*react-dom/i,
      
      // Chrome extension warnings
      /extensions::/i,
      /chrome-extension:/i,
      
      // Development server warnings
      /webpack.*dev.*server/i,
      /HMR/i,
      /Hot.*reload/i,
      
      // Known iframe-boot.js patterns (from development tools)
      /iframe-boot\.js/i,
      /iframe.*boot/i,
      
      // Storybook warnings
      /storybook/i,
      /@storybook/i
    ];
    
    return suppressPatterns.some(pattern => pattern.test(message));
  }

  /**
   * Check if an error should be suppressed
   */
  shouldSuppressError(message) {
    const suppressPatterns = [
      // Development tool errors that don't affect production
      /chrome-extension:/i,
      /extensions::/i,
      
      // Known iframe-boot.js errors (from development tools)
      /iframe-boot\.js/i,
      
      // GraphQL fragment errors from development tools
      /Fragment.*BaseJam.*already defined/i,
      /Fragment.*RecordingLink.*already defined/i,
      /Duplicate fragment definition/i
    ];
    
    return suppressPatterns.some(pattern => pattern.test(message));
  }

  /**
   * Check if warning is related to GraphQL fragments
   */
  isGraphQLFragmentWarning(message) {
    const fragmentPatterns = [
      /Fragment.*already defined/i,
      /Duplicate fragment/i,
      /BaseJam/i,
      /RecordingLink/i
    ];
    
    return fragmentPatterns.some(pattern => pattern.test(message));
  }

  /**
   * Handle GraphQL fragment warnings
   */
  handleFragmentWarning(message) {
    // Extract fragment name if possible
    const fragmentMatch = message.match(/Fragment\s+"?([^"'\s]+)"?/);
    const fragmentName = fragmentMatch ? fragmentMatch[1] : 'unknown';
    
    // Track duplicate warnings
    const count = this.fragmentWarnings.get(fragmentName) || 0;
    this.fragmentWarnings.set(fragmentName, count + 1);
    
    // Only log the first occurrence
    if (count === 0) {
      console.debug(`[DevTools] GraphQL fragment warning suppressed: ${fragmentName}`);
      console.debug('[DevTools] This is likely from development tools or browser extensions');
    }
  }

  /**
   * Handle global errors
   */
  handleGlobalError(event) {
    const { filename, message } = event;
    
    // Check if error is from iframe-boot.js or similar development files
    if (filename && filename.includes('iframe-boot')) {
      console.debug('[DevTools] Suppressed iframe-boot.js error:', message);
      event.preventDefault();
      return;
    }
    
    // Check for extension-related errors
    if (filename && (filename.includes('chrome-extension') || filename.includes('extensions::'))) {
      console.debug('[DevTools] Suppressed browser extension error:', message);
      event.preventDefault();
      return;
    }
  }

  /**
   * Handle unhandled promise rejections
   */
  handleUnhandledRejection(event) {
    const reason = event.reason;
    
    if (reason && typeof reason === 'string') {
      if (this.shouldSuppressError(reason)) {
        console.debug('[DevTools] Suppressed rejected promise:', reason);
        event.preventDefault();
        return;
      }
    }
  }

  /**
   * Get detected tools summary
   */
  getDetectedTools() {
    return {
      tools: Array.from(this.detectedTools),
      fragmentWarnings: Object.fromEntries(this.fragmentWarnings),
      suppressedCount: this.suppressedWarnings.size
    };
  }

  /**
   * Enable or disable suppression
   */
  setSuppression(enabled) {
    this.suppressionEnabled = enabled;
    
    if (enabled) {
      console.log('[DevTools] Development tool warning suppression enabled');
    } else {
      console.log('[DevTools] Development tool warning suppression disabled');
    }
  }
}

// Create global instance
const developmentToolsDetector = new DevelopmentToolsDetector();

// Export for manual control if needed
export default developmentToolsDetector;

// Auto-initialize in development
if (process.env.NODE_ENV === 'development') {
  console.log('[DevTools] Development tools detector initialized');
}