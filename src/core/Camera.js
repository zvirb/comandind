import * as PIXI from "pixi.js";

export class Camera {
    constructor(stage, screenWidth, screenHeight) {
        this.stage = stage;
        this.screenWidth = screenWidth;
        this.screenHeight = screenHeight;
        
        // Camera position (world coordinates)
        this.x = 0;
        this.y = 0;
        
        // Camera velocity for smooth movement
        this.velocity = { x: 0, y: 0 };
        
        // Camera bounds (if set, camera won't go outside these bounds)
        this.bounds = null;
        
        // Zoom level
        this.scale = 1;
        this.minScale = 0.5;
        this.maxScale = 2;
        
        // Smooth movement parameters
        this.smoothing = 0.1; // Lerp factor for smooth movement
        this.targetX = 0;
        this.targetY = 0;
        
        // Follow target
        this.followTarget = null;
        this.followOffset = { x: 0, y: 0 };
        this.followDeadzone = { width: 100, height: 100 };
    }
    
    update(deltaTime) {
        // Update position based on velocity
        if (this.velocity.x !== 0 || this.velocity.y !== 0) {
            this.targetX += this.velocity.x * deltaTime * 60;
            this.targetY += this.velocity.y * deltaTime * 60;
        }
        
        // Follow target if set
        if (this.followTarget) {
            this.updateFollow();
        }
        
        // Apply smooth movement
        this.x += (this.targetX - this.x) * this.smoothing;
        this.y += (this.targetY - this.y) * this.smoothing;
        
        // Apply bounds if set
        if (this.bounds) {
            this.applyBounds();
        }
        
        // Update stage position
        this.updateStagePosition();
    }
    
    updateFollow() {
        if (!this.followTarget) return;
        
        const targetWorldX = this.followTarget.x + this.followOffset.x;
        const targetWorldY = this.followTarget.y + this.followOffset.y;
        
        const cameraTargetX = targetWorldX - this.screenWidth / 2 / this.scale;
        const cameraTargetY = targetWorldY - this.screenHeight / 2 / this.scale;
        
        // Apply deadzone
        const dx = cameraTargetX - this.targetX;
        const dy = cameraTargetY - this.targetY;
        
        if (Math.abs(dx) > this.followDeadzone.width / 2) {
            this.targetX = cameraTargetX;
        }
        
        if (Math.abs(dy) > this.followDeadzone.height / 2) {
            this.targetY = cameraTargetY;
        }
    }
    
    applyBounds() {
        if (!this.bounds) return;
        
        const viewWidth = this.screenWidth / this.scale;
        const viewHeight = this.screenHeight / this.scale;
        
        // Clamp camera position to bounds
        this.targetX = Math.max(this.bounds.x, Math.min(this.targetX, this.bounds.x + this.bounds.width - viewWidth));
        this.targetY = Math.max(this.bounds.y, Math.min(this.targetY, this.bounds.y + this.bounds.height - viewHeight));
        
        this.x = Math.max(this.bounds.x, Math.min(this.x, this.bounds.x + this.bounds.width - viewWidth));
        this.y = Math.max(this.bounds.y, Math.min(this.y, this.bounds.y + this.bounds.height - viewHeight));
    }
    
    updateStagePosition() {
        // Apply camera transform to stage
        this.stage.x = -this.x * this.scale;
        this.stage.y = -this.y * this.scale;
        this.stage.scale.x = this.scale;
        this.stage.scale.y = this.scale;
    }
    
    // Set camera position (instant)
    setPosition(x, y) {
        this.x = x;
        this.y = y;
        this.targetX = x;
        this.targetY = y;
        this.updateStagePosition();
    }
    
    // Move camera to position (smooth)
    moveTo(x, y) {
        this.targetX = x;
        this.targetY = y;
    }
    
    // Center camera on a point
    centerOn(x, y) {
        const centerX = x - (this.screenWidth / 2 / this.scale);
        const centerY = y - (this.screenHeight / 2 / this.scale);
        this.moveTo(centerX, centerY);
    }
    
    // Set zoom level
    zoom(scale) {
        // Clamp scale to min/max
        scale = Math.max(this.minScale, Math.min(scale, this.maxScale));
        
        // Calculate zoom center (screen center in world coordinates)
        const centerX = this.x + (this.screenWidth / 2 / this.scale);
        const centerY = this.y + (this.screenHeight / 2 / this.scale);
        
        // Apply new scale
        this.scale = scale;
        
        // Adjust position to keep center point fixed
        this.x = centerX - (this.screenWidth / 2 / this.scale);
        this.y = centerY - (this.screenHeight / 2 / this.scale);
        this.targetX = this.x;
        this.targetY = this.y;
        
        this.updateStagePosition();
    }
    
    // Convert screen coordinates to world coordinates
    // If canvasElement is provided, converts viewport coordinates to canvas-relative first
    screenToWorld(screenX, screenY, canvasElement = null) {
        let canvasX = screenX;
        let canvasY = screenY;
        
        // Convert viewport coordinates to canvas-relative coordinates if canvas element provided
        if (canvasElement) {
            const rect = canvasElement.getBoundingClientRect();
            canvasX = screenX - rect.left;
            canvasY = screenY - rect.top;
        }
        
        return {
            x: (canvasX / this.scale) + this.x,
            y: (canvasY / this.scale) + this.y
        };
    }
    
    // Convert world coordinates to screen coordinates
    worldToScreen(worldX, worldY) {
        return {
            x: (worldX - this.x) * this.scale,
            y: (worldY - this.y) * this.scale
        };
    }
    
    // Set camera bounds
    setBounds(x, y, width, height) {
        this.bounds = { x, y, width, height };
    }
    
    // Clear camera bounds
    clearBounds() {
        this.bounds = null;
    }
    
    // Set follow target
    follow(target, offsetX = 0, offsetY = 0) {
        this.followTarget = target;
        this.followOffset.x = offsetX;
        this.followOffset.y = offsetY;
    }
    
    // Stop following
    stopFollowing() {
        this.followTarget = null;
    }
    
    // Resize camera viewport
    resize(width, height) {
        this.screenWidth = width;
        this.screenHeight = height;
        this.updateStagePosition();
    }
    
    // Shake effect
    shake(intensity = 10, duration = 500) {
        const startTime = Date.now();
        const originalX = this.x;
        const originalY = this.y;
        
        const shakeInterval = setInterval(() => {
            const elapsed = Date.now() - startTime;
            
            if (elapsed >= duration) {
                clearInterval(shakeInterval);
                this.x = originalX;
                this.y = originalY;
                this.updateStagePosition();
                return;
            }
            
            const progress = elapsed / duration;
            const currentIntensity = intensity * (1 - progress);
            
            this.x = originalX + (Math.random() - 0.5) * currentIntensity;
            this.y = originalY + (Math.random() - 0.5) * currentIntensity;
            this.updateStagePosition();
        }, 16);
    }
}