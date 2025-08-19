/**
 * Entity - Unique identifier for game objects
 * Entities are lightweight containers that hold components
 */
export class Entity {
    static nextId = 1;
    static livingEntities = new WeakSet(); // Track living entities for validation
    
    constructor() {
        this.id = Entity.nextId++;
        this.components = new Map();
        this.active = true;
        this.destroyed = false;
        this.creationTime = Date.now();
        this.lastAccessTime = Date.now();
        
        // Track living entities
        Entity.livingEntities.add(this);
    }
    
    /**
     * Add a component to this entity
     */
    addComponent(component) {
        if (this.destroyed) {
            console.warn(`Attempting to add component to destroyed entity ${this.id}`);
            return this;
        }
        
        const componentName = component.constructor.name;
        
        // Check for duplicate components
        if (this.components.has(componentName)) {
            console.warn(`Duplicate component ${componentName} detected on entity ${this.id}. Replacing existing component.`);
            const existingComponent = this.components.get(componentName);
            if (existingComponent && existingComponent.destroy) {
                existingComponent.destroy();
            }
        }
        
        this.components.set(componentName, component);
        
        // Use weak reference pattern
        Object.defineProperty(component, 'entity', {
            value: this,
            writable: false,
            enumerable: false,
            configurable: true
        });
        
        this.lastAccessTime = Date.now();
        return this;
    }
    
    /**
     * Get a component by type
     */
    getComponent(ComponentType) {
        // Handle both class and string inputs
        const componentName = typeof ComponentType === 'string' 
            ? ComponentType 
            : ComponentType.name;
        return this.components.get(componentName) || null;
    }
    
    /**
     * Check if entity has a component
     */
    hasComponent(ComponentType) {
        // Handle both class and string inputs
        const componentName = typeof ComponentType === 'string' 
            ? ComponentType 
            : ComponentType.name;
        return this.components.has(componentName);
    }
    
    /**
     * Remove a component
     */
    removeComponent(ComponentType) {
        if (this.destroyed) {
            console.warn(`Attempting to remove component from destroyed entity ${this.id}`);
            return this;
        }
        
        // Handle both class and string inputs
        const componentName = typeof ComponentType === 'string' 
            ? ComponentType 
            : ComponentType.name;
        const component = this.components.get(componentName);
        if (component) {
            // Properly cleanup component
            if (component.destroy) {
                component.destroy();
            }
            
            // Remove entity reference
            delete component.entity;
            
            this.components.delete(componentName);
            this.lastAccessTime = Date.now();
        }
        return this;
    }
    
    /**
     * Get all components
     */
    getAllComponents() {
        this.lastAccessTime = Date.now();
        return Array.from(this.components.values());
    }
    
    /**
     * Validate entity lifecycle - check if entity is in valid state
     */
    isValid() {
        return !this.destroyed && this.active && Entity.livingEntities.has(this);
    }
    
    /**
     * Get entity memory usage information
     */
    getMemoryInfo() {
        return {
            id: this.id,
            componentCount: this.components.size,
            active: this.active,
            destroyed: this.destroyed,
            creationTime: this.creationTime,
            lastAccessTime: this.lastAccessTime,
            age: Date.now() - this.creationTime,
            timeSinceLastAccess: Date.now() - this.lastAccessTime
        };
    }
    
    /**
     * Destroy entity and cleanup
     */
    destroy() {
        if (this.destroyed) {
            console.warn(`Entity ${this.id} already destroyed`);
            return;
        }
        
        this.active = false;
        this.destroyed = true;
        
        // Cleanup all components in reverse order of addition
        const componentArray = Array.from(this.components.values());
        for (let i = componentArray.length - 1; i >= 0; i--) {
            const component = componentArray[i];
            if (component.destroy) {
                try {
                    component.destroy();
                } catch (error) {
                    console.error(`Error destroying component ${component.constructor.name} on entity ${this.id}:`, error);
                }
            }
            // Remove entity reference
            delete component.entity;
        }
        this.components.clear();
        
        // Final cleanup
        this.lastAccessTime = Date.now();
    }
}