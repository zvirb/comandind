/**
 * Authentication State Machine
 * Prevents invalid authentication state transitions and reduces infinite loops
 */

export class AuthStateMachine {
  constructor() {
    this.states = {
      UNAUTHENTICATED: 'unauthenticated',
      AUTHENTICATING: 'authenticating', 
      AUTHENTICATED: 'authenticated',
      RESTORING: 'restoring',
      ERROR: 'error',
      CIRCUIT_OPEN: 'circuit_open'
    };
    
    this.validTransitions = {
      [this.states.UNAUTHENTICATED]: [
        this.states.AUTHENTICATING,
        this.states.RESTORING,
        this.states.CIRCUIT_OPEN
      ],
      [this.states.AUTHENTICATING]: [
        this.states.AUTHENTICATED,
        this.states.ERROR,
        this.states.UNAUTHENTICATED,
        this.states.CIRCUIT_OPEN
      ],
      [this.states.AUTHENTICATED]: [
        this.states.AUTHENTICATING,
        this.states.UNAUTHENTICATED,
        this.states.ERROR,
        this.states.RESTORING
      ],
      [this.states.RESTORING]: [
        this.states.AUTHENTICATED,
        this.states.UNAUTHENTICATED,
        this.states.ERROR,
        this.states.CIRCUIT_OPEN
      ],
      [this.states.ERROR]: [
        this.states.AUTHENTICATING,
        this.states.RESTORING,
        this.states.UNAUTHENTICATED,
        this.states.CIRCUIT_OPEN
      ],
      [this.states.CIRCUIT_OPEN]: [
        this.states.UNAUTHENTICATED,
        this.states.AUTHENTICATING,
        this.states.RESTORING
      ]
    };
    
    this.actionCooldowns = new Map();
    this.lastStateChange = Date.now();
    this.stateChangeMinInterval = 2000; // INCREASED: Minimum 2000ms (2s) between state changes to prevent rapid cycling
    this.consecutiveStateChanges = 0;
    this.maxConsecutiveChanges = 3; // Maximum 3 consecutive state changes before forced circuit breaker
    this.stateChangeHistory = []; // Track state change history for debugging
    this.isInitialized = false; // Flag to track if state machine has been initialized
    this.initialLoadTimestamp = null; // Track when initial load started
  }
  
  /**
   * Get current state from auth context values
   */
  getCurrentState(authState) {
    const { isAuthenticated, isLoading, isRestoring, error } = authState;
    
    if (isRestoring) return this.states.RESTORING;
    if (isLoading) return this.states.AUTHENTICATING;
    if (error) return this.states.ERROR;
    if (isAuthenticated) return this.states.AUTHENTICATED;
    
    return this.states.UNAUTHENTICATED;
  }
  
  /**
   * Check if an action is valid given the current state and recent history
   */
  getValidTransition(currentAuthState, action, options = {}) {
    const currentState = this.getCurrentState(currentAuthState);
    const now = Date.now();
    const isInitialLoad = options.isInitialLoad || false;
    
    // Track state change history for debugging
    this.stateChangeHistory.push({ state: currentState, action, timestamp: now, isInitialLoad });
    if (this.stateChangeHistory.length > 10) {
      this.stateChangeHistory.shift(); // Keep only last 10 entries
    }
    
    // SPECIAL CASE: Allow session restoration on initial page load without cooldown restrictions
    // Handle React Strict Mode double execution by allowing multiple initial load attempts within 5 seconds
    if (isInitialLoad && action === 'restore_session') {
      // Set initial timestamp on first call
      if (!this.isInitialized) {
        this.initialLoadTimestamp = now;
      }
      
      const timeSinceInitialLoad = this.initialLoadTimestamp ? (now - this.initialLoadTimestamp) : 0;
      
      // Allow initial load attempts within 5 seconds (handles React Strict Mode double execution)
      if (!this.isInitialized || timeSinceInitialLoad < 5000) {
        console.log('AuthStateMachine: Allowing initial session restoration (React Strict Mode compatible)', {
          isInitialized: this.isInitialized,
          timeSinceInitialLoad: timeSinceInitialLoad
        });
        
        this.isInitialized = true;
        
        // Validate the action is still valid for the current state
        const actionValidation = this.validateAction(currentState, action);
        if (!actionValidation.isValid) {
          return actionValidation;
        }
        
        // Update last state change but don't set action cooldown for initial load
        this.lastStateChange = now;
        return { isValid: true, newState: actionValidation.targetState };
      } else {
        // Initial load window expired - block the request
        console.log('AuthStateMachine: Initial load window expired, blocking request');
        return { 
          isValid: false, 
          reason: 'Initial load window expired (5 seconds)',
          timeSinceInitialLoad: timeSinceInitialLoad
        };
      }
    }
    
    // Prevent rapid state changes - ENHANCED DETECTION (except for initial load)
    const timeSinceLastChange = now - this.lastStateChange;
    if (timeSinceLastChange < this.stateChangeMinInterval) {
      this.consecutiveStateChanges++;
      
      // Force circuit breaker if too many consecutive rapid changes
      if (this.consecutiveStateChanges >= this.maxConsecutiveChanges) {
        console.warn('AuthStateMachine: Too many rapid state changes detected, forcing circuit breaker', {
          consecutiveChanges: this.consecutiveStateChanges,
          recentHistory: this.stateChangeHistory.slice(-5)
        });
        this.consecutiveStateChanges = 0;
        return { 
          isValid: false, 
          reason: 'Circuit breaker activated due to rapid state changes',
          cooldownRemaining: this.stateChangeMinInterval * 2 // Extended cooldown
        };
      }
      
      return { 
        isValid: false, 
        reason: 'State change too frequent',
        cooldownRemaining: this.stateChangeMinInterval - timeSinceLastChange,
        consecutiveAttempts: this.consecutiveStateChanges
      };
    }
    
    // Reset consecutive counter on successful timing
    this.consecutiveStateChanges = 0;
    
    // Check action-specific cooldowns
    const actionKey = `${currentState}_${action}`;
    const actionCooldown = this.actionCooldowns.get(actionKey);
    
    if (actionCooldown && now < actionCooldown.nextAllowedTime) {
      return {
        isValid: false,
        reason: 'Action in cooldown',
        cooldownRemaining: actionCooldown.nextAllowedTime - now
      };
    }
    
    // Define action-specific validation rules
    const actionValidation = this.validateAction(currentState, action);
    
    if (!actionValidation.isValid) {
      return actionValidation;
    }
    
    // Set cooldown for this action
    this.setActionCooldown(actionKey, this.getActionCooldownMs(action));
    this.lastStateChange = now;
    
    return { isValid: true, newState: actionValidation.targetState };
  }
  
  /**
   * Validate specific actions based on current state
   */
  validateAction(currentState, action) {
    switch (action) {
      case 'navigate':
        // Navigation is generally allowed but may trigger auth checks
        return { 
          isValid: true, 
          targetState: currentState,
          requiresAuthCheck: currentState === this.states.AUTHENTICATED
        };
        
      case 'login':
        // Login only valid from unauthenticated, error, or circuit_open states
        if ([this.states.UNAUTHENTICATED, this.states.ERROR, this.states.CIRCUIT_OPEN].includes(currentState)) {
          return { isValid: true, targetState: this.states.AUTHENTICATING };
        }
        return { isValid: false, reason: 'Already authenticated or in process' };
        
      case 'restore_session':
        // Session restoration valid from unauthenticated or error states
        // Also allow from restoring state to handle re-attempts
        if ([this.states.UNAUTHENTICATED, this.states.ERROR, this.states.RESTORING].includes(currentState)) {
          return { isValid: true, targetState: this.states.RESTORING };
        }
        return { isValid: false, reason: 'Session restoration not needed' };
        
      case 'refresh_auth':
        // Auth refresh only valid from authenticated state
        if (currentState === this.states.AUTHENTICATED) {
          return { isValid: true, targetState: this.states.AUTHENTICATING };
        }
        return { isValid: false, reason: 'Cannot refresh unauthenticated session' };
        
      case 'logout':
        // Logout valid from any state except circuit_open
        if (currentState !== this.states.CIRCUIT_OPEN) {
          return { isValid: true, targetState: this.states.UNAUTHENTICATED };
        }
        return { isValid: false, reason: 'Cannot logout while circuit breaker is open' };
        
      case 'health_check':
        // Health checks are always allowed but with cooldown
        return { isValid: true, targetState: currentState };
        
      default:
        return { isValid: false, reason: `Unknown action: ${action}` };
    }
  }
  
  /**
   * Get cooldown period for specific actions
   */
  getActionCooldownMs(action) {
    const cooldowns = {
      navigate: 3000,        // INCREASED: 3 seconds between navigation auth checks
      login: 5000,           // INCREASED: 5 seconds between login attempts
      restore_session: 10000, // INCREASED: 10 seconds between session restoration attempts
      refresh_auth: 15000,    // INCREASED: 15 seconds between auth refreshes
      logout: 2000,          // INCREASED: 2 seconds between logout attempts
      health_check: 30000    // INCREASED: 30 seconds between health checks
    };
    
    return cooldowns[action] || 3000; // Default increased to 3 seconds
  }
  
  /**
   * Set cooldown for a specific action
   */
  setActionCooldown(actionKey, cooldownMs) {
    this.actionCooldowns.set(actionKey, {
      nextAllowedTime: Date.now() + cooldownMs,
      cooldownMs
    });
  }
  
  /**
   * Clear all cooldowns (use sparingly, for recovery scenarios)
   */
  clearCooldowns() {
    this.actionCooldowns.clear();
    this.lastStateChange = 0;
  }
  
  /**
   * Reset state machine for new session (handles page reloads and new user sessions)
   */
  resetForNewSession() {
    console.log('AuthStateMachine: Resetting for new session');
    this.isInitialized = false;
    this.initialLoadTimestamp = null;
    this.actionCooldowns.clear();
    this.lastStateChange = 0;
    this.consecutiveStateChanges = 0;
    this.stateChangeHistory = [];
  }
  
  /**
   * Get debug information about current state machine status
   */
  getDebugInfo() {
    const now = Date.now();
    const activeCooldowns = [];
    
    for (const [actionKey, cooldown] of this.actionCooldowns.entries()) {
      if (now < cooldown.nextAllowedTime) {
        activeCooldowns.push({
          action: actionKey,
          remainingMs: cooldown.nextAllowedTime - now
        });
      }
    }
    
    return {
      states: this.states,
      activeCooldowns,
      timeSinceLastStateChange: now - this.lastStateChange,
      stateChangeMinInterval: this.stateChangeMinInterval
    };
  }
}

export default AuthStateMachine;