/**
 * Unit tests for TensorFlowManager
 * Tests TensorFlow.js initialization and management
 */

import { TensorFlowManager } from "./TensorFlowManager.js";
import * as tf from "@tensorflow/tfjs";
import { jest } from "@jest/globals";

// Mock TensorFlow.js
jest.mock("@tensorflow/tfjs", () => ({
    setBackend: jest.fn(),
    ready: jest.fn(),
    getBackend: jest.fn(),
    engine: jest.fn(() => ({
        backendName: "webgl",
        memory: jest.fn(() => ({
            numTensors: 5,
            numBytes: 1024
        }))
    })),
    tensor: jest.fn(() => ({
        dispose: jest.fn()
    })),
    randomNormal: jest.fn(() => ({
        dispose: jest.fn()
    })),
    tidy: jest.fn((fn) => fn()),
    dispose: jest.fn(),
    memory: jest.fn(() => ({
        numTensors: 5,
        numBytes: 1024
    }))
}));

describe("TensorFlowManager", () => {
    let manager;

    beforeEach(() => {
        manager = new TensorFlowManager();
        jest.clearAllMocks();
    });

    afterEach(() => {
        manager.cleanup();
    });

    describe("constructor", () => {
        test("should initialize with default values", () => {
            expect(manager.isInitialized).toBe(false);
            expect(manager.currentBackend).toBeNull();
            expect(manager.initializationAttempts).toBe(0);
            expect(manager.performanceMetrics.inferenceCount).toBe(0);
        });

        test("should setup event listener for cleanup", () => {
            const addEventListenerSpy = jest.spyOn(window, "addEventListener");
            new TensorFlowManager();
            expect(addEventListenerSpy).toHaveBeenCalledWith("beforeunload", expect.any(Function));
        });
    });

    describe("initialize", () => {
        test("should successfully initialize with WebGL backend", async () => {
            tf.setBackend.mockResolvedValue(true);
            tf.ready.mockResolvedValue();
            tf.getBackend.mockReturnValue("webgl");

            const result = await manager.initialize();
      
            expect(result).toBe(true);
            expect(manager.isInitialized).toBe(true);
            expect(manager.currentBackend).toBe("webgl");
            expect(tf.setBackend).toHaveBeenCalledWith("webgl");
        });

        test("should fallback to CPU backend on WebGL failure", async () => {
            tf.setBackend
                .mockRejectedValueOnce(new Error("WebGL not available"))
                .mockResolvedValueOnce(true);
            tf.ready.mockResolvedValue();
            tf.getBackend.mockReturnValue("cpu");

            const result = await manager.initialize();
      
            expect(result).toBe(true);
            expect(manager.currentBackend).toBe("cpu");
            expect(tf.setBackend).toHaveBeenCalledWith("cpu");
        });

        test("should handle initialization failure", async () => {
            tf.setBackend.mockRejectedValue(new Error("Backend error"));
      
            const result = await manager.initialize();
      
            expect(result).toBe(false);
            expect(manager.isInitialized).toBe(false);
            expect(manager.initializationAttempts).toBeGreaterThan(0);
        });

        test("should not reinitialize if already initialized", async () => {
            manager.isInitialized = true;
            manager.currentBackend = "webgl";
      
            const result = await manager.initialize();
      
            expect(result).toBe(true);
            expect(tf.setBackend).not.toHaveBeenCalled();
        });
    });

    describe("performanceTest", () => {
        test("should run performance test and update metrics", async () => {
            manager.isInitialized = true;
      
            const mockTensor = { dispose: jest.fn() };
            tf.randomNormal.mockReturnValue(mockTensor);
            tf.tidy.mockImplementation((fn) => fn());
      
            const result = await manager.performanceTest();
      
            expect(result).toHaveProperty("success", true);
            expect(result).toHaveProperty("averageTime");
            expect(manager.performanceMetrics.inferenceCount).toBeGreaterThan(0);
        });

        test("should handle performance test failure", async () => {
            manager.isInitialized = false;
      
            const result = await manager.performanceTest();
      
            expect(result.success).toBe(false);
            expect(result.error).toBeDefined();
        });
    });

    describe("trackInference", () => {
        test("should update inference metrics", () => {
            const startTime = Date.now();
            const endTime = startTime + 50;
      
            manager.trackInference(startTime, endTime);
      
            expect(manager.performanceMetrics.inferenceCount).toBe(1);
            expect(manager.performanceMetrics.lastInferenceTime).toBe(50);
            expect(manager.performanceMetrics.totalInferenceTime).toBe(50);
            expect(manager.performanceMetrics.averageInferenceTime).toBe(50);
        });

        test("should track slow inferences", () => {
            const startTime = Date.now();
            const endTime = startTime + 150; // Slow inference > 100ms
      
            manager.trackInference(startTime, endTime);
      
            expect(manager.performanceMetrics.slowInferences).toBe(1);
        });
    });

    describe("checkMemory", () => {
        test("should check and update memory usage", () => {
            manager.isInitialized = true;
            tf.memory.mockReturnValue({
                numTensors: 10,
                numBytes: 2048
            });
      
            const memoryInfo = manager.checkMemory();
      
            expect(memoryInfo).toHaveProperty("numTensors", 10);
            expect(memoryInfo).toHaveProperty("numBytes", 2048);
            expect(manager.memoryTracker.tensorCount).toBe(10);
        });

        test("should detect memory leaks", () => {
            manager.isInitialized = true;
            tf.memory.mockReturnValue({
                numTensors: 150, // High tensor count
                numBytes: 10000
            });
      
            manager.checkMemory();
      
            expect(manager.performanceMetrics.memoryLeaks).toBeGreaterThan(0);
        });
    });

    describe("cleanup", () => {
        test("should dispose all test tensors", () => {
            const mockTensor = { dispose: jest.fn() };
            manager.testTensors = [mockTensor, mockTensor];
      
            manager.cleanup();
      
            expect(mockTensor.dispose).toHaveBeenCalledTimes(2);
            expect(manager.testTensors).toEqual([]);
        });

        test("should handle cleanup errors gracefully", () => {
            const mockTensor = { 
                dispose: jest.fn(() => { throw new Error("Dispose error"); })
            };
            manager.testTensors = [mockTensor];
      
            expect(() => manager.cleanup()).not.toThrow();
        });
    });

    describe("getStatus", () => {
        test("should return complete status information", () => {
            manager.isInitialized = true;
            manager.currentBackend = "webgl";
            manager.performanceMetrics.inferenceCount = 10;
      
            const status = manager.getStatus();
      
            expect(status).toHaveProperty("initialized", true);
            expect(status).toHaveProperty("backend", "webgl");
            expect(status).toHaveProperty("performanceMetrics");
            expect(status).toHaveProperty("memoryStatus");
        });
    });
});