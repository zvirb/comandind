import { inputConfig } from "./InputConfig.js";

export class InputHandler {
    constructor(element) {
        this.element = element || document;
        this.listeners = new Map();
        this.keys = new Set();
        this.mouseButtons = new Set();
        this.mousePosition = { x: 0, y: 0 };
        this.inputConfig = inputConfig;
        
        // Touch/gesture tracking
        this.touches = new Map();
        this.lastTouchDistance = 0;
        this.isPinching = false;
        this.isPanning = false;
        
        // Wheel event tracking for trackpad detection
        this.lastWheelEvent = null;
        this.wheelEventCount = 0;
        
        // Event listener tracking for cleanup
        this.eventListeners = new Map();
        this.isDestroyed = false;
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        if (this.isDestroyed) return;
        
        // Create bound event handlers for proper cleanup
        const keydownHandler = (e) => {
            if (this.isDestroyed) return;
            
            // Allow browser navigation shortcuts
            if (this.isNavigationKey(e)) {
                console.log(`🔑 Allowing navigation key: ${e.key} ${e.ctrlKey ? "+ Ctrl" : ""} ${e.metaKey ? "+ Meta" : ""}`);
                return; // Don't prevent default or emit for navigation keys
            }
            
            this.keys.add(e.key);
            this.emit("keydown", e);
        };
        
        const keyupHandler = (e) => {
            if (this.isDestroyed) return;
            
            // Skip processing for navigation keys
            if (this.isNavigationKey(e)) {
                return;
            }
            
            this.keys.delete(e.key);
            this.emit("keyup", e);
        };
        
        const mousedownHandler = (e) => {
            if (this.isDestroyed) return;
            this.mouseButtons.add(e.button);
            this.emit("mousedown", e);
        };
        
        const mouseupHandler = (e) => {
            if (this.isDestroyed) return;
            this.mouseButtons.delete(e.button);
            this.emit("mouseup", e);
        };
        
        const mousemoveHandler = (e) => {
            if (this.isDestroyed) return;
            this.mousePosition.x = e.clientX;
            this.mousePosition.y = e.clientY;
            this.emit("mousemove", e);
        };
        
        const wheelHandler = (e) => {
            if (this.isDestroyed) return;
            this.handleWheel(e);
        };
        
        const touchstartHandler = (e) => {
            if (this.isDestroyed) return;
            this.handleTouchStart(e);
        };
        
        const touchmoveHandler = (e) => {
            if (this.isDestroyed) return;
            this.handleTouchMove(e);
        };
        
        const touchendHandler = (e) => {
            if (this.isDestroyed) return;
            this.handleTouchEnd(e);
        };
        
        const contextmenuHandler = (e) => {
            if (this.isDestroyed) return;
            
            // Only prevent context menu on the game canvas, not on other elements
            const target = e.target;
            const isCanvasElement = target.tagName === "CANVAS" || 
                                  target.closest("#game-container") ||
                                  target.closest("canvas");
            
            if (isCanvasElement) {
                e.preventDefault(); // Prevent context menu on game elements
                console.log("🚫 Context menu prevented on game canvas");
            } else {
                console.log("📋 Allowing context menu on non-game element");
            }
        };
        
        // Store handlers for cleanup
        this.eventListeners.set("keydown", keydownHandler);
        this.eventListeners.set("keyup", keyupHandler);
        this.eventListeners.set("mousedown", mousedownHandler);
        this.eventListeners.set("mouseup", mouseupHandler);
        this.eventListeners.set("mousemove", mousemoveHandler);
        this.eventListeners.set("wheel", wheelHandler);
        this.eventListeners.set("touchstart", touchstartHandler);
        this.eventListeners.set("touchmove", touchmoveHandler);
        this.eventListeners.set("touchend", touchendHandler);
        this.eventListeners.set("contextmenu", contextmenuHandler);
        
        // Add event listeners with proper options
        this.element.addEventListener("keydown", keydownHandler);
        this.element.addEventListener("keyup", keyupHandler);
        this.element.addEventListener("mousedown", mousedownHandler);
        this.element.addEventListener("mouseup", mouseupHandler);
        
        // Use passive for mousemove when possible (better performance)
        this.element.addEventListener("mousemove", mousemoveHandler, { passive: true });
        
        // Wheel event needs to be non-passive since we prevent default for zoom
        this.element.addEventListener("wheel", wheelHandler, { passive: false });
        
        // Touch events - optimize passive usage
        // touchstart: need preventDefault for pinch detection
        this.element.addEventListener("touchstart", touchstartHandler, { passive: false });
        // touchmove: need preventDefault for pan/pinch control
        this.element.addEventListener("touchmove", touchmoveHandler, { passive: false });
        // touchend: can be passive since we don't prevent default
        this.element.addEventListener("touchend", touchendHandler, { passive: true });
        
        // Context menu prevention (for right-click commands)
        this.element.addEventListener("contextmenu", contextmenuHandler);
        
        console.log("✅ InputHandler event listeners setup completed");
    }
    
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }
    
    off(event, callback) {
        if (!this.listeners.has(event)) return;
        
        const callbacks = this.listeners.get(event);
        const index = callbacks.indexOf(callback);
        
        if (index !== -1) {
            callbacks.splice(index, 1);
        }
    }
    
    emit(event, data) {
        if (!this.listeners.has(event)) return;
        
        const callbacks = this.listeners.get(event);
        callbacks.forEach(callback => callback(data));
    }
    
    isKeyPressed(key) {
        return this.keys.has(key);
    }
    
    isMouseButtonPressed(button) {
        return this.mouseButtons.has(button);
    }
    
    getMousePosition() {
        return { ...this.mousePosition };
    }
    
    /**
     * Check if a key event should be allowed for browser navigation
     */
    isNavigationKey(event) {
        const key = event.key;
        const ctrl = event.ctrlKey || event.metaKey; // Cmd on Mac
        const alt = event.altKey;
        const shift = event.shiftKey;
        
        // Function keys for refresh
        if (key === "F5" || (key === "F5" && ctrl)) {
            return true; // Allow F5 and Ctrl+F5 for refresh
        }
        
        // Browser refresh shortcuts
        if (ctrl && key === "r") {
            return true; // Ctrl+R for refresh
        }
        
        // Hard refresh
        if (ctrl && shift && key === "r") {
            return true; // Ctrl+Shift+R for hard refresh
        }
        
        // Navigation shortcuts
        if (alt && (key === "ArrowLeft" || key === "ArrowRight")) {
            return true; // Alt+Arrow for back/forward
        }
        
        // Address bar focus
        if (ctrl && key === "l") {
            return true; // Ctrl+L for address bar
        }
        
        // New tab/window
        if (ctrl && (key === "t" || key === "n")) {
            return true; // Ctrl+T/N for new tab/window
        }
        
        // Close tab/window
        if (ctrl && key === "w") {
            return true; // Ctrl+W to close
        }
        
        // Other browser shortcuts we shouldn't interfere with
        if (ctrl && ["d", "f", "g", "h", "j", "k", "o", "p", "u", "y", "z"].includes(key)) {
            return true; // Various browser shortcuts
        }
        
        // Developer tools
        if (event.key === "F12" || (ctrl && shift && key === "I")) {
            return true; // F12 or Ctrl+Shift+I for dev tools
        }
        
        return false;
    }
    
    /**
     * Handle wheel events with trackpad support
     */
    handleWheel(e) {
        // Only prevent default for game-related wheel events, not navigation
        const shouldPreventDefault = (e.ctrlKey || e.metaKey) || // Zoom gestures
                                   (this.inputConfig.isTrackpad && this.inputConfig.config.camera.twoFingerPanEnabled);
        
        if (shouldPreventDefault) {
            e.preventDefault();
        } else {
            // Allow normal browser scrolling for page navigation
            console.log("🔄 Allowing browser scroll event");
        }
        
        // Update trackpad detection
        this.wheelEventCount++;
        if (this.wheelEventCount <= 5) {
            this.inputConfig.updateTrackpadDetection(e);
        }
        
        const config = this.inputConfig.config.camera;
        
        // Detect pinch-to-zoom (Ctrl+wheel or gesture)
        if (e.ctrlKey || e.metaKey) {
            // Pinch zoom on trackpad (browsers send ctrl+wheel for pinch)
            const zoomDelta = -e.deltaY * config.pinchZoomSpeed;
            this.emit("pinchzoom", {
                delta: config.zoomInverted ? -zoomDelta : zoomDelta,
                clientX: e.clientX,
                clientY: e.clientY
            });
        } 
        // Two-finger pan on trackpad (horizontal or vertical scroll without modifiers)
        else if (config.trackpadEnabled && (Math.abs(e.deltaX) > 0 || Math.abs(e.deltaY) > 0)) {
            const isTrackpadPan = this.inputConfig.isTrackpad && config.twoFingerPanEnabled;
            
            if (isTrackpadPan) {
                // Two-finger trackpad pan
                const panX = e.deltaX * config.trackpadPanSpeed;
                const panY = e.deltaY * config.trackpadPanSpeed;
                
                this.emit("trackpadpan", {
                    deltaX: config.trackpadPanInverted ? -panX : panX,
                    deltaY: config.trackpadPanInverted ? -panY : panY
                });
            } else {
                // Regular mouse wheel zoom
                const zoomDelta = -e.deltaY * config.wheelZoomSpeed;
                this.emit("wheelzoom", {
                    delta: config.zoomInverted ? -zoomDelta : zoomDelta,
                    clientX: e.clientX,
                    clientY: e.clientY
                });
            }
        }
        
        // Always emit the raw wheel event for compatibility
        this.emit("wheel", e);
    }
    
    /**
     * Handle touch start for pinch/pan gestures
     */
    handleTouchStart(e) {
        // Store all active touches
        for (let i = 0; i < e.touches.length; i++) {
            const touch = e.touches[i];
            this.touches.set(touch.identifier, {
                x: touch.clientX,
                y: touch.clientY,
                startX: touch.clientX,
                startY: touch.clientY
            });
        }
        
        // Detect pinch gesture start
        if (e.touches.length === 2) {
            const touch1 = e.touches[0];
            const touch2 = e.touches[1];
            this.lastTouchDistance = this.getTouchDistance(touch1, touch2);
            this.isPinching = true;
            this.isPanning = false;
        } else if (e.touches.length === 1) {
            this.isPanning = true;
            this.isPinching = false;
        }
        
        this.emit("touchstart", e);
    }
    
    /**
     * Handle touch move for pinch/pan gestures
     */
    handleTouchMove(e) {
        const config = this.inputConfig.config.camera;
        let shouldPreventDefault = false;
        
        // Update touch positions
        for (let i = 0; i < e.touches.length; i++) {
            const touch = e.touches[i];
            if (this.touches.has(touch.identifier)) {
                const stored = this.touches.get(touch.identifier);
                stored.x = touch.clientX;
                stored.y = touch.clientY;
            }
        }
        
        // Handle pinch zoom
        if (this.isPinching && e.touches.length === 2 && config.pinchToZoomEnabled) {
            shouldPreventDefault = true;
            
            const touch1 = e.touches[0];
            const touch2 = e.touches[1];
            const distance = this.getTouchDistance(touch1, touch2);
            
            if (this.lastTouchDistance > 0) {
                const scale = distance / this.lastTouchDistance;
                const centerX = (touch1.clientX + touch2.clientX) / 2;
                const centerY = (touch1.clientY + touch2.clientY) / 2;
                
                this.emit("pinchzoom", {
                    delta: (scale - 1) * 2, // Convert scale to delta
                    clientX: centerX,
                    clientY: centerY
                });
            }
            
            this.lastTouchDistance = distance;
        }
        // Handle single touch pan
        else if (this.isPanning && e.touches.length === 1) {
            const touch = e.touches[0];
            const stored = this.touches.get(touch.identifier);
            
            if (stored) {
                const deltaX = touch.clientX - stored.startX;
                const deltaY = touch.clientY - stored.startY;
                
                // Only prevent default and handle pan if we've moved enough (not a tap)
                if (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5) {
                    shouldPreventDefault = true;
                    
                    this.emit("touchpan", {
                        deltaX: deltaX,
                        deltaY: deltaY,
                        clientX: touch.clientX,
                        clientY: touch.clientY
                    });
                }
            }
        }
        
        // Only prevent default when we actually need to (better event handling)
        if (shouldPreventDefault) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        this.emit("touchmove", e);
    }
    
    /**
     * Handle touch end
     */
    handleTouchEnd(e) {
        // Remove ended touches
        for (let i = 0; i < e.changedTouches.length; i++) {
            const touch = e.changedTouches[i];
            this.touches.delete(touch.identifier);
        }
        
        // Reset gesture states
        if (e.touches.length === 0) {
            this.isPinching = false;
            this.isPanning = false;
            this.lastTouchDistance = 0;
            this.touches.clear();
        } else if (e.touches.length === 1) {
            // Switch from pinch to pan
            this.isPinching = false;
            this.isPanning = true;
            
            // Reset the start position for the remaining touch
            const touch = e.touches[0];
            if (this.touches.has(touch.identifier)) {
                const stored = this.touches.get(touch.identifier);
                stored.startX = stored.x;
                stored.startY = stored.y;
            }
        }
        
        this.emit("touchend", e);
    }
    
    /**
     * Calculate distance between two touches
     */
    getTouchDistance(touch1, touch2) {
        const dx = touch2.clientX - touch1.clientX;
        const dy = touch2.clientY - touch1.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    /**
     * Remove a specific event listener callback
     */
    removeListener(event, callback) {
        if (!this.listeners.has(event)) return false;
        
        const callbacks = this.listeners.get(event);
        const index = callbacks.indexOf(callback);
        
        if (index !== -1) {
            callbacks.splice(index, 1);
            if (callbacks.length === 0) {
                this.listeners.delete(event);
            }
            return true;
        }
        
        return false;
    }
    
    /**
     * Remove all listeners for a specific event
     */
    removeAllListeners(event) {
        if (event) {
            this.listeners.delete(event);
        } else {
            this.listeners.clear();
        }
    }
    
    /**
     * Clean up all event listeners and resources
     */
    destroy() {
        if (this.isDestroyed) {
            console.warn("InputHandler already destroyed");
            return;
        }
        
        console.log("🗑️ Destroying InputHandler...");
        
        this.isDestroyed = true;
        
        // Remove DOM event listeners
        for (const [eventType, handler] of this.eventListeners) {
            try {
                this.element.removeEventListener(eventType, handler);
            } catch (error) {
                console.warn(`Failed to remove ${eventType} listener:`, error);
            }
        }
        
        // Clear all event listener references
        this.eventListeners.clear();
        this.listeners.clear();
        
        // Clear state
        this.keys.clear();
        this.mouseButtons.clear();
        this.touches.clear();
        
        // Reset references
        this.element = null;
        this.inputConfig = null;
        this.mousePosition = null;
        
        console.log("✅ InputHandler destroyed successfully");
    }
    
    /**
     * Check if InputHandler is destroyed
     */
    isAlive() {
        return !this.isDestroyed;
    }
    
    /**
     * Clean up event listeners
     */
    cleanup() {
        if (this.isDestroyed) return;
        
        console.log("🧹 Cleaning up InputHandler...");
        
        // Remove all DOM event listeners
        for (const [eventName, handler] of this.eventListeners) {
            this.element.removeEventListener(eventName, handler);
        }
        this.eventListeners.clear();
        
        // Clear custom event listeners
        this.listeners.clear();
        
        // Clear state
        this.keys.clear();
        this.mouseButtons.clear();
        this.touches.clear();
        
        this.isDestroyed = true;
        console.log("✅ InputHandler cleanup completed");
    }
    
    /**
     * Get event listener statistics for debugging
     */
    getListenerStats() {
        const stats = {
            domListeners: this.eventListeners.size,
            customListeners: this.listeners.size,
            totalCallbacks: 0,
            isDestroyed: this.isDestroyed
        };
        
        for (const callbacks of this.listeners.values()) {
            stats.totalCallbacks += callbacks.length;
        }
        
        return stats;
    }
}