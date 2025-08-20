/**
 * Input Configuration System
 * Manages input preferences and control schemes
 */
export class InputConfig {
    constructor() {
        // Default configuration
        this.config = {
            // Camera controls
            camera: {
                // Zoom controls
                zoomMethod: "auto", // 'auto', 'wheel', 'pinch', 'keys'
                zoomSpeed: 0.1,
                zoomInverted: false,
                pinchZoomSpeed: 0.02,
                wheelZoomSpeed: 0.1,
                keyZoomSpeed: 0.05,
                
                // Pan controls  
                panMethod: "auto", // 'auto', 'edge', 'drag', 'keys', 'trackpad'
                edgeScrollSpeed: 5,
                dragPanSpeed: 1,
                trackpadPanSpeed: 2,
                keyPanSpeed: 10,
                edgeScrollThreshold: 50,
                
                // Trackpad specific
                trackpadEnabled: true,
                trackpadPanInverted: false,
                pinchToZoomEnabled: true,
                twoFingerPanEnabled: true,
                
                // Smoothing
                smoothing: 0.1,
                zoomSmoothing: 0.15
            },
            
            // Selection controls
            selection: {
                boxSelectThreshold: 5, // pixels before box select starts
                clickRadius: 5, // tolerance for clicks vs drags
                doubleClickTime: 300, // ms for double click
                multiSelectKey: "shift", // key for adding to selection
                toggleSelectKey: "ctrl", // key for toggle selection
            },
            
            // Command controls
            commands: {
                attackMoveKey: "a",
                stopKey: "s",
                holdPositionKey: "h",
                patrolKey: "p",
                queueCommandKey: "shift"
            },
            
            // Accessibility
            accessibility: {
                reducedMotion: false,
                highContrast: false,
                largeUI: false
            },
            
            // Navigation protection
            navigation: {
                allowBrowserShortcuts: true,
                allowRefresh: true,
                allowBackForward: true,
                protectFromNavigation: true,
                confirmOnExit: false // Set to true if game has unsaved changes
            }
        };
        
        // Load saved preferences
        this.loadPreferences();
        
        // Detect input devices
        this.detectInputDevices();
    }
    
    /**
     * Detect available input devices and set appropriate defaults
     */
    detectInputDevices() {
        // Guard against server-side execution
        if (typeof window === "undefined" || typeof navigator === "undefined") {
            console.log("InputConfig: Running in non-browser environment, using defaults");
            this.hasTouch = false;
            this.isTrackpad = false;
            this.detectionComplete = false;
            return;
        }
        
        // Initialize detection state
        this.detectionComplete = false;
        this.detectionConfidence = {
            touch: 0,
            trackpad: 0
        };
        
        // Check for touch support with multiple methods
        this.hasTouch = this.detectTouchSupport();
        
        // Check for trackpad vs mouse (heuristic based on platform)
        this.isTrackpad = this.detectTrackpad();
        
        // Set up dynamic detection
        this.setupDynamicDetection();
        
        // Auto-configure based on detected devices
        this.updateAutoConfiguration();
        
        console.log(`Input devices detected - Touch: ${this.hasTouch}, Trackpad: ${this.isTrackpad}`);
        this.logDetectionDetails();
        
        // Mark initial detection as complete
        this.detectionComplete = true;
    }
    
    /**
     * Set up dynamic detection that updates based on user interaction
     */
    setupDynamicDetection() {
        // Guard against server-side execution
        if (typeof window === "undefined") return;
        
        // Track interaction events for better detection
        this.interactionEvents = [];
        this.detectionListeners = [];
        
        // Listen for wheel events to detect trackpad behavior
        const wheelListener = (event) => {
            this.updateTrackpadDetection(event);
        };
        
        // Listen for touch events to confirm touch support
        const touchListener = (event) => {
            this.updateTouchDetection(event);
        };
        
        // Listen for pointer events for better device detection
        const pointerListener = (event) => {
            this.updatePointerDetection(event);
        };
        
        // Add event listeners with passive option for performance
        if (typeof window !== "undefined" && window.addEventListener) {
            window.addEventListener("wheel", wheelListener, { passive: true });
            window.addEventListener("touchstart", touchListener, { passive: true });
            window.addEventListener("touchmove", touchListener, { passive: true });
            window.addEventListener("pointerdown", pointerListener, { passive: true });
            window.addEventListener("pointermove", pointerListener, { passive: true });
            
            // Store listeners for cleanup
            this.detectionListeners.push(
                { event: "wheel", listener: wheelListener },
                { event: "touchstart", listener: touchListener },
                { event: "touchmove", listener: touchListener },
                { event: "pointerdown", listener: pointerListener },
                { event: "pointermove", listener: pointerListener }
            );
        }
        
        // Set up a timer to finalize detection after user interaction
        this.detectionTimeout = setTimeout(() => {
            this.finalizeDetection();
        }, 5000); // 5 seconds to observe user behavior
    }
    
    /**
     * Update auto-configuration based on current detection
     */
    updateAutoConfiguration() {
        if (this.config.camera.zoomMethod === "auto") {
            if (this.hasTouch) {
                this.config.camera.zoomMethod = "pinch";
            } else if (this.isTrackpad) {
                this.config.camera.zoomMethod = "pinch"; // Will use ctrl+wheel
            } else {
                this.config.camera.zoomMethod = "wheel";
            }
        }
        
        if (this.config.camera.panMethod === "auto") {
            if (this.hasTouch) {
                this.config.camera.panMethod = "drag";
            } else if (this.isTrackpad) {
                this.config.camera.panMethod = "trackpad";
            } else {
                this.config.camera.panMethod = "edge";
            }
        }
    }
    
    /**
     * Detect touch support using multiple methods
     */
    detectTouchSupport() {
        // Guard against server-side execution
        if (typeof window === "undefined" || typeof navigator === "undefined") {
            console.log("InputConfig: No browser environment, touch support: false");
            this.detectionConfidence.touch = 0;
            return false;
        }
        
        let touchScore = 0;
        const detectionMethods = [];
        
        // Method 1: Check for touch events in window object
        const hasOntouchstart = "ontouchstart" in window;
        if (hasOntouchstart) {
            touchScore += 20;
            detectionMethods.push("ontouchstart");
        }
        
        // Method 2: Check navigator.maxTouchPoints
        const maxTouchPoints = navigator.maxTouchPoints || 0;
        const hasMaxTouchPoints = maxTouchPoints > 0;
        if (hasMaxTouchPoints) {
            touchScore += 25;
            detectionMethods.push(`maxTouchPoints(${maxTouchPoints})`);
        }
        
        // Method 3: Check for TouchEvent constructor
        const hasTouchEvents = typeof TouchEvent !== "undefined";
        if (hasTouchEvents) {
            touchScore += 15;
            detectionMethods.push("TouchEvent");
        }
        
        // Method 4: Check for touch-specific APIs
        const hasTouchList = typeof TouchList !== "undefined";
        if (hasTouchList) {
            touchScore += 10;
            detectionMethods.push("TouchList");
        }
        
        // Method 5: Media query for pointer type
        let hasCoarsePointer = false;
        let hasHoverNone = false;
        try {
            if (window.matchMedia) {
                hasCoarsePointer = window.matchMedia("(pointer: coarse)").matches;
                hasHoverNone = window.matchMedia("(hover: none)").matches;
                
                if (hasCoarsePointer) {
                    touchScore += 20;
                    detectionMethods.push("coarsePointer");
                }
                if (hasHoverNone) {
                    touchScore += 15;
                    detectionMethods.push("hoverNone");
                }
            }
        } catch (e) {
            console.warn("InputConfig: Media query error:", e);
        }
        
        // Method 6: Enhanced user agent analysis
        const userAgent = (navigator.userAgent || "").toLowerCase();
        const platform = (navigator.platform || "").toLowerCase();
        
        const mobileIndicators = [
            "mobile", "tablet", "ipad", "iphone", "ipod", 
            "android", "blackberry", "windows phone", "webos",
            "kindle", "silk", "mobile safari"
        ];
        
        const platformIndicators = [
            "iphone", "ipad", "ipod", "android"
        ];
        
        const isMobileUA = mobileIndicators.some(indicator => userAgent.includes(indicator));
        const isMobilePlatform = platformIndicators.some(indicator => platform.includes(indicator));
        
        if (isMobileUA) {
            touchScore += 15;
            detectionMethods.push("mobileUA");
        }
        if (isMobilePlatform) {
            touchScore += 20;
            detectionMethods.push("mobilePlatform");
        }
        
        // Method 7: Screen size heuristics (mobile-like screen sizes)
        let isMobileScreen = false;
        try {
            if (typeof screen !== "undefined" && screen.width && screen.height) {
                const screenWidth = Math.min(screen.width, screen.height);
                const screenHeight = Math.max(screen.width, screen.height);
                
                // Typical mobile/tablet screen size ranges
                isMobileScreen = (screenWidth <= 768 && screenHeight <= 1366) || 
                               (screenWidth <= 1024 && screenHeight <= 1366 && screenWidth < screenHeight);
                
                if (isMobileScreen) {
                    touchScore += 10;
                    detectionMethods.push(`mobileScreen(${screenWidth}x${screenHeight})`);
                }
            }
        } catch (e) {
            console.warn("InputConfig: Screen detection error:", e);
        }
        
        // Method 8: Check for device orientation API
        const hasOrientation = "orientation" in window || "onorientationchange" in window;
        if (hasOrientation) {
            touchScore += 10;
            detectionMethods.push("orientationAPI");
        }
        
        // Method 9: Check for vibration API (mobile-specific)
        const hasVibration = "vibrate" in navigator;
        if (hasVibration) {
            touchScore += 5;
            detectionMethods.push("vibrationAPI");
        }
        
        // Method 10: Check for device motion/orientation APIs
        const hasDeviceMotion = "ondevicemotion" in window;
        const hasDeviceOrientation = "ondeviceorientation" in window;
        if (hasDeviceMotion || hasDeviceOrientation) {
            touchScore += 8;
            detectionMethods.push("deviceMotionAPI");
        }
        
        // Store confidence score (0-100)
        this.detectionConfidence.touch = Math.min(touchScore, 100);
        
        // Determine touch support (threshold: 50)
        const touchSupport = touchScore >= 50;
        
        console.log(`InputConfig: Touch detection - Score: ${touchScore}/100, Methods: [${detectionMethods.join(", ")}], Result: ${touchSupport}`);
        
        return touchSupport;
    }
    
    /**
     * Detect if user likely has a trackpad
     */
    detectTrackpad() {
        // Guard against server-side execution
        if (typeof navigator === "undefined") {
            this.detectionConfidence.trackpad = 0;
            return false;
        }
        
        let trackpadScore = 0;
        const detectionMethods = [];
        
        // Check platform hints - be extra careful with undefined/null values
        const platform = (navigator.platform || "").toLowerCase();
        const userAgent = (navigator.userAgent || "").toLowerCase();
        
        // Method 1: macOS detection - Mac users almost always have trackpads
        const macIndicators = ["mac", "darwin", "macintosh"];
        const isMac = macIndicators.some(indicator => 
            platform.includes(indicator) || userAgent.includes(indicator)
        );
        
        if (isMac) {
            trackpadScore += 40;
            detectionMethods.push("macOS");
        }
        
        // Method 2: Explicit laptop/trackpad indicators
        const explicitIndicators = [
            "laptop", "notebook", "portable", "macbook",
            "touchpad", "trackpad", "multitouch"
        ];
        
        const hasExplicitIndicator = explicitIndicators.some(indicator => 
            platform.includes(indicator) || userAgent.includes(indicator)
        );
        
        if (hasExplicitIndicator) {
            trackpadScore += 35;
            detectionMethods.push("explicitLaptop");
        }
        
        // Method 3: Windows laptop detection
        const isWindows = userAgent.includes("windows");
        if (isWindows) {
            // Windows touch devices often have trackpads
            const hasWindowsTouch = userAgent.includes("touch");
            // Windows 10/11 devices without WoW64 often indicate newer laptops
            const isModernWindows = userAgent.includes("windows nt 10") || userAgent.includes("windows nt 11");
            const noWow64 = !userAgent.includes("wow64");
            
            if (hasWindowsTouch) {
                trackpadScore += 25;
                detectionMethods.push("windowsTouch");
            }
            
            if (isModernWindows && noWow64) {
                trackpadScore += 15;
                detectionMethods.push("modernWindows");
            }
        }
        
        // Method 4: Linux laptop detection
        const isLinux = userAgent.includes("linux");
        if (isLinux) {
            const hasX11 = userAgent.includes("x11");
            const hasWayland = userAgent.includes("wayland");
            const noDesktopHint = !userAgent.includes("desktop");
            
            if (hasX11 || hasWayland) {
                trackpadScore += 20;
                detectionMethods.push("linuxGraphical");
            }
            
            if (noDesktopHint) {
                trackpadScore += 10;
                detectionMethods.push("linuxNoDesktop");
            }
        }
        
        // Method 5: Screen size and orientation heuristics
        try {
            if (typeof screen !== "undefined" && screen.width && screen.height) {
                const screenWidth = Math.max(screen.width, screen.height);
                const screenHeight = Math.min(screen.width, screen.height);
                const aspectRatio = screenWidth / screenHeight;
                
                // Common laptop screen ratios and sizes
                const isLaptopSize = (
                    (screenWidth >= 1280 && screenWidth <= 1920 && screenHeight >= 720 && screenHeight <= 1200) ||
                    (screenWidth >= 2560 && screenWidth <= 3840 && screenHeight >= 1440 && screenHeight <= 2400)
                );
                
                const isLaptopRatio = aspectRatio >= 1.3 && aspectRatio <= 1.8;
                
                if (isLaptopSize && isLaptopRatio) {
                    trackpadScore += 15;
                    detectionMethods.push(`laptopScreen(${screenWidth}x${screenHeight})`);
                }
            }
        } catch (e) {
            console.warn("InputConfig: Screen detection error:", e);
        }
        
        // Method 6: Browser and device capabilities
        if (typeof window !== "undefined") {
            // Check for pointer events API which is common on trackpad devices
            const hasPointerEvents = "PointerEvent" in window;
            if (hasPointerEvents) {
                trackpadScore += 10;
                detectionMethods.push("pointerEvents");
            }
            
            // Check for specific trackpad-related events
            const hasWheelEvent = "WheelEvent" in window;
            if (hasWheelEvent) {
                trackpadScore += 5;
                detectionMethods.push("wheelEvent");
            }
        }
        
        // Method 7: Hardware concurrency heuristics (laptops often have fewer cores)
        try {
            if (typeof navigator !== "undefined" && navigator.hardwareConcurrency) {
                const cores = navigator.hardwareConcurrency;
                // Laptops commonly have 2-8 cores, desktops often have more
                if (cores >= 2 && cores <= 8) {
                    trackpadScore += 5;
                    detectionMethods.push(`laptopCores(${cores})`);
                }
            }
        } catch (e) {
            console.warn("InputConfig: Hardware concurrency detection error:", e);
        }
        
        // Method 8: Memory heuristics (laptops often have less RAM)
        try {
            if (typeof navigator !== "undefined" && navigator.deviceMemory) {
                const memory = navigator.deviceMemory;
                // Laptops commonly have 4-16GB, gaming desktops often have more
                if (memory >= 4 && memory <= 16) {
                    trackpadScore += 3;
                    detectionMethods.push(`laptopMemory(${memory}GB)`);
                }
            }
        } catch (e) {
            console.warn("InputConfig: Memory detection error:", e);
        }
        
        // Method 9: Check for mobile/tablet devices which might have trackpad-like gestures
        if (this.hasTouch && !isMac) {
            // Touch devices that aren't clearly mobile might be laptops with touch
            try {
                if (typeof screen !== "undefined") {
                    const screenSize = Math.max(screen.width, screen.height);
                    if (screenSize > 1024) { // Larger than typical phone/small tablet
                        trackpadScore += 12;
                        detectionMethods.push("touchLaptop");
                    }
                }
            } catch (e) {
                console.warn("InputConfig: Touch laptop detection error:", e);
            }
        }
        
        // Store confidence score (0-100)
        this.detectionConfidence.trackpad = Math.min(trackpadScore, 100);
        
        // Determine trackpad support (threshold: 30 for initial detection)
        const trackpadSupport = trackpadScore >= 30;
        
        console.log(`InputConfig: Trackpad detection - Score: ${trackpadScore}/100, Methods: [${detectionMethods.join(", ")}], Result: ${trackpadSupport}`);
        
        if (!trackpadSupport) {
            console.log("InputConfig: No strong trackpad indicators found, will refine detection from user interactions");
        }
        
        return trackpadSupport;
    }
    
    /**
     * Update trackpad detection based on wheel event
     */
    updateTrackpadDetection(wheelEvent) {
        // Record the interaction for analysis
        this.recordInteraction("wheel", wheelEvent);
        
        // Skip if already highly confident about trackpad
        if (this.detectionConfidence.trackpad >= 90) {
            return;
        }
        
        let trackpadScore = 0;
        const detectionMethods = [];
        
        // Method 1: Trackpads often produce fractional delta values
        const isFractional = (wheelEvent.deltaY % 1 !== 0) || (wheelEvent.deltaX % 1 !== 0);
        if (isFractional) {
            trackpadScore += 25;
            detectionMethods.push("fractionalDeltas");
        }
        
        // Method 2: Trackpads can produce horizontal scroll
        const hasHorizontal = Math.abs(wheelEvent.deltaX) > 0;
        if (hasHorizontal) {
            trackpadScore += 20;
            detectionMethods.push("horizontalScroll");
        }
        
        // Method 3: Trackpads typically have smaller, more precise delta values
        const hasSmallDeltas = Math.abs(wheelEvent.deltaY) < 50 && Math.abs(wheelEvent.deltaX) < 50;
        if (hasSmallDeltas && wheelEvent.deltaMode === 0) {
            trackpadScore += 15;
            detectionMethods.push("smallDeltas");
        }
        
        // Method 4: Trackpad wheel events often have deltaMode 0 (pixel-based)
        if (wheelEvent.deltaMode === 0) {
            trackpadScore += 10;
            detectionMethods.push("pixelMode");
        }
        
        // Method 5: Very smooth delta patterns (less than 1 pixel changes)
        const isSmoothScroll = Math.abs(wheelEvent.deltaY) < 1 || Math.abs(wheelEvent.deltaX) < 1;
        if (isSmoothScroll) {
            trackpadScore += 15;
            detectionMethods.push("smoothScroll");
        }
        
        // Method 6: Trackpads often produce non-standard delta ratios
        const deltaRatio = Math.abs(wheelEvent.deltaY) / Math.max(Math.abs(wheelEvent.deltaX), 1);
        const hasUnusualRatio = deltaRatio > 0 && deltaRatio < 10 && Math.abs(wheelEvent.deltaX) > 0;
        if (hasUnusualRatio) {
            trackpadScore += 12;
            detectionMethods.push("unusualRatio");
        }
        
        // Update confidence score
        if (trackpadScore > 0) {
            this.detectionConfidence.trackpad += trackpadScore;
            this.detectionConfidence.trackpad = Math.min(this.detectionConfidence.trackpad, 100);
            
            console.log(`InputConfig: Trackpad wheel detection - Score: +${trackpadScore}, Total: ${this.detectionConfidence.trackpad}/100, Methods: [${detectionMethods.join(", ")}]`);
        }
        
        // Update detection if we reach threshold
        const wasTrackpad = this.isTrackpad;
        this.isTrackpad = this.detectionConfidence.trackpad >= 50;
        
        if (this.isTrackpad && !wasTrackpad) {
            console.log(`InputConfig: Trackpad confirmed via wheel interactions - Confidence: ${this.detectionConfidence.trackpad}/100`);
            console.log(`Input devices updated - Touch: ${this.hasTouch}, Trackpad: ${this.isTrackpad}`);
            
            // Auto-enable trackpad features if using auto mode
            this.updateAutoConfiguration();
        }
    }
    
    /**
     * Update touch detection based on actual touch events
     */
    updateTouchDetection(touchEvent) {
        // Record the interaction for analysis
        this.recordInteraction("touch", touchEvent);
        
        // If we see actual touch events, we definitely have touch support
        if (!this.hasTouch) {
            this.hasTouch = true;
            this.detectionConfidence.touch = 100;
            
            console.log("InputConfig: Touch confirmed via actual touch event");
            console.log(`Input devices updated - Touch: ${this.hasTouch}, Trackpad: ${this.isTrackpad}`);
            
            // Update auto-configuration
            this.updateAutoConfiguration();
        }
    }
    
    /**
     * Update detection based on pointer events
     */
    updatePointerDetection(pointerEvent) {
        // Record the interaction for analysis
        this.recordInteraction("pointer", pointerEvent);
        
        // Analyze pointer type
        if (pointerEvent.pointerType) {
            switch (pointerEvent.pointerType) {
            case "touch":
                if (!this.hasTouch) {
                    this.hasTouch = true;
                    this.detectionConfidence.touch = 100;
                    console.log("InputConfig: Touch confirmed via pointer event");
                    this.updateAutoConfiguration();
                }
                break;
                    
            case "pen":
                // Pen input often indicates touch-capable device
                if (this.detectionConfidence.touch < 80) {
                    this.detectionConfidence.touch = 80;
                    this.hasTouch = true;
                    console.log("InputConfig: Touch likely via pen pointer event");
                    this.updateAutoConfiguration();
                }
                break;
                    
            case "mouse":
                // Mouse events from trackpad might have specific characteristics
                if (pointerEvent.pressure && pointerEvent.pressure > 0) {
                    this.detectionConfidence.trackpad += 5;
                    this.detectionConfidence.trackpad = Math.min(this.detectionConfidence.trackpad, 100);
                        
                    const wasTrackpad = this.isTrackpad;
                    this.isTrackpad = this.detectionConfidence.trackpad >= 50;
                        
                    if (this.isTrackpad && !wasTrackpad) {
                        console.log("InputConfig: Trackpad detected via pressure-sensitive mouse pointer");
                        this.updateAutoConfiguration();
                    }
                }
                break;
            }
        }
    }
    
    /**
     * Record interaction for pattern analysis
     */
    recordInteraction(type, event) {
        // Keep only recent interactions (last 50)
        if (this.interactionEvents.length >= 50) {
            this.interactionEvents.shift();
        }
        
        const interaction = {
            type,
            timestamp: Date.now(),
            event: {
                // Store relevant event properties without keeping full event reference
                ...(type === "wheel" && {
                    deltaX: event.deltaX,
                    deltaY: event.deltaY,
                    deltaZ: event.deltaZ,
                    deltaMode: event.deltaMode
                }),
                ...(type === "touch" && {
                    touches: event.touches ? event.touches.length : 0,
                    changedTouches: event.changedTouches ? event.changedTouches.length : 0
                }),
                ...(type === "pointer" && {
                    pointerType: event.pointerType,
                    pressure: event.pressure,
                    tiltX: event.tiltX,
                    tiltY: event.tiltY
                })
            }
        };
        
        this.interactionEvents.push(interaction);
    }
    
    /**
     * Finalize detection after observation period
     */
    finalizeDetection() {
        console.log("InputConfig: Finalizing device detection after observation period");
        console.log(`Final confidence scores - Touch: ${this.detectionConfidence.touch}/100, Trackpad: ${this.detectionConfidence.trackpad}/100`);
        console.log(`Final detection - Touch: ${this.hasTouch}, Trackpad: ${this.isTrackpad}`);
        console.log(`Recorded ${this.interactionEvents.length} user interactions for analysis`);
        
        // Clean up event listeners to prevent memory leaks
        if (this.detectionListeners && typeof window !== "undefined") {
            this.detectionListeners.forEach(({ event, listener }) => {
                window.removeEventListener(event, listener);
            });
            this.detectionListeners = [];
        }
        
        // Clear timeout
        if (this.detectionTimeout) {
            clearTimeout(this.detectionTimeout);
            this.detectionTimeout = null;
        }
        
        this.detectionComplete = true;
    }
    
    /**
     * Get detailed detection information for debugging
     */
    getDetectionInfo() {
        return {
            hasTouch: this.hasTouch,
            isTrackpad: this.isTrackpad,
            confidence: { ...this.detectionConfidence },
            complete: this.detectionComplete,
            interactionCount: this.interactionEvents ? this.interactionEvents.length : 0,
            currentConfig: {
                zoomMethod: this.config.camera.zoomMethod,
                panMethod: this.config.camera.panMethod
            }
        };
    }
    
    /**
     * Log detailed detection information for debugging
     */
    logDetectionDetails() {
        console.log("InputConfig: === DEVICE DETECTION SUMMARY ===");
        console.log(`  Touch Support: ${this.hasTouch} (Confidence: ${this.detectionConfidence.touch}/100)`);
        console.log(`  Trackpad Support: ${this.isTrackpad} (Confidence: ${this.detectionConfidence.trackpad}/100)`);
        console.log(`  Detection Complete: ${this.detectionComplete}`);
        console.log(`  Zoom Method: ${this.config.camera.zoomMethod}`);
        console.log(`  Pan Method: ${this.config.camera.panMethod}`);
        
        if (typeof navigator !== "undefined") {
            console.log("InputConfig: === BROWSER ENVIRONMENT ===");
            console.log(`  Platform: ${navigator.platform || "unknown"}`);
            console.log(`  User Agent: ${navigator.userAgent || "unknown"}`);
            console.log(`  Max Touch Points: ${navigator.maxTouchPoints || 0}`);
            console.log(`  Hardware Concurrency: ${navigator.hardwareConcurrency || "unknown"}`);
            console.log(`  Device Memory: ${navigator.deviceMemory || "unknown"}GB`);
        }
        
        if (typeof screen !== "undefined") {
            console.log("InputConfig: === SCREEN INFORMATION ===");
            console.log(`  Screen Size: ${screen.width}x${screen.height}`);
            console.log(`  Color Depth: ${screen.colorDepth || "unknown"}`);
            console.log(`  Pixel Depth: ${screen.pixelDepth || "unknown"}`);
        }
        
        if (typeof window !== "undefined") {
            console.log("InputConfig: === FEATURE SUPPORT ===");
            console.log(`  TouchEvent: ${typeof TouchEvent !== "undefined"}`);
            console.log(`  TouchList: ${typeof TouchList !== "undefined"}`);
            console.log(`  PointerEvent: ${typeof PointerEvent !== "undefined"}`);
            console.log(`  WheelEvent: ${typeof WheelEvent !== "undefined"}`);
            console.log(`  ontouchstart: ${"ontouchstart" in window}`);
            console.log(`  onpointerdown: ${"onpointerdown" in window}`);
            console.log(`  Orientation API: ${"orientation" in window || "onorientationchange" in window}`);
            console.log(`  Device Motion: ${"ondevicemotion" in window}`);
            console.log(`  Vibration API: ${"vibrate" in navigator}`);
            
            // Test media query support
            let pointerType = "unknown";
            let hoverCapability = "unknown";
            try {
                if (window.matchMedia) {
                    if (window.matchMedia("(pointer: coarse)").matches) pointerType = "coarse";
                    else if (window.matchMedia("(pointer: fine)").matches) pointerType = "fine";
                    else if (window.matchMedia("(pointer: none)").matches) pointerType = "none";
                    
                    if (window.matchMedia("(hover: hover)").matches) hoverCapability = "hover";
                    else if (window.matchMedia("(hover: none)").matches) hoverCapability = "none";
                }
            } catch (e) {
                console.warn("InputConfig: Media query error:", e);
                pointerType = "error";
                hoverCapability = "error";
            }
            console.log(`  Primary Pointer: ${pointerType}`);
            console.log(`  Hover Capability: ${hoverCapability}`);
        }
        
        // Log interaction history if available
        if (this.interactionEvents && this.interactionEvents.length > 0) {
            console.log("InputConfig: === INTERACTION HISTORY ===");
            console.log(`  Total Interactions Recorded: ${this.interactionEvents.length}`);
            
            const eventTypes = this.interactionEvents.reduce((acc, interaction) => {
                acc[interaction.type] = (acc[interaction.type] || 0) + 1;
                return acc;
            }, {});
            
            console.log("  Event Types:", eventTypes);
            
            // Show some recent interactions
            const recentInteractions = this.interactionEvents.slice(-5);
            console.log(`  Recent Interactions (last ${recentInteractions.length}):`);
            recentInteractions.forEach((interaction, index) => {
                console.log(`    ${index + 1}. ${interaction.type} at ${new Date(interaction.timestamp).toTimeString()}`);
            });
        }
        
        console.log("InputConfig: === END DETECTION SUMMARY ===");
    }
    
    /**
     * Clean up resources and event listeners
     */
    cleanup() {
        console.log("InputConfig: Cleaning up resources");
        
        // Clear detection timeout
        if (this.detectionTimeout) {
            clearTimeout(this.detectionTimeout);
            this.detectionTimeout = null;
        }
        
        // Remove event listeners
        if (this.detectionListeners && typeof window !== "undefined" && window.removeEventListener) {
            this.detectionListeners.forEach(({ event, listener }) => {
                try {
                    window.removeEventListener(event, listener);
                } catch (e) {
                    console.warn(`InputConfig: Failed to remove ${event} listener:`, e);
                }
            });
            this.detectionListeners = [];
        }
        
        // Clear interaction history
        if (this.interactionEvents) {
            this.interactionEvents = [];
        }
        
        console.log("InputConfig: Cleanup complete");
    }
    
    /**
     * Force re-detection of input devices
     */
    redetect() {
        console.log("InputConfig: Forcing device re-detection");
        
        // Clean up current detection
        this.cleanup();
        
        // Reset detection state
        this.detectionComplete = false;
        this.detectionConfidence = {
            touch: 0,
            trackpad: 0
        };
        
        // Re-run detection
        this.detectInputDevices();
    }
    
    /**
     * Get a config value
     */
    get(path) {
        const keys = path.split(".");
        let value = this.config;
        
        for (const key of keys) {
            value = value[key];
            if (value === undefined) return undefined;
        }
        
        return value;
    }
    
    /**
     * Set a config value
     */
    set(path, value) {
        const keys = path.split(".");
        let obj = this.config;
        
        for (let i = 0; i < keys.length - 1; i++) {
            if (!obj[keys[i]]) obj[keys[i]] = {};
            obj = obj[keys[i]];
        }
        
        obj[keys[keys.length - 1]] = value;
        this.savePreferences();
    }
    
    /**
     * Load preferences from localStorage
     */
    loadPreferences() {
        // Guard against server-side execution
        if (typeof localStorage === "undefined") {
            console.log("InputConfig: localStorage not available, using defaults");
            return;
        }
        
        try {
            const saved = localStorage.getItem("comandind_input_config");
            if (saved) {
                const parsed = JSON.parse(saved);
                // Deep merge with defaults
                this.mergeConfig(this.config, parsed);
            }
        } catch (e) {
            console.warn("Failed to load input preferences:", e);
        }
    }
    
    /**
     * Save preferences to localStorage
     */
    savePreferences() {
        // Guard against server-side execution
        if (typeof localStorage === "undefined") {
            console.log("InputConfig: localStorage not available, cannot save preferences");
            return;
        }
        
        try {
            localStorage.setItem("comandind_input_config", JSON.stringify(this.config));
        } catch (e) {
            console.warn("Failed to save input preferences:", e);
        }
    }
    
    /**
     * Deep merge configuration objects
     */
    mergeConfig(target, source) {
        for (const key in source) {
            if (source[key] && typeof source[key] === "object" && !Array.isArray(source[key])) {
                if (!target[key]) target[key] = {};
                this.mergeConfig(target[key], source[key]);
            } else {
                target[key] = source[key];
            }
        }
    }
    
    /**
     * Reset to defaults
     */
    reset() {
        console.log("InputConfig: Resetting to defaults");
        
        // Clean up current resources
        this.cleanup();
        
        // Remove saved preferences
        if (typeof localStorage !== "undefined") {
            localStorage.removeItem("comandind_input_config");
        }
        
        // Reset to default configuration
        this.config = {
            // Camera controls
            camera: {
                // Zoom controls
                zoomMethod: "auto", // 'auto', 'wheel', 'pinch', 'keys'
                zoomSpeed: 0.1,
                zoomInverted: false,
                pinchZoomSpeed: 0.02,
                wheelZoomSpeed: 0.1,
                keyZoomSpeed: 0.05,
                
                // Pan controls  
                panMethod: "auto", // 'auto', 'edge', 'drag', 'keys', 'trackpad'
                edgeScrollSpeed: 5,
                dragPanSpeed: 1,
                trackpadPanSpeed: 2,
                keyPanSpeed: 10,
                edgeScrollThreshold: 50,
                
                // Trackpad specific
                trackpadEnabled: true,
                trackpadPanInverted: false,
                pinchToZoomEnabled: true,
                twoFingerPanEnabled: true,
                
                // Smoothing
                smoothing: 0.1,
                zoomSmoothing: 0.15
            },
            
            // Selection controls
            selection: {
                boxSelectThreshold: 5, // pixels before box select starts
                clickRadius: 5, // tolerance for clicks vs drags
                doubleClickTime: 300, // ms for double click
                multiSelectKey: "shift", // key for adding to selection
                toggleSelectKey: "ctrl", // key for toggle selection
            },
            
            // Command controls
            commands: {
                attackMoveKey: "a",
                stopKey: "s",
                holdPositionKey: "h",
                patrolKey: "p",
                queueCommandKey: "shift"
            },
            
            // Accessibility
            accessibility: {
                reducedMotion: false,
                highContrast: false,
                largeUI: false
            }
        };
        
        // Re-initialize detection
        this.detectInputDevices();
        
        console.log("InputConfig: Reset complete");
    }
}

// Singleton instance
export const inputConfig = new InputConfig();