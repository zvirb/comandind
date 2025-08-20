/**
 * Unit Tests for AStar Pathfinding Algorithm
 * Tests pathfinding logic, optimization, caching, and edge cases
 */

import { AStar } from "../AStar.js";

describe("AStar Pathfinding", () => {
    let aStar;
    let mockGrid;

    beforeEach(() => {
    // Create mock navigation grid
        mockGrid = createMockNavigationGrid(10, 10);
        aStar = new AStar(mockGrid);
    });

    afterEach(() => {
        if (aStar) {
            aStar.clearCache();
        }
    });

    describe("Initialization and Configuration", () => {
        test("should create AStar with default configuration", () => {
            expect(aStar.grid).toBe(mockGrid);
            expect(aStar.maxSearchNodes).toBe(1000);
            expect(aStar.allowDiagonal).toBe(true);
            expect(aStar.smoothPath).toBe(true);
            expect(aStar.pathCache).toBeInstanceOf(Map);
        });

        test("should initialize with empty cache", () => {
            expect(aStar.pathCache.size).toBe(0);
        });
    });

    describe("Basic Pathfinding", () => {
        test("should find simple straight path", () => {
            const path = aStar.findPath(0, 0, 96, 0); // 3 cells right
      
            expect(path).toBeDefined();
            expect(path.length).toBeGreaterThan(0);
            expect(path[0]).toEqual({ x: 16, y: 16 }); // Start position (grid center)
            expect(path[path.length - 1]).toBeWithinRange({ x: 96, y: 0 }, 50); // Near goal
        });

        test("should find diagonal path when allowed", () => {
            aStar.allowDiagonal = true;
            const path = aStar.findPath(0, 0, 64, 64); // Diagonal movement
      
            expect(path).toBeDefined();
            expect(path.length).toBeGreaterThan(0);
            expect(path.length).toBeLessThan(6); // Should be shorter than non-diagonal
        });

        test("should find longer path when diagonal disabled", () => {
            aStar.allowDiagonal = false;
            const path = aStar.findPath(0, 0, 64, 64);
      
            expect(path).toBeDefined();
            expect(path.length).toBeGreaterThan(4); // Should need more steps
        });

        test("should return empty path for unreachable destination", () => {
            // Mock grid to return false for walkable at destination
            mockGrid.isWalkable.mockImplementation((x, y) => !(x === 3 && y === 3));
            mockGrid.worldToGrid.mockReturnValue({ x: 3, y: 3 });
      
            const path = aStar.findPath(0, 0, 96, 96);
      
            expect(path).toEqual([]);
        });

        test("should handle start position not walkable", () => {
            mockGrid.isWalkable.mockImplementation((x, y) => !(x === 0 && y === 0));
      
            const path = aStar.findPath(0, 0, 64, 64);
      
            expect(path).toEqual([]);
        });
    });

    describe("Path Optimization and Smoothing", () => {
        test("should smooth path when enabled", () => {
            aStar.smoothPath = true;
      
            // Create a path that can be smoothed
            const originalPath = aStar.findPath(0, 0, 128, 128);
            expect(originalPath.length).toBeGreaterThan(0);
      
            // Path should be optimized (fewer waypoints than grid cells)
            expect(originalPath.length).toBeLessThan(8);
        });

        test("should not smooth path when disabled", () => {
            aStar.smoothPath = false;
      
            const path = aStar.findPath(0, 0, 96, 96);
      
            // Should have more waypoints when not smoothed
            expect(path.length).toBeGreaterThan(2);
        });

        test("should handle line of sight checks", () => {
            const from = { x: 0, y: 0 };
            const to = { x: 64, y: 64 };
      
            // Mock grid to always allow line of sight
            mockGrid.isWalkable.mockReturnValue(true);
      
            const hasLOS = aStar.hasLineOfSight(from, to);
            expect(hasLOS).toBe(true);
        });

        test("should detect blocked line of sight", () => {
            const from = { x: 0, y: 0 };
            const to = { x: 64, y: 64 };
      
            // Mock grid to block path at midpoint
            mockGrid.isWalkable.mockImplementation((x, y) => !(x === 1 && y === 1));
      
            const hasLOS = aStar.hasLineOfSight(from, to);
            expect(hasLOS).toBe(false);
        });
    });

    describe("Caching System", () => {
        test("should cache successful paths", () => {
            const path1 = aStar.findPath(0, 0, 64, 64);
            expect(aStar.pathCache.size).toBe(1);
      
            const path2 = aStar.findPath(0, 0, 64, 64); // Same request
            expect(path2).toEqual(path1);
            expect(aStar.pathCache.size).toBe(1); // Cache size unchanged
        });

        test("should return copy of cached path", () => {
            const path1 = aStar.findPath(0, 0, 64, 64);
            const path2 = aStar.findPath(0, 0, 64, 64);
      
            // Should be equal but not same reference
            expect(path2).toEqual(path1);
            expect(path2).not.toBe(path1);
        });

        test("should limit cache size", () => {
            aStar.cacheSize = 3;
      
            // Fill cache beyond limit
            aStar.findPath(0, 0, 32, 0);
            aStar.findPath(0, 0, 64, 0);
            aStar.findPath(0, 0, 96, 0);
            aStar.findPath(0, 0, 128, 0); // Should evict oldest
      
            expect(aStar.pathCache.size).toBe(3);
        });

        test("should clear cache when requested", () => {
            aStar.findPath(0, 0, 64, 64);
            expect(aStar.pathCache.size).toBeGreaterThan(0);
      
            aStar.clearCache();
            expect(aStar.pathCache.size).toBe(0);
        });
    });

    describe("Nearest Walkable Finding", () => {
        test("should find nearest walkable cell", () => {
            // Mock grid where only (2,2) is walkable near (3,3)
            mockGrid.isWalkable.mockImplementation((x, y) => (x === 2 && y === 2));
            mockGrid.isValidCell.mockReturnValue(true);
      
            const nearest = aStar.findNearestWalkable(3, 3, 5);
      
            expect(nearest).toEqual({ x: 2, y: 2, dist: expect.any(Number) });
        });

        test("should return null when no walkable cells in range", () => {
            mockGrid.isWalkable.mockReturnValue(false);
            mockGrid.isValidCell.mockReturnValue(true);
      
            const nearest = aStar.findNearestWalkable(5, 5, 2);
      
            expect(nearest).toBeNull();
        });

        test("should respect maximum search radius", () => {
            mockGrid.isWalkable.mockImplementation((x, y) => (x === 10 && y === 10));
            mockGrid.isValidCell.mockReturnValue(true);
      
            const nearest = aStar.findNearestWalkable(5, 5, 3); // Radius too small
      
            expect(nearest).toBeNull();
        });
    });

    describe("Performance and Scalability", () => {
        test("should respect maximum search nodes limit", () => {
            aStar.maxSearchNodes = 10; // Very low limit
      
            // Try to find long path
            const path = aStar.findPath(0, 0, 320, 320);
      
            // Should return empty path due to search limit
            expect(path).toEqual([]);
        });

        test("should handle large grid efficiently", () => {
            const largeMockGrid = createMockNavigationGrid(100, 100);
            const largeAStar = new AStar(largeMockGrid);
      
            const start = performance.now();
            const path = largeAStar.findPath(0, 0, 320, 320);
            const end = performance.now();
      
            expect(end - start).toBeLessThan(1000); // Should complete within 1 second
            expect(path).toBeDefined();
        });

        test("should get pathfinding statistics", () => {
            const stats = aStar.getStats();
      
            expect(stats).toHaveProperty("cacheSize");
            expect(stats).toHaveProperty("maxCacheSize");
            expect(stats).toHaveProperty("allowDiagonal");
            expect(stats).toHaveProperty("smoothPath");
            expect(typeof stats.cacheSize).toBe("number");
        });
    });

    describe("Error Handling and Edge Cases", () => {
        test("should handle null grid gracefully", () => {
            const nullAStar = new AStar(null);
      
            expect(() => {
                nullAStar.findPath(0, 0, 64, 64);
            }).toThrow();
        });

        test("should handle same start and end position", () => {
            const path = aStar.findPath(64, 64, 64, 64);
      
            expect(path).toBeDefined();
            expect(path.length).toBeGreaterThanOrEqual(1);
        });

        test("should handle negative coordinates", () => {
            // Mock grid to handle negative coordinates
            mockGrid.worldToGrid.mockImplementation((x, y) => ({
                x: Math.floor(x / 32),
                y: Math.floor(y / 32)
            }));
      
            const path = aStar.findPath(-32, -32, 32, 32);
      
            expect(path).toBeDefined();
        });

        test("should handle floating point coordinates", () => {
            const path = aStar.findPath(15.7, 23.3, 47.9, 71.2);
      
            expect(path).toBeDefined();
            expect(path.length).toBeGreaterThan(0);
        });
    });

    describe("Goal Adjustment", () => {
        test("should find nearest walkable goal when target is blocked", () => {
            // Mock grid where (3,3) is blocked but (2,3) is walkable
            mockGrid.isWalkable.mockImplementation((x, y) => !(x === 3 && y === 3));
            mockGrid.worldToGrid.mockImplementation((x, y) => ({ x: Math.floor(x / 32), y: Math.floor(y / 32) }));
      
            const path = aStar.findPath(0, 0, 96, 96); // Target is blocked cell (3,3)
      
            expect(path).toBeDefined();
            expect(path.length).toBeGreaterThan(0);
        });

        test("should warn when start position is not walkable", () => {
            const consoleSpy = jest.spyOn(console, "warn").mockImplementation();
            mockGrid.isWalkable.mockImplementation((x, y) => !(x === 0 && y === 0));
      
            aStar.findPath(0, 0, 64, 64);
      
            expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining("Start position is not walkable"));
            consoleSpy.mockRestore();
        });

        test("should warn when no walkable path to goal exists", () => {
            const consoleSpy = jest.spyOn(console, "warn").mockImplementation();
      
            // Make goal unreachable and no nearby walkable cells
            mockGrid.isWalkable.mockReturnValue(false);
      
            aStar.findPath(0, 0, 96, 96);
      
            expect(consoleSpy).toHaveBeenCalled();
            consoleSpy.mockRestore();
        });
    });

    describe("Path Reconstruction", () => {
        test("should reconstruct path correctly", () => {
            const cameFrom = new Map();
            const goal = { x: 2, y: 2 };
            const intermediate = { x: 1, y: 1 };
            const start = { x: 0, y: 0 };
      
            cameFrom.set("2,2", intermediate);
            cameFrom.set("1,1", start);
      
            const path = aStar.reconstructPath(cameFrom, goal);
      
            expect(path).toHaveLength(3);
            expect(path[0]).toEqual(start);
            expect(path[1]).toEqual(intermediate);
            expect(path[2]).toEqual(goal);
        });

        test("should handle single node path", () => {
            const path = aStar.reconstructPath(new Map(), { x: 0, y: 0 });
      
            expect(path).toHaveLength(1);
            expect(path[0]).toEqual({ x: 0, y: 0 });
        });
    });

    describe("A* Algorithm Core", () => {
        test("should find optimal path length", () => {
            // Create simple 3x3 grid with no obstacles
            const simpleGrid = createMockNavigationGrid(3, 3);
            const simpleAStar = new AStar(simpleGrid);
      
            const path = simpleAStar.findPath(0, 0, 64, 64); // Corner to corner
      
            expect(path).toBeDefined();
            expect(path.length).toBeGreaterThan(1);
      
            // Path should be reasonably short for such simple case
            expect(path.length).toBeLessThan(5);
        });

        test("should handle complex maze-like scenarios", () => {
            // Mock a maze where only specific cells are walkable
            const mazePattern = new Set(["0,0", "1,0", "2,0", "2,1", "2,2"]);
            mockGrid.isWalkable.mockImplementation((x, y) => mazePattern.has(`${x},${y}`));
      
            const path = aStar.findPath(0, 0, 64, 64);
      
            expect(path).toBeDefined();
            // Should find a path even through complex maze
            expect(path.length).toBeGreaterThan(2);
        });
    });

    describe("Integration with Grid System", () => {
        test("should correctly use grid coordinate conversion", () => {
            aStar.findPath(50, 75, 150, 225);
      
            expect(mockGrid.worldToGrid).toHaveBeenCalledWith(50, 75);
            expect(mockGrid.worldToGrid).toHaveBeenCalledWith(150, 225);
            expect(mockGrid.gridToWorld).toHaveBeenCalled();
        });

        test("should use grid neighbor finding", () => {
            aStar.findPath(0, 0, 32, 32);
      
            expect(mockGrid.getNeighbors).toHaveBeenCalled();
        });

        test("should use grid movement costs", () => {
            aStar.findPath(0, 0, 32, 32);
      
            expect(mockGrid.getMovementCost).toHaveBeenCalled();
        });

        test("should use grid heuristic function", () => {
            aStar.findPath(0, 0, 32, 32);
      
            expect(mockGrid.heuristic).toHaveBeenCalled();
        });
    });
});