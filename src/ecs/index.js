/**
 * ECS (Entity-Component-System) Module
 * Export all ECS classes for easy importing
 */

// Core ECS classes
export { Entity } from "./Entity.js";
export { World } from "./World.js";
export { EntityFactory } from "./EntityFactory.js";

// Base classes
export { Component } from "./Component.js";
export { System } from "./System.js";

// Components
export {
    TransformComponent,
    VelocityComponent,
    SpriteComponent,
    HealthComponent,
    UnitComponent,
    BuildingComponent,
    MovementComponent,
    CombatComponent,
    AIComponent,
    SelectableComponent,
    CommandComponent
} from "./Component.js";

// Systems
export {
    MovementSystem,
    RenderingSystem,
    UnitMovementSystem,
    CombatSystem,
    AISystem
} from "./System.js";

export { SelectionSystem } from "./SelectionSystem.js";