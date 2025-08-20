/**
 * Global Notification System for UI Feedback
 * Provides toast notifications, error handling, and user feedback
 */

class NotificationManager {
  constructor() {
    this.notifications = [];
    this.listeners = new Set();
    this.maxNotifications = 5;
    this.defaultDuration = 5000; // 5 seconds
  }

  /**
   * Add a notification listener
   * @param {Function} callback - Function to call when notifications change
   */
  addListener(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  /**
   * Notify all listeners of notification changes
   */
  notifyListeners() {
    this.listeners.forEach(callback => callback([...this.notifications]));
  }

  /**
   * Generate unique notification ID
   */
  generateId() {
    return `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Add a notification to the system
   * @param {Object} options - Notification configuration
   */
  addNotification({
    type = 'info',
    title,
    message,
    duration = this.defaultDuration,
    persistent = false,
    action = null,
    data = {}
  }) {
    const notification = {
      id: this.generateId(),
      type,
      title,
      message,
      timestamp: Date.now(),
      duration,
      persistent,
      action,
      data,
      dismissed: false
    };

    // Add to beginning of array for newest first
    this.notifications.unshift(notification);

    // Limit max notifications
    if (this.notifications.length > this.maxNotifications) {
      this.notifications = this.notifications.slice(0, this.maxNotifications);
    }

    // Auto-dismiss non-persistent notifications
    if (!persistent && duration > 0) {
      setTimeout(() => {
        this.dismissNotification(notification.id);
      }, duration);
    }

    this.notifyListeners();
    return notification.id;
  }

  /**
   * Dismiss a specific notification
   * @param {string} id - Notification ID
   */
  dismissNotification(id) {
    const index = this.notifications.findIndex(n => n.id === id);
    if (index !== -1) {
      this.notifications.splice(index, 1);
      this.notifyListeners();
    }
  }

  /**
   * Clear all notifications
   */
  clearAll() {
    this.notifications = [];
    this.notifyListeners();
  }

  /**
   * Clear notifications by type
   * @param {string} type - Notification type to clear
   */
  clearByType(type) {
    this.notifications = this.notifications.filter(n => n.type !== type);
    this.notifyListeners();
  }

  /**
   * Show success notification
   * @param {string} message - Success message
   * @param {Object} options - Additional options
   */
  success(message, options = {}) {
    return this.addNotification({
      type: 'success',
      title: options.title || 'Success',
      message,
      duration: options.duration || 4000,
      ...options
    });
  }

  /**
   * Show error notification
   * @param {string|Error} error - Error message or Error object
   * @param {Object} options - Additional options
   */
  error(error, options = {}) {
    let message = '';
    let title = options.title || 'Error';
    let data = {};

    if (error instanceof Error) {
      message = error.message;
      data.stack = error.stack;
      data.name = error.name;
    } else if (typeof error === 'string') {
      message = error;
    } else {
      message = 'An unexpected error occurred';
    }

    return this.addNotification({
      type: 'error',
      title,
      message,
      duration: options.duration || 8000, // Longer for errors
      persistent: options.persistent || false,
      data,
      ...options
    });
  }

  /**
   * Show warning notification
   * @param {string} message - Warning message
   * @param {Object} options - Additional options
   */
  warning(message, options = {}) {
    return this.addNotification({
      type: 'warning',
      title: options.title || 'Warning',
      message,
      duration: options.duration || 6000,
      ...options
    });
  }

  /**
   * Show info notification
   * @param {string} message - Info message
   * @param {Object} options - Additional options
   */
  info(message, options = {}) {
    return this.addNotification({
      type: 'info',
      title: options.title || 'Information',
      message,
      duration: options.duration || 5000,
      ...options
    });
  }

  /**
   * Show loading notification with progress
   * @param {string} message - Loading message
   * @param {Object} options - Additional options
   */
  loading(message, options = {}) {
    return this.addNotification({
      type: 'loading',
      title: options.title || 'Loading',
      message,
      persistent: true, // Loading notifications should be manually dismissed
      ...options
    });
  }

  /**
   * Update an existing notification
   * @param {string} id - Notification ID
   * @param {Object} updates - Updates to apply
   */
  updateNotification(id, updates) {
    const notification = this.notifications.find(n => n.id === id);
    if (notification) {
      Object.assign(notification, updates);
      this.notifyListeners();
    }
  }

  /**
   * Handle API errors with smart error extraction
   * @param {Response|Error} error - API error response or Error
   * @param {Object} options - Additional options
   */
  async handleApiError(error, options = {}) {
    let message = 'An unexpected error occurred';
    let title = 'API Error';
    let data = {};

    try {
      if (error instanceof Response) {
        // Handle Response objects
        const status = error.status;
        title = `${status} Error`;
        
        try {
          const responseData = await error.json();
          message = responseData.message || responseData.error || `HTTP ${status} Error`;
          data.response = responseData;
        } catch {
          // Fallback if response isn't JSON
          message = `HTTP ${status}: ${error.statusText}`;
        }
        
        data.status = status;
        data.url = error.url;
      } else if (error instanceof Error) {
        // Handle Error objects
        message = error.message;
        title = error.name || 'Error';
        data.stack = error.stack;
        
        // Handle specific error types
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
          message = 'Network connection failed. Please check your internet connection.';
          title = 'Connection Error';
        }
      }
    } catch (parseError) {
      console.error('Error parsing API error:', parseError);
    }

    return this.error(message, {
      title,
      data,
      ...options
    });
  }

  /**
   * Handle authentication errors specifically
   * @param {Error|Response} error - Authentication error
   * @param {Object} options - Additional options
   */
  handleAuthError(error, options = {}) {
    return this.error('Authentication failed. Please log in again.', {
      title: 'Authentication Required',
      persistent: true,
      action: {
        label: 'Login',
        callback: () => {
          window.location.href = '/login';
        }
      },
      ...options
    });
  }

  /**
   * Show offline/online status notifications
   * @param {boolean} isOnline - Current online status
   */
  handleConnectivityChange(isOnline) {
    if (isOnline) {
      this.success('Connection restored', {
        title: 'Back Online',
        duration: 3000
      });
      // Clear any offline notifications
      this.clearByType('offline');
    } else {
      this.warning('You are currently offline. Some features may be limited.', {
        title: 'Offline Mode',
        type: 'offline',
        persistent: true
      });
    }
  }
}

// Create global instance
const notificationManager = new NotificationManager();

// Export convenience functions and the manager
export const notifications = {
  success: (message, options) => notificationManager.success(message, options),
  error: (error, options) => notificationManager.error(error, options),
  warning: (message, options) => notificationManager.warning(message, options),
  info: (message, options) => notificationManager.info(message, options),
  loading: (message, options) => notificationManager.loading(message, options),
  
  // Management functions
  dismiss: (id) => notificationManager.dismissNotification(id),
  clearAll: () => notificationManager.clearAll(),
  clearByType: (type) => notificationManager.clearByType(type),
  update: (id, updates) => notificationManager.updateNotification(id, updates),
  
  // Specialized handlers
  handleApiError: (error, options) => notificationManager.handleApiError(error, options),
  handleAuthError: (error, options) => notificationManager.handleAuthError(error, options),
  handleConnectivity: (isOnline) => notificationManager.handleConnectivityChange(isOnline),
  
  // Listener management
  addListener: (callback) => notificationManager.addListener(callback),
};

export default notificationManager;