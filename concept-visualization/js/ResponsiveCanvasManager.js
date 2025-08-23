/**
 * ResponsiveCanvasManager - Advanced Canvas Management System
 * 
 * Handles responsive canvas sizing, device-specific optimizations,
 * touch input, and performance management for different device capabilities.
 * 
 * Features:
 * - Automatic canvas scaling based on device capabilities
 * - Touch and mouse input handling
 * - Memory management for low-end devices
 * - Performance monitoring and optimization
 * - High-DPI display support
 */

class ResponsiveCanvasManager {
    constructor(canvas, options = {}) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        
        // Configuration
        this.config = {
            minScale: 0.25,
            maxScale: 3.0,
            baseWidth: 1280,  // Base resolution width
            baseHeight: 960,  // Base resolution height
            enableTouch: true,
            enableMouse: true,
            enableHighDPI: true,
            performanceMode: 'auto', // 'auto', 'performance', 'quality'
            ...options
        };
        
        // Device capabilities
        this.deviceCapabilities = this.detectDeviceCapabilities();
        
        // State management
        this.state = {
            scale: 1,
            offsetX: 0,
            offsetY: 0,
            isDragging: false,
            lastTouchTime: 0,
            touchStartDistance: 0,
            renderRequests: 0,
            lastFrameTime: 0,
            fps: 60,
            isVisible: true
        };
        
        // Input handling
        this.inputHandlers = {
            onPinch: null,
            onPan: null,
            onClick: null,
            onDoubleClick: null,
            onLongPress: null
        };
        
        // Performance monitoring
        this.performanceMetrics = {
            frameCount: 0,
            totalFrameTime: 0,
            avgFps: 60,
            memoryUsage: 0,
            renderTime: 0
        };
        
        // Initialize the manager
        this.initialize();
    }
    
    detectDeviceCapabilities() {
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const isTablet = /iPad|Android(?=.*\bmobile\b)/i.test(navigator.userAgent) && window.innerWidth >= 768;
        const memoryInfo = navigator.deviceMemory || (isMobile ? 2 : 8);
        const isLowEnd = memoryInfo < 4 || (isMobile && !isTablet);
        
        // Estimate device performance tier
        let performanceTier = 'high';
        if (isLowEnd) performanceTier = 'low';
        else if (isMobile || memoryInfo < 8) performanceTier = 'medium';
        
        return {
            isMobile,
            isTablet,
            isLowEnd,
            deviceMemory: memoryInfo,
            performanceTier,
            pixelRatio: window.devicePixelRatio || 1,
            maxTextureSize: this.getMaxTextureSize(),
            supportsTouch: 'ontouchstart' in window,
            supportsPassiveEvents: this.checkPassiveEventSupport(),
            hardwareConcurrency: navigator.hardwareConcurrency || 4
        };
    }
    
    getMaxTextureSize() {
        try {
            const testCanvas = document.createElement('canvas');
            const gl = testCanvas.getContext('webgl') || testCanvas.getContext('experimental-webgl');
            if (gl) {
                return gl.getParameter(gl.MAX_TEXTURE_SIZE);
            }
        } catch (e) {
            // WebGL not supported
        }
        
        // Fallback estimation
        return this.deviceCapabilities?.isLowEnd ? 1024 : 2048;
    }
    
    checkPassiveEventSupport() {
        let passiveSupported = false;
        try {
            const options = {
                get passive() {
                    passiveSupported = true;
                    return false;
                }
            };
            window.addEventListener('test', null, options);
            window.removeEventListener('test', null, options);
        } catch (err) {
            passiveSupported = false;
        }
        return passiveSupported;
    }
    
    initialize() {
        this.setupCanvas();
        this.setupInputHandlers();
        this.setupResizeObserver();
        this.setupVisibilityChange();
        this.startPerformanceMonitoring();
        
        console.log('ResponsiveCanvasManager initialized:', {
            device: this.deviceCapabilities.performanceTier,
            mobile: this.deviceCapabilities.isMobile,
            memory: this.deviceCapabilities.deviceMemory + 'GB',
            pixelRatio: this.deviceCapabilities.pixelRatio
        });
    }
    
    setupCanvas() {
        const container = this.canvas.parentElement;
        const containerRect = container ? container.getBoundingClientRect() : { width: window.innerWidth, height: window.innerHeight };
        
        // Calculate optimal canvas dimensions
        const maxWidth = this.deviceCapabilities.isLowEnd ? 800 : this.config.baseWidth;
        const maxHeight = this.deviceCapabilities.isLowEnd ? 600 : this.config.baseHeight;
        
        const scaleX = containerRect.width / maxWidth;
        const scaleY = containerRect.height / maxHeight;
        let scale = Math.min(scaleX, scaleY);
        
        // Apply device-specific scaling constraints
        scale = Math.max(this.config.minScale, Math.min(this.config.maxScale, scale));
        
        // Adjust for device performance
        if (this.deviceCapabilities.performanceTier === 'low') {
            scale = Math.min(scale, 1.0);
        }
        
        const canvasWidth = maxWidth * scale;
        const canvasHeight = maxHeight * scale;
        
        // Set canvas size
        this.canvas.width = canvasWidth * (this.config.enableHighDPI ? this.deviceCapabilities.pixelRatio : 1);
        this.canvas.height = canvasHeight * (this.config.enableHighDPI ? this.deviceCapabilities.pixelRatio : 1);
        
        // Set CSS size
        this.canvas.style.width = canvasWidth + 'px';
        this.canvas.style.height = canvasHeight + 'px';
        
        // Scale context for high-DPI displays
        if (this.config.enableHighDPI && this.deviceCapabilities.pixelRatio > 1) {
            this.ctx.scale(this.deviceCapabilities.pixelRatio, this.deviceCapabilities.pixelRatio);
        }
        
        this.state.scale = scale;
        
        console.log(`Canvas configured: ${canvasWidth}x${canvasHeight}px (scale: ${scale.toFixed(2)})`);
    }
    
    setupInputHandlers() {
        if (this.deviceCapabilities.supportsTouch && this.config.enableTouch) {
            this.setupTouchHandlers();
        }
        
        if (this.config.enableMouse) {
            this.setupMouseHandlers();
        }
    }
    
    setupTouchHandlers() {
        const eventOptions = this.deviceCapabilities.supportsPassiveEvents ? { passive: false } : false;
        
        this.canvas.addEventListener('touchstart', this.handleTouchStart.bind(this), eventOptions);
        this.canvas.addEventListener('touchmove', this.handleTouchMove.bind(this), eventOptions);
        this.canvas.addEventListener('touchend', this.handleTouchEnd.bind(this), eventOptions);
        this.canvas.addEventListener('touchcancel', this.handleTouchEnd.bind(this), eventOptions);
        
        console.log('Touch handlers configured');
    }
    
    setupMouseHandlers() {
        this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));
        this.canvas.addEventListener('wheel', this.handleWheel.bind(this));
        this.canvas.addEventListener('click', this.handleClick.bind(this));
        this.canvas.addEventListener('dblclick', this.handleDoubleClick.bind(this));
        
        console.log('Mouse handlers configured');
    }
    
    setupResizeObserver() {
        if (window.ResizeObserver) {
            const resizeObserver = new ResizeObserver((entries) => {
                if (this.state.isVisible) {
                    this.handleResize();
                }
            });
            
            const container = this.canvas.parentElement || document.body;
            resizeObserver.observe(container);
        } else {
            // Fallback to window resize
            window.addEventListener('resize', () => {
                if (this.state.isVisible) {
                    setTimeout(() => this.handleResize(), 100);
                }
            });
        }
    }
    
    setupVisibilityChange() {
        document.addEventListener('visibilitychange', () => {
            this.state.isVisible = !document.hidden;
            if (this.state.isVisible) {
                this.startPerformanceMonitoring();
            }
        });
    }
    
    // Touch event handlers
    handleTouchStart(event) {
        event.preventDefault();
        const touches = event.touches;
        
        if (touches.length === 1) {
            // Single touch - start pan or prepare for long press
            this.state.isDragging = false;
            this.startTouch = this.getTouchPosition(touches[0]);
            this.state.lastTouchTime = Date.now();
            
            // Setup long press detection
            this.longPressTimer = setTimeout(() => {
                if (!this.state.isDragging && this.inputHandlers.onLongPress) {
                    this.inputHandlers.onLongPress(this.startTouch);
                }
            }, 500);
            
        } else if (touches.length === 2) {
            // Pinch gesture start
            this.state.touchStartDistance = this.getTouchDistance(touches[0], touches[1]);
            this.clearLongPressTimer();
        }
    }
    
    handleTouchMove(event) {
        event.preventDefault();
        const touches = event.touches;
        
        if (touches.length === 1 && this.startTouch) {
            // Pan gesture
            const currentTouch = this.getTouchPosition(touches[0]);
            const deltaX = currentTouch.x - this.startTouch.x;
            const deltaY = currentTouch.y - this.startTouch.y;
            
            if (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5) {
                this.state.isDragging = true;
                this.clearLongPressTimer();
                
                if (this.inputHandlers.onPan) {
                    this.inputHandlers.onPan({ deltaX, deltaY, currentTouch, startTouch: this.startTouch });
                }
            }
            
        } else if (touches.length === 2) {
            // Pinch gesture
            const currentDistance = this.getTouchDistance(touches[0], touches[1]);
            const scale = currentDistance / this.state.touchStartDistance;
            
            if (this.inputHandlers.onPinch) {
                this.inputHandlers.onPinch({ scale, center: this.getTouchCenter(touches[0], touches[1]) });
            }
        }
    }
    
    handleTouchEnd(event) {
        const touches = event.changedTouches;
        
        if (touches.length === 1 && !this.state.isDragging) {
            // Tap gesture
            const touchPosition = this.getTouchPosition(touches[0]);
            const tapTime = Date.now() - this.state.lastTouchTime;
            
            if (tapTime < 200) {
                // Quick tap
                if (this.inputHandlers.onClick) {
                    this.inputHandlers.onClick(touchPosition);
                }
            }
        }
        
        this.clearLongPressTimer();
        this.state.isDragging = false;
        this.startTouch = null;
    }
    
    // Mouse event handlers
    handleMouseDown(event) {
        this.state.isDragging = true;
        this.lastMousePosition = { x: event.clientX, y: event.clientY };
    }
    
    handleMouseMove(event) {
        if (this.state.isDragging && this.inputHandlers.onPan) {
            const deltaX = event.clientX - this.lastMousePosition.x;
            const deltaY = event.clientY - this.lastMousePosition.y;
            
            this.inputHandlers.onPan({ 
                deltaX, 
                deltaY, 
                currentTouch: { x: event.clientX, y: event.clientY },
                startTouch: this.lastMousePosition 
            });
            
            this.lastMousePosition = { x: event.clientX, y: event.clientY };
        }
    }
    
    handleMouseUp(event) {
        this.state.isDragging = false;
        this.lastMousePosition = null;
    }
    
    handleWheel(event) {
        event.preventDefault();
        
        if (this.inputHandlers.onPinch) {
            const scale = event.deltaY > 0 ? 0.9 : 1.1;
            const rect = this.canvas.getBoundingClientRect();
            const center = {
                x: event.clientX - rect.left,
                y: event.clientY - rect.top
            };
            
            this.inputHandlers.onPinch({ scale, center });
        }
    }
    
    handleClick(event) {
        if (!this.state.isDragging && this.inputHandlers.onClick) {
            const rect = this.canvas.getBoundingClientRect();
            const position = {
                x: event.clientX - rect.left,
                y: event.clientY - rect.top
            };
            
            this.inputHandlers.onClick(position);
        }
    }
    
    handleDoubleClick(event) {
        if (this.inputHandlers.onDoubleClick) {
            const rect = this.canvas.getBoundingClientRect();
            const position = {
                x: event.clientX - rect.left,
                y: event.clientY - rect.top
            };
            
            this.inputHandlers.onDoubleClick(position);
        }
    }
    
    handleResize() {
        // Debounce resize events
        clearTimeout(this.resizeTimer);
        this.resizeTimer = setTimeout(() => {
            this.setupCanvas();
            
            // Trigger custom resize event
            this.canvas.dispatchEvent(new CustomEvent('canvasresize', {
                detail: {
                    width: this.canvas.width,
                    height: this.canvas.height,
                    scale: this.state.scale
                }
            }));
        }, 100);
    }
    
    // Performance monitoring
    startPerformanceMonitoring() {
        if (this.performanceTimer) {
            clearInterval(this.performanceTimer);
        }
        
        this.performanceTimer = setInterval(() => {
            this.updatePerformanceMetrics();
        }, 1000);
    }
    
    updatePerformanceMetrics() {
        const now = performance.now();
        
        if (this.performanceMetrics.frameCount > 0) {
            this.performanceMetrics.avgFps = this.performanceMetrics.frameCount;
            
            // Adjust performance mode based on FPS
            if (this.config.performanceMode === 'auto') {
                if (this.performanceMetrics.avgFps < 30 && this.deviceCapabilities.performanceTier !== 'low') {
                    this.deviceCapabilities.performanceTier = 'low';
                    console.log('Performance mode adjusted to low');
                } else if (this.performanceMetrics.avgFps > 50 && this.deviceCapabilities.performanceTier === 'low') {
                    this.deviceCapabilities.performanceTier = 'medium';
                    console.log('Performance mode adjusted to medium');
                }
            }
        }
        
        // Get memory info if available
        if (performance.memory) {
            this.performanceMetrics.memoryUsage = performance.memory.usedJSHeapSize / (1024 * 1024); // MB
        }
        
        this.performanceMetrics.frameCount = 0;
        this.performanceMetrics.totalFrameTime = 0;
    }
    
    // Utility methods
    getTouchPosition(touch) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: touch.clientX - rect.left,
            y: touch.clientY - rect.top
        };
    }
    
    getTouchDistance(touch1, touch2) {
        const dx = touch2.clientX - touch1.clientX;
        const dy = touch2.clientY - touch1.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    getTouchCenter(touch1, touch2) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: (touch1.clientX + touch2.clientX) / 2 - rect.left,
            y: (touch1.clientY + touch2.clientY) / 2 - rect.top
        };
    }
    
    clearLongPressTimer() {
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }
    }
    
    // Public API
    setInputHandler(event, handler) {
        if (this.inputHandlers.hasOwnProperty('on' + event.charAt(0).toUpperCase() + event.slice(1))) {
            this.inputHandlers['on' + event.charAt(0).toUpperCase() + event.slice(1)] = handler;
        }
    }
    
    getDeviceCapabilities() {
        return { ...this.deviceCapabilities };
    }
    
    getPerformanceMetrics() {
        return { ...this.performanceMetrics };
    }
    
    getCanvasInfo() {
        return {
            width: this.canvas.width,
            height: this.canvas.height,
            cssWidth: parseInt(this.canvas.style.width),
            cssHeight: parseInt(this.canvas.style.height),
            scale: this.state.scale,
            pixelRatio: this.deviceCapabilities.pixelRatio
        };
    }
    
    requestFrame(callback) {
        this.state.renderRequests++;
        
        requestAnimationFrame((timestamp) => {
            const frameTime = timestamp - this.state.lastFrameTime;
            this.state.lastFrameTime = timestamp;
            
            this.performanceMetrics.frameCount++;
            this.performanceMetrics.totalFrameTime += frameTime;
            
            if (callback) {
                const renderStart = performance.now();
                callback(timestamp);
                this.performanceMetrics.renderTime = performance.now() - renderStart;
            }
        });
    }
    
    // Memory management
    optimizeForLowMemory() {
        if (this.deviceCapabilities.performanceTier === 'low') {
            // Reduce canvas resolution
            const currentWidth = this.canvas.width;
            const currentHeight = this.canvas.height;
            
            this.canvas.width = Math.floor(currentWidth * 0.75);
            this.canvas.height = Math.floor(currentHeight * 0.75);
            
            console.log(`Optimized canvas for low memory: ${currentWidth}x${currentHeight} -> ${this.canvas.width}x${this.canvas.height}`);
        }
    }
    
    cleanup() {
        // Clear all timers
        if (this.performanceTimer) clearInterval(this.performanceTimer);
        if (this.resizeTimer) clearTimeout(this.resizeTimer);
        if (this.longPressTimer) clearTimeout(this.longPressTimer);
        
        // Remove event listeners
        this.canvas.removeEventListener('touchstart', this.handleTouchStart);
        this.canvas.removeEventListener('touchmove', this.handleTouchMove);
        this.canvas.removeEventListener('touchend', this.handleTouchEnd);
        this.canvas.removeEventListener('touchcancel', this.handleTouchEnd);
        this.canvas.removeEventListener('mousedown', this.handleMouseDown);
        this.canvas.removeEventListener('mousemove', this.handleMouseMove);
        this.canvas.removeEventListener('mouseup', this.handleMouseUp);
        this.canvas.removeEventListener('wheel', this.handleWheel);
        this.canvas.removeEventListener('click', this.handleClick);
        this.canvas.removeEventListener('dblclick', this.handleDoubleClick);
        
        console.log('ResponsiveCanvasManager cleaned up');
    }
}

export default ResponsiveCanvasManager;