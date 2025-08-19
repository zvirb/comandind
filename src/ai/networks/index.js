/**
 * Neural Networks Module Index
 * Exports Q-learning network components for easy import
 */

export { QNetwork } from './QNetwork.js';
export { NetworkConfig, COMPACT_CONFIG, PERFORMANCE_CONFIG, BROWSER_CONFIG } from './NetworkConfig.js';
export { testQNetwork, benchmarkPerformance } from './test-qnetwork.js';

// Default export for convenience
export { QNetwork as default } from './QNetwork.js';