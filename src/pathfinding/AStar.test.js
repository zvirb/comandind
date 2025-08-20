/**
 * Unit tests for AStar pathfinding algorithm
 */

import { AStar } from "./AStar.js";
import { jest } from "@jest/globals";

// Mock NavigationGrid
class MockNavigationGrid {
    constructor(width = 10, height = 10) {
        this.width = width;
        this.height = height;
        this.cellSize = 32;
        this.obstacles = new Set();
    }

    worldToGrid(x, y) {
        return {
            x: Math.floor(x / this.cellSize),
            y: Math.floor(y / this.cellSize)
        };
    }

    gridToWorld(x, y) {
        return {
            x: x * this.cellSize + this.cellSize / 2,
            y: y * this.cellSize + this.cellSize / 2
        };
    }

    isWalkable(x, y) {
        if (x < 0 || x >= this.width || y < 0 || y >= this.height) {
            return false;
        }
        return !this.obstacles.has(`${x},${y}`);
    }

    isValidCell(x, y) {
        return x >= 0 && x < this.width && y >= 0 && y < this.height;
    }

    getNeighbors(x, y, allowDiagonal = true) {
        const neighbors = [];
        const directions = [
            { dx: 0, dy: -1 }, // North
            { dx: 1, dy: 0 },  // East
            { dx: 0, dy: 1 },  // South
            { dx: -1, dy: 0 }  // West
        ];

        if (allowDiagonal) {
            directions.push(
                { dx: 1, dy: -1 },  // NE
                { dx: 1, dy: 1 },   // SE
                { dx: -1, dy: 1 },  // SW
                { dx: -1, dy: -1 }  // NW
            );
        }

        for (const { dx, dy } of directions) {
            const nx = x + dx;
            const ny = y + dy;
            if (this.isWalkable(nx, ny)) {
                neighbors.push({ x: nx, y: ny });
            }
        }

        return neighbors;
    }

    getMovementCost(x1, y1, x2, y2) {
        const dx = Math.abs(x2 - x1);
        const dy = Math.abs(y2 - y1);
        return dx + dy === 2 ? 1.414 : 1; // Diagonal vs straight
    }

    heuristic(x1, y1, x2, y2) {
        return Math.abs(x2 - x1) + Math.abs(y2 - y1); // Manhattan distance
    }

    addObstacle(x, y) {
        this.obstacles.add(`${x},${y}`);
    }

    removeObstacle(x, y) {
        this.obstacles.delete(`${x},${y}`);
    }
}

describe("AStar", () => {
    let grid;
    let pathfinder;

    beforeEach(() => {
        grid = new MockNavigationGrid(10, 10);
        pathfinder = new AStar(grid);
    });

    describe("constructor", () => {
        test("should initialize with default values", () => {
            expect(pathfinder.grid).toBe(grid);
            expect(pathfinder.maxSearchNodes).toBe(1000);
            expect(pathfinder.allowDiagonal).toBe(true);
            expect(pathfinder.smoothPath).toBe(true);
            expect(pathfinder.pathCache).toBeInstanceOf(Map);
        });
    });

    describe("findPath", () => {
        test("should find straight path in empty grid", () => {
            const path = pathfinder.findPath(32, 32, 160, 32);
      
            expect(path).toBeDefined();
            expect(path.length).toBeGreaterThan(0);
            expect(path[0]).toMatchObject({ x: 32, y: 32 });
            expect(path[path.length - 1]).toMatchObject({ x: 160, y: 32 });
        });

        test("should find path around obstacles", () => {
            // Create a wall
            for (let i = 2; i < 8; i++) {
                grid.addObstacle(5, i);
            }
      
            const path = pathfinder.findPath(32, 160, 224, 160);
      
            expect(path).toBeDefined();
            expect(path.length).toBeGreaterThan(0);
            // Path should go around the wall
            const gridPath = path.map(p => grid.worldToGrid(p.x, p.y));
            const crossesWall = gridPath.some(p => p.x === 5 && p.y >= 2 && p.y < 8);
            expect(crossesWall).toBe(false);
        });

        test("should return empty array for unreachable goal", () => {
            // Surround the goal with obstacles
            grid.addObstacle(4, 4);
            grid.addObstacle(5, 4);
            grid.addObstacle(6, 4);
            grid.addObstacle(4, 5);
            grid.addObstacle(6, 5);
            grid.addObstacle(4, 6);
            grid.addObstacle(5, 6);
            grid.addObstacle(6, 6);
      
            const path = pathfinder.findPath(32, 32, 160, 160);
      
            expect(path).toEqual([]);
        });

        test("should handle start position not walkable", () => {
            grid.addObstacle(1, 1);
      
            const consoleSpy = jest.spyOn(console, "warn").mockImplementation();
            const path = pathfinder.findPath(32, 32, 160, 160);
      
            expect(path).toEqual([]);
            expect(consoleSpy).toHaveBeenCalledWith("Start position is not walkable");
            consoleSpy.mockRestore();
        });

        test("should find nearest walkable cell if goal is blocked", () => {
            grid.addObstacle(5, 5);
      
            const path = pathfinder.findPath(32, 32, 160, 160);
      
            expect(path).toBeDefined();
            expect(path.length).toBeGreaterThan(0);
            // Should find path to a cell near the blocked goal
            const finalPos = grid.worldToGrid(path[path.length - 1].x, path[path.length - 1].y);
            const distanceToGoal = Math.abs(finalPos.x - 5) + Math.abs(finalPos.y - 5);
            expect(distanceToGoal).toBeLessThanOrEqual(2);
        });

        test("should use cache for repeated path requests", () => {
            const path1 = pathfinder.findPath(32, 32, 160, 160);
            const path2 = pathfinder.findPath(32, 32, 160, 160);
      
            expect(path1).toEqual(path2);
            expect(pathfinder.pathCache.size).toBe(1);
        });

        test("should handle diagonal movement when enabled", () => {
            pathfinder.allowDiagonal = true;
      
            const path = pathfinder.findPath(32, 32, 160, 160);
      
            expect(path).toBeDefined();
            // Diagonal path should be shorter than manhattan distance
            const gridStart = grid.worldToGrid(32, 32);
            const gridEnd = grid.worldToGrid(160, 160);
            const manhattanDistance = Math.abs(gridEnd.x - gridStart.x) + Math.abs(gridEnd.y - gridStart.y);
            expect(path.length).toBeLessThan(manhattanDistance);
        });

        test("should not use diagonal movement when disabled", () => {
            pathfinder.allowDiagonal = false;
      
            const path = pathfinder.findPath(32, 32, 96, 96);
      
            expect(path).toBeDefined();
            // Check that path only moves orthogonally
            for (let i = 1; i < path.length; i++) {
                const prev = grid.worldToGrid(path[i - 1].x, path[i - 1].y);
                const curr = grid.worldToGrid(path[i].x, path[i].y);
                const dx = Math.abs(curr.x - prev.x);
                const dy = Math.abs(curr.y - prev.y);
                // Should move only in one direction at a time
                expect(dx + dy).toBe(1);
            }
        });
    });

    describe("clearCache", () => {
        test("should clear path cache", () => {
            pathfinder.findPath(32, 32, 160, 160);
            expect(pathfinder.pathCache.size).toBe(1);
      
            pathfinder.clearCache();
      
            expect(pathfinder.pathCache.size).toBe(0);
        });
    });

    describe("performance", () => {
        test("should limit search nodes to prevent infinite loops", () => {
            // Create a large grid with complex obstacles
            const largeGrid = new MockNavigationGrid(100, 100);
            const largePF = new AStar(largeGrid);
            largePF.maxSearchNodes = 100; // Limit search
      
            // Create a maze-like pattern
            for (let i = 0; i < 100; i++) {
                if (i % 2 === 0) {
                    for (let j = 0; j < 98; j++) {
                        largeGrid.addObstacle(i, j);
                    }
                }
            }
      
            const startTime = Date.now();
            const path = largePF.findPath(16, 16, 3168, 3168);
            const duration = Date.now() - startTime;
      
            // Should complete quickly due to node limit
            expect(duration).toBeLessThan(100);
        });

        test("should maintain cache size limit", () => {
            pathfinder.cacheSize = 3;
      
            // Add more paths than cache size
            for (let i = 0; i < 5; i++) {
                pathfinder.findPath(i * 32, 0, i * 32, 320);
            }
      
            expect(pathfinder.pathCache.size).toBeLessThanOrEqual(3);
        });
    });
});