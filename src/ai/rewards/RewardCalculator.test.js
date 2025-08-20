/**
 * Unit tests for RewardCalculator
 * Tests reward calculation for AI learning in RTS game
 */

import { RewardCalculator } from './RewardCalculator.js';
import { jest } from '@jest/globals';

describe('RewardCalculator', () => {
  let calculator;
  let mockGameState;
  let mockUnit;

  beforeEach(() => {
    calculator = new RewardCalculator();
    
    mockGameState = {
      entities: new Map(),
      resources: { metal: 1000, energy: 500 },
      playerScore: 100,
      enemyScore: 50,
      time: Date.now()
    };
    
    mockUnit = {
      id: 'unit-1',
      type: 'soldier',
      health: 100,
      maxHealth: 100,
      team: 'player',
      position: { x: 100, y: 100 }
    };
  });

  describe('constructor', () => {
    test('should initialize with default values', () => {
      expect(calculator.rewardHistory).toEqual([]);
      expect(calculator.averageReward).toBe(0);
      expect(calculator.totalRewards).toBe(0);
      expect(calculator.rewardCount).toBe(0);
      expect(calculator.adaptiveScaling).toBe(true);
    });

    test('should accept custom options', () => {
      const customCalculator = new RewardCalculator({
        maxHistoryLength: 50,
        adaptiveScaling: false,
        debugMode: true
      });
      
      expect(customCalculator.maxHistoryLength).toBe(50);
      expect(customCalculator.adaptiveScaling).toBe(false);
      expect(customCalculator.debugMode).toBe(true);
    });
  });

  describe('calculateReward', () => {
    test('should calculate positive reward for successful combat', () => {
      const actionOutcome = {
        success: true,
        damageDealt: 50,
        unitsDestroyed: 1
      };
      
      const reward = calculator.calculateReward(1, mockGameState, actionOutcome, mockUnit);
      expect(reward).toBeGreaterThan(0);
    });

    test('should calculate negative reward for unit loss', () => {
      const actionOutcome = {
        success: false,
        unitLost: true
      };
      
      const reward = calculator.calculateReward(1, mockGameState, actionOutcome, mockUnit);
      expect(reward).toBeLessThan(0);
    });

    test('should provide reward breakdown in debug mode', () => {
      calculator.debugMode = true;
      
      const actionOutcome = {
        success: true,
        resourcesGathered: 10
      };
      
      calculator.calculateReward(4, mockGameState, actionOutcome, mockUnit);
      
      expect(calculator.rewardBreakdown).toBeDefined();
      expect(calculator.rewardBreakdown.actionId).toBe(4);
      expect(calculator.rewardBreakdown.components).toBeDefined();
    });
  });

  describe('updateRewardHistory', () => {
    test('should maintain history within max length', () => {
      calculator.maxHistoryLength = 3;
      
      for (let i = 0; i < 5; i++) {
        calculator.updateRewardHistory(i);
      }
      
      expect(calculator.rewardHistory.length).toBe(3);
      expect(calculator.rewardHistory).toEqual([2, 3, 4]);
    });

    test('should update average reward', () => {
      calculator.updateRewardHistory(10);
      calculator.updateRewardHistory(20);
      calculator.updateRewardHistory(30);
      
      expect(calculator.averageReward).toBe(20);
      expect(calculator.totalRewards).toBe(60);
      expect(calculator.rewardCount).toBe(3);
    });
  });

  describe('getAdaptiveMultiplier', () => {
    test('should return 1 when adaptive scaling is disabled', () => {
      calculator.adaptiveScaling = false;
      calculator.performanceBaseline = 50;
      
      const multiplier = calculator.getAdaptiveMultiplier(100);
      expect(multiplier).toBe(1);
    });

    test('should scale reward based on performance', () => {
      calculator.adaptiveScaling = true;
      calculator.performanceBaseline = 50;
      
      const higherMultiplier = calculator.getAdaptiveMultiplier(100);
      const lowerMultiplier = calculator.getAdaptiveMultiplier(25);
      
      expect(higherMultiplier).toBeGreaterThan(1);
      expect(lowerMultiplier).toBeLessThan(1);
    });
  });

  describe('reset', () => {
    test('should clear all history and stats', () => {
      calculator.updateRewardHistory(10);
      calculator.updateRewardHistory(20);
      calculator.reset();
      
      expect(calculator.rewardHistory).toEqual([]);
      expect(calculator.averageReward).toBe(0);
      expect(calculator.totalRewards).toBe(0);
      expect(calculator.rewardCount).toBe(0);
    });
  });
});