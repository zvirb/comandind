/**
 * Advanced Map Generation System - Entry Point
 * 
 * This module exports all the advanced map generation components
 * for easy integration with the Command & Conquer clone project.
 */

import AdvancedMapGenerator from './AdvancedMapGenerator.js';
import WaveFunctionCollapse from './WaveFunctionCollapse.js';
import AutoTiler from './AutoTiler.js';
import ResourcePlacer from './ResourcePlacer.js';
import SymmetricGenerator from './SymmetricGenerator.js';
import MapValidator from './MapValidator.js';
import MLMapQualityEvaluator from './MLMapQualityEvaluator.js';

// Main exports
export {
    AdvancedMapGenerator,
    WaveFunctionCollapse,
    AutoTiler,
    ResourcePlacer,
    SymmetricGenerator,
    MapValidator,
    MLMapQualityEvaluator
};

// Default export is the main generator
export default AdvancedMapGenerator;

// Convenience factory functions
export const createMapGenerator = (options = {}) => {
    return new AdvancedMapGenerator(options);
};

export const createCompetitiveGenerator = (playerCount = 2) => {
    const presets = AdvancedMapGenerator.getPresets();
    let config;
    
    switch (playerCount) {
        case 2:
            config = presets.skirmish1v1;
            break;
        case 4:
            config = presets.competitive2v2;
            break;
        default:
            config = {
                playerCount,
                algorithm: 'symmetric',
                symmetryType: playerCount <= 4 ? 'rotational' : 'mirror',
                resourceBalance: true,
                enableValidation: true
            };
    }
    
    return new AdvancedMapGenerator(config);
};

export const createCampaignGenerator = (options = {}) => {
    const presets = AdvancedMapGenerator.getPresets();
    const config = { ...presets.campaign, ...options };
    return new AdvancedMapGenerator(config);
};

export const createMLEnhancedGenerator = (options = {}) => {
    const config = {
        enableMLEvaluation: true,
        enableValidation: true,
        mlQualityThreshold: 70,
        qualityThreshold: 75,
        maxGenerationAttempts: 3,
        ...options
    };
    return new AdvancedMapGenerator(config);
};

// Utility functions
export const validateMap = (mapData, options = {}) => {
    const validator = new MapValidator(options);
    return validator.validateMap(mapData);
};

export const evaluateMapWithML = async (mapData, options = {}) => {
    const mlEvaluator = new MLMapQualityEvaluator(options);
    const initialized = await mlEvaluator.initialize();
    
    if (!initialized) {
        throw new Error('Failed to initialize ML evaluator');
    }
    
    const result = await mlEvaluator.evaluateMap(mapData);
    mlEvaluator.cleanup();
    
    return result;
};

export const getAvailablePresets = () => {
    return AdvancedMapGenerator.getPresets();
};