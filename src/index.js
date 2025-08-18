import { Application } from './core/Application.js';
import { GameLoop } from './core/GameLoop.js';
import { Camera } from './core/Camera.js';
import { PerformanceMonitor } from './utils/PerformanceMonitor.js';
import { InputHandler } from './core/InputHandler.js';
import { TestSprites } from './rendering/TestSprites.js';

class CommandAndIndependentThought {
    constructor() {
        this.application = null;
        this.gameLoop = null;
        this.camera = null;
        this.performanceMonitor = null;
        this.inputHandler = null;
        this.testSprites = null;
        this.isInitialized = false;
    }

    async initialize() {
        try {
            // Update loading progress
            this.updateLoadingProgress(10, 'Creating application...');
            
            // Initialize PixiJS application
            this.application = new Application({
                width: window.innerWidth,
                height: window.innerHeight,
                backgroundColor: 0x1a1a1a,
                antialias: true,
                resolution: window.devicePixelRatio || 1,
                autoDensity: true,
                powerPreference: 'high-performance'
            });
            
            await this.application.initialize();
            this.updateLoadingProgress(30, 'Setting up camera...');
            
            // Initialize camera system
            this.camera = new Camera(
                this.application.stage,
                window.innerWidth,
                window.innerHeight
            );
            
            this.updateLoadingProgress(50, 'Initializing game loop...');
            
            // Initialize game loop
            this.gameLoop = new GameLoop(
                this.update.bind(this),
                this.render.bind(this),
                60 // Target 60 FPS
            );
            
            this.updateLoadingProgress(70, 'Setting up input handlers...');
            
            // Initialize input handler
            this.inputHandler = new InputHandler(this.application.view);
            this.setupInputHandlers();
            
            this.updateLoadingProgress(85, 'Starting performance monitor...');
            
            // Initialize performance monitor
            this.performanceMonitor = new PerformanceMonitor();
            
            this.updateLoadingProgress(90, 'Creating test sprites...');
            
            // Create test sprites for demonstration
            this.testSprites = new TestSprites(this.application);
            await this.testSprites.createTestSprites(100); // Start with 100 sprites
            
            this.updateLoadingProgress(95, 'Finalizing...');
            
            // Setup window resize handler
            window.addEventListener('resize', this.handleResize.bind(this));
            
            // Hide loading screen and show performance monitor
            setTimeout(() => {
                document.getElementById('loading-screen').classList.add('hidden');
                document.getElementById('performance-monitor').classList.remove('hidden');
                this.isInitialized = true;
                
                // Start the game loop
                this.gameLoop.start();
            }, 500);
            
            this.updateLoadingProgress(100, 'Ready!');
            
        } catch (error) {
            console.error('Failed to initialize Command and Independent Thought:', error);
            document.getElementById('loading-text').textContent = 
                'ERROR: Failed to initialize. Check console for details.';
            document.getElementById('loading-text').style.color = '#f00';
        }
    }
    
    updateLoadingProgress(percent, message) {
        const progressBar = document.getElementById('loading-progress');
        const loadingText = document.getElementById('loading-text');
        
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
        }
        
        if (loadingText && message) {
            loadingText.textContent = message;
        }
    }
    
    setupInputHandlers() {
        // Camera controls
        this.inputHandler.on('mousemove', (event) => {
            const edgeScrollSpeed = 5;
            const edgeThreshold = 50;
            
            // Edge scrolling
            if (event.clientX < edgeThreshold) {
                this.camera.velocity.x = -edgeScrollSpeed;
            } else if (event.clientX > window.innerWidth - edgeThreshold) {
                this.camera.velocity.x = edgeScrollSpeed;
            } else {
                this.camera.velocity.x = 0;
            }
            
            if (event.clientY < edgeThreshold) {
                this.camera.velocity.y = -edgeScrollSpeed;
            } else if (event.clientY > window.innerHeight - edgeThreshold) {
                this.camera.velocity.y = edgeScrollSpeed;
            } else {
                this.camera.velocity.y = 0;
            }
        });
        
        // Keyboard controls
        this.inputHandler.on('keydown', (event) => {
            const scrollSpeed = 10;
            switch(event.key) {
                case 'ArrowLeft':
                case 'a':
                case 'A':
                    this.camera.velocity.x = -scrollSpeed;
                    break;
                case 'ArrowRight':
                case 'd':
                case 'D':
                    this.camera.velocity.x = scrollSpeed;
                    break;
                case 'ArrowUp':
                case 'w':
                case 'W':
                    this.camera.velocity.y = -scrollSpeed;
                    break;
                case 'ArrowDown':
                case 's':
                case 'S':
                    this.camera.velocity.y = scrollSpeed;
                    break;
                // Test controls
                case '1':
                    // Add 100 more sprites
                    this.testSprites.createTestSprites(100);
                    console.log('Added 100 sprites');
                    break;
                case '2':
                    // Start stress test (1000 sprites)
                    this.testSprites.stressTest(1000);
                    break;
                case '0':
                    // Clear all sprites
                    this.testSprites.clearSprites();
                    break;
            }
        });
        
        this.inputHandler.on('keyup', (event) => {
            switch(event.key) {
                case 'ArrowLeft':
                case 'ArrowRight':
                case 'a':
                case 'A':
                case 'd':
                case 'D':
                    this.camera.velocity.x = 0;
                    break;
                case 'ArrowUp':
                case 'ArrowDown':
                case 'w':
                case 'W':
                case 's':
                case 'S':
                    this.camera.velocity.y = 0;
                    break;
            }
        });
        
        // Mouse wheel zoom
        this.inputHandler.on('wheel', (event) => {
            event.preventDefault();
            const zoomSpeed = 0.1;
            const delta = event.deltaY > 0 ? -zoomSpeed : zoomSpeed;
            this.camera.zoom(this.camera.scale + delta);
        });
    }
    
    update(deltaTime) {
        if (!this.isInitialized) return;
        
        // Update camera
        this.camera.update(deltaTime);
        
        // Animate test sprites
        if (this.testSprites) {
            this.testSprites.animateSprites(deltaTime);
        }
        
        // Update performance monitor
        this.performanceMonitor.update();
        
        // Update performance display
        const fps = Math.round(this.performanceMonitor.getFPS());
        const memory = Math.round(this.performanceMonitor.getMemoryUsage());
        const drawCalls = this.application.renderer.gl?.drawingBufferHeight ? 
            this.application.renderer.drawCalls || 0 : 0;
        const sprites = this.application.stage.children.length;
        
        document.getElementById('fps').textContent = fps;
        document.getElementById('draw-calls').textContent = drawCalls;
        document.getElementById('sprite-count').textContent = sprites;
        document.getElementById('memory').textContent = memory;
    }
    
    render(interpolation) {
        if (!this.isInitialized) return;
        
        // Render with interpolation for smooth visuals
        this.application.render(interpolation);
    }
    
    handleResize() {
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        this.application.resize(width, height);
        this.camera.resize(width, height);
    }
}

// Initialize game when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGame);
} else {
    initGame();
}

async function initGame() {
    const game = new CommandAndIndependentThought();
    window.game = game; // Expose for debugging
    await game.initialize();
}

export { CommandAndIndependentThought };