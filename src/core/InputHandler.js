export class InputHandler {
    constructor(element) {
        this.element = element || document;
        this.listeners = new Map();
        this.keys = new Set();
        this.mouseButtons = new Set();
        this.mousePosition = { x: 0, y: 0 };
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Keyboard events
        this.element.addEventListener('keydown', (e) => {
            this.keys.add(e.key);
            this.emit('keydown', e);
        });
        
        this.element.addEventListener('keyup', (e) => {
            this.keys.delete(e.key);
            this.emit('keyup', e);
        });
        
        // Mouse events
        this.element.addEventListener('mousedown', (e) => {
            this.mouseButtons.add(e.button);
            this.emit('mousedown', e);
        });
        
        this.element.addEventListener('mouseup', (e) => {
            this.mouseButtons.delete(e.button);
            this.emit('mouseup', e);
        });
        
        this.element.addEventListener('mousemove', (e) => {
            this.mousePosition.x = e.clientX;
            this.mousePosition.y = e.clientY;
            this.emit('mousemove', e);
        });
        
        this.element.addEventListener('wheel', (e) => {
            this.emit('wheel', e);
        });
        
        // Touch events (for mobile)
        this.element.addEventListener('touchstart', (e) => {
            this.emit('touchstart', e);
        });
        
        this.element.addEventListener('touchmove', (e) => {
            this.emit('touchmove', e);
        });
        
        this.element.addEventListener('touchend', (e) => {
            this.emit('touchend', e);
        });
        
        // Context menu prevention
        this.element.addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });
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
}