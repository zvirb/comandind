import * as PIXI from "pixi.js";

export class TestSprites {
    constructor(application) {
        this.app = application;
        this.sprites = [];
        this.textures = {};
    }
    
    // Create test sprites to verify rendering performance
    async createTestSprites(count = 100) {
        // Create a simple colored rectangle texture for testing
        const graphics = new PIXI.Graphics();
        graphics.beginFill(0x00FF00, 0.8);
        graphics.drawRect(0, 0, 32, 32);
        graphics.endFill();
        
        // Create texture from graphics
        const texture = this.app.renderer.generateTexture(graphics);
        this.textures.testUnit = texture;
        
        // Create sprites spread across the screen
        const gridSize = Math.ceil(Math.sqrt(count));
        const spacing = 40;
        const startX = 100;
        const startY = 100;
        
        for (let i = 0; i < count; i++) {
            const sprite = new PIXI.Sprite(texture);
            
            // Position in grid
            const gridX = i % gridSize;
            const gridY = Math.floor(i / gridSize);
            
            sprite.x = startX + gridX * spacing;
            sprite.y = startY + gridY * spacing;
            
            // Add some variety
            sprite.tint = Math.random() * 0xFFFFFF;
            sprite.scale.set(0.8 + Math.random() * 0.4);
            
            // Add to units layer
            this.app.addToLayer(sprite, "units");
            this.sprites.push(sprite);
        }
        
        console.log(`Created ${count} test sprites`);
        return this.sprites;
    }
    
    // Animate sprites for performance testing
    animateSprites(deltaTime) {
        this.sprites.forEach((sprite, index) => {
            // Simple circular motion
            const time = Date.now() / 1000;
            const radius = 20;
            const speed = 0.5 + (index % 5) * 0.2;
            
            sprite.rotation += deltaTime * speed;
            
            // Pulse effect
            const scale = 0.8 + Math.sin(time * 2 + index) * 0.2;
            sprite.scale.set(scale);
        });
    }
    
    // Stress test with many sprites
    async stressTest(targetCount = 1000) {
        console.log(`Starting stress test with ${targetCount} sprites...`);
        
        const batchSize = 100;
        let currentCount = 0;
        
        const addBatch = async () => {
            if (currentCount >= targetCount) {
                console.log(`Stress test complete: ${this.sprites.length} sprites`);
                return;
            }
            
            await this.createTestSprites(Math.min(batchSize, targetCount - currentCount));
            currentCount += batchSize;
            
            // Add next batch after a short delay
            setTimeout(addBatch, 500);
        };
        
        await addBatch();
    }
    
    // Clear all test sprites
    clearSprites() {
        this.sprites.forEach(sprite => {
            sprite.destroy();
        });
        this.sprites = [];
        
        // Clean up textures
        Object.values(this.textures).forEach(texture => {
            texture.destroy(true);
        });
        this.textures = {};
        
        console.log("Cleared all test sprites");
    }
}