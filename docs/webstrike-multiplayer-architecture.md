# WebStrike Command - Multiplayer Architecture

## Colyseus Server Setup

```javascript
const rooms = new Map();

io.on('connection', (socket) => {
  socket.on('createRoom', (settings) => {
    const roomId = generateRoomId();
    const room = new GameRoom(settings);
    rooms.set(roomId, room);
    socket.join(roomId);
    
    room.onStateChange((state) => {
      socket.to(roomId).emit('stateUpdate', state);
    });
  });
  
  socket.on('joinRoom', (roomId) => {
    const room = rooms.get(roomId);
    if (room && room.players.length < room.maxPlayers) {
      socket.join(roomId);
      room.addPlayer(socket.id);
    }
  });
});
```

## WebRTC Data Channels
- Low-latency peer-to-peer communication
- Direct unit command transmission
- Bypasses server for time-critical operations
- STUN/TURN servers for NAT traversal
- Fallback to Colyseus for connection failures

```javascript
class WebRTCManager {
  constructor() {
    this.connections = new Map();
    this.stunServers = [
      'stun:stun.l.google.com:19302',
      'stun:stun1.l.google.com:19302'
    ];
  }
  
  async createConnection(peerId) {
    const connection = new RTCPeerConnection({
      iceServers: [{urls: this.stunServers}]
    });
    
    const dataChannel = connection.createDataChannel('gameCommands', {
      ordered: false,
      maxRetransmits: 0
    });
    
    dataChannel.onopen = () => {
      console.log('WebRTC data channel opened with', peerId);
    };
    
    dataChannel.onmessage = (event) => {
      this.handleGameCommand(JSON.parse(event.data));
    };
    
    this.connections.set(peerId, {connection, dataChannel});
    return connection;
  }
}
```

## State Synchronization Strategy
- **Server maintains authoritative game state**
- **Client-side prediction** for responsive controls
- **Server reconciliation** validates client actions
- **Delta compression** reduces bandwidth usage
- **Rollback netcode** for desync recovery

```javascript
class StateManager {
  constructor() {
    this.authoritative = true; // Server-side
    this.stateHistory = [];
    this.maxHistorySize = 60; // 1 second at 60 FPS
  }
  
  predictMove(unit, command, timestamp) {
    // Client-side prediction
    const predictedPosition = this.calculateNewPosition(unit, command);
    unit.predictedX = predictedPosition.x;
    unit.predictedY = predictedPosition.y;
    unit.predictionTimestamp = timestamp;
    
    return predictedPosition;
  }
  
  reconcile(serverState, clientState) {
    // Server reconciliation
    const discrepancies = [];
    
    for (let unitId in serverState.units) {
      const serverUnit = serverState.units[unitId];
      const clientUnit = clientState.units[unitId];
      
      if (clientUnit) {
        const distance = Math.sqrt(
          Math.pow(serverUnit.x - clientUnit.x, 2) +
          Math.pow(serverUnit.y - clientUnit.y, 2)
        );
        
        if (distance > this.reconciliationThreshold) {
          discrepancies.push({
            unitId,
            serverPosition: {x: serverUnit.x, y: serverUnit.y},
            clientPosition: {x: clientUnit.x, y: clientUnit.y}
          });
        }
      }
    }
    
    return discrepancies;
  }
}
```

## Anti-Cheat Measures
- **Server-side validation** of all player inputs
- **Rate limiting** for action frequency
- **Statistical analysis** for impossible actions
- **Replay-based detection** systems
- **Client-side game state obfuscation**

```javascript
class AntiCheatSystem {
  constructor() {
    this.actionLimits = {
      unitCommand: {maxPerSecond: 20, window: 1000},
      buildingPlacement: {maxPerSecond: 5, window: 1000}
    };
    this.playerStats = new Map();
  }
  
  validateAction(playerId, actionType, actionData) {
    const stats = this.getPlayerStats(playerId);
    
    // Rate limiting check
    if (!this.checkRateLimit(stats, actionType)) {
      this.flagSuspiciousActivity(playerId, 'rate_limit_exceeded', actionType);
      return false;
    }
    
    // Physics validation
    if (actionType === 'unitMove') {
      const isValidMove = this.validateMovement(actionData);
      if (!isValidMove) {
        this.flagSuspiciousActivity(playerId, 'impossible_movement', actionData);
        return false;
      }
    }
    
    // Resource validation
    if (actionType === 'buildBuilding') {
      const hasResources = this.validateResources(playerId, actionData.cost);
      if (!hasResources) {
        this.flagSuspiciousActivity(playerId, 'insufficient_resources', actionData);
        return false;
      }
    }
    
    return true;
  }
  
  validateMovement(moveData) {
    const {unitId, fromPosition, toPosition, timestamp, unitSpeed} = moveData;
    const distance = Math.sqrt(
      Math.pow(toPosition.x - fromPosition.x, 2) +
      Math.pow(toPosition.y - fromPosition.y, 2)
    );
    
    const maxPossibleDistance = (unitSpeed * timestamp) / 1000;
    return distance <= maxPossibleDistance * 1.1; // 10% tolerance
  }
}
```

## Latency Optimization
- **Client prediction** with rollback
- **Input buffering** and smoothing
- **Adaptive tick rates** based on network conditions
- **Priority queuing** for critical commands
- **Regional server deployment**

## Room Management
- Lobby system with game browser
- Skill-based matchmaking
- Spectator mode support
- Reconnection handling
- Game state persistence during disconnections

```javascript
class RoomManager {
  constructor() {
    this.activeRooms = new Map();
    this.playerQueue = [];
    this.skillRanges = {
      beginner: {min: 0, max: 500},
      intermediate: {min: 400, max: 1000},
      advanced: {min: 900, max: 1500},
      expert: {min: 1400, max: Infinity}
    };
  }
  
  findMatch(player) {
    const playerSkill = player.skillRating;
    const potentialMatches = this.playerQueue.filter(p => 
      Math.abs(p.skillRating - playerSkill) <= 200
    );
    
    if (potentialMatches.length >= 1) {
      const opponent = potentialMatches[0];
      this.createMatch([player, opponent]);
      return true;
    }
    
    this.playerQueue.push(player);
    return false;
  }
  
  handleReconnection(playerId, roomId) {
    const room = this.activeRooms.get(roomId);
    if (room && room.hasPlayer(playerId)) {
      room.reconnectPlayer(playerId);
      return room.getGameState();
    }
    return null;
  }
}
```

## Network Protocols
- **WebSocket** for reliable state updates
- **WebRTC DataChannel** for unreliable fast commands
- **HTTP** for lobby and authentication
- **Binary serialization** for state data

## Scalability Features
- Horizontal server scaling
- Load balancing across game instances
- Geographic server distribution
- Connection pooling and reuse
- Database clustering for user data

## Monitoring and Debugging
- Real-time latency measurement
- Network packet loss tracking
- Desync detection and logging
- Performance metrics collection
- Automated crash reporting

## Performance Targets
- Latency < 100ms P95
- State sync errors < 0.1%
- 8 players stable connection
- Anti-cheat detection rate > 95%
- Connection success rate > 95%