import MapGenerator from './MapGenerator.js';

class ConceptVisualizer {
    constructor(canvas, spriteConfig) {
        this.mapGen = new MapGenerator(canvas, spriteConfig);
        this.currentConcept = null;
        this.canvasCache = new Map();
        this.resizeObserver = null;
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.setupCanvasResponsiveness();
    }

    async init() {
        await this.mapGen.init();
        this.setupTouchEvents();
        this.setupCanvasResize();
    }
    
    setupCanvasResponsiveness() {
        if (!this.mapGen.canvas) return;
        
        // Make canvas responsive
        const canvas = this.mapGen.canvas;
        const container = canvas.parentElement;
        
        const updateCanvasSize = () => {
            if (!container) return;
            
            const rect = container.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            
            // Set display size
            canvas.style.width = rect.width + 'px';
            canvas.style.height = rect.height + 'px';
            
            // Set actual canvas size for crisp rendering
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            
            // Scale canvas context
            const ctx = canvas.getContext('2d');
            ctx.scale(dpr, dpr);
            
            // Update MapGenerator with new dimensions
            this.mapGen.canvas.width = rect.width * dpr;
            this.mapGen.canvas.height = rect.height * dpr;
            this.mapGen.width = rect.width;
            this.mapGen.height = rect.height;
        };
        
        updateCanvasSize();
        
        // Update on window resize
        window.addEventListener('resize', updateCanvasSize);
        window.addEventListener('orientationchange', () => {
            setTimeout(updateCanvasSize, 100);
        });
    }
    
    setupCanvasResize() {
        if (!window.ResizeObserver || !this.mapGen.canvas) return;
        
        this.resizeObserver = new ResizeObserver((entries) => {
            for (let entry of entries) {
                this.handleCanvasResize(entry.contentRect);
            }
        });
        
        const container = this.mapGen.canvas.parentElement;
        if (container) {
            this.resizeObserver.observe(container);
        }
    }
    
    handleCanvasResize(rect) {
        const canvas = this.mapGen.canvas;
        const dpr = window.devicePixelRatio || 1;
        
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        canvas.style.width = rect.width + 'px';
        canvas.style.height = rect.height + 'px';
        
        const ctx = canvas.getContext('2d');
        ctx.scale(dpr, dpr);
        
        this.mapGen.width = rect.width;
        this.mapGen.height = rect.height;
        
        // Redraw current visualization
        if (this.currentConcept) {
            this.redrawCurrentConcept();
        }
    }
    
    setupTouchEvents() {
        if (!this.mapGen.canvas) return;
        
        const canvas = this.mapGen.canvas;
        
        // Touch events for canvas interaction
        canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            this.touchStartX = touch.clientX;
            this.touchStartY = touch.clientY;
        }, { passive: false });
        
        canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            // Handle touch move for canvas interaction if needed
        }, { passive: false });
        
        canvas.addEventListener('touchend', (e) => {
            e.preventDefault();
            const touch = e.changedTouches[0];
            const deltaX = touch.clientX - this.touchStartX;
            const deltaY = touch.clientY - this.touchStartY;
            
            // Handle tap interactions
            if (Math.abs(deltaX) < 10 && Math.abs(deltaY) < 10) {
                this.handleCanvasTap(touch.clientX, touch.clientY);
            }
        }, { passive: false });
        
        // Mouse events for desktop
        canvas.addEventListener('click', (e) => {
            this.handleCanvasTap(e.clientX, e.clientY);
        });
    }
    
    handleCanvasTap(x, y) {
        // Convert screen coordinates to canvas coordinates
        const canvas = this.mapGen.canvas;
        const rect = canvas.getBoundingClientRect();
        const canvasX = (x - rect.left) * (canvas.width / rect.width);
        const canvasY = (y - rect.top) * (canvas.height / rect.height);
        
        // Handle interactive elements in visualizations
        this.handleInteractiveElement(canvasX, canvasY);
    }
    
    handleInteractiveElement(x, y) {
        // Can be extended for interactive visualizations
        console.log('Canvas interaction at:', x, y);
    }
    
    cacheVisualization(conceptKey) {
        if (!this.mapGen.canvas) return;
        
        const canvas = this.mapGen.canvas;
        const imageData = canvas.toDataURL();
        this.canvasCache.set(conceptKey, imageData);
    }
    
    loadCachedVisualization(conceptKey) {
        if (!this.canvasCache.has(conceptKey)) return false;
        
        const canvas = this.mapGen.canvas;
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        img.onload = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        };
        
        img.src = this.canvasCache.get(conceptKey);
        return true;
    }
    
    redrawCurrentConcept() {
        if (!this.currentConcept) return;
        
        // Redraw the current concept visualization
        const conceptMap = {
            'classes-objects': () => this.visualizeClassesAndObjects(),
            'variables': () => this.visualizeClassesAndObjects(),
            'methods': () => this.visualizePolymorphism(),
            'conditionals': () => this.visualizeConditionals(),
            'loops': () => this.visualizeLoops(),
            'switch': () => this.visualizeConditionals(),
            'abstraction': () => this.visualizeAbstraction(),
            'encapsulation': () => this.visualizeEncapsulation(),
            'inheritance': () => this.visualizeInheritance(),
            'polymorphism': () => this.visualizePolymorphism(),
            'interfaces': () => this.visualizeInterfaces(),
            'events': () => this.visualizeEvents(),
            'exceptions': () => this.visualizeExceptionHandling(),
            'collections': () => this.visualizeArraysAndCollections(),
            'singleton': () => this.visualizeSingleton(),
            'debugging': () => this.visualizeDebugging()
        };
        
        const visualizeFunc = conceptMap[this.currentConcept];
        if (visualizeFunc) {
            visualizeFunc();
        }
    }
    
    setCurrentConcept(conceptKey) {
        this.currentConcept = conceptKey;
    }

    visualizeClassesAndObjects() {
        this.setCurrentConcept('classes-objects');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        // Adjust for mobile screens
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        const fontSize = isMobile ? 18 : 24;
        
        this.mapGen.drawText("CLASSES vs OBJECTS", 20, 20, { fontSize: fontSize, color: '#00FF00' });
        
        this.mapGen.drawText("CLASS: Barracks Blueprint", 50, 80, { fontSize: 16, color: '#FFD700' });
        this.mapGen.ctx.strokeStyle = '#FFD700';
        this.mapGen.ctx.lineWidth = 2;
        this.mapGen.ctx.setLineDash([5, 5]);
        this.mapGen.ctx.strokeRect(45, 120, 100, 100);
        this.mapGen.ctx.setLineDash([]);
        this.mapGen.drawText("Properties:\n- Health: 800\n- Power: -20\n- Cost: 300", 50, 130, { fontSize: 12 });
        
        this.mapGen.drawText("OBJECTS: Actual Barracks Instances", 250, 80, { fontSize: 16, color: '#00FF00' });
        this.mapGen.drawSprite('gdi-barracks', 280 * scale, 160, 2 * scale);  
        this.mapGen.drawText("Barracks #1\nHP: 800/800", 250 * scale, 220, { fontSize: 11 * scale });
        
        this.mapGen.drawSprite('gdi-barracks', 400 * scale, 160, 2 * scale);  
        this.mapGen.drawText("Barracks #2\nHP: 650/800", 370 * scale, 220, { fontSize: 11 * scale });
        
        this.mapGen.drawSprite('gdi-barracks', 520 * scale, 160, 2 * scale);  
        this.mapGen.drawText("Barracks #3\nHP: 200/800", 490 * scale, 220, { fontSize: 11 * scale });
        
        this.mapGen.drawArrow(150, 170, 240, 145, '#FFD700', 'instantiate');
        this.mapGen.drawArrow(150, 170, 340, 145, '#FFD700', 'instantiate');
        this.mapGen.drawArrow(150, 170, 440, 145, '#FFD700', 'instantiate');
        
        this.mapGen.drawText(
            "The CLASS is the blueprint (like in the build menu).\nOBJECTS are the actual buildings you place on the map.",
            50, 300, { fontSize: 14, color: '#FFFFFF', maxWidth: 500 }
        );
    }

    visualizeInheritance() {
        this.setCurrentConcept('inheritance');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        
        this.mapGen.drawText("INHERITANCE HIERARCHY", 20, 20, { fontSize: 24, color: '#00FF00' });
        
        this.mapGen.drawText("BASE CLASS: Vehicle", 300, 80, { fontSize: 16, color: '#FFD700' });
        this.mapGen.ctx.strokeStyle = '#FFD700';
        this.mapGen.ctx.strokeRect(280, 110, 140, 60);
        this.mapGen.drawText("move()\ntakeDamage()\nrepair()", 290, 120, { fontSize: 11 });
        
        this.mapGen.drawText("Tank", 150, 220, { fontSize: 14, color: '#00FF00' });
        this.mapGen.drawSprite('medium-tank', 140, 250, 2);
        this.mapGen.drawText("+ fire()\n+ rotateTurret()", 130, 290, { fontSize: 11 });
        
        this.mapGen.drawText("Harvester", 300, 220, { fontSize: 14, color: '#00FF00' });
        this.mapGen.ctx.fillStyle = '#FFD700';
        this.mapGen.ctx.fillRect(295, 250, 40, 30);
        this.mapGen.drawText("+ harvest()\n+ unload()", 280, 290, { fontSize: 11 });
        
        this.mapGen.drawText("Recon Bike", 450, 220, { fontSize: 14, color: '#00FF00' });
        this.mapGen.drawSprite('recon-bike', 440, 250, 2);
        this.mapGen.drawText("+ stealth()\n+ quickAttack()", 430, 290, { fontSize: 11 });
        
        this.mapGen.drawArrow(350, 170, 180, 220, '#FFFF00');
        this.mapGen.drawArrow(350, 170, 320, 220, '#FFFF00');
        this.mapGen.drawArrow(350, 170, 480, 220, '#FFFF00');
        
        this.mapGen.drawText(
            "All vehicles inherit basic abilities from Vehicle class,\nthen add their own specialized features.",
            50, 350, { fontSize: 14, color: '#FFFFFF', maxWidth: 600 }
        );
    }

    visualizePolymorphism() {
        this.setCurrentConcept('polymorphism');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        
        this.mapGen.drawText("POLYMORPHISM - Same Command, Different Behavior", 20, 20, { fontSize: 20, color: '#00FF00' });
        
        this.mapGen.drawText("ATTACK COMMAND", 300, 80, { fontSize: 18, color: '#FFD700', backgroundColor: 'rgba(255,0,0,0.3)' });
        
        this.mapGen.drawSprite('gdi-barracks', 100, 150, 2);
        this.mapGen.drawText("Infantry\nRifle Fire", 90, 200, { fontSize: 11 });
        
        this.mapGen.drawSprite('medium-tank', 250, 160, 2);
        this.mapGen.drawText("Tank\nCannon Fire", 240, 200, { fontSize: 11 });
        
        this.mapGen.drawSprite('nod-obelisk', 380, 140, 2);
        this.mapGen.drawText("Obelisk\nLaser Beam", 370, 200, { fontSize: 11 });
        
        const centerX = 350;
        const centerY = 100;
        this.mapGen.drawArrow(centerX, centerY, 120, 150, '#FF0000');
        this.mapGen.drawArrow(centerX, centerY, 270, 160, '#FF0000');
        this.mapGen.drawArrow(centerX, centerY, 400, 150, '#FF0000');
        
        this.mapGen.ctx.strokeStyle = '#00FF00';
        this.mapGen.ctx.lineWidth = 2;
        this.mapGen.ctx.beginPath();
        this.mapGen.ctx.arc(520, 170, 15, 0, Math.PI * 2);
        this.mapGen.ctx.stroke();
        this.mapGen.ctx.fillStyle = '#FF0000';
        this.mapGen.ctx.font = 'bold 20px Arial';
        this.mapGen.ctx.fillText('X', 513, 178);
        this.mapGen.drawText("Target", 500, 190, { fontSize: 11 });
        
        this.mapGen.drawText(
            "Same 'Attack' command → Different implementation for each unit type",
            50, 250, { fontSize: 14, color: '#FFFFFF' }
        );
    }

    visualizeEncapsulation() {
        this.setCurrentConcept('encapsulation');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        
        this.mapGen.drawText("ENCAPSULATION - Hidden Internal State", 20, 20, { fontSize: 20, color: '#00FF00' });
        
        this.mapGen.drawSprite('gdi-cy', 200, 100, 2);
        
        this.mapGen.ctx.strokeStyle = '#FF0000';
        this.mapGen.ctx.lineWidth = 3;
        this.mapGen.ctx.strokeRect(195, 95, 58, 58);
        
        this.mapGen.ctx.fillStyle = 'rgba(255,0,0,0.2)';
        this.mapGen.ctx.fillRect(195, 95, 58, 58);
        
        this.mapGen.drawText("PRIVATE", 200, 80, { fontSize: 12, color: '#FF0000', bold: true });
        this.mapGen.drawText("- buildQueue[]\n- construction%\n- powerGrid", 270, 105, { fontSize: 11, color: '#FF6666' });
        
        this.mapGen.drawText("PUBLIC INTERFACE", 200, 180, { fontSize: 12, color: '#00FF00', bold: true });
        this.mapGen.ctx.strokeStyle = '#00FF00';
        this.mapGen.ctx.setLineDash([3, 3]);
        this.mapGen.ctx.strokeRect(195, 195, 200, 80);
        this.mapGen.ctx.setLineDash([]);
        
        this.mapGen.drawText("+ build(unit)\n+ cancelBuild()\n+ getStatus()\n+ isReady()", 205, 205, { fontSize: 11, color: '#00FF00' });
        
        this.mapGen.drawArrow(450, 130, 400, 130, '#FFFF00');
        this.mapGen.drawText("Can't access\ninternal state\ndirectly!", 460, 115, { fontSize: 11 });
        
        this.mapGen.drawArrow(450, 230, 395, 230, '#00FF00');
        this.mapGen.drawText("Must use\npublic methods", 460, 215, { fontSize: 11 });
        
        this.mapGen.drawText(
            "Construction Yard hides its internal workings.\nOther units can only interact through defined methods.",
            50, 300, { fontSize: 14, color: '#FFFFFF' }
        );
    }

    visualizeAbstraction() {
        this.setCurrentConcept('abstraction');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        
        this.mapGen.drawText("ABSTRACTION - Simple Interface, Complex Implementation", 20, 20, { fontSize: 18, color: '#00FF00' });
        
        this.mapGen.drawText("ION CANNON UPLINK", 250, 70, { fontSize: 16, color: '#00FFFF' });
        
        this.mapGen.ctx.fillStyle = '#0066CC';
        this.mapGen.ctx.fillRect(280, 100, 60, 60);
        this.mapGen.ctx.fillStyle = '#00FFFF';
        this.mapGen.ctx.beginPath();
        this.mapGen.ctx.arc(310, 130, 20, 0, Math.PI * 2);
        this.mapGen.ctx.fill();
        
        this.mapGen.drawText("SIMPLE INTERFACE", 150, 180, { fontSize: 12, color: '#00FF00' });
        this.mapGen.drawText("1. Select Ion Cannon\n2. Click Target\n3. Fire!", 150, 200, { fontSize: 11 });
        
        this.mapGen.drawText("COMPLEX HIDDEN PROCESS", 350, 180, { fontSize: 12, color: '#FF6666' });
        this.mapGen.drawText(
            "• Satellite positioning\n• Orbital calculations\n• Energy charging\n• Beam focusing\n• Atmospheric entry\n• Target tracking",
            350, 200, { fontSize: 10, color: '#FFD700' }
        );
        
        this.mapGen.ctx.strokeStyle = '#00FFFF';
        this.mapGen.ctx.lineWidth = 3;
        this.mapGen.ctx.beginPath();
        this.mapGen.ctx.moveTo(310, 160);
        this.mapGen.ctx.lineTo(310, 350);
        this.mapGen.ctx.stroke();
        
        for (let i = 0; i < 5; i++) {
            this.mapGen.ctx.beginPath();
            this.mapGen.ctx.moveTo(310 - 20 + i * 10, 350 - i * 5);
            this.mapGen.ctx.lineTo(310, 350);
            this.mapGen.ctx.stroke();
        }
        
        this.mapGen.ctx.fillStyle = '#FFFF00';
        this.mapGen.ctx.beginPath();
        this.mapGen.ctx.arc(310, 350, 30, 0, Math.PI * 2);
        this.mapGen.ctx.fill();
        this.mapGen.ctx.fillStyle = '#FF0000';
        this.mapGen.ctx.beginPath();
        this.mapGen.ctx.arc(310, 350, 20, 0, Math.PI * 2);
        this.mapGen.ctx.fill();
        
        this.mapGen.drawText(
            "You don't need to know HOW it works, just how to USE it!",
            100, 400, { fontSize: 14, color: '#FFFFFF', bold: true }
        );
    }

    visualizeLoops() {
        this.setCurrentConcept('loops');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        
        this.mapGen.drawText("LOOPS IN ACTION", 20, 20, { fontSize: 24, color: '#00FF00' });
        
        this.mapGen.drawText("FOR LOOP: Deploy 5 Infantry", 50, 80, { fontSize: 14, color: '#FFD700' });
        for (let i = 0; i < 5; i++) {
            this.mapGen.ctx.fillStyle = '#4444FF';
            this.mapGen.ctx.fillRect(60 + i * 30, 110, 20, 20);
            this.mapGen.drawText(`${i+1}`, 65 + i * 30, 135, { fontSize: 10 });
        }
        
        this.mapGen.drawText("WHILE: Harvest Until Refinery Full", 50, 180, { fontSize: 14, color: '#FFD700' });
        this.mapGen.ctx.fillStyle = '#8B4513';
        this.mapGen.ctx.fillRect(60, 210, 120, 40);
        this.mapGen.ctx.fillStyle = '#FFD700';
        let fillLevel = 0;
        for (let i = 0; i < 4; i++) {
            fillLevel += 25;
            this.mapGen.ctx.fillRect(60, 250 - fillLevel * 0.4, 120, fillLevel * 0.4);
            this.mapGen.drawText(`${fillLevel}%`, 190 + i * 40, 220, { fontSize: 11 });
            
            if (i < 3) {
                this.mapGen.drawArrow(210 + i * 40, 230, 230 + i * 40, 230, '#00FF00');
            }
        }
        
        this.mapGen.drawText("FOREACH: Check All Enemy Units", 50, 280, { fontSize: 14, color: '#FFD700' });
        const enemyUnits = ['Tank', 'Infantry', 'Orca', 'Bike'];
        enemyUnits.forEach((unit, index) => {
            this.mapGen.ctx.fillStyle = '#FF4444';
            this.mapGen.ctx.fillRect(60 + index * 80, 310, 30, 30);
            this.mapGen.drawText(unit, 60 + index * 80, 345, { fontSize: 10 });
            
            const status = index % 2 === 0 ? '✓' : 'X';
            const color = index % 2 === 0 ? '#00FF00' : '#FF0000';
            this.mapGen.drawText(status, 75 + index * 80, 315, { fontSize: 16, color: color });
        });
        
        this.mapGen.drawText(
            "Loops automate repetitive tasks - essential for RTS games!",
            50, 390, { fontSize: 14, color: '#FFFFFF' }
        );
    }

    visualizeConditionals() {
        this.setCurrentConcept('conditionals');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        
        this.mapGen.drawText("IF-ELSE DECISION MAKING", 20, 20, { fontSize: 24, color: '#00FF00' });
        
        const decisionX = 320;
        const decisionY = 100;
        
        this.mapGen.ctx.fillStyle = '#FFD700';
        this.mapGen.ctx.beginPath();
        this.mapGen.ctx.moveTo(decisionX, decisionY - 20);
        this.mapGen.ctx.lineTo(decisionX + 40, decisionY + 20);
        this.mapGen.ctx.lineTo(decisionX, decisionY + 60);
        this.mapGen.ctx.lineTo(decisionX - 40, decisionY + 20);
        this.mapGen.ctx.closePath();
        this.mapGen.ctx.fill();
        
        this.mapGen.drawText("Enemy\nDetected?", decisionX - 30, decisionY + 10, { fontSize: 11, color: '#000000' });
        
        this.mapGen.drawArrow(decisionX - 40, decisionY + 20, 200, 180, '#00FF00');
        this.mapGen.drawText("YES", 230, 140, { fontSize: 12, color: '#00FF00' });
        this.mapGen.drawText("ATTACK MODE", 140, 180, { fontSize: 14, color: '#FF0000' });
        this.mapGen.drawSprite('medium-tank', 150, 210, 0.8);
        this.mapGen.drawText("• Target acquired\n• Weapons hot\n• Fire at will", 130, 250, { fontSize: 11 });
        
        this.mapGen.drawArrow(decisionX + 40, decisionY + 20, 480, 180, '#0000FF');
        this.mapGen.drawText("NO", 430, 140, { fontSize: 12, color: '#0000FF' });
        this.mapGen.drawText("PATROL MODE", 420, 180, { fontSize: 14, color: '#0000FF' });
        this.mapGen.ctx.strokeStyle = '#0000FF';
        this.mapGen.ctx.setLineDash([5, 5]);
        this.mapGen.ctx.strokeRect(430, 210, 40, 40);
        this.mapGen.ctx.setLineDash([]);
        this.mapGen.drawText("• Continue patrol\n• Scan perimeter\n• Stay alert", 410, 260, { fontSize: 11 });
        
        this.mapGen.drawText("SWITCH: Response to Unit Type", 50, 320, { fontSize: 14, color: '#FFD700' });
        
        const switchOptions = [
            { type: 'Infantry', response: 'Flamers', color: '#FF6600' },
            { type: 'Tanks', response: 'Rockets', color: '#FF0000' },
            { type: 'Aircraft', response: 'SAM Sites', color: '#0066FF' }
        ];
        
        switchOptions.forEach((option, index) => {
            const x = 100 + index * 140;
            this.mapGen.drawText(option.type, x, 350, { fontSize: 12 });
            this.mapGen.drawArrow(x + 30, 365, x + 30, 385, option.color);
            this.mapGen.drawText(option.response, x, 395, { fontSize: 11, color: option.color });
        });
        
        this.mapGen.drawText(
            "Strategic decisions based on battlefield conditions",
            100, 440, { fontSize: 14, color: '#FFFFFF' }
        );
    }

    visualizeEvents() {
        this.setCurrentConcept('events');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        
        this.mapGen.drawText("EVENT-DRIVEN SYSTEM", 20, 20, { fontSize: 24, color: '#00FF00' });
        
        this.mapGen.drawText("EVENT: Enemy Detected!", 250, 80, { fontSize: 16, color: '#FF0000', backgroundColor: 'rgba(255,0,0,0.2)' });
        
        this.mapGen.ctx.fillStyle = '#FF0000';
        this.mapGen.ctx.beginPath();
        this.mapGen.ctx.arc(350, 140, 30, 0, Math.PI * 2);
        this.mapGen.ctx.fill();
        this.mapGen.drawText("!", 343, 125, { fontSize: 30, color: '#FFFFFF' });
        
        this.mapGen.drawText("TRIGGERED RESPONSES:", 50, 200, { fontSize: 14, color: '#FFD700' });
        
        const responses = [
            { text: "Sound Alarm", x: 100, y: 230, delay: 0 },
            { text: "Flash Minimap", x: 100, y: 260, delay: 100 },
            { text: "Auto-Target Defenses", x: 100, y: 290, delay: 200 },
            { text: "EVA Alert: 'Unit Under Attack!'", x: 100, y: 320, delay: 300 }
        ];
        
        responses.forEach((response, index) => {
            this.mapGen.drawArrow(350, 170, response.x - 10, response.y + 5, '#FFFF00');
            this.mapGen.drawText(`${index + 1}. ${response.text}`, response.x, response.y, { fontSize: 12 });
        });
        
        this.mapGen.drawText(
            "One event triggers multiple automatic responses across the system",
            50, 370, { fontSize: 14, color: '#FFFFFF' }
        );
    }

    visualizeInterfaces() {
        this.setCurrentConcept('interfaces');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        
        this.mapGen.drawText("INTERFACES - Common Contracts", 20, 20, { fontSize: 24, color: '#00FF00' });
        
        this.mapGen.ctx.strokeStyle = '#FFD700';
        this.mapGen.ctx.lineWidth = 2;
        this.mapGen.ctx.strokeRect(250, 70, 180, 80);
        this.mapGen.drawText("IDestructible Interface", 255, 75, { fontSize: 14, color: '#FFD700' });
        this.mapGen.drawText("• takeDamage(amount)\n• getCurrentHealth()\n• isDestroyed()\n• explode()", 260, 100, { fontSize: 11 });
        
        this.mapGen.drawText("GDI Units", 120, 180, { fontSize: 14, color: '#0088FF' });
        this.mapGen.drawSprite('gdi-barracks', 100, 210, 2);
        this.mapGen.drawSprite('mammoth', 100, 270, 1.5);
        
        this.mapGen.drawText("NOD Units", 420, 180, { fontSize: 14, color: '#FF0000' });
        this.mapGen.drawSprite('nod-hand', 400, 210, 2);
        this.mapGen.drawSprite('recon-bike', 400, 270, 1.5);
        
        this.mapGen.drawArrow(250, 120, 150, 230, '#FFD700');
        this.mapGen.drawArrow(250, 120, 150, 280, '#FFD700');
        this.mapGen.drawArrow(430, 120, 450, 230, '#FFD700');
        this.mapGen.drawArrow(430, 120, 450, 280, '#FFD700');
        
        this.mapGen.drawText(
            "Both factions implement the same interface differently,\nbut all units can be damaged and destroyed the same way!",
            80, 340, { fontSize: 14, color: '#FFFFFF' }
        );
    }

    visualizeArraysAndCollections() {
        this.setCurrentConcept('collections');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        
        this.mapGen.drawText("ARRAYS & COLLECTIONS", 20, 20, { fontSize: 24, color: '#00FF00' });
        
        this.mapGen.drawText("ARRAY: Unit Selection (Fixed Size)", 50, 80, { fontSize: 14, color: '#FFD700' });
        this.mapGen.ctx.strokeStyle = '#00FF00';
        this.mapGen.ctx.lineWidth = 2;
        for (let i = 0; i < 5; i++) {
            this.mapGen.ctx.strokeRect(60 + i * 50, 110, 40, 40);
            if (i < 3) {
                this.mapGen.drawSprite('medium-tank', 65 + i * 50, 115, 0.6);
                this.mapGen.drawText(`[${i}]`, 75 + i * 50, 155, { fontSize: 10 });
            } else {
                this.mapGen.drawText("empty", 65 + i * 50, 125, { fontSize: 10, color: '#666666' });
                this.mapGen.drawText(`[${i}]`, 75 + i * 50, 155, { fontSize: 10, color: '#666666' });
            }
        }
        this.mapGen.drawText("Max 5 units selected", 320, 125, { fontSize: 11, color: '#FFFF00' });
        
        this.mapGen.drawText("LIST: Build Queue (Dynamic)", 50, 200, { fontSize: 14, color: '#FFD700' });
        const buildQueue = ['Tank', 'Infantry', 'Infantry', 'APC', '+ Add'];
        buildQueue.forEach((item, index) => {
            if (index < buildQueue.length - 1) {
                this.mapGen.ctx.fillStyle = '#444444';
                this.mapGen.ctx.fillRect(60 + index * 70, 230, 60, 30);
                this.mapGen.ctx.fillStyle = '#00FF00';
                this.mapGen.ctx.fillRect(60 + index * 70, 230, 60 * ((4-index)/4), 30);
                this.mapGen.drawText(item, 65 + index * 70, 235, { fontSize: 10, color: '#FFFFFF' });
            } else {
                this.mapGen.ctx.strokeStyle = '#00FF00';
                this.mapGen.ctx.setLineDash([3, 3]);
                this.mapGen.ctx.strokeRect(60 + index * 70, 230, 60, 30);
                this.mapGen.ctx.setLineDash([]);
                this.mapGen.drawText(item, 65 + index * 70, 238, { fontSize: 10, color: '#00FF00' });
            }
        });
        
        this.mapGen.drawText("DICTIONARY: Player → Base Location", 50, 290, { fontSize: 14, color: '#FFD700' });
        const players = [
            { name: 'Player1', x: 100, y: 320, color: '#0088FF' },
            { name: 'Player2', x: 250, y: 320, color: '#FF0000' },
            { name: 'Player3', x: 400, y: 320, color: '#00FF00' }
        ];
        
        players.forEach(player => {
            this.mapGen.drawText(player.name, player.x - 20, player.y, { fontSize: 11 });
            this.mapGen.drawArrow(player.x + 20, player.y + 10, player.x + 20, player.y + 30, player.color);
            this.mapGen.ctx.fillStyle = player.color;
            this.mapGen.ctx.fillRect(player.x, player.y + 35, 40, 40);
            this.mapGen.drawText(`Base`, player.x + 5, player.y + 50, { fontSize: 10, color: '#FFFFFF' });
        });
        
        this.mapGen.drawText(
            "Different data structures for different battlefield needs",
            100, 400, { fontSize: 14, color: '#FFFFFF' }
        );
    }

    visualizeSingleton() {
        this.setCurrentConcept('singleton');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        
        this.mapGen.drawText("SINGLETON PATTERN - Ion Cannon", 20, 20, { fontSize: 24, color: '#00FF00' });
        
        this.mapGen.ctx.fillStyle = '#0066CC';
        this.mapGen.ctx.fillRect(300, 100, 80, 80);
        this.mapGen.ctx.fillStyle = '#00FFFF';
        this.mapGen.ctx.beginPath();
        this.mapGen.ctx.arc(340, 140, 30, 0, Math.PI * 2);
        this.mapGen.ctx.fill();
        this.mapGen.drawText("ION CANNON", 305, 85, { fontSize: 12, color: '#00FFFF' });
        this.mapGen.drawText("SINGLETON", 310, 190, { fontSize: 11, color: '#FFD700' });
        
        this.mapGen.ctx.strokeStyle = '#FF0000';
        this.mapGen.ctx.lineWidth = 3;
        this.mapGen.ctx.beginPath();
        this.mapGen.ctx.moveTo(150, 250);
        this.mapGen.ctx.lineTo(190, 290);
        this.mapGen.ctx.moveTo(150, 290);
        this.mapGen.ctx.lineTo(190, 250);
        this.mapGen.ctx.stroke();
        
        this.mapGen.drawText("Cannot Build", 140, 300, { fontSize: 11, color: '#FF0000' });
        this.mapGen.drawText("Second Uplink", 135, 315, { fontSize: 11, color: '#FF0000' });
        
        this.mapGen.ctx.strokeStyle = '#00FF00';
        this.mapGen.ctx.lineWidth = 2;
        this.mapGen.ctx.beginPath();
        this.mapGen.ctx.arc(450, 270, 15, 0, Math.PI * 2);
        this.mapGen.ctx.stroke();
        this.mapGen.drawText("✓", 443, 258, { fontSize: 20, color: '#00FF00' });
        this.mapGen.drawText("Only ONE", 425, 295, { fontSize: 11, color: '#00FF00' });
        this.mapGen.drawText("Instance Allowed", 410, 310, { fontSize: 11, color: '#00FF00' });
        
        for (let i = 0; i < 3; i++) {
            const angle = (i * 120 - 90) * Math.PI / 180;
            const startX = 340 + Math.cos(angle) * 50;
            const startY = 140 + Math.sin(angle) * 50;
            const endX = 340 + Math.cos(angle) * 100;
            const endY = 140 + Math.sin(angle) * 100;
            
            this.mapGen.ctx.strokeStyle = '#00FFFF';
            this.mapGen.ctx.lineWidth = 2;
            this.mapGen.ctx.beginPath();
            this.mapGen.ctx.moveTo(startX, startY);
            this.mapGen.ctx.lineTo(endX, endY);
            this.mapGen.ctx.stroke();
            
            this.mapGen.ctx.beginPath();
            this.mapGen.ctx.arc(endX, endY, 3, 0, Math.PI * 2);
            this.mapGen.ctx.fill();
        }
        
        this.mapGen.drawText(
            "Only ONE Ion Cannon uplink can exist at a time.\nThis is the Singleton pattern - ensuring single instance!",
            80, 360, { fontSize: 14, color: '#FFFFFF' }
        );
    }

    visualizeExceptionHandling() {
        this.setCurrentConcept('exceptions');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        
        this.mapGen.drawText("EXCEPTION HANDLING", 20, 20, { fontSize: 24, color: '#00FF00' });
        
        this.mapGen.drawText("TRY: Launch Nuclear Strike", 200, 80, { fontSize: 16, color: '#FFD700' });
        
        this.mapGen.ctx.fillStyle = '#FF6600';
        this.mapGen.ctx.fillRect(250, 110, 100, 60);
        this.mapGen.drawText("TEMPLE OF NOD", 260, 130, { fontSize: 11, color: '#FFFFFF' });
        this.mapGen.drawText("Launching...", 270, 150, { fontSize: 10, color: '#FFFF00' });
        
        this.mapGen.drawText("POSSIBLE EXCEPTIONS:", 50, 200, { fontSize: 14, color: '#FF0000' });
        
        const exceptions = [
            { error: "Insufficient Power", solution: "Build Power Plant", x: 80 },
            { error: "Temple Destroyed", solution: "Rebuild Temple", x: 250 },
            { error: "No Target Selected", solution: "Select Target", x: 420 }
        ];
        
        exceptions.forEach(exc => {
            this.mapGen.ctx.fillStyle = '#FF0000';
            this.mapGen.ctx.fillRect(exc.x, 230, 100, 40);
            this.mapGen.drawText("CATCH:", exc.x + 5, 235, { fontSize: 10, color: '#FFFFFF' });
            this.mapGen.drawText(exc.error, exc.x + 5, 248, { fontSize: 9, color: '#FFFF00' });
            
            this.mapGen.drawArrow(exc.x + 50, 270, exc.x + 50, 300, '#00FF00');
            
            this.mapGen.ctx.fillStyle = '#00AA00';
            this.mapGen.ctx.fillRect(exc.x, 305, 100, 30);
            this.mapGen.drawText(exc.solution, exc.x + 5, 315, { fontSize: 10, color: '#FFFFFF' });
        });
        
        this.mapGen.drawText("FINALLY: Resume Normal Operations", 200, 360, { fontSize: 14, color: '#00FFFF' });
        
        this.mapGen.drawText(
            "Handle errors gracefully to keep the battle going!",
            150, 400, { fontSize: 14, color: '#FFFFFF' }
        );
    }

    visualizeDebugging() {
        this.setCurrentConcept('debugging');
        this.mapGen.clear();
        this.mapGen.drawTerrain();
        
        const isMobile = window.innerWidth < 768;
        const scale = isMobile ? 0.8 : 1;
        
        this.mapGen.drawText("DEBUGGING AS BATTLEFIELD INTELLIGENCE", 20, 20, { fontSize: 20, color: '#00FF00' });
        
        this.mapGen.drawText("LOGGING - EVA Status Updates", 50, 80, { fontSize: 14, color: '#FFD700' });
        const logs = [
            { time: "10:01", msg: "Construction Complete", color: '#00FF00' },
            { time: "10:02", msg: "Unit Ready", color: '#00FF00' },
            { time: "10:03", msg: "Insufficient Funds", color: '#FF0000' },
            { time: "10:04", msg: "Building...", color: '#FFFF00' }
        ];
        
        logs.forEach((log, index) => {
            this.mapGen.drawText(`[${log.time}] ${log.msg}`, 60, 110 + index * 20, { fontSize: 11, color: log.color });
        });
        
        this.mapGen.drawText("BREAKPOINTS - Pause & Analyze", 350, 80, { fontSize: 14, color: '#FFD700' });
        this.mapGen.ctx.fillStyle = '#FF0000';
        this.mapGen.ctx.fillRect(380, 110, 60, 20);
        this.mapGen.drawText("PAUSED", 390, 114, { fontSize: 11, color: '#FFFFFF' });
        
        this.mapGen.drawText("Inspect State:", 360, 145, { fontSize: 11 });
        this.mapGen.drawText("• Units: 12\n• Credits: 2450\n• Power: -50\n• Queue: 3", 360, 160, { fontSize: 10, color: '#00FF00' });
        
        this.mapGen.drawText("HAND TRACING - Plan Your Attack", 50, 250, { fontSize: 14, color: '#FFD700' });
        
        this.mapGen.ctx.strokeStyle = '#666666';
        this.mapGen.ctx.setLineDash([2, 2]);
        for (let i = 1; i < 4; i++) {
            this.mapGen.ctx.beginPath();
            this.mapGen.ctx.moveTo(80, 280);
            this.mapGen.ctx.lineTo(80 + i * 60, 320 + i * 10);
            this.mapGen.ctx.stroke();
        }
        this.mapGen.ctx.setLineDash([]);
        
        this.mapGen.drawText("1. Scout", 80, 265, { fontSize: 10 });
        this.mapGen.drawText("2. Flank", 140, 330, { fontSize: 10 });
        this.mapGen.drawText("3. Attack", 200, 340, { fontSize: 10 });
        this.mapGen.drawText("4. Win!", 260, 350, { fontSize: 10 });
        
        this.mapGen.drawText("MENTAL TRACING - Predict Outcomes", 350, 250, { fontSize: 14, color: '#FFD700' });
        this.mapGen.ctx.strokeStyle = '#00FF00';
        this.mapGen.ctx.lineWidth = 1;
        this.mapGen.ctx.beginPath();
        this.mapGen.ctx.arc(420, 300, 30, 0, Math.PI * 2);
        this.mapGen.ctx.stroke();
        this.mapGen.drawText("If I attack...", 385, 285, { fontSize: 10 });
        this.mapGen.drawText("Enemy responds", 380, 315, { fontSize: 10 });
        this.mapGen.drawText("I counter with...", 375, 330, { fontSize: 10 });
        
        this.mapGen.drawText(
            "Master debugging = Master the battlefield!",
            180, 400, { fontSize: 14, color: '#FFFFFF' }
        );
    }
}

export default ConceptVisualizer;