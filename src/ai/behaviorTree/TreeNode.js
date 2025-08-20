/**
 * Behavior Tree Node System
 * Base TreeNode class providing common functionality for all behavior tree nodes
 */

/**
 * Node execution status enumeration
 */
export const NodeStatus = {
    RUNNING: "RUNNING",    // Node is still executing
    SUCCESS: "SUCCESS",    // Node completed successfully
    FAILURE: "FAILURE"     // Node failed to complete
};

/**
 * Abstract base class for all behavior tree nodes
 * Provides common functionality and defines the contract for node implementations
 */
export class TreeNode {
    constructor(name = "Unnamed Node") {
        this.name = name;
        this.status = NodeStatus.RUNNING;
        this.children = [];
        this.parent = null;
        this.isRunning = false;
        
        // Time-slicing support
        this.maxExecutionTime = 5; // Maximum milliseconds per tick
        this.startTime = 0;
    }

    /**
     * Add a child node to this node
     * @param {TreeNode} child - The child node to add
     * @returns {TreeNode} This node for chaining
     */
    addChild(child) {
        if (!(child instanceof TreeNode)) {
            throw new Error("Child must be an instance of TreeNode");
        }
        
        this.children.push(child);
        child.parent = this;
        return this;
    }

    /**
     * Remove a child node from this node
     * @param {TreeNode} child - The child node to remove
     * @returns {boolean} True if child was removed, false if not found
     */
    removeChild(child) {
        const index = this.children.indexOf(child);
        if (index !== -1) {
            this.children.splice(index, 1);
            child.parent = null;
            return true;
        }
        return false;
    }

    /**
     * Get all child nodes
     * @returns {TreeNode[]} Array of child nodes
     */
    getChildren() {
        return [...this.children];
    }

    /**
     * Check if this node has children
     * @returns {boolean} True if node has children
     */
    hasChildren() {
        return this.children.length > 0;
    }

    /**
     * Reset the node to its initial state
     * Called when the tree needs to restart or when a parent resets
     */
    reset() {
        this.status = NodeStatus.RUNNING;
        this.isRunning = false;
        this.startTime = 0;
        
        // Reset all children
        this.children.forEach(child => child.reset());
    }

    /**
     * Abstract tick method - must be implemented by subclasses
     * This is the main execution method called during tree traversal
     * @param {number} deltaTime - Time elapsed since last tick in milliseconds
     * @returns {string} NodeStatus - Current status after execution
     */
    tick(deltaTime = 0) {
        throw new Error("tick() method must be implemented by subclass");
    }

    /**
     * Execute a single tick with time-slicing support
     * Wraps the tick method to provide time management and status tracking
     * @param {number} deltaTime - Time elapsed since last tick in milliseconds
     * @returns {string} NodeStatus - Current status after execution
     */
    execute(deltaTime = 0) {
        // Record start time for this execution
        this.startTime = performance.now();
        
        // If node is not running and not failed/succeeded, start it
        if (!this.isRunning && this.status === NodeStatus.RUNNING) {
            this.isRunning = true;
        }

        // Execute the node's specific tick logic
        try {
            this.status = this.tick(deltaTime);
        } catch (error) {
            console.error(`Error in node ${this.name}:`, error);
            this.status = NodeStatus.FAILURE;
        }

        // If node completed (success or failure), mark as not running
        if (this.status !== NodeStatus.RUNNING) {
            this.isRunning = false;
        }

        return this.status;
    }

    /**
     * Check if time slice has been exceeded
     * @returns {boolean} True if execution should yield to prevent frame drops
     */
    hasTimeSliceExpired() {
        const elapsed = performance.now() - this.startTime;
        return elapsed >= this.maxExecutionTime;
    }

    /**
     * Set the maximum execution time for this node
     * @param {number} maxTime - Maximum execution time in milliseconds
     */
    setMaxExecutionTime(maxTime) {
        this.maxExecutionTime = Math.max(1, maxTime);
    }

    /**
     * Get debug information about this node
     * @returns {Object} Debug information object
     */
    getDebugInfo() {
        return {
            name: this.name,
            type: this.constructor.name,
            status: this.status,
            isRunning: this.isRunning,
            childCount: this.children.length,
            hasParent: this.parent !== null
        };
    }

    /**
     * Get a string representation of the node tree
     * @param {number} depth - Current depth for indentation
     * @returns {string} Tree structure as string
     */
    toString(depth = 0) {
        const indent = "  ".repeat(depth);
        const statusIcon = this.status === NodeStatus.SUCCESS ? "✓" : 
            this.status === NodeStatus.FAILURE ? "✗" : 
                this.isRunning ? "⟳" : "○";
        
        let result = `${indent}${statusIcon} ${this.name} (${this.constructor.name})\n`;
        
        this.children.forEach(child => {
            result += child.toString(depth + 1);
        });
        
        return result;
    }
}

/**
 * Helper function to create a node tree from a simple configuration object
 * @param {Object} config - Node configuration
 * @returns {TreeNode} The created node tree
 */
export async function createNodeFromConfig(config) {
    if (!config.type) {
        throw new Error("Node configuration must specify a type");
    }

    let node;
    
    // Import basic nodes dynamically to avoid circular dependencies
    const { SelectorNode, SequenceNode, ActionNode } = await import("./BasicNodes.js");
    
    switch (config.type.toLowerCase()) {
    case "selector":
        node = new SelectorNode(config.name);
        break;
    case "sequence":
        node = new SequenceNode(config.name);
        break;
    case "action":
        node = new ActionNode(config.action || null, config.name);
        if (config.context) {
            node.setContext(config.context);
        }
        break;
    default:
        throw new Error(`Unknown node type: ${config.type}`);
    }

    // Set custom execution time if provided
    if (config.maxExecutionTime !== undefined) {
        node.setMaxExecutionTime(config.maxExecutionTime);
    }

    // Add children if provided
    if (config.children && Array.isArray(config.children)) {
        for (const childConfig of config.children) {
            const childNode = await createNodeFromConfig(childConfig);
            node.addChild(childNode);
        }
    }

    return node;
}

/**
 * Synchronous version of createNodeFromConfig for when async is not needed
 * Requires BasicNodes to be imported manually
 * @param {Object} config - Node configuration
 * @param {Object} nodeTypes - Object containing node constructors
 * @returns {TreeNode} The created node tree
 */
export function createNodeFromConfigSync(config, nodeTypes) {
    if (!config.type) {
        throw new Error("Node configuration must specify a type");
    }

    let node;
    const { SelectorNode, SequenceNode, ActionNode } = nodeTypes;
    
    switch (config.type.toLowerCase()) {
    case "selector":
        node = new SelectorNode(config.name);
        break;
    case "sequence":
        node = new SequenceNode(config.name);
        break;
    case "action":
        node = new ActionNode(config.action || null, config.name);
        if (config.context) {
            node.setContext(config.context);
        }
        break;
    default:
        throw new Error(`Unknown node type: ${config.type}`);
    }

    // Set custom execution time if provided
    if (config.maxExecutionTime !== undefined) {
        node.setMaxExecutionTime(config.maxExecutionTime);
    }

    // Add children if provided
    if (config.children && Array.isArray(config.children)) {
        config.children.forEach(childConfig => {
            const childNode = createNodeFromConfigSync(childConfig, nodeTypes);
            node.addChild(childNode);
        });
    }

    return node;
}