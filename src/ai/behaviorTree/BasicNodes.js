/**
 * Basic Behavior Tree Node Implementations
 * Core node types: Selector, Sequence, and Action nodes
 */

import { TreeNode, NodeStatus } from './TreeNode.js';

/**
 * Selector Node (OR logic)
 * Executes children in order until one succeeds or all fail
 * - Returns SUCCESS if any child succeeds
 * - Returns FAILURE if all children fail
 * - Returns RUNNING while children are executing
 */
export class SelectorNode extends TreeNode {
    constructor(name = 'Selector') {
        super(name);
        this.currentChildIndex = 0;
    }

    /**
     * Reset the selector and its children
     */
    reset() {
        super.reset();
        this.currentChildIndex = 0;
    }

    /**
     * Execute the selector logic
     * @param {number} deltaTime - Time elapsed since last tick
     * @returns {string} NodeStatus
     */
    tick(deltaTime) {
        // If no children, return failure
        if (this.children.length === 0) {
            return NodeStatus.FAILURE;
        }

        // Execute children starting from current index
        while (this.currentChildIndex < this.children.length) {
            const currentChild = this.children[this.currentChildIndex];
            const childStatus = currentChild.execute(deltaTime);

            switch (childStatus) {
                case NodeStatus.SUCCESS:
                    // Child succeeded, selector succeeds
                    this.reset();
                    return NodeStatus.SUCCESS;

                case NodeStatus.FAILURE:
                    // Child failed, try next child
                    currentChild.reset();
                    this.currentChildIndex++;
                    
                    // Check time slice before continuing
                    if (this.hasTimeSliceExpired()) {
                        return NodeStatus.RUNNING;
                    }
                    break;

                case NodeStatus.RUNNING:
                    // Child is still running, keep waiting
                    return NodeStatus.RUNNING;
            }
        }

        // All children failed
        this.reset();
        return NodeStatus.FAILURE;
    }

    /**
     * Get debug information specific to selector
     */
    getDebugInfo() {
        const baseInfo = super.getDebugInfo();
        return {
            ...baseInfo,
            currentChildIndex: this.currentChildIndex,
            totalChildren: this.children.length
        };
    }
}

/**
 * Sequence Node (AND logic)
 * Executes children in order until one fails or all succeed
 * - Returns SUCCESS if all children succeed
 * - Returns FAILURE if any child fails
 * - Returns RUNNING while children are executing
 */
export class SequenceNode extends TreeNode {
    constructor(name = 'Sequence') {
        super(name);
        this.currentChildIndex = 0;
    }

    /**
     * Reset the sequence and its children
     */
    reset() {
        super.reset();
        this.currentChildIndex = 0;
    }

    /**
     * Execute the sequence logic
     * @param {number} deltaTime - Time elapsed since last tick
     * @returns {string} NodeStatus
     */
    tick(deltaTime) {
        // If no children, return success (empty sequence succeeds)
        if (this.children.length === 0) {
            return NodeStatus.SUCCESS;
        }

        // Execute children starting from current index
        while (this.currentChildIndex < this.children.length) {
            const currentChild = this.children[this.currentChildIndex];
            const childStatus = currentChild.execute(deltaTime);

            switch (childStatus) {
                case NodeStatus.SUCCESS:
                    // Child succeeded, move to next child
                    currentChild.reset();
                    this.currentChildIndex++;
                    
                    // Check if all children completed successfully
                    if (this.currentChildIndex >= this.children.length) {
                        this.reset();
                        return NodeStatus.SUCCESS;
                    }
                    
                    // Check time slice before continuing
                    if (this.hasTimeSliceExpired()) {
                        return NodeStatus.RUNNING;
                    }
                    break;

                case NodeStatus.FAILURE:
                    // Child failed, sequence fails
                    this.reset();
                    return NodeStatus.FAILURE;

                case NodeStatus.RUNNING:
                    // Child is still running, keep waiting
                    return NodeStatus.RUNNING;
            }
        }

        // Should not reach here, but return success if all children completed
        this.reset();
        return NodeStatus.SUCCESS;
    }

    /**
     * Get debug information specific to sequence
     */
    getDebugInfo() {
        const baseInfo = super.getDebugInfo();
        return {
            ...baseInfo,
            currentChildIndex: this.currentChildIndex,
            totalChildren: this.children.length,
            progress: this.children.length > 0 ? (this.currentChildIndex / this.children.length) : 1
        };
    }
}

/**
 * Action Node (Leaf node)
 * Executes a specific behavior or action
 * - Calls the provided action function
 * - Returns the status returned by the action function
 * - Supports async actions with promise handling
 */
export class ActionNode extends TreeNode {
    constructor(actionFunction, name = 'Action') {
        super(name);
        this.actionFunction = actionFunction;
        this.actionContext = {};
        this.isAsyncAction = false;
        this.actionPromise = null;
    }

    /**
     * Set the action function to execute
     * @param {Function} actionFunction - Function that returns NodeStatus or Promise<NodeStatus>
     */
    setAction(actionFunction) {
        if (typeof actionFunction !== 'function') {
            throw new Error('Action must be a function');
        }
        this.actionFunction = actionFunction;
    }

    /**
     * Set context data that will be passed to the action function
     * @param {Object} context - Context object for the action
     */
    setContext(context) {
        this.actionContext = { ...context };
    }

    /**
     * Reset the action node
     */
    reset() {
        super.reset();
        this.actionPromise = null;
        this.isAsyncAction = false;
    }

    /**
     * Execute the action
     * @param {number} deltaTime - Time elapsed since last tick
     * @returns {string} NodeStatus
     */
    tick(deltaTime) {
        // If no action function is set, return failure
        if (!this.actionFunction) {
            console.warn(`Action node ${this.name} has no action function`);
            return NodeStatus.FAILURE;
        }

        try {
            // If this is the first execution or we're not waiting for an async action
            if (!this.isAsyncAction && !this.actionPromise) {
                // Execute the action function
                const result = this.actionFunction(deltaTime, this.actionContext);

                // Check if result is a promise (async action)
                if (result && typeof result.then === 'function') {
                    this.isAsyncAction = true;
                    this.actionPromise = result;
                    
                    // Handle promise resolution
                    this.actionPromise
                        .then(status => {
                            // Validate returned status
                            if (!Object.values(NodeStatus).includes(status)) {
                                console.warn(`Action ${this.name} returned invalid status:`, status);
                                this.status = NodeStatus.FAILURE;
                            } else {
                                this.status = status;
                            }
                            this.isAsyncAction = false;
                            this.actionPromise = null;
                        })
                        .catch(error => {
                            console.error(`Async action ${this.name} failed:`, error);
                            this.status = NodeStatus.FAILURE;
                            this.isAsyncAction = false;
                            this.actionPromise = null;
                        });

                    return NodeStatus.RUNNING;
                } else {
                    // Synchronous action - validate and return result
                    if (!Object.values(NodeStatus).includes(result)) {
                        console.warn(`Action ${this.name} returned invalid status:`, result);
                        return NodeStatus.FAILURE;
                    }
                    return result;
                }
            } else if (this.isAsyncAction) {
                // Async action is still running
                return NodeStatus.RUNNING;
            }
        } catch (error) {
            console.error(`Action ${this.name} threw an error:`, error);
            return NodeStatus.FAILURE;
        }

        return NodeStatus.FAILURE;
    }

    /**
     * Get debug information specific to action
     */
    getDebugInfo() {
        const baseInfo = super.getDebugInfo();
        return {
            ...baseInfo,
            hasAction: this.actionFunction !== null,
            isAsync: this.isAsyncAction,
            contextKeys: Object.keys(this.actionContext)
        };
    }
}

/**
 * Utility function to create a simple action that always succeeds
 * @param {string} name - Name of the action
 * @returns {ActionNode} Action node that always succeeds
 */
export function createSuccessAction(name = 'Success Action') {
    return new ActionNode(() => NodeStatus.SUCCESS, name);
}

/**
 * Utility function to create a simple action that always fails
 * @param {string} name - Name of the action
 * @returns {ActionNode} Action node that always fails
 */
export function createFailureAction(name = 'Failure Action') {
    return new ActionNode(() => NodeStatus.FAILURE, name);
}

/**
 * Utility function to create a delay action that runs for a specified time
 * @param {number} duration - Duration in milliseconds
 * @param {string} name - Name of the action
 * @returns {ActionNode} Action node that runs for the specified duration
 */
export function createDelayAction(duration, name = `Delay ${duration}ms`) {
    let startTime = null;
    
    return new ActionNode((deltaTime) => {
        if (startTime === null) {
            startTime = performance.now();
        }
        
        const elapsed = performance.now() - startTime;
        if (elapsed >= duration) {
            startTime = null; // Reset for next execution
            return NodeStatus.SUCCESS;
        }
        
        return NodeStatus.RUNNING;
    }, name);
}

/**
 * Utility function to create a conditional action
 * @param {Function} condition - Function that returns boolean
 * @param {string} name - Name of the action
 * @returns {ActionNode} Action node that succeeds if condition is true, fails otherwise
 */
export function createConditionalAction(condition, name = 'Conditional Action') {
    return new ActionNode(() => {
        try {
            return condition() ? NodeStatus.SUCCESS : NodeStatus.FAILURE;
        } catch (error) {
            console.error(`Condition in ${name} threw error:`, error);
            return NodeStatus.FAILURE;
        }
    }, name);
}

/**
 * Factory function to update the createNodeFromConfig function in TreeNode.js
 * This extends the base functionality to support basic node types
 */
export function extendNodeFactory() {
    // This function can be called to register the basic node types
    // with the createNodeFromConfig factory function
    return {
        'selector': (config) => new SelectorNode(config.name),
        'sequence': (config) => new SequenceNode(config.name),
        'action': (config) => {
            const node = new ActionNode(null, config.name);
            if (config.action) {
                node.setAction(config.action);
            }
            if (config.context) {
                node.setContext(config.context);
            }
            return node;
        }
    };
}