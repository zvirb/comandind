# WebStrike Command - Knowledge Base Index

## Overview
This knowledge base contains comprehensive documentation for the WebStrike Command (C&C Tiberian Dawn Clone) project. All information has been organized into structured entities for easy retrieval and reference during development.

---

## Core Documentation Entities

### 1. Project Overview
**File:** `webstrike-project-overview.md`
**Entity Type:** project-documentation  
**Contains:**
- Project charter and success criteria
- 20-week timeline and technology stack
- Performance targets and quality metrics
- Risk management matrix
- User stories and epics

### 2. Technical Architecture
**File:** `webstrike-technical-architecture.md`
**Entity Type:** architecture-documentation  
**Contains:**
- PixiJS rendering engine specifications
- Colyseus + WebRTC multiplayer hybrid
- TensorFlow.js + Ollama AI framework
- Game loop and ECS architecture
- Development tools and pipeline

### 3. Game Mechanics
**File:** `webstrike-game-mechanics.md`
**Entity Type:** gameplay-documentation  
**Contains:**
- Unit statistics (GDI/NOD)
- Damage system and economic mechanics
- Pathfinding algorithms (A*/Flow Fields)
- Fog of war implementation
- Selection and control systems

### 4. AI Systems
**File:** `webstrike-ai-systems.md`
**Entity Type:** ai-documentation  
**Contains:**
- Q-Learning with TensorFlow.js
- Behavior trees for unit autonomy
- Goal-Oriented Action Planning (GOAP)
- Ollama LLM strategic integration
- Influence maps and steering behaviors

### 5. Multiplayer Architecture
**File:** `webstrike-multiplayer-architecture.md`
**Entity Type:** network-documentation  
**Contains:**
- Colyseus server setup and WebRTC channels
- State synchronization strategies
- Anti-cheat measures and security
- Latency optimization techniques
- Room management and matchmaking

### 6. Performance Optimization
**File:** `webstrike-performance-optimization.md`
**Entity Type:** optimization-documentation  
**Contains:**
- Sprite batching optimization
- Quadtree spatial indexing
- Object pooling systems
- Memory management strategies
- Performance monitoring tools

### 7. Iteration Plan
**File:** `webstrike-iteration-plan.md`
**Entity Type:** planning-documentation  
**Contains:**
- 5 iterations with 4-week cycles
- 12-phase Claude Code Orchestration
- Agent coordination matrix
- Knowledge base evolution
- Final delivery checklist

### 8. Asset Resources
**File:** `webstrike-asset-resources.md`
**Entity Type:** resource-documentation  
**Contains:**
- Legal foundation (EA freeware)
- Asset extraction tools (XCC Mixer)
- High-resolution options and upscaling
- Audio resources and organization
- Modding community resources

### 9. Code Patterns
**File:** `webstrike-code-patterns.md`
**Entity Type:** implementation-documentation  
**Contains:**
- Core engine patterns (ECS, State Management)
- Rendering optimization implementations
- Pathfinding algorithms (A*, Flow Fields)
- Input handling with Command pattern
- Camera system with smooth following

### 10. Success Metrics
**File:** `webstrike-success-metrics.md`
**Entity Type:** metrics-documentation  
**Contains:**
- Performance metrics (FPS, Memory, Latency)
- Quality assurance standards
- AI and multiplayer performance
- Validation framework
- Production health monitoring

---

## Quick Reference Guide

### Technology Stack Summary
- **Frontend:** HTML5, JavaScript, PixiJS
- **Multiplayer:** Colyseus + WebRTC
- **AI/ML:** TensorFlow.js + Ollama LLM
- **Assets:** EA C&C Freeware + XCC Mixer
- **Testing:** Jest, Playwright, Lighthouse

### Key Performance Targets
- **60+ FPS** with 200+ units on screen
- **Sub-100ms** multiplayer latency (P95)
- **< 200MB** baseline memory usage
- **80%+** code coverage
- **> 4.5/5** user satisfaction

### Critical File Locations
```
docs/
├── webstrike-project-overview.md          # Project charter
├── webstrike-technical-architecture.md    # System design
├── webstrike-game-mechanics.md           # Gameplay rules
├── webstrike-ai-systems.md              # AI implementation
├── webstrike-multiplayer-architecture.md # Network design
├── webstrike-performance-optimization.md # Optimization
├── webstrike-iteration-plan.md          # Development plan
├── webstrike-asset-resources.md         # Asset management
├── webstrike-code-patterns.md           # Implementation
└── webstrike-success-metrics.md         # Validation
```

---

## Search and Retrieval Tips

### By Development Phase
- **Phase 1 (Foundation):** Technical Architecture + Performance Optimization
- **Phase 2 (Mechanics):** Game Mechanics + Code Patterns
- **Phase 3 (AI):** AI Systems + Implementation Documentation
- **Phase 4 (Multiplayer):** Multiplayer Architecture + Network Code
- **Phase 5 (Polish):** Success Metrics + Validation Framework

### By Domain
- **Rendering:** Technical Architecture + Performance Optimization
- **Gameplay:** Game Mechanics + Code Patterns
- **Networking:** Multiplayer Architecture + Security
- **Intelligence:** AI Systems + Machine Learning
- **Assets:** Asset Resources + Legal Considerations

### By Role
- **Game Engine Architect:** Technical Architecture + Code Patterns
- **AI Specialist:** AI Systems + Machine Learning Implementation
- **Network Engineer:** Multiplayer Architecture + Anti-Cheat
- **Performance Engineer:** Performance Optimization + Monitoring
- **Project Manager:** Project Overview + Iteration Plan

---

## Knowledge Relationships

### Cross-References
- **Performance Optimization** ↔ **Technical Architecture**
- **AI Systems** ↔ **Game Mechanics** (Unit behavior)
- **Multiplayer Architecture** ↔ **Performance Optimization** (Bandwidth)
- **Code Patterns** ↔ All implementation documents
- **Success Metrics** ↔ All technical specifications

### Dependencies
- **Asset Resources** → Required before implementation
- **Technical Architecture** → Foundation for all systems
- **Game Mechanics** → Required for AI training
- **Performance Optimization** → Critical for multiplayer
- **Success Metrics** → Validation for all components

---

## Update Protocol

### Adding New Knowledge
1. Create new documentation file in `/docs/` directory
2. Update this index with new entity information
3. Add cross-references to related documents
4. Include search keywords and retrieval tips

### Maintaining Accuracy
- Review documentation after each iteration
- Update performance targets based on testing results
- Maintain version history for major changes
- Validate code examples against implementation

---

## Usage Notes

### For Development Teams
- Reference appropriate domain documents before starting work
- Use Code Patterns for implementation guidance
- Check Success Metrics for validation criteria
- Follow Iteration Plan for project progression

### For Claude Code Orchestration
- Query specific entity types for focused context
- Use cross-references for comprehensive understanding
- Reference Success Metrics for validation requirements
- Follow agent coordination patterns from Iteration Plan

### For Stakeholders
- Start with Project Overview for high-level understanding
- Review Success Metrics for quality standards
- Check Iteration Plan for timeline and deliverables
- Reference Asset Resources for legal considerations

This knowledge base serves as the single source of truth for the WebStrike Command project, ensuring consistent understanding and implementation across all development phases and team members.