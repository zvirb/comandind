/**
 * UIUpdateManager
 * 
 * Optimized DOM update manager that separates UI updates from the main game loop
 * to prevent performance degradation. Uses throttled updates and batched DOM operations.
 * 
 * Features:
 * - Throttled updates at configurable rate (default 10Hz)
 * - Batched DOM updates to minimize reflows
 * - CSS transform optimization for position updates
 * - Virtual DOM pattern for complex UI changes
 * - RequestAnimationFrame integration for smooth UI
 */

export class UIUpdateManager {
    constructor(options = {}) {
        // Configuration
        this.updateHz = options.updateHz || 10; // 10Hz for performance stats
        this.updateInterval = 1000 / this.updateHz;
        this.enableVirtualDOM = options.enableVirtualDOM || false;
        
        // Timing
        this.lastUpdateTime = 0;
        this.rafId = null;
        this.isRunning = false;
        
        // Update queues for batching
        this.pendingUpdates = new Map();
        this.pendingTransforms = new Map();
        this.pendingClassChanges = new Map();
        this.pendingStyleChanges = new Map();
        
        // Virtual DOM state (simple implementation)
        this.virtualDOM = new Map();
        this.lastKnownState = new Map();
        
        // Performance tracking
        this.updateCount = 0;
        this.avgUpdateTime = 0;
        this.maxUpdateTime = 0;
        
        // Cached DOM references
        this.domElements = new Map();
        
        // Bind methods
        this.update = this.update.bind(this);
        this.rafUpdate = this.rafUpdate.bind(this);
        
        console.log(`🎨 UIUpdateManager initialized - Update rate: ${this.updateHz}Hz`);
    }
    
    /**
     * Start the UI update manager
     */
    start() {
        if (this.isRunning) {
            console.warn('UIUpdateManager already running');
            return;
        }
        
        this.isRunning = true;
        this.lastUpdateTime = performance.now();
        this.rafId = requestAnimationFrame(this.rafUpdate);
        
        console.log('🎨 UIUpdateManager started');
    }
    
    /**
     * Stop the UI update manager
     */
    stop() {
        if (!this.isRunning) return;
        
        this.isRunning = false;
        if (this.rafId) {
            cancelAnimationFrame(this.rafId);
            this.rafId = null;
        }
        
        console.log('🎨 UIUpdateManager stopped');
    }
    
    /**
     * RequestAnimationFrame callback - checks if it's time for throttled updates
     */
    rafUpdate(timestamp) {
        if (!this.isRunning) return;
        
        // Check if enough time has passed for the next update
        if (timestamp - this.lastUpdateTime >= this.updateInterval) {
            this.update(timestamp);
            this.lastUpdateTime = timestamp;
        }
        
        // Always schedule next frame for smooth checking
        this.rafId = requestAnimationFrame(this.rafUpdate);
    }
    
    /**
     * Main update function - processes all pending UI updates
     */
    update(timestamp) {
        const startTime = performance.now();
        
        try {
            // Process all batched updates
            this.processBatchedUpdates();
            
            // Update performance tracking
            const updateTime = performance.now() - startTime;
            this.updateCount++;
            this.avgUpdateTime = (this.avgUpdateTime * (this.updateCount - 1) + updateTime) / this.updateCount;
            this.maxUpdateTime = Math.max(this.maxUpdateTime, updateTime);
            
            // Warn if update is taking too long
            if (updateTime > 16) { // More than 1 frame at 60fps
                console.warn(`UIUpdateManager slow update: ${updateTime.toFixed(2)}ms`);
            }
            
        } catch (error) {
            console.error('Error in UIUpdateManager update:', error);
        }
    }
    
    /**
     * Process all batched DOM updates in optimal order
     */
    processBatchedUpdates() {
        // 1. Style changes first (may affect layout)
        this.processStyleChanges();
        
        // 2. Class changes (may affect layout)
        this.processClassChanges();
        
        // 3. Content updates (may affect layout)
        this.processContentUpdates();
        
        // 4. Transform updates last (don't affect layout)
        this.processTransformUpdates();
    }
    
    /**
     * Process batched style changes
     */
    processStyleChanges() {
        if (this.pendingStyleChanges.size === 0) return;
        
        for (const [elementId, styles] of this.pendingStyleChanges) {
            const element = this.getElement(elementId);
            if (element) {
                // Batch all style changes for this element
                for (const [property, value] of Object.entries(styles)) {
                    element.style[property] = value;
                }
            }
        }
        
        this.pendingStyleChanges.clear();
    }
    
    /**
     * Process batched class changes
     */
    processClassChanges() {
        if (this.pendingClassChanges.size === 0) return;
        
        for (const [elementId, changes] of this.pendingClassChanges) {
            const element = this.getElement(elementId);
            if (element) {
                if (changes.add) {
                    element.classList.add(...changes.add);
                }
                if (changes.remove) {
                    element.classList.remove(...changes.remove);
                }
                if (changes.toggle) {
                    changes.toggle.forEach(cls => element.classList.toggle(cls));
                }
            }
        }
        
        this.pendingClassChanges.clear();
    }
    
    /**
     * Process batched content updates
     */
    processContentUpdates() {
        if (this.pendingUpdates.size === 0) return;
        
        for (const [elementId, content] of this.pendingUpdates) {
            const element = this.getElement(elementId);
            if (element) {
                // Only update if content has changed (virtual DOM pattern)
                if (this.enableVirtualDOM) {
                    const lastContent = this.lastKnownState.get(elementId);
                    if (lastContent !== content) {
                        element.textContent = content;
                        this.lastKnownState.set(elementId, content);
                    }
                } else {
                    element.textContent = content;
                }
            }
        }
        
        this.pendingUpdates.clear();
    }
    
    /**
     * Process batched transform updates (most efficient)
     */
    processTransformUpdates() {
        if (this.pendingTransforms.size === 0) return;
        
        for (const [elementId, transform] of this.pendingTransforms) {
            const element = this.getElement(elementId);
            if (element) {
                // Use CSS transforms for optimal performance
                let transformStr = '';
                
                if (transform.x !== undefined || transform.y !== undefined) {
                    transformStr += `translate(${transform.x || 0}px, ${transform.y || 0}px) `;
                }
                
                if (transform.scale !== undefined) {
                    transformStr += `scale(${transform.scale}) `;
                }
                
                if (transform.rotation !== undefined) {
                    transformStr += `rotate(${transform.rotation}deg) `;
                }
                
                element.style.transform = transformStr.trim();
            }
        }
        
        this.pendingTransforms.clear();
    }
    
    /**
     * Queue a text content update for an element
     */
    queueTextUpdate(elementId, content) {
        this.pendingUpdates.set(elementId, String(content));
    }
    
    /**
     * Queue a transform update for an element (uses CSS transforms)
     */
    queueTransformUpdate(elementId, transform) {
        this.pendingTransforms.set(elementId, transform);
    }
    
    /**
     * Queue a class change for an element
     */
    queueClassChange(elementId, changes) {
        let existing = this.pendingClassChanges.get(elementId) || {};
        
        if (changes.add) {
            existing.add = [...(existing.add || []), ...changes.add];
        }
        if (changes.remove) {
            existing.remove = [...(existing.remove || []), ...changes.remove];
        }
        if (changes.toggle) {
            existing.toggle = [...(existing.toggle || []), ...changes.toggle];
        }
        
        this.pendingClassChanges.set(elementId, existing);
    }
    
    /**
     * Queue a style change for an element
     */
    queueStyleChange(elementId, styles) {
        let existing = this.pendingStyleChanges.get(elementId) || {};
        this.pendingStyleChanges.set(elementId, { ...existing, ...styles });
    }
    
    /**
     * Update performance stats (convenience method for the game)
     */
    updatePerformanceStats(stats) {
        if (stats.fps !== undefined) {
            this.queueTextUpdate('fps', Math.round(stats.fps));
        }
        
        if (stats.drawCalls !== undefined) {
            this.queueTextUpdate('draw-calls', stats.drawCalls);
        }
        
        if (stats.spriteCount !== undefined) {
            this.queueTextUpdate('sprite-count', stats.spriteCount);
        }
        
        if (stats.memory !== undefined) {
            this.queueTextUpdate('memory', `${Math.round(stats.memory)} MB`);
        }
    }
    
    /**
     * Get cached DOM element reference
     */
    getElement(elementId) {
        if (!this.domElements.has(elementId)) {
            const element = document.getElementById(elementId);
            if (element) {
                this.domElements.set(elementId, element);
            } else {
                console.warn(`Element with id '${elementId}' not found`);
                return null;
            }
        }
        
        return this.domElements.get(elementId);
    }
    
    /**
     * Clear cached element reference (useful when DOM changes)
     */
    clearElementCache(elementId) {
        this.domElements.delete(elementId);
        this.lastKnownState.delete(elementId);
    }
    
    /**
     * Clear all cached elements
     */
    clearAllCaches() {
        this.domElements.clear();
        this.lastKnownState.clear();
        this.virtualDOM.clear();
    }
    
    /**
     * Force immediate update (bypasses throttling)
     */
    forceUpdate() {
        this.processBatchedUpdates();
    }
    
    /**
     * Get performance statistics
     */
    getPerformanceStats() {
        return {
            updateHz: this.updateHz,
            updateCount: this.updateCount,
            avgUpdateTime: this.avgUpdateTime,
            maxUpdateTime: this.maxUpdateTime,
            pendingUpdates: this.pendingUpdates.size,
            cachedElements: this.domElements.size
        };
    }
    
    /**
     * Set update rate (Hz)
     */
    setUpdateRate(hz) {
        this.updateHz = hz;
        this.updateInterval = 1000 / hz;
        console.log(`🎨 UIUpdateManager rate changed to ${hz}Hz`);
    }
    
    /**
     * Enable/disable virtual DOM pattern
     */
    setVirtualDOM(enabled) {
        this.enableVirtualDOM = enabled;
        if (!enabled) {
            this.lastKnownState.clear();
        }
        console.log(`🎨 Virtual DOM ${enabled ? 'enabled' : 'disabled'}`);
    }
}