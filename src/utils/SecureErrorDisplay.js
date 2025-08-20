/**
 * Secure Error Display Component
 * Provides XSS-safe error display with user-friendly error reporting
 */

import { secureErrorHandler } from "./SecureErrorHandler.js";

class SecureErrorDisplay {
    constructor() {
        this.overlayElement = null;
        this.isVisible = false;
        this.updateInterval = null;
        this.cspNonce = this.generateNonce(); // For inline styles if needed
    }

    /**
     * Generate a cryptographic nonce for CSP
     */
    generateNonce() {
        const array = new Uint8Array(16);
        crypto.getRandomValues(array);
        return btoa(String.fromCharCode(...array));
    }

    /**
     * Create and inject the error overlay into the DOM
     */
    initialize() {
        this.createOverlayElement();
        this.setupEventListeners();
        this.setupAutoUpdate();
        
        console.log("🛡️ Secure Error Display initialized");
    }

    /**
     * Create the secure error overlay element
     */
    createOverlayElement() {
        this.overlayElement = document.createElement("div");
        this.overlayElement.id = "secure-error-overlay";
        this.overlayElement.className = "secure-error-overlay";
        this.overlayElement.setAttribute("role", "alert");
        this.overlayElement.setAttribute("aria-live", "polite");
        this.overlayElement.style.display = "none";
        
        // Apply secure inline styles (CSP-safe)
        this.applySecureStyles();
        
        document.body.appendChild(this.overlayElement);
    }

    /**
     * Apply secure styles without innerHTML injection
     */
    applySecureStyles() {
        const styles = {
            position: "fixed",
            top: "0",
            left: "0",
            width: "100%",
            height: "100%",
            backgroundColor: "rgba(0, 0, 0, 0.95)",
            color: "#ff4444",
            fontFamily: "monospace",
            fontSize: "14px",
            zIndex: "10000",
            padding: "20px",
            overflowY: "auto",
            boxSizing: "border-box"
        };

        Object.assign(this.overlayElement.style, styles);
    }

    /**
     * Setup event listeners for error handling
     */
    setupEventListeners() {
        // Listen for new errors
        window.addEventListener("secureErrorCaptured", (event) => {
            this.handleNewError(event.detail);
        });

        // Handle escape key to close overlay
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && this.isVisible) {
                this.hide();
                event.preventDefault();
            }
        });

        // Prevent background interaction when overlay is visible
        this.overlayElement.addEventListener("click", (event) => {
            if (event.target === this.overlayElement) {
                event.stopPropagation();
            }
        });
    }

    /**
     * Setup automatic updates for error display
     */
    setupAutoUpdate() {
        // Check for errors periodically
        this.updateInterval = setInterval(() => {
            if (this.isVisible) {
                this.updateDisplay();
            } else {
                // Check if we should show errors
                const errors = secureErrorHandler.getErrors();
                if (errors.length > 0) {
                    this.show();
                }
            }
        }, 2000);
    }

    /**
     * Handle new error notification
     */
    handleNewError(errorDetail) {
        if (errorDetail.severity === "high") {
            this.show(); // Immediately show for high severity errors
        }
        
        if (this.isVisible) {
            this.updateDisplay();
        }
    }

    /**
     * Show the error overlay
     */
    show() {
        if (this.isVisible) return;
        
        this.isVisible = true;
        this.overlayElement.style.display = "block";
        this.updateDisplay();
        
        // Focus management for accessibility
        this.overlayElement.focus();
    }

    /**
     * Hide the error overlay
     */
    hide() {
        if (!this.isVisible) return;
        
        this.isVisible = false;
        this.overlayElement.style.display = "none";
    }

    /**
     * Update the error display with current errors
     */
    updateDisplay() {
        if (!this.overlayElement) return;

        const errors = secureErrorHandler.getErrors(20); // Get last 20 errors
        const stats = secureErrorHandler.getStats();
        
        // Clear existing content safely
        while (this.overlayElement.firstChild) {
            this.overlayElement.removeChild(this.overlayElement.firstChild);
        }

        // Create header
        const header = this.createHeaderElement(stats);
        this.overlayElement.appendChild(header);

        // Create controls
        const controls = this.createControlsElement();
        this.overlayElement.appendChild(controls);

        // Create error list
        if (errors.length > 0) {
            const errorList = this.createErrorListElement(errors);
            this.overlayElement.appendChild(errorList);
        } else {
            const noErrors = this.createNoErrorsElement();
            this.overlayElement.appendChild(noErrors);
        }
    }

    /**
     * Create header element safely
     */
    createHeaderElement(stats) {
        const header = document.createElement("div");
        header.className = "error-header";
        
        const title = document.createElement("h2");
        title.textContent = "🛡️ Secure Error Monitor";
        title.style.cssText = "margin: 0 0 10px 0; color: #ff4444; text-align: center;";
        header.appendChild(title);

        const subtitle = document.createElement("div");
        subtitle.textContent = `${stats.totalErrors} error${stats.totalErrors !== 1 ? "s" : ""} captured with security protection`;
        subtitle.style.cssText = "color: #888; text-align: center; margin-bottom: 20px;";
        header.appendChild(subtitle);

        // Stats summary
        const statsSummary = document.createElement("div");
        statsSummary.style.cssText = "display: flex; justify-content: space-around; margin-bottom: 20px; font-size: 12px;";
        
        const severityDiv = document.createElement("div");
        severityDiv.textContent = `High: ${stats.severityCounts.high || 0} | Medium: ${stats.severityCounts.medium || 0} | Low: ${stats.severityCounts.low || 0}`;
        severityDiv.style.color = "#0ff";
        statsSummary.appendChild(severityDiv);

        const rateLimitDiv = document.createElement("div");
        rateLimitDiv.textContent = `Rate Limit: ${stats.rateLimitStatus.currentCount}/${stats.rateLimitStatus.maxPerWindow}`;
        rateLimitDiv.style.color = "#0f0";
        statsSummary.appendChild(rateLimitDiv);

        header.appendChild(statsSummary);

        return header;
    }

    /**
     * Create controls element safely
     */
    createControlsElement() {
        const controls = document.createElement("div");
        controls.style.cssText = "margin-bottom: 20px; text-align: center;";

        const clearBtn = this.createButton("Clear Errors", () => {
            this.clearErrors();
        });
        clearBtn.style.backgroundColor = "#ff4444";
        clearBtn.style.color = "white";

        const hideBtn = this.createButton("Hide (ESC)", () => {
            this.hide();
        });

        const reloadBtn = this.createButton("Reload Page", () => {
            if (confirm("Are you sure you want to reload the page? All current progress may be lost.")) {
                location.reload();
            }
        });
        reloadBtn.style.backgroundColor = "#ff8800";

        const statsBtn = this.createButton("Show Stats", () => {
            this.showDetailedStats();
        });

        controls.appendChild(clearBtn);
        controls.appendChild(hideBtn);
        controls.appendChild(reloadBtn);
        controls.appendChild(statsBtn);

        return controls;
    }

    /**
     * Create a secure button element
     */
    createButton(text, onClick) {
        const button = document.createElement("button");
        button.textContent = text;
        button.style.cssText = `
            background: #0f0;
            color: #000;
            border: none;
            padding: 10px 15px;
            margin: 0 5px;
            cursor: pointer;
            font-family: monospace;
            font-size: 12px;
            border-radius: 3px;
        `;
        
        button.addEventListener("click", onClick);
        
        // Hover effect
        button.addEventListener("mouseenter", () => {
            button.style.backgroundColor = "#0a0";
        });
        
        button.addEventListener("mouseleave", () => {
            button.style.backgroundColor = button.style.backgroundColor === "rgb(255, 68, 68)" ? "#ff4444" :
                button.style.backgroundColor === "rgb(255, 136, 0)" ? "#ff8800" : "#0f0";
        });

        return button;
    }

    /**
     * Create error list element safely
     */
    createErrorListElement(errors) {
        const errorList = document.createElement("div");
        errorList.className = "error-list";
        errorList.style.cssText = "max-height: 60vh; overflow-y: auto; border: 1px solid #333;";

        errors.forEach((error, index) => {
            const errorElement = this.createErrorItemElement(error, index);
            errorList.appendChild(errorElement);
        });

        return errorList;
    }

    /**
     * Create individual error item element safely
     */
    createErrorItemElement(error, _index) {
        const errorDiv = document.createElement("div");
        errorDiv.className = "error-item";
        errorDiv.style.cssText = `
            background: #111;
            border: 1px solid ${this.getSeverityColor(error.severity)};
            margin: 5px 0;
            padding: 10px;
            border-radius: 3px;
        `;

        // Error header
        const headerDiv = document.createElement("div");
        headerDiv.style.cssText = "font-weight: bold; margin-bottom: 5px; color: " + this.getSeverityColor(error.severity);
        headerDiv.textContent = `Error #${error.id} - ${error.severity.toUpperCase()} - ${error.source}`;
        errorDiv.appendChild(headerDiv);

        // Timestamp
        const timestampDiv = document.createElement("div");
        timestampDiv.style.cssText = "color: #888; font-size: 11px; margin-bottom: 5px;";
        timestampDiv.textContent = new Date(error.timestamp).toLocaleString();
        errorDiv.appendChild(timestampDiv);

        // Message (already sanitized)
        const messageDiv = document.createElement("div");
        messageDiv.style.cssText = "color: #ff8888; margin-bottom: 5px;";
        messageDiv.textContent = error.message;
        errorDiv.appendChild(messageDiv);

        // File info
        const fileDiv = document.createElement("div");
        fileDiv.style.cssText = "color: #88ff88; font-size: 11px; margin-bottom: 5px;";
        fileDiv.textContent = `File: ${error.filename}:${error.lineno}:${error.colno}`;
        errorDiv.appendChild(fileDiv);

        // Stack trace (collapsible for readability)
        if (error.stack && error.stack !== "No stack trace") {
            const stackToggle = document.createElement("div");
            stackToggle.style.cssText = "color: #ffff88; cursor: pointer; font-size: 11px; margin: 5px 0;";
            stackToggle.textContent = "▶ Show Stack Trace";
            
            const stackDiv = document.createElement("pre");
            stackDiv.style.cssText = `
                color: #ffff88;
                font-size: 10px;
                margin: 5px 0 0 20px;
                white-space: pre-wrap;
                word-break: break-word;
                display: none;
                max-height: 200px;
                overflow-y: auto;
                background: #0a0a0a;
                padding: 5px;
                border-left: 2px solid #ffff88;
            `;
            stackDiv.textContent = error.stack;

            stackToggle.addEventListener("click", () => {
                if (stackDiv.style.display === "none") {
                    stackDiv.style.display = "block";
                    stackToggle.textContent = "▼ Hide Stack Trace";
                } else {
                    stackDiv.style.display = "none";
                    stackToggle.textContent = "▶ Show Stack Trace";
                }
            });

            errorDiv.appendChild(stackToggle);
            errorDiv.appendChild(stackDiv);
        }

        return errorDiv;
    }

    /**
     * Get color based on error severity
     */
    getSeverityColor(severity) {
        switch (severity) {
        case "high": return "#ff4444";
        case "medium": return "#ffaa44";
        case "low": return "#44ff44";
        default: return "#ffffff";
        }
    }

    /**
     * Create no errors element
     */
    createNoErrorsElement() {
        const noErrors = document.createElement("div");
        noErrors.style.cssText = "text-align: center; color: #0f0; font-size: 18px; margin-top: 40px;";
        noErrors.textContent = "✅ No errors detected - System is healthy!";
        return noErrors;
    }

    /**
     * Clear all errors with confirmation
     */
    clearErrors() {
        if (confirm("Are you sure you want to clear all captured errors? This cannot be undone.")) {
            secureErrorHandler.clearErrors();
            this.updateDisplay();
        }
    }

    /**
     * Show detailed statistics
     */
    showDetailedStats() {
        const stats = secureErrorHandler.getStats();
        const statsWindow = window.open("", "_blank", "width=600,height=400");
        
        if (statsWindow) {
            statsWindow.document.title = "Error Statistics";
            statsWindow.document.body.innerHTML = `
                <style>
                    body { font-family: monospace; background: #000; color: #0f0; padding: 20px; }
                    .stat-group { margin: 20px 0; padding: 10px; border: 1px solid #333; }
                    .stat-title { color: #ff0; font-weight: bold; margin-bottom: 10px; }
                </style>
                <h1>🛡️ Secure Error Handler Statistics</h1>
                <div class="stat-group">
                    <div class="stat-title">General Stats</div>
                    <div>Total Errors: ${stats.totalErrors}</div>
                    <div>Storage Usage: ${(stats.storageUsage / 1024).toFixed(1)} KB</div>
                </div>
                <div class="stat-group">
                    <div class="stat-title">Severity Distribution</div>
                    ${Object.entries(stats.severityCounts).map(([severity, count]) => 
        `<div>${severity}: ${count}</div>`).join("")}
                </div>
                <div class="stat-group">
                    <div class="stat-title">Error Sources</div>
                    ${Object.entries(stats.sourceCounts).map(([source, count]) => 
        `<div>${source}: ${count}</div>`).join("")}
                </div>
                <div class="stat-group">
                    <div class="stat-title">Rate Limiting</div>
                    <div>Current Window: ${stats.rateLimitStatus.currentWindow}</div>
                    <div>Current Count: ${stats.rateLimitStatus.currentCount} / ${stats.rateLimitStatus.maxPerWindow}</div>
                </div>
            `;
        }
    }

    /**
     * Cleanup on destruction
     */
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        if (this.overlayElement && this.overlayElement.parentNode) {
            this.overlayElement.parentNode.removeChild(this.overlayElement);
        }
    }
}

// Export singleton instance
export const secureErrorDisplay = new SecureErrorDisplay();