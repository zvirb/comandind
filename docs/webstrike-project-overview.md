# WebStrike Command - Project Overview

## Project Charter
**Project Name:** WebStrike Command (C&C Tiberian Dawn Clone)  
**Project Code:** WSC-2025  
**Duration:** 20 weeks (5 iterations × 4 weeks)  
**Technology Stack:** HTML5, JavaScript, PixiJS, Colyseus, TensorFlow.js, Ollama

## Success Criteria
- [ ] 60+ FPS with 200+ units on screen
- [ ] Sub-100ms multiplayer latency (P95)
- [ ] AI opponents with adaptive learning
- [ ] Full campaign mode (12 missions)
- [ ] Cross-browser compatibility (Chrome, Firefox, Safari, Edge)
- [ ] Mobile responsive controls

## Performance Targets
- **FPS:** Target 60, Minimum 47
- **Memory:** Baseline 200MB, Maximum 500MB
- **Latency:** P50 50ms, P95 100ms, P99 150ms

## Quality Metrics
- **Code coverage:** 80%
- **Bug density:** < 1 per KLOC
- **User satisfaction:** > 4.5/5
- **Crash rate:** < 0.01%

## AI Performance Metrics
- **Learning convergence:** < 1000 episodes
- **Win rate:** > 40% vs human players
- **Decision time:** < 1ms per unit
- **Strategy quality:** Expert-validated

## Legal Foundation
- EA released C&C Tiberian Dawn as freeware in 2007
- Assets available on Archive.org
- OpenRA project provides automatic asset downloading
- XCC Mixer tools for asset extraction from MIX archives

## Risk Management Matrix
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Performance degradation | Medium | High | Continuous profiling, quadtree optimization |
| Network desync | Low | Critical | State reconciliation, rollback netcode |
| AI training failure | Medium | Medium | Fallback to scripted AI, pre-trained models |
| Browser compatibility | Low | High | Progressive enhancement, polyfills |
| Scalability issues | Medium | High | Load balancing, CDN distribution |

## User Stories

### Epic: Core Gameplay
- As a player, I want to select units with mouse
- As a player, I want to command units to move
- As a player, I want to harvest resources
- As a player, I want to construct buildings
- As a player, I want to engage in combat

### Epic: Multiplayer
- As a player, I want to create/join games
- As a player, I want low-latency gameplay
- As a player, I want fair matchmaking
- As a player, I want replay functionality

### Epic: AI Opponents
- As a player, I want challenging AI opponents
- As a player, I want AI that learns my strategies
- As a player, I want different difficulty levels
- As a player, I want AI personalities