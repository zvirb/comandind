/**
 * InputBatcher - Optimized input event batching system
 * 
 * High-performance input processing system that batches mouse/touch events
 * to prevent UI lag and maintain 60+ FPS performance. Processes multiple
 * events per frame while maintaining responsive game controls.
 * 
 * Features:
 * - Event batching and deduplication
 * - Touch and mouse unification
 * - Coordinate transformation caching
 * - Priority-based event processing
 * - Multi-touch gesture recognition
 * - Input lag minimization
 */

export class InputBatcher {
    constructor(inputHandler, camera, options = {}) {
        this.inputHandler = inputHandler;
        this.camera = camera;
        
        // Configuration
        this.config = {
            batchSize: options.batchSize || 16,
            processFrequency: options.processFrequency || 60, // Hz
            maxEventAge: options.maxEventAge || 33, // ms
            enableDeduplication: options.enableDeduplication !== false,
            enableGestures: options.enableGestures !== false,
            mouseThreshold: options.mouseThreshold || 2, // pixels
            touchThreshold: options.touchThreshold || 4, // pixels
            dragThreshold: options.dragThreshold || 8, // pixels
            doubleTapTime: options.doubleTapTime || 300 // ms
        };
        
        // Event batching state
        this.eventQueue = [];
        this.processedEvents = [];
        this.lastProcessTime = 0;
        this.processInterval = 1000 / this.config.processFrequency;
        
        // Input state tracking
        this.inputState = {
            mouse: {
                x: 0,
                y: 0,
                worldX: 0,
                worldY: 0,
                buttons: 0,
                lastUpdate: 0
            },
            touches: new Map(), // touchId -> touch data
            activePointers: new Set(),
            isDragging: false,
            dragStart: null,
            lastTap: null
        };
        
        // Coordinate transformation cache
        this.transformCache = {
            lastCameraState: null,
            screenToWorld: new Map(),
            worldToScreen: new Map(),
            cacheTime: 0,
            maxCacheAge: 16 // ms - 1 frame at 60fps
        };
        
        // Event handlers registry
        this.eventHandlers = new Map();
        this.priorityHandlers = new Map(); // High-priority handlers
        
        // Performance tracking
        this.stats = {
            eventsReceived: 0,
            eventsProcessed: 0,
            eventsBatched: 0,
            eventsDeduped: 0,
            cacheHits: 0,
            cacheMisses: 0,
            averageProcessTime: 0,
            maxProcessTime: 0
        };
        
        // Touch gesture state
        this.gestureState = {
            pinchStart: null,
            pinchScale: 1,
            rotationStart: null,
            twoFingerStart: null,
            panVelocity: { x: 0, y: 0 }
        };
        
        this.isDestroyed = false;
        this.rafId = null;
        
        this.init();
    }
    
    /**
     * Initialize the input batcher
     */
    init() {
        console.log('⌨️  Initializing InputBatcher...');
        
        // Start processing loop
        this.startProcessingLoop();
        
        // Setup native event interception
        this.setupEventInterception();
        
        console.log(`✅ InputBatcher initialized - Processing at ${this.config.processFrequency}Hz`);
    }
    
    /**
     * Start the input processing loop
     */
    startProcessingLoop() {
        const processLoop = (timestamp) => {
            if (this.isDestroyed) return;
            
            if (timestamp - this.lastProcessTime >= this.processInterval) {
                this.processEventBatch(timestamp);
                this.lastProcessTime = timestamp;
            }
            
            this.rafId = requestAnimationFrame(processLoop);
        };
        
        this.rafId = requestAnimationFrame(processLoop);
    }
    
    /**
     * Setup native event interception to batch inputs
     */
    setupEventInterception() {
        // Intercept mouse events
        const mouseHandler = (event) => {
            this.queueEvent({
                type: event.type,
                sourceType: 'mouse',
                x: event.clientX,
                y: event.clientY,
                button: event.button,
                buttons: event.buttons,
                timestamp: performance.now(),
                originalEvent: event
            });
        };
        
        // Intercept touch events
        const touchHandler = (event) => {
            const touches = Array.from(event.changedTouches).map(touch => ({
                id: touch.identifier,
                x: touch.clientX,
                y: touch.clientY,
                force: touch.force || 1
            }));
            
            this.queueEvent({
                type: event.type,
                sourceType: 'touch',
                touches: touches,
                timestamp: performance.now(),
                originalEvent: event
            });
        };
        
        // Register event listeners if inputHandler exists
        if (this.inputHandler && this.inputHandler.on) {
            // Mouse events
            ['mousedown', 'mouseup', 'mousemove'].forEach(eventType => {
                this.inputHandler.on(eventType, mouseHandler);
            });
            
            // Touch events
            ['touchstart', 'touchend', 'touchmove', 'touchcancel'].forEach(eventType => {
                this.inputHandler.on(eventType, touchHandler);
            });
        }
        
        console.log('🖱️  Native event interception setup complete');
    }
    
    /**
     * Queue input event for batch processing
     */
    queueEvent(event) {
        if (this.isDestroyed) return;
        
        this.stats.eventsReceived++;
        
        // Add to queue
        this.eventQueue.push(event);
        
        // Limit queue size to prevent memory issues
        if (this.eventQueue.length > this.config.batchSize * 4) {
            const removed = this.eventQueue.splice(0, this.config.batchSize);
            console.warn(`⚠️ Input queue overflow, removed ${removed.length} old events`);
        }
    }
    
    /**
     * Process batched events
     */
    processEventBatch(timestamp) {
        if (this.eventQueue.length === 0) return;
        
        const startTime = performance.now();
        
        // Get events to process
        const eventsToProcess = this.eventQueue.splice(0, this.config.batchSize);
        
        // Remove stale events
        const currentTime = performance.now();
        const freshEvents = eventsToProcess.filter(event => 
            (currentTime - event.timestamp) <= this.config.maxEventAge
        );
        
        if (freshEvents.length < eventsToProcess.length) {
            console.debug(`🗑️ Discarded ${eventsToProcess.length - freshEvents.length} stale events`);
        }
        
        // Deduplicate events if enabled
        let processEvents = freshEvents;
        if (this.config.enableDeduplication) {
            processEvents = this.deduplicateEvents(freshEvents);
        }
        
        // Process each event
        for (const event of processEvents) {
            this.processEvent(event);
        }
        
        this.stats.eventsBatched += processEvents.length;
        this.stats.eventsProcessed += processEvents.length;
        
        // Update performance stats
        const processTime = performance.now() - startTime;
        this.stats.averageProcessTime = (this.stats.averageProcessTime + processTime) / 2;
        this.stats.maxProcessTime = Math.max(this.stats.maxProcessTime, processTime);
        
        // Warn if processing is taking too long
        if (processTime > 8) { // More than half a frame at 60fps
            console.warn(`⚠️ Input processing slow: ${processTime.toFixed(2)}ms`);
        }
    }
    
    /**
     * Deduplicate similar events to reduce processing load
     */
    deduplicateEvents(events) {
        if (events.length <= 1) return events;
        
        const deduplicated = [];
        let lastMouseMove = null;
        let lastTouchMove = null;
        
        for (const event of events) {
            let shouldKeep = true;
            
            // Deduplicate mouse move events
            if (event.type === 'mousemove' && event.sourceType === 'mouse') {
                if (lastMouseMove) {
                    const dx = Math.abs(event.x - lastMouseMove.x);
                    const dy = Math.abs(event.y - lastMouseMove.y);
                    
                    if (dx < this.config.mouseThreshold && dy < this.config.mouseThreshold) {
                        shouldKeep = false;
                        this.stats.eventsDeduped++;
                    }
                }
                
                if (shouldKeep) {
                    lastMouseMove = event;
                }
            }
            
            // Deduplicate touch move events
            if (event.type === 'touchmove' && event.sourceType === 'touch') {
                if (lastTouchMove && event.touches.length === 1 && lastTouchMove.touches.length === 1) {
                    const dx = Math.abs(event.touches[0].x - lastTouchMove.touches[0].x);
                    const dy = Math.abs(event.touches[0].y - lastTouchMove.touches[0].y);
                    
                    if (dx < this.config.touchThreshold && dy < this.config.touchThreshold) {
                        shouldKeep = false;
                        this.stats.eventsDeduped++;
                    }
                }
                
                if (shouldKeep) {
                    lastTouchMove = event;
                }
            }
            
            if (shouldKeep) {
                deduplicated.push(event);
            }
        }
        
        return deduplicated;
    }
    
    /**
     * Process individual event
     */
    processEvent(event) {
        // Update internal state
        this.updateInputState(event);
        
        // Transform coordinates
        const transformedEvent = this.transformEventCoordinates(event);
        
        // Detect gestures for touch events
        if (event.sourceType === 'touch' && this.config.enableGestures) {
            this.processGestures(transformedEvent);
        }
        
        // Dispatch to registered handlers
        this.dispatchEvent(transformedEvent);
    }
    
    /**
     * Update internal input state
     */
    updateInputState(event) {
        const now = performance.now();
        
        if (event.sourceType === 'mouse') {
            this.inputState.mouse.x = event.x;
            this.inputState.mouse.y = event.y;
            this.inputState.mouse.buttons = event.buttons || 0;
            this.inputState.mouse.lastUpdate = now;
            
            // Track dragging
            if (event.type === 'mousedown' && event.button === 0) {
                this.inputState.dragStart = { x: event.x, y: event.y, time: now };
                this.inputState.isDragging = false;
            } else if (event.type === 'mousemove' && this.inputState.dragStart) {
                const dx = Math.abs(event.x - this.inputState.dragStart.x);
                const dy = Math.abs(event.y - this.inputState.dragStart.y);
                
                if (!this.inputState.isDragging && (dx > this.config.dragThreshold || dy > this.config.dragThreshold)) {
                    this.inputState.isDragging = true;
                }
            } else if (event.type === 'mouseup') {
                this.inputState.dragStart = null;
                this.inputState.isDragging = false;
            }
        }
        
        if (event.sourceType === 'touch') {
            // Update touch state
            event.touches.forEach(touch => {
                if (event.type === 'touchstart') {
                    this.inputState.touches.set(touch.id, {
                        x: touch.x,
                        y: touch.y,
                        startX: touch.x,
                        startY: touch.y,
                        startTime: now,
                        force: touch.force
                    });
                    this.inputState.activePointers.add(touch.id);
                } else if (event.type === 'touchmove') {
                    const existing = this.inputState.touches.get(touch.id);
                    if (existing) {
                        existing.x = touch.x;
                        existing.y = touch.y;
                    }
                } else if (event.type === 'touchend' || event.type === 'touchcancel') {
                    // Detect tap
                    const touchData = this.inputState.touches.get(touch.id);
                    if (touchData) {
                        const dx = Math.abs(touch.x - touchData.startX);
                        const dy = Math.abs(touch.y - touchData.startY);
                        const duration = now - touchData.startTime;
                        
                        if (dx < this.config.touchThreshold && dy < this.config.touchThreshold && duration < 300) {
                            // It's a tap - check for double tap
                            if (this.inputState.lastTap && (now - this.inputState.lastTap.time) < this.config.doubleTapTime) {
                                // Double tap detected
                                this.dispatchCustomEvent('doubletap', {
                                    x: touch.x,
                                    y: touch.y,
                                    worldX: this.screenToWorld(touch.x, touch.y).x,
                                    worldY: this.screenToWorld(touch.x, touch.y).y
                                });
                            } else {
                                this.inputState.lastTap = { x: touch.x, y: touch.y, time: now };
                            }
                        }
                    }
                    
                    this.inputState.touches.delete(touch.id);
                    this.inputState.activePointers.delete(touch.id);
                }
            });
        }
    }
    
    /**
     * Transform event coordinates to world space
     */
    transformEventCoordinates(event) {
        const transformedEvent = { ...event };
        
        if (event.sourceType === 'mouse') {
            const worldPos = this.screenToWorld(event.x, event.y);
            transformedEvent.worldX = worldPos.x;
            transformedEvent.worldY = worldPos.y;
            
            // Update cached mouse world position
            this.inputState.mouse.worldX = worldPos.x;
            this.inputState.mouse.worldY = worldPos.y;
        }
        
        if (event.sourceType === 'touch') {
            transformedEvent.touches = event.touches.map(touch => {
                const worldPos = this.screenToWorld(touch.x, touch.y);
                return {
                    ...touch,
                    worldX: worldPos.x,
                    worldY: worldPos.y
                };
            });
        }
        
        return transformedEvent;
    }
    
    /**
     * Process touch gestures
     */
    processGestures(event) {
        if (event.sourceType !== 'touch') return;
        
        const touches = Array.from(this.inputState.touches.values());
        
        // Two-finger gestures (pinch, rotate, pan)
        if (touches.length === 2) {
            const [touch1, touch2] = touches;
            const currentDistance = Math.hypot(touch2.x - touch1.x, touch2.y - touch1.y);
            const currentAngle = Math.atan2(touch2.y - touch1.y, touch2.x - touch1.x);
            const centerX = (touch1.x + touch2.x) / 2;
            const centerY = (touch1.y + touch2.y) / 2;
            
            if (event.type === 'touchstart' && !this.gestureState.twoFingerStart) {
                // Start two-finger gesture
                this.gestureState.twoFingerStart = {
                    distance: currentDistance,
                    angle: currentAngle,
                    centerX: centerX,
                    centerY: centerY
                };
                this.gestureState.pinchStart = currentDistance;
                this.gestureState.rotationStart = currentAngle;
            } else if (event.type === 'touchmove' && this.gestureState.twoFingerStart) {
                // Pinch detection
                const scaleChange = currentDistance / this.gestureState.pinchStart;
                if (Math.abs(scaleChange - 1) > 0.1) { // 10% threshold
                    this.dispatchCustomEvent('pinch', {
                        scale: scaleChange,
                        centerX: centerX,
                        centerY: centerY,
                        worldCenterX: this.screenToWorld(centerX, centerY).x,
                        worldCenterY: this.screenToWorld(centerX, centerY).y
                    });
                }
                
                // Rotation detection
                const rotationChange = currentAngle - this.gestureState.rotationStart;
                if (Math.abs(rotationChange) > 0.2) { // ~11 degrees threshold
                    this.dispatchCustomEvent('rotate', {
                        rotation: rotationChange,
                        centerX: centerX,
                        centerY: centerY
                    });
                }
            } else if (event.type === 'touchend') {
                this.gestureState.twoFingerStart = null;
                this.gestureState.pinchStart = null;
                this.gestureState.rotationStart = null;
            }
        }
    }
    
    /**
     * Screen to world coordinate transformation with caching
     */
    screenToWorld(screenX, screenY) {
        if (!this.camera) {
            return { x: screenX, y: screenY };
        }
        
        // Check cache
        const cacheKey = `${screenX}_${screenY}`;
        const cached = this.transformCache.screenToWorld.get(cacheKey);
        
        if (cached && (performance.now() - this.transformCache.cacheTime) < this.transformCache.maxCacheAge) {
            this.stats.cacheHits++;
            return cached;
        }
        
        // Transform coordinates
        const result = this.camera.screenToWorld(screenX, screenY);
        
        // Cache result
        this.transformCache.screenToWorld.set(cacheKey, result);
        this.transformCache.cacheTime = performance.now();
        this.stats.cacheMisses++;
        
        // Limit cache size
        if (this.transformCache.screenToWorld.size > 100) {
            const firstKey = this.transformCache.screenToWorld.keys().next().value;
            this.transformCache.screenToWorld.delete(firstKey);
        }
        
        return result;
    }
    
    /**
     * Register event handler
     */
    on(eventType, handler, priority = 'normal') {
        const handlers = priority === 'high' ? this.priorityHandlers : this.eventHandlers;
        
        if (!handlers.has(eventType)) {
            handlers.set(eventType, []);
        }
        
        handlers.get(eventType).push(handler);
        
        console.log(`📝 Registered ${priority} priority handler for ${eventType}`);
    }
    
    /**
     * Remove event handler
     */
    off(eventType, handler) {
        // Check both priority levels
        [this.eventHandlers, this.priorityHandlers].forEach(handlers => {
            const eventHandlers = handlers.get(eventType);
            if (eventHandlers) {
                const index = eventHandlers.indexOf(handler);
                if (index !== -1) {
                    eventHandlers.splice(index, 1);
                }
            }
        });
    }
    
    /**
     * Dispatch event to registered handlers
     */
    dispatchEvent(event) {
        // Dispatch to high-priority handlers first
        this.dispatchToHandlers(event, this.priorityHandlers);
        
        // Then to normal priority handlers
        this.dispatchToHandlers(event, this.eventHandlers);
    }
    
    /**
     * Dispatch to specific handler group
     */
    dispatchToHandlers(event, handlerMap) {
        const handlers = handlerMap.get(event.type);
        if (!handlers) return;
        
        for (const handler of handlers) {
            try {
                handler(event);
            } catch (error) {
                console.error(`❌ Error in input event handler for ${event.type}:`, error);
            }
        }
    }
    
    /**
     * Dispatch custom event
     */
    dispatchCustomEvent(eventType, data) {
        const customEvent = {
            type: eventType,
            sourceType: 'gesture',
            timestamp: performance.now(),
            ...data
        };
        
        this.dispatchEvent(customEvent);
    }
    
    /**
     * Get current input state
     */
    getInputState() {
        return {
            mouse: { ...this.inputState.mouse },
            touchCount: this.inputState.touches.size,
            isDragging: this.inputState.isDragging,
            hasActivePointers: this.inputState.activePointers.size > 0
        };
    }
    
    /**
     * Clear transformation cache
     */
    clearTransformCache() {
        this.transformCache.screenToWorld.clear();
        this.transformCache.worldToScreen.clear();
        this.transformCache.cacheTime = 0;
    }
    
    /**
     * Get performance statistics
     */
    getStats() {
        return {
            ...this.stats,
            queueLength: this.eventQueue.length,
            cacheSize: this.transformCache.screenToWorld.size,
            cacheHitRate: this.stats.cacheHits / (this.stats.cacheHits + this.stats.cacheMisses),
            activeTouches: this.inputState.touches.size,
            registeredHandlers: this.eventHandlers.size + this.priorityHandlers.size
        };
    }
    
    /**
     * Update configuration
     */
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        
        // Update processing frequency if changed
        if (newConfig.processFrequency) {
            this.processInterval = 1000 / newConfig.processFrequency;
        }
        
        console.log('⚙️  InputBatcher config updated:', this.config);
    }
    
    /**
     * Destroy and cleanup
     */
    destroy() {
        if (this.isDestroyed) return;
        
        console.log('🗑️ Destroying InputBatcher...');
        this.isDestroyed = true;
        
        // Cancel animation frame
        if (this.rafId) {
            cancelAnimationFrame(this.rafId);
            this.rafId = null;
        }
        
        // Clear event queues
        this.eventQueue = [];
        this.processedEvents = [];
        
        // Clear handlers
        this.eventHandlers.clear();
        this.priorityHandlers.clear();
        
        // Clear caches
        this.clearTransformCache();
        
        // Clear state
        this.inputState.touches.clear();
        this.inputState.activePointers.clear();
        
        console.log('✅ InputBatcher destroyed successfully');
    }
}