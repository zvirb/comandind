/**
 * EventListenerManager - Global event listener tracking and cleanup system
 * 
 * This utility helps prevent memory leaks by:
 * - Tracking all event listeners added to DOM elements
 * - Providing automatic cleanup on component destruction
 * - Supporting event delegation patterns
 * - Monitoring event listener health
 */

export class EventListenerManager {
    constructor(name = 'DefaultManager') {
        this.name = name;
        this.listeners = new Map(); // element -> Map(eventType -> handlers[])
        this.delegatedListeners = new Map(); // container -> Map(selector -> Map(eventType -> handlers[]))
        this.passiveEvents = new Set(['scroll', 'touchmove', 'touchstart', 'touchend', 'wheel']);
        this.isDestroyed = false;
        
        // Statistics
        this.stats = {
            listenersAdded: 0,
            listenersRemoved: 0,
            delegatedListenersAdded: 0,
            activeListeners: 0
        };
        
        console.log(`✅ EventListenerManager '${this.name}' initialized`);
    }
    
    /**
     * Add an event listener with automatic tracking and cleanup
     */
    addEventListener(element, eventType, handler, options = {}) {
        if (this.isDestroyed) {
            console.warn('EventListenerManager destroyed, ignoring addEventListener');
            return false;
        }
        
        if (!element || typeof handler !== 'function') {
            console.error('Invalid element or handler for addEventListener');
            return false;
        }
        
        // Auto-detect passive events for better performance
        if (this.passiveEvents.has(eventType) && !options.hasOwnProperty('passive')) {
            options.passive = true;
        }
        
        // Create wrapped handler for better tracking
        const wrappedHandler = (event) => {
            try {
                if (!this.isDestroyed) {
                    handler(event);
                }
            } catch (error) {
                console.error(`Error in event handler for ${eventType}:`, error);
            }
        };
        
        // Store handler mapping for cleanup
        if (!this.listeners.has(element)) {
            this.listeners.set(element, new Map());
        }
        
        const elementListeners = this.listeners.get(element);
        if (!elementListeners.has(eventType)) {
            elementListeners.set(eventType, []);
        }
        
        const handlers = elementListeners.get(eventType);
        handlers.push({
            original: handler,
            wrapped: wrappedHandler,
            options: options
        });
        
        // Add the actual DOM listener
        element.addEventListener(eventType, wrappedHandler, options);
        
        this.stats.listenersAdded++;
        this.stats.activeListeners++;
        
        return true;
    }
    
    /**
     * Remove a specific event listener
     */
    removeEventListener(element, eventType, handler) {
        if (!element || !this.listeners.has(element)) {
            return false;
        }
        
        const elementListeners = this.listeners.get(element);
        if (!elementListeners.has(eventType)) {
            return false;
        }
        
        const handlers = elementListeners.get(eventType);
        const handlerIndex = handlers.findIndex(h => h.original === handler);
        
        if (handlerIndex === -1) {
            return false;
        }
        
        const handlerInfo = handlers[handlerIndex];
        element.removeEventListener(eventType, handlerInfo.wrapped, handlerInfo.options);
        
        handlers.splice(handlerIndex, 1);
        
        // Cleanup empty maps
        if (handlers.length === 0) {
            elementListeners.delete(eventType);
        }
        if (elementListeners.size === 0) {
            this.listeners.delete(element);
        }
        
        this.stats.listenersRemoved++;
        this.stats.activeListeners--;
        
        return true;
    }
    
    /**
     * Add delegated event listener (event delegation pattern)
     */
    addDelegatedListener(container, selector, eventType, handler, options = {}) {
        if (this.isDestroyed) {
            console.warn('EventListenerManager destroyed, ignoring addDelegatedListener');
            return false;
        }
        
        if (!container || !selector || typeof handler !== 'function') {
            console.error('Invalid parameters for addDelegatedListener');
            return false;
        }
        
        // Create delegated handler
        const delegatedHandler = (event) => {
            try {
                if (this.isDestroyed) return;
                
                const target = event.target.closest(selector);
                if (target && container.contains(target)) {
                    handler.call(target, event, target);
                }
            } catch (error) {
                console.error(`Error in delegated handler for ${selector}:${eventType}:`, error);
            }
        };
        
        // Store delegated listener info
        if (!this.delegatedListeners.has(container)) {
            this.delegatedListeners.set(container, new Map());
        }
        
        const containerDelegated = this.delegatedListeners.get(container);
        if (!containerDelegated.has(selector)) {
            containerDelegated.set(selector, new Map());
        }
        
        const selectorDelegated = containerDelegated.get(selector);
        if (!selectorDelegated.has(eventType)) {
            selectorDelegated.set(eventType, []);
        }
        
        const handlers = selectorDelegated.get(eventType);
        handlers.push({
            original: handler,
            delegated: delegatedHandler,
            options: options
        });
        
        // Add the actual delegated listener to container
        this.addEventListener(container, eventType, delegatedHandler, options);
        
        this.stats.delegatedListenersAdded++;
        
        return true;
    }
    
    /**
     * Remove delegated event listener
     */
    removeDelegatedListener(container, selector, eventType, handler) {
        if (!container || !this.delegatedListeners.has(container)) {
            return false;
        }
        
        const containerDelegated = this.delegatedListeners.get(container);
        if (!containerDelegated.has(selector)) {
            return false;
        }
        
        const selectorDelegated = containerDelegated.get(selector);
        if (!selectorDelegated.has(eventType)) {
            return false;
        }
        
        const handlers = selectorDelegated.get(eventType);
        const handlerIndex = handlers.findIndex(h => h.original === handler);
        
        if (handlerIndex === -1) {
            return false;
        }
        
        const handlerInfo = handlers[handlerIndex];
        this.removeEventListener(container, eventType, handlerInfo.delegated);
        
        handlers.splice(handlerIndex, 1);
        
        // Cleanup empty maps
        if (handlers.length === 0) {
            selectorDelegated.delete(eventType);
        }
        if (selectorDelegated.size === 0) {
            containerDelegated.delete(selector);
        }
        if (containerDelegated.size === 0) {
            this.delegatedListeners.delete(container);
        }
        
        return true;
    }
    
    /**
     * Remove all event listeners from a specific element
     */
    removeAllListeners(element) {
        if (!element || !this.listeners.has(element)) {
            return 0;
        }
        
        const elementListeners = this.listeners.get(element);
        let removedCount = 0;
        
        for (const [eventType, handlers] of elementListeners) {
            for (const handlerInfo of handlers) {
                element.removeEventListener(eventType, handlerInfo.wrapped, handlerInfo.options);
                removedCount++;
            }
        }
        
        this.listeners.delete(element);
        this.stats.listenersRemoved += removedCount;
        this.stats.activeListeners -= removedCount;
        
        return removedCount;
    }
    
    /**
     * Get statistics about managed listeners
     */
    getStats() {
        const elementCount = this.listeners.size;
        const delegatedContainers = this.delegatedListeners.size;
        
        let totalHandlers = 0;
        for (const elementListeners of this.listeners.values()) {
            for (const handlers of elementListeners.values()) {
                totalHandlers += handlers.length;
            }
        }
        
        return {
            ...this.stats,
            elementCount,
            delegatedContainers,
            totalHandlers,
            isDestroyed: this.isDestroyed
        };
    }
    
    /**
     * Check for potential memory leaks
     */
    checkForLeaks() {
        const stats = this.getStats();
        const warnings = [];
        
        if (stats.activeListeners > 100) {
            warnings.push(`High listener count: ${stats.activeListeners}`);
        }
        
        if (stats.elementCount > 50) {
            warnings.push(`Many elements with listeners: ${stats.elementCount}`);
        }
        
        if (stats.totalHandlers !== stats.activeListeners) {
            warnings.push('Mismatch in listener counts - possible tracking error');
        }
        
        return {
            hasLeaks: warnings.length > 0,
            warnings,
            stats
        };
    }
    
    /**
     * Debug: List all managed listeners
     */
    debugListeners() {
        console.group(`EventListenerManager '${this.name}' Debug Info`);
        
        console.log('Statistics:', this.getStats());
        
        console.log('Elements with listeners:', this.listeners.size);
        for (const [element, elementListeners] of this.listeners) {
            console.log(`  Element:`, element);
            for (const [eventType, handlers] of elementListeners) {
                console.log(`    ${eventType}: ${handlers.length} handlers`);
            }
        }
        
        console.log('Delegated listeners:', this.delegatedListeners.size);
        for (const [container, containerDelegated] of this.delegatedListeners) {
            console.log(`  Container:`, container);
            for (const [selector, selectorDelegated] of containerDelegated) {
                console.log(`    Selector '${selector}':`);
                for (const [eventType, handlers] of selectorDelegated) {
                    console.log(`      ${eventType}: ${handlers.length} handlers`);
                }
            }
        }
        
        console.groupEnd();
    }
    
    /**
     * Destroy and cleanup all managed listeners
     */
    destroy() {
        if (this.isDestroyed) {
            console.warn(`EventListenerManager '${this.name}' already destroyed`);
            return;
        }
        
        console.log(`🗑️ Destroying EventListenerManager '${this.name}'...`);
        
        this.isDestroyed = true;
        
        // Remove all regular listeners
        let totalRemoved = 0;
        for (const element of Array.from(this.listeners.keys())) {
            totalRemoved += this.removeAllListeners(element);
        }
        
        // Clear delegated listeners (they're tracked as regular listeners too)
        this.delegatedListeners.clear();
        
        console.log(`✅ EventListenerManager '${this.name}' destroyed (removed ${totalRemoved} listeners)`);
    }
}

/**
 * Global event listener manager instance
 */
export const globalEventManager = new EventListenerManager('GlobalManager');

/**
 * Utility function to create a scoped event manager
 */
export function createEventManager(name) {
    return new EventListenerManager(name);
}

/**
 * Utility to add listeners with automatic passive detection
 */
export function addListener(element, eventType, handler, options = {}) {
    return globalEventManager.addEventListener(element, eventType, handler, options);
}

/**
 * Utility to remove listeners
 */
export function removeListener(element, eventType, handler) {
    return globalEventManager.removeEventListener(element, eventType, handler);
}

/**
 * Utility for event delegation
 */
export function addDelegatedListener(container, selector, eventType, handler, options = {}) {
    return globalEventManager.addDelegatedListener(container, selector, eventType, handler, options);
}