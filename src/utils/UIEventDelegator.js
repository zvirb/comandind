/**
 * UIEventDelegator - Event delegation patterns for UI interactions
 * 
 * This system provides:
 * - Centralized event delegation for UI elements
 * - Automatic cleanup and memory leak prevention
 * - Performance optimization through event delegation
 * - Common UI interaction patterns
 */

import { createEventManager } from './EventListenerManager.js';

export class UIEventDelegator {
    constructor(container = document.body) {
        this.container = container;
        this.eventManager = createEventManager('UIEventDelegator');
        this.handlers = new Map(); // selector -> Map(eventType -> handlers[])
        this.isDestroyed = false;
        
        // Common UI patterns
        this.setupCommonPatterns();
        
        console.log('✅ UIEventDelegator initialized');
    }
    
    /**
     * Setup common UI interaction patterns
     */
    setupCommonPatterns() {
        // Button click delegation
        this.delegate('button, [role="button"], .btn', 'click', (event, element) => {
            // Prevent double-clicks and provide feedback
            if (element.disabled || element.classList.contains('processing')) {
                event.preventDefault();
                return;
            }
            
            // Add visual feedback
            element.classList.add('clicked');
            setTimeout(() => {
                element.classList.remove('clicked');
            }, 150);
        });
        
        // Form validation on input
        this.delegate('input, textarea, select', 'input', (event, element) => {
            // Remove error states on input
            element.classList.remove('error', 'invalid');
            const errorMsg = element.parentNode.querySelector('.error-message');
            if (errorMsg) {
                errorMsg.style.display = 'none';
            }
        });
        
        // Tooltip hover handling
        this.delegate('[data-tooltip]', 'mouseenter', (event, element) => {
            this.showTooltip(element, element.dataset.tooltip);
        });
        
        this.delegate('[data-tooltip]', 'mouseleave', (event, element) => {
            this.hideTooltip();
        });
        
        // Modal/dialog handling
        this.delegate('[data-modal-trigger]', 'click', (event, element) => {
            const modalId = element.dataset.modalTrigger;
            this.openModal(modalId);
        });
        
        this.delegate('[data-modal-close]', 'click', (event, element) => {
            this.closeModal(element.closest('.modal'));
        });
        
        // Keyboard navigation
        this.delegate('[tabindex], input, button, select, textarea, [role="button"]', 'keydown', (event, element) => {
            this.handleKeyboardNavigation(event, element);
        });
        
        // Focus management
        this.delegate('input, textarea, select', 'focus', (event, element) => {
            element.closest('.form-group')?.classList.add('focused');
        });
        
        this.delegate('input, textarea, select', 'blur', (event, element) => {
            element.closest('.form-group')?.classList.remove('focused');
        });
        
        // Drag and drop support
        this.delegate('[draggable="true"]', 'dragstart', (event, element) => {
            element.classList.add('dragging');
            event.dataTransfer.effectAllowed = 'move';
        });
        
        this.delegate('[draggable="true"]', 'dragend', (event, element) => {
            element.classList.remove('dragging');
        });
    }
    
    /**
     * Add a delegated event listener
     */
    delegate(selector, eventType, handler, options = {}) {
        if (this.isDestroyed) {
            console.warn('UIEventDelegator destroyed, ignoring delegate');
            return false;
        }
        
        // Store handler for cleanup
        if (!this.handlers.has(selector)) {
            this.handlers.set(selector, new Map());
        }
        
        const selectorHandlers = this.handlers.get(selector);
        if (!selectorHandlers.has(eventType)) {
            selectorHandlers.set(eventType, []);
        }
        
        selectorHandlers.get(eventType).push(handler);
        
        // Add delegated listener
        return this.eventManager.addDelegatedListener(
            this.container,
            selector,
            eventType,
            handler,
            options
        );
    }
    
    /**
     * Remove a delegated event listener
     */
    undelegate(selector, eventType, handler) {
        if (!this.handlers.has(selector)) {
            return false;
        }
        
        const selectorHandlers = this.handlers.get(selector);
        if (!selectorHandlers.has(eventType)) {
            return false;
        }
        
        const handlers = selectorHandlers.get(eventType);
        const index = handlers.indexOf(handler);
        
        if (index === -1) {
            return false;
        }
        
        handlers.splice(index, 1);
        
        // Clean up empty maps
        if (handlers.length === 0) {
            selectorHandlers.delete(eventType);
        }
        if (selectorHandlers.size === 0) {
            this.handlers.delete(selector);
        }
        
        return this.eventManager.removeDelegatedListener(
            this.container,
            selector,
            eventType,
            handler
        );
    }
    
    /**
     * Handle keyboard navigation
     */
    handleKeyboardNavigation(event, element) {
        const { key, ctrlKey, altKey, shiftKey } = event;
        
        switch (key) {
            case 'Enter':
            case ' ': // Space
                if (element.matches('button, [role="button"], .btn')) {
                    event.preventDefault();
                    element.click();
                }
                break;
                
            case 'Tab':
                // Let browser handle tab navigation but emit custom event
                this.emit('navigation', {
                    type: 'tab',
                    element,
                    direction: shiftKey ? 'backward' : 'forward'
                });
                break;
                
            case 'Escape':
                // Close modals, dropdowns, etc.
                const modal = element.closest('.modal');
                if (modal) {
                    this.closeModal(modal);
                }
                break;
                
            case 'ArrowUp':
            case 'ArrowDown':
                if (element.matches('select, [role="listbox"], [role="menu"]')) {
                    // Handle arrow navigation for custom controls
                    event.preventDefault();
                    this.navigateList(element, key === 'ArrowDown' ? 1 : -1);
                }
                break;
        }
    }
    
    /**
     * Show tooltip
     */
    showTooltip(element, text) {
        let tooltip = document.getElementById('global-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'global-tooltip';
            tooltip.className = 'tooltip';
            document.body.appendChild(tooltip);
        }
        
        tooltip.textContent = text;
        tooltip.style.display = 'block';
        
        // Position tooltip
        const rect = element.getBoundingClientRect();
        tooltip.style.left = rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
        
        // Handle edge cases
        const tooltipRect = tooltip.getBoundingClientRect();
        if (tooltipRect.left < 0) {
            tooltip.style.left = '8px';
        } else if (tooltipRect.right > window.innerWidth) {
            tooltip.style.left = window.innerWidth - tooltipRect.width - 8 + 'px';
        }
    }
    
    /**
     * Hide tooltip
     */
    hideTooltip() {
        const tooltip = document.getElementById('global-tooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
    }
    
    /**
     * Open modal
     */
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        
        modal.classList.add('open');
        modal.style.display = 'block';
        
        // Focus first focusable element
        const firstFocusable = modal.querySelector('input, button, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (firstFocusable) {
            firstFocusable.focus();
        }
        
        this.emit('modal-opened', { modalId, modal });
    }
    
    /**
     * Close modal
     */
    closeModal(modal) {
        if (!modal) return;
        
        modal.classList.remove('open');
        modal.style.display = 'none';
        
        this.emit('modal-closed', { modal });
    }
    
    /**
     * Navigate list items
     */
    navigateList(container, direction) {
        const items = container.querySelectorAll('[role="option"], li, .list-item');
        const currentIndex = Array.from(items).findIndex(item => item.classList.contains('selected') || item === document.activeElement);\n        \n        let newIndex = currentIndex + direction;\n        if (newIndex < 0) newIndex = items.length - 1;\n        if (newIndex >= items.length) newIndex = 0;\n        \n        // Remove previous selection\n        items[currentIndex]?.classList.remove('selected');\n        \n        // Set new selection\n        if (items[newIndex]) {\n            items[newIndex].classList.add('selected');\n            items[newIndex].focus();\n        }\n    }\n    \n    /**\n     * Emit custom event\n     */\n    emit(eventType, data) {\n        const event = new CustomEvent(`ui-${eventType}`, {\n            detail: data,\n            bubbles: true,\n            cancelable: true\n        });\n        \n        this.container.dispatchEvent(event);\n    }\n    \n    /**\n     * Get statistics about delegated events\n     */\n    getStats() {\n        let totalHandlers = 0;\n        for (const selectorHandlers of this.handlers.values()) {\n            for (const handlers of selectorHandlers.values()) {\n                totalHandlers += handlers.length;\n            }\n        }\n        \n        return {\n            selectors: this.handlers.size,\n            totalHandlers,\n            eventManagerStats: this.eventManager.getStats(),\n            isDestroyed: this.isDestroyed\n        };\n    }\n    \n    /**\n     * Destroy and cleanup\n     */\n    destroy() {\n        if (this.isDestroyed) {\n            console.warn('UIEventDelegator already destroyed');\n            return;\n        }\n        \n        console.log('🗑️ Destroying UIEventDelegator...');\n        \n        this.isDestroyed = true;\n        \n        // Hide tooltip\n        this.hideTooltip();\n        \n        // Remove tooltip element\n        const tooltip = document.getElementById('global-tooltip');\n        if (tooltip) {\n            tooltip.remove();\n        }\n        \n        // Destroy event manager (removes all delegated listeners)\n        if (this.eventManager) {\n            this.eventManager.destroy();\n            this.eventManager = null;\n        }\n        \n        // Clear handler references\n        this.handlers.clear();\n        this.container = null;\n        \n        console.log('✅ UIEventDelegator destroyed successfully');\n    }\n}\n\n/**\n * Global UI event delegator instance\n */\nexport const globalUIEventDelegator = new UIEventDelegator(document.body);\n\n/**\n * Utility function to create a scoped UI event delegator\n */\nexport function createUIEventDelegator(container) {\n    return new UIEventDelegator(container);\n}\n\n/**\n * Utility functions for common UI patterns\n */\nexport function delegateClick(selector, handler, container = document.body) {\n    return globalUIEventDelegator.delegate(selector, 'click', handler);\n}\n\nexport function delegateInput(selector, handler, container = document.body) {\n    return globalUIEventDelegator.delegate(selector, 'input', handler);\n}\n\nexport function delegateChange(selector, handler, container = document.body) {\n    return globalUIEventDelegator.delegate(selector, 'change', handler);\n}