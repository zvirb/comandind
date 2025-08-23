// Generate C&C-style placeholder sprites
class SpriteGenerator {
    static generateTank(canvas, color = '#4a5568', turretColor = '#2d3748') {
        const ctx = canvas.getContext('2d');
        canvas.width = 32;
        canvas.height = 32;
        
        // Clear
        ctx.clearRect(0, 0, 32, 32);
        
        // Tank body
        ctx.fillStyle = color;
        ctx.fillRect(8, 10, 16, 12);
        
        // Tracks
        ctx.fillStyle = '#1a202c';
        ctx.fillRect(6, 9, 20, 3);
        ctx.fillRect(6, 20, 20, 3);
        
        // Turret base
        ctx.fillStyle = turretColor;
        ctx.beginPath();
        ctx.arc(16, 16, 5, 0, Math.PI * 2);
        ctx.fill();
        
        // Cannon
        ctx.strokeStyle = turretColor;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(16, 16);
        ctx.lineTo(16, 6);
        ctx.stroke();
        
        return canvas;
    }
    
    static generateBuilding(canvas, type = 'barracks') {
        const ctx = canvas.getContext('2d');
        canvas.width = 48;
        canvas.height = 48;
        
        ctx.clearRect(0, 0, 48, 48);
        
        // Building base
        ctx.fillStyle = '#718096';
        ctx.fillRect(8, 12, 32, 28);
        
        // Roof
        ctx.fillStyle = '#4a5568';
        ctx.beginPath();
        ctx.moveTo(4, 12);
        ctx.lineTo(24, 4);
        ctx.lineTo(44, 12);
        ctx.closePath();
        ctx.fill();
        
        // Windows/details based on type
        ctx.fillStyle = '#fbbf24';
        if (type === 'barracks') {
            // Door
            ctx.fillStyle = '#1a202c';
            ctx.fillRect(20, 25, 8, 15);
            // Windows
            ctx.fillStyle = '#fbbf24';
            ctx.fillRect(10, 16, 6, 6);
            ctx.fillRect(32, 16, 6, 6);
        } else if (type === 'power') {
            // Smokestacks
            ctx.fillStyle = '#2d3748';
            ctx.fillRect(12, 8, 6, 12);
            ctx.fillRect(30, 8, 6, 12);
            // Glow
            ctx.fillStyle = '#fbbf24';
            ctx.fillRect(20, 20, 8, 8);
        } else if (type === 'refinery') {
            // Silo
            ctx.fillStyle = '#a78bfa';
            ctx.beginPath();
            ctx.arc(35, 25, 8, 0, Math.PI * 2);
            ctx.fill();
        }
        
        // Team color stripe
        ctx.fillStyle = '#3b82f6';
        ctx.fillRect(8, 35, 32, 3);
        
        return canvas;
    }
    
    static generateInfantry(canvas, color = '#4a5568') {
        const ctx = canvas.getContext('2d');
        canvas.width = 16;
        canvas.height = 16;
        
        ctx.clearRect(0, 0, 16, 16);
        
        // Head
        ctx.fillStyle = '#fbbf24';
        ctx.beginPath();
        ctx.arc(8, 4, 2, 0, Math.PI * 2);
        ctx.fill();
        
        // Body
        ctx.fillStyle = color;
        ctx.fillRect(6, 6, 4, 6);
        
        // Arms
        ctx.fillRect(4, 7, 8, 2);
        
        // Legs
        ctx.fillRect(6, 12, 2, 3);
        ctx.fillRect(8, 12, 2, 3);
        
        // Weapon
        ctx.strokeStyle = '#1a202c';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(10, 8);
        ctx.lineTo(13, 6);
        ctx.stroke();
        
        return canvas;
    }
    
    static generateObelisk(canvas) {
        const ctx = canvas.getContext('2d');
        canvas.width = 32;
        canvas.height = 48;
        
        ctx.clearRect(0, 0, 32, 48);
        
        // Base
        ctx.fillStyle = '#1a202c';
        ctx.fillRect(10, 36, 12, 12);
        
        // Obelisk tower
        ctx.fillStyle = '#4a5568';
        ctx.beginPath();
        ctx.moveTo(16, 4);
        ctx.lineTo(12, 36);
        ctx.lineTo(20, 36);
        ctx.closePath();
        ctx.fill();
        
        // Energy glow
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(16, 4);
        ctx.lineTo(16, 20);
        ctx.stroke();
        
        // Crystal at top
        ctx.fillStyle = '#ef4444';
        ctx.beginPath();
        ctx.arc(16, 4, 3, 0, Math.PI * 2);
        ctx.fill();
        
        return canvas;
    }
    
    static generateTiberium(canvas, color = '#10b981') {
        const ctx = canvas.getContext('2d');
        canvas.width = 24;
        canvas.height = 24;
        
        ctx.clearRect(0, 0, 24, 24);
        
        // Crystal clusters
        const crystals = [
            { x: 8, y: 12, size: 4 },
            { x: 14, y: 10, size: 5 },
            { x: 12, y: 16, size: 3 },
            { x: 16, y: 14, size: 4 }
        ];
        
        crystals.forEach(crystal => {
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.moveTo(crystal.x, crystal.y - crystal.size);
            ctx.lineTo(crystal.x - crystal.size/2, crystal.y);
            ctx.lineTo(crystal.x, crystal.y + crystal.size/2);
            ctx.lineTo(crystal.x + crystal.size/2, crystal.y);
            ctx.closePath();
            ctx.fill();
            
            // Highlight
            ctx.fillStyle = color + '88';
            ctx.beginPath();
            ctx.moveTo(crystal.x, crystal.y - crystal.size);
            ctx.lineTo(crystal.x + crystal.size/2, crystal.y);
            ctx.lineTo(crystal.x, crystal.y);
            ctx.closePath();
            ctx.fill();
        });
        
        return canvas;
    }
}

export default SpriteGenerator;