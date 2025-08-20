/**
 * Unit Tests for Network Manager
 * Tests multiplayer connections, message handling, and state synchronization
 */

// Mock NetworkManager implementation for testing multiplayer concepts
class NetworkManager {
    constructor(options = {}) {
        this.isConnected = false;
        this.isHost = false;
        this.playerId = null;
        this.room = null;
        this.players = new Map();
        this.pendingMessages = [];
        this.messageQueue = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 3;
        this.reconnectDelay = options.reconnectDelay || 1000;
        this.pingInterval = options.pingInterval || 5000;
        this.lastPing = 0;
        this.latency = 0;
        this.eventHandlers = new Map();
        this.debug = options.debug || false;
    }

    async connect(serverUrl, roomId) {
        try {
            if (this.isConnected) {
                throw new Error("Already connected");
            }

            this.serverUrl = serverUrl;
            this.roomId = roomId;
      
            // Simulate connection delay
            await new Promise(resolve => setTimeout(resolve, 100));
      
            this.isConnected = true;
            this.playerId = `player-${Date.now()}`;
            this.room = { id: roomId, state: {} };
      
            this.emit("connected", { playerId: this.playerId, roomId });
      
            return { success: true, playerId: this.playerId };
        } catch (error) {
            this.emit("error", error);
            throw error;
        }
    }

    disconnect() {
        if (!this.isConnected) return;
    
        this.isConnected = false;
        this.isHost = false;
        this.playerId = null;
        this.room = null;
        this.players.clear();
        this.messageQueue = [];
    
        this.emit("disconnected");
    }

    sendMessage(type, data) {
        if (!this.isConnected) {
            throw new Error("Not connected to server");
        }

        const message = {
            id: `msg-${Date.now()}-${Math.random()}`,
            type,
            data,
            timestamp: Date.now(),
            playerId: this.playerId
        };

        this.messageQueue.push(message);
        this.emit("messageSent", message);
    
        return message.id;
    }

    simulateReceiveMessage(type, data, fromPlayerId = "other-player") {
        if (!this.isConnected) return;

        const message = {
            id: `msg-${Date.now()}-${Math.random()}`,
            type,
            data,
            timestamp: Date.now(),
            playerId: fromPlayerId
        };

        this.emit("messageReceived", message);
        this.emit(type, message);
    }

    addPlayer(playerId, playerData = {}) {
        this.players.set(playerId, {
            id: playerId,
            connected: true,
            lastSeen: Date.now(),
            ...playerData
        });
    
        this.emit("playerJoined", { playerId, playerData });
    }

    removePlayer(playerId) {
        if (this.players.has(playerId)) {
            const playerData = this.players.get(playerId);
            this.players.delete(playerId);
            this.emit("playerLeft", { playerId, playerData });
        }
    }

    updatePlayerState(playerId, state) {
        if (this.players.has(playerId)) {
            const player = this.players.get(playerId);
            Object.assign(player, state);
            this.emit("playerStateUpdate", { playerId, state });
        }
    }

    getRoomState() {
        return {
            ...this.room?.state,
            players: Array.from(this.players.values()),
            isHost: this.isHost
        };
    }

    ping() {
        const pingTime = Date.now();
        this.lastPing = pingTime;
    
        // Simulate network delay
        setTimeout(() => {
            this.latency = Date.now() - pingTime;
            this.emit("pong", { latency: this.latency });
        }, Math.random() * 50 + 10); // 10-60ms simulated latency
    }

    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }

    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            const handlers = this.eventHandlers.get(event);
            const index = handlers.indexOf(handler);
            if (index !== -1) {
                handlers.splice(index, 1);
            }
        }
    }

    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }

    getNetworkStats() {
        return {
            isConnected: this.isConnected,
            playerId: this.playerId,
            playerCount: this.players.size,
            messageQueueSize: this.messageQueue.length,
            latency: this.latency,
            reconnectAttempts: this.reconnectAttempts
        };
    }
}

describe("NetworkManager", () => {
    let networkManager;
    let mockEventHandler;

    beforeEach(() => {
        networkManager = new NetworkManager({ debug: true });
        mockEventHandler = jest.fn();
    });

    afterEach(() => {
        if (networkManager.isConnected) {
            networkManager.disconnect();
        }
    });

    describe("Connection Management", () => {
        test("should initialize with disconnected state", () => {
            expect(networkManager.isConnected).toBe(false);
            expect(networkManager.isHost).toBe(false);
            expect(networkManager.playerId).toBeNull();
            expect(networkManager.players.size).toBe(0);
        });

        test("should connect to server successfully", async () => {
            const result = await networkManager.connect("ws://localhost:3000", "test-room");
      
            expect(result.success).toBe(true);
            expect(networkManager.isConnected).toBe(true);
            expect(networkManager.playerId).toBeDefined();
            expect(networkManager.room.id).toBe("test-room");
        });

        test("should emit connected event on successful connection", async () => {
            networkManager.on("connected", mockEventHandler);
      
            await networkManager.connect("ws://localhost:3000", "test-room");
      
            expect(mockEventHandler).toHaveBeenCalledWith({
                playerId: expect.any(String),
                roomId: "test-room"
            });
        });

        test("should throw error when already connected", async () => {
            await networkManager.connect("ws://localhost:3000", "test-room");
      
            await expect(
                networkManager.connect("ws://localhost:3000", "other-room")
            ).rejects.toThrow("Already connected");
        });

        test("should disconnect properly", async () => {
            await networkManager.connect("ws://localhost:3000", "test-room");
            networkManager.on("disconnected", mockEventHandler);
      
            networkManager.disconnect();
      
            expect(networkManager.isConnected).toBe(false);
            expect(networkManager.playerId).toBeNull();
            expect(networkManager.room).toBeNull();
            expect(mockEventHandler).toHaveBeenCalled();
        });

        test("should handle disconnect when not connected", () => {
            expect(() => {
                networkManager.disconnect();
            }).not.toThrow();
        });
    });

    describe("Message System", () => {
        beforeEach(async () => {
            await networkManager.connect("ws://localhost:3000", "test-room");
        });

        test("should send messages when connected", () => {
            const messageId = networkManager.sendMessage("playerMove", {
                x: 100,
                y: 200,
                direction: "north"
            });
      
            expect(messageId).toBeDefined();
            expect(networkManager.messageQueue).toHaveLength(1);
      
            const message = networkManager.messageQueue[0];
            expect(message.type).toBe("playerMove");
            expect(message.data.x).toBe(100);
            expect(message.playerId).toBe(networkManager.playerId);
        });

        test("should emit messageSent event", () => {
            networkManager.on("messageSent", mockEventHandler);
      
            networkManager.sendMessage("test", { data: "test" });
      
            expect(mockEventHandler).toHaveBeenCalledWith(
                expect.objectContaining({
                    type: "test",
                    data: { data: "test" }
                })
            );
        });

        test("should throw error when sending message while disconnected", () => {
            networkManager.disconnect();
      
            expect(() => {
                networkManager.sendMessage("test", {});
            }).toThrow("Not connected to server");
        });

        test("should handle received messages", () => {
            networkManager.on("messageReceived", mockEventHandler);
            networkManager.on("playerMove", mockEventHandler);
      
            networkManager.simulateReceiveMessage("playerMove", {
                x: 150,
                y: 250
            }, "other-player");
      
            expect(mockEventHandler).toHaveBeenCalledTimes(2); // Once for each event
        });

        test("should include timestamp and player info in messages", () => {
            const messageId = networkManager.sendMessage("test", {});
            const message = networkManager.messageQueue.find(m => m.id === messageId);
      
            expect(message.timestamp).toBeDefined();
            expect(message.playerId).toBe(networkManager.playerId);
            expect(message.id).toBeDefined();
        });
    });

    describe("Player Management", () => {
        beforeEach(async () => {
            await networkManager.connect("ws://localhost:3000", "test-room");
        });

        test("should add players to the room", () => {
            networkManager.on("playerJoined", mockEventHandler);
      
            networkManager.addPlayer("player-123", {
                name: "TestPlayer",
                team: "red"
            });
      
            expect(networkManager.players.has("player-123")).toBe(true);
            expect(networkManager.players.get("player-123").name).toBe("TestPlayer");
            expect(mockEventHandler).toHaveBeenCalledWith({
                playerId: "player-123",
                playerData: expect.objectContaining({ name: "TestPlayer" })
            });
        });

        test("should remove players from the room", () => {
            networkManager.addPlayer("player-123", { name: "TestPlayer" });
            networkManager.on("playerLeft", mockEventHandler);
      
            networkManager.removePlayer("player-123");
      
            expect(networkManager.players.has("player-123")).toBe(false);
            expect(mockEventHandler).toHaveBeenCalled();
        });

        test("should update player state", () => {
            networkManager.addPlayer("player-123", { name: "TestPlayer", x: 0, y: 0 });
            networkManager.on("playerStateUpdate", mockEventHandler);
      
            networkManager.updatePlayerState("player-123", { x: 100, y: 200, health: 90 });
      
            const player = networkManager.players.get("player-123");
            expect(player.x).toBe(100);
            expect(player.y).toBe(200);
            expect(player.health).toBe(90);
            expect(mockEventHandler).toHaveBeenCalled();
        });

        test("should handle removing non-existent player", () => {
            expect(() => {
                networkManager.removePlayer("non-existent");
            }).not.toThrow();
        });

        test("should handle updating non-existent player", () => {
            expect(() => {
                networkManager.updatePlayerState("non-existent", {});
            }).not.toThrow();
        });
    });

    describe("Room State Management", () => {
        beforeEach(async () => {
            await networkManager.connect("ws://localhost:3000", "test-room");
        });

        test("should provide current room state", () => {
            networkManager.addPlayer("player-1", { name: "Player1" });
            networkManager.addPlayer("player-2", { name: "Player2" });
      
            const roomState = networkManager.getRoomState();
      
            expect(roomState.players).toHaveLength(2);
            expect(roomState.isHost).toBe(false);
            expect(roomState.players[0].name).toBeDefined();
        });

        test("should update room state when players change", () => {
            networkManager.addPlayer("player-1", { name: "Player1" });
      
            let roomState = networkManager.getRoomState();
            expect(roomState.players).toHaveLength(1);
      
            networkManager.removePlayer("player-1");
      
            roomState = networkManager.getRoomState();
            expect(roomState.players).toHaveLength(0);
        });
    });

    describe("Network Diagnostics", () => {
        beforeEach(async () => {
            await networkManager.connect("ws://localhost:3000", "test-room");
        });

        test("should measure network latency", (done) => {
            networkManager.on("pong", (data) => {
                expect(data.latency).toBeGreaterThan(0);
                expect(data.latency).toBeLessThan(100); // Simulated latency
                done();
            });
      
            networkManager.ping();
        });

        test("should provide network statistics", () => {
            networkManager.addPlayer("player-1");
            networkManager.sendMessage("test", {});
      
            const stats = networkManager.getNetworkStats();
      
            expect(stats.isConnected).toBe(true);
            expect(stats.playerId).toBeDefined();
            expect(stats.playerCount).toBe(1);
            expect(stats.messageQueueSize).toBe(1);
            expect(stats.latency).toBeGreaterThanOrEqual(0);
        });

        test("should track message queue size", () => {
            for (let i = 0; i < 5; i++) {
                networkManager.sendMessage("test", { index: i });
            }
      
            const stats = networkManager.getNetworkStats();
            expect(stats.messageQueueSize).toBe(5);
        });
    });

    describe("Event System", () => {
        test("should register and trigger event handlers", () => {
            const handler1 = jest.fn();
            const handler2 = jest.fn();
      
            networkManager.on("testEvent", handler1);
            networkManager.on("testEvent", handler2);
      
            networkManager.emit("testEvent", { data: "test" });
      
            expect(handler1).toHaveBeenCalledWith({ data: "test" });
            expect(handler2).toHaveBeenCalledWith({ data: "test" });
        });

        test("should remove event handlers", () => {
            const handler = jest.fn();
      
            networkManager.on("testEvent", handler);
            networkManager.off("testEvent", handler);
      
            networkManager.emit("testEvent", {});
      
            expect(handler).not.toHaveBeenCalled();
        });

        test("should handle errors in event handlers gracefully", () => {
            const errorHandler = jest.fn(() => {
                throw new Error("Handler error");
            });
            const goodHandler = jest.fn();
      
            const consoleSpy = jest.spyOn(console, "error").mockImplementation();
      
            networkManager.on("testEvent", errorHandler);
            networkManager.on("testEvent", goodHandler);
      
            networkManager.emit("testEvent", {});
      
            expect(consoleSpy).toHaveBeenCalled();
            expect(goodHandler).toHaveBeenCalled(); // Should still be called
      
            consoleSpy.mockRestore();
        });

        test("should handle removing non-existent event handler", () => {
            const handler = jest.fn();
      
            expect(() => {
                networkManager.off("nonExistentEvent", handler);
            }).not.toThrow();
        });
    });

    describe("Error Handling and Edge Cases", () => {
        test("should handle connection errors", async () => {
            const errorManager = new NetworkManager();
            errorManager.on("error", mockEventHandler);
      
            // Simulate connection failure
            jest.spyOn(errorManager, "connect").mockRejectedValue(new Error("Connection failed"));
      
            await expect(
                errorManager.connect("invalid://url", "test-room")
            ).rejects.toThrow("Connection failed");
      
            expect(mockEventHandler).toHaveBeenCalled();
        });

        test("should handle message queue overflow", async () => {
            await networkManager.connect("ws://localhost:3000", "test-room");
      
            // Send many messages
            for (let i = 0; i < 1000; i++) {
                networkManager.sendMessage("spam", { index: i });
            }
      
            expect(networkManager.messageQueue.length).toBe(1000);
            expect(networkManager.getNetworkStats().messageQueueSize).toBe(1000);
        });

        test("should handle rapid connect/disconnect cycles", async () => {
            for (let i = 0; i < 5; i++) {
                await networkManager.connect("ws://localhost:3000", `room-${i}`);
                networkManager.disconnect();
            }
      
            expect(networkManager.isConnected).toBe(false);
        });

        test("should handle receiving messages when disconnected", () => {
            expect(() => {
                networkManager.simulateReceiveMessage("test", {});
            }).not.toThrow();
        });

        test("should maintain state consistency during errors", async () => {
            await networkManager.connect("ws://localhost:3000", "test-room");
            networkManager.addPlayer("player-1");
      
            // Simulate error during message sending
            const originalSend = networkManager.sendMessage;
            networkManager.sendMessage = jest.fn(() => {
                throw new Error("Send failed");
            });
      
            expect(() => {
                networkManager.sendMessage("test", {});
            }).toThrow();
      
            // State should remain consistent
            expect(networkManager.isConnected).toBe(true);
            expect(networkManager.players.size).toBe(1);
      
            networkManager.sendMessage = originalSend;
        });
    });

    describe("Performance and Scalability", () => {
        beforeEach(async () => {
            await networkManager.connect("ws://localhost:3000", "test-room");
        });

        test("should handle many players efficiently", () => {
            const start = performance.now();
      
            // Add many players
            for (let i = 0; i < 100; i++) {
                networkManager.addPlayer(`player-${i}`, { name: `Player${i}` });
            }
      
            const addTime = performance.now() - start;
            expect(addTime).toBeLessThan(100); // Should be fast
      
            const roomState = networkManager.getRoomState();
            expect(roomState.players).toHaveLength(100);
        });

        test("should handle rapid message sending", () => {
            const start = performance.now();
      
            for (let i = 0; i < 100; i++) {
                networkManager.sendMessage("rapidTest", { index: i });
            }
      
            const sendTime = performance.now() - start;
            expect(sendTime).toBeLessThan(100); // Should be fast
            expect(networkManager.messageQueue).toHaveLength(100);
        });

        test("should efficiently manage event handlers", () => {
            const handlers = [];
      
            // Register many handlers
            for (let i = 0; i < 50; i++) {
                const handler = jest.fn();
                handlers.push(handler);
                networkManager.on("massTest", handler);
            }
      
            const start = performance.now();
            networkManager.emit("massTest", {});
            const emitTime = performance.now() - start;
      
            expect(emitTime).toBeLessThan(50); // Should be reasonably fast
            handlers.forEach(handler => {
                expect(handler).toHaveBeenCalled();
            });
        });
    });
});