# Command and Independent Thought

A real-time strategy game built with modern web technologies, inspired by classic RTS games.

## 🎮 Features

- **High-Performance Rendering**: PixiJS v7 with WebGL2/WebGL1 fallback
- **Fixed Timestep Game Loop**: Consistent 60 FPS gameplay
- **Smooth Camera System**: Edge scrolling, keyboard controls, and zoom
- **Performance Monitoring**: Real-time FPS, memory, and draw call tracking
- **Sprite Batching**: Optimized rendering for 1000+ units

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## 🕹️ Controls

### Camera Controls
- **WASD** or **Arrow Keys**: Move camera
- **Mouse Edge Scrolling**: Move mouse to screen edges
- **Mouse Wheel**: Zoom in/out

### Test Controls
- **Press 1**: Add 100 test sprites
- **Press 2**: Start stress test (adds 1000 sprites)
- **Press 0**: Clear all sprites

## 🏗️ Architecture

### Core Systems
- **Application**: PixiJS renderer management with layer system
- **GameLoop**: Fixed timestep with interpolation for smooth rendering
- **Camera**: World/screen coordinate conversion with smooth movement
- **InputHandler**: Event-driven input system for keyboard, mouse, and touch
- **PerformanceMonitor**: Real-time performance metrics tracking

### Technology Stack
- **Rendering**: PixiJS v7.3.3
- **Build Tool**: Vite
- **Multiplayer** (planned): Colyseus
- **AI** (planned): TensorFlow.js
- **LLM Integration** (planned): Ollama

## 📊 Performance Targets

- **Frame Rate**: 60+ FPS (minimum 47 FPS)
- **Memory Usage**: <200MB baseline, <500MB maximum
- **Unit Count**: 200+ units on screen simultaneously
- **Draw Calls**: Optimized batching with <10 draw calls for 1000 sprites

## 🗂️ Project Structure

```
comandind/
├── src/
│   ├── core/           # Core engine systems
│   ├── rendering/      # Rendering and graphics
│   ├── gameplay/       # Game mechanics (planned)
│   ├── ai/            # AI systems (planned)
│   ├── multiplayer/   # Network code (planned)
│   └── utils/         # Utility functions
├── public/
│   └── assets/        # Game assets
├── .claude/           # Orchestration configuration
└── docs/             # Documentation
```

## 🔄 Development Roadmap

### ✅ Iteration 1: Foundation (Complete)
- Core rendering engine
- Game loop and camera system
- Performance monitoring
- Development environment

### 🚧 Iteration 2: Game Mechanics (Next)
- Entity-Component System
- Unit selection and movement
- Pathfinding (A* and flow fields)
- Resource gathering
- Building construction

### 📅 Future Iterations
- **Iteration 3**: AI Systems (TensorFlow.js, behavior trees)
- **Iteration 4**: Multiplayer (Colyseus, WebRTC)
- **Iteration 5**: Polish and Production

## 📝 License

MIT

## 🤝 Contributing

This project uses Claude Code orchestration for development. See `.claude/` for configuration.