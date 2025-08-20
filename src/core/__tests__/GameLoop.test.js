/**
 * Unit Tests for Game Loop
 * Tests game timing, frame rate control, and update cycles
 */

import { GameLoop } from "../GameLoop.js";

describe("GameLoop", () => {
    let gameLoop;
    let mockUpdateFunction;
    let mockRenderFunction;

    beforeEach(() => {
        mockUpdateFunction = jest.fn();
        mockRenderFunction = jest.fn();
    
        gameLoop = new GameLoop();
    });

    afterEach(() => {
        if (gameLoop && gameLoop.running) {
            gameLoop.stop();
        }
    });

    describe("Initialization", () => {
        test("should create GameLoop with default values", () => {
            expect(gameLoop.running).toBe(false);
            expect(gameLoop.targetFPS).toBe(60);
            expect(gameLoop.maxFrameSkip).toBe(5);
            expect(gameLoop.frameTime).toBeCloseTo(16.67, 1);
        });

        test("should allow custom target FPS", () => {
            const customLoop = new GameLoop({ targetFPS: 30 });
      
            expect(customLoop.targetFPS).toBe(30);
            expect(customLoop.frameTime).toBeCloseTo(33.33, 1);
        });

        test("should initialize timing variables", () => {
            expect(gameLoop.lastTime).toBe(0);
            expect(gameLoop.accumulator).toBe(0);
            expect(gameLoop.currentTime).toBe(0);
            expect(gameLoop.frameCount).toBe(0);
        });
    });

    describe("Game Loop Control", () => {
        test("should start game loop", () => {
            gameLoop.start(mockUpdateFunction, mockRenderFunction);
      
            expect(gameLoop.running).toBe(true);
            expect(gameLoop.updateFunction).toBe(mockUpdateFunction);
            expect(gameLoop.renderFunction).toBe(mockRenderFunction);
        });

        test("should stop game loop", () => {
            gameLoop.start(mockUpdateFunction, mockRenderFunction);
            gameLoop.stop();
      
            expect(gameLoop.running).toBe(false);
        });

        test("should not start if already running", () => {
            gameLoop.start(mockUpdateFunction, mockRenderFunction);
      
            const result = gameLoop.start(jest.fn(), jest.fn());
      
            expect(result).toBe(false);
        });

        test("should handle missing update or render functions", () => {
            expect(() => {
                gameLoop.start(null, mockRenderFunction);
            }).toThrow("Update and render functions are required");
      
            expect(() => {
                gameLoop.start(mockUpdateFunction, null);
            }).toThrow("Update and render functions are required");
        });
    });

    describe("Frame Timing", () => {
        test("should calculate correct frame time for different FPS", () => {
            const loop60 = new GameLoop({ targetFPS: 60 });
            const loop30 = new GameLoop({ targetFPS: 30 });
            const loop120 = new GameLoop({ targetFPS: 120 });
      
            expect(loop60.frameTime).toBeCloseTo(16.67, 1);
            expect(loop30.frameTime).toBeCloseTo(33.33, 1);
            expect(loop120.frameTime).toBeCloseTo(8.33, 1);
        });

        test("should handle zero or negative FPS gracefully", () => {
            expect(() => {
                new GameLoop({ targetFPS: 0 });
            }).toThrow("Target FPS must be greater than 0");
      
            expect(() => {
                new GameLoop({ targetFPS: -30 });
            }).toThrow("Target FPS must be greater than 0");
        });

        test("should limit maximum FPS to reasonable values", () => {
            const highFPSLoop = new GameLoop({ targetFPS: 1000 });
      
            expect(highFPSLoop.targetFPS).toBeLessThanOrEqual(240); // Reasonable maximum
        });
    });

    describe("Fixed Timestep Updates", () => {
        test("should call update function with fixed timestep", (done) => {
            let updateCount = 0;
      
            const testUpdate = (deltaTime) => {
                updateCount++;
                expect(deltaTime).toBeCloseTo(16.67, 1); // 60 FPS timestep
        
                if (updateCount >= 3) {
                    gameLoop.stop();
                    done();
                }
            };
      
            gameLoop.start(testUpdate, mockRenderFunction);
      
            // Simulate time passage
            setTimeout(() => {
                if (gameLoop.running) {
                    gameLoop.stop();
                    done(new Error("Game loop did not call update function"));
                }
            }, 1000);
        });

        test("should accumulate time and run multiple updates if needed", () => {
            let updateCount = 0;
      
            const testUpdate = (deltaTime) => {
                updateCount++;
                expect(deltaTime).toBeCloseTo(16.67, 1);
            };
      
            gameLoop.start(testUpdate, mockRenderFunction);
      
            // Simulate large time jump (should trigger multiple updates)
            const originalNow = performance.now;
            let timeStep = 0;
            performance.now = jest.fn(() => {
                timeStep += 100; // 100ms jumps
                return timeStep;
            });
      
            // Run one frame
            gameLoop.tick();
      
            expect(updateCount).toBeGreaterThan(1);
      
            performance.now = originalNow;
            gameLoop.stop();
        });

        test("should limit frame skipping to prevent spiral of death", () => {
            let updateCount = 0;
      
            const testUpdate = () => {
                updateCount++;
            };
      
            gameLoop.maxFrameSkip = 2;
            gameLoop.start(testUpdate, mockRenderFunction);
      
            // Simulate massive time jump
            const originalNow = performance.now;
            performance.now = jest.fn(() => Date.now() + 1000); // 1 second jump
      
            gameLoop.tick();
      
            expect(updateCount).toBeLessThanOrEqual(gameLoop.maxFrameSkip);
      
            performance.now = originalNow;
            gameLoop.stop();
        });
    });

    describe("Interpolated Rendering", () => {
        test("should call render function with interpolation value", (done) => {
            let renderCount = 0;
      
            const testRender = (interpolation) => {
                renderCount++;
                expect(interpolation).toBeGreaterThanOrEqual(0);
                expect(interpolation).toBeLessThanOrEqual(1);
        
                if (renderCount >= 3) {
                    gameLoop.stop();
                    done();
                }
            };
      
            gameLoop.start(mockUpdateFunction, testRender);
      
            setTimeout(() => {
                if (gameLoop.running) {
                    gameLoop.stop();
                    done(new Error("Game loop did not call render function"));
                }
            }, 1000);
        });

        test("should calculate interpolation correctly", () => {
            const testRender = jest.fn();
      
            gameLoop.start(mockUpdateFunction, testRender);
            gameLoop.accumulator = 8.33; // Half a frame
      
            gameLoop.tick();
      
            expect(testRender).toHaveBeenCalled();
            const interpolation = testRender.mock.calls[0][0];
            expect(interpolation).toBeCloseTo(0.5, 1);
      
            gameLoop.stop();
        });
    });

    describe("Performance Monitoring", () => {
        test("should track frame count", () => {
            gameLoop.start(mockUpdateFunction, mockRenderFunction);
      
            // Run a few frames
            for (let i = 0; i < 5; i++) {
                gameLoop.tick();
            }
      
            expect(gameLoop.frameCount).toBeGreaterThan(0);
            gameLoop.stop();
        });

        test("should calculate FPS accurately", () => {
            gameLoop.start(mockUpdateFunction, mockRenderFunction);
      
            // Simulate consistent timing
            const startTime = performance.now();
      
            for (let i = 0; i < 60; i++) {
                gameLoop.tick();
            }
      
            const fps = gameLoop.getCurrentFPS();
            expect(fps).toBeGreaterThan(0);
            expect(fps).toBeLessThan(1000); // Reasonable upper bound
      
            gameLoop.stop();
        });

        test("should provide performance statistics", () => {
            gameLoop.start(mockUpdateFunction, mockRenderFunction);
      
            // Run some frames
            for (let i = 0; i < 10; i++) {
                gameLoop.tick();
            }
      
            const stats = gameLoop.getPerformanceStats();
      
            expect(stats).toHaveProperty("fps");
            expect(stats).toHaveProperty("frameCount");
            expect(stats).toHaveProperty("averageFrameTime");
            expect(stats).toHaveProperty("targetFPS");
            expect(stats).toHaveProperty("running");
      
            gameLoop.stop();
        });
    });

    describe("Error Handling", () => {
        test("should handle update function errors gracefully", () => {
            const errorUpdate = () => {
                throw new Error("Update error");
            };
      
            const consoleSpy = jest.spyOn(console, "error").mockImplementation();
      
            gameLoop.start(errorUpdate, mockRenderFunction);
            gameLoop.tick();
      
            expect(consoleSpy).toHaveBeenCalled();
            expect(gameLoop.running).toBe(true); // Should continue running
      
            consoleSpy.mockRestore();
            gameLoop.stop();
        });

        test("should handle render function errors gracefully", () => {
            const errorRender = () => {
                throw new Error("Render error");
            };
      
            const consoleSpy = jest.spyOn(console, "error").mockImplementation();
      
            gameLoop.start(mockUpdateFunction, errorRender);
            gameLoop.tick();
      
            expect(consoleSpy).toHaveBeenCalled();
            expect(gameLoop.running).toBe(true); // Should continue running
      
            consoleSpy.mockRestore();
            gameLoop.stop();
        });

        test("should handle performance.now() unavailability", () => {
            const originalNow = performance.now;
            delete performance.now;
      
            expect(() => {
                const fallbackLoop = new GameLoop();
                fallbackLoop.start(mockUpdateFunction, mockRenderFunction);
                fallbackLoop.tick();
                fallbackLoop.stop();
            }).not.toThrow();
      
            performance.now = originalNow;
        });
    });

    describe("Game Loop States", () => {
        test("should handle pause and resume", () => {
            gameLoop.start(mockUpdateFunction, mockRenderFunction);
      
            gameLoop.pause();
            expect(gameLoop.paused).toBe(true);
      
            gameLoop.resume();
            expect(gameLoop.paused).toBe(false);
      
            gameLoop.stop();
        });

        test("should not update when paused", () => {
            let updateCount = 0;
            const testUpdate = () => { updateCount++; };
      
            gameLoop.start(testUpdate, mockRenderFunction);
            gameLoop.pause();
      
            gameLoop.tick();
            gameLoop.tick();
      
            expect(updateCount).toBe(0);
      
            gameLoop.stop();
        });

        test("should continue rendering when paused", () => {
            let renderCount = 0;
            const testRender = () => { renderCount++; };
      
            gameLoop.start(mockUpdateFunction, testRender);
            gameLoop.pause();
      
            gameLoop.tick();
      
            expect(renderCount).toBeGreaterThan(0);
      
            gameLoop.stop();
        });
    });

    describe("Memory and Resource Management", () => {
        test("should clean up resources when stopped", () => {
            gameLoop.start(mockUpdateFunction, mockRenderFunction);
            gameLoop.stop();
      
            expect(gameLoop.updateFunction).toBeNull();
            expect(gameLoop.renderFunction).toBeNull();
            expect(gameLoop.frameCount).toBe(0);
        });

        test("should handle multiple start/stop cycles", () => {
            for (let i = 0; i < 5; i++) {
                gameLoop.start(mockUpdateFunction, mockRenderFunction);
                gameLoop.stop();
            }
      
            expect(gameLoop.running).toBe(false);
        });

        test("should not leak memory with long running loops", () => {
            let largeObject = new Array(1000).fill().map((_, i) => ({ id: i, data: new Array(100).fill(Math.random()) }));
      
            const testUpdate = () => {
                // Simulate work with large object
                largeObject.forEach(item => item.data[0] = Math.random());
            };
      
            gameLoop.start(testUpdate, mockRenderFunction);
      
            // Run many frames
            for (let i = 0; i < 100; i++) {
                gameLoop.tick();
            }
      
            gameLoop.stop();
            largeObject = null;
      
            // Should not throw memory errors
            expect(gameLoop.running).toBe(false);
        });
    });

    describe("Edge Cases", () => {
        test("should handle very high FPS requests", () => {
            const highFPSLoop = new GameLoop({ targetFPS: 240 });
      
            expect(highFPSLoop.frameTime).toBeGreaterThan(0);
            expect(highFPSLoop.frameTime).toBeLessThan(100);
        });

        test("should handle system time changes", () => {
            gameLoop.start(mockUpdateFunction, mockRenderFunction);
      
            // Simulate system clock going backwards
            const originalNow = performance.now;
            let timeValue = 1000;
            performance.now = jest.fn(() => timeValue);
      
            gameLoop.tick(); // Initialize timing
      
            timeValue = 500; // Go backwards
      
            expect(() => {
                gameLoop.tick();
            }).not.toThrow();
      
            performance.now = originalNow;
            gameLoop.stop();
        });

        test("should handle requestAnimationFrame unavailability", () => {
            const originalRAF = global.requestAnimationFrame;
            delete global.requestAnimationFrame;
      
            expect(() => {
                const fallbackLoop = new GameLoop();
                fallbackLoop.start(mockUpdateFunction, mockRenderFunction);
                fallbackLoop.stop();
            }).not.toThrow();
      
            global.requestAnimationFrame = originalRAF;
        });
    });
});