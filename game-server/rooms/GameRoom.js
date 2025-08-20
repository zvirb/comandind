const { Room } = require('colyseus');

class GameRoom extends Room {
  onCreate(options) {
    console.log('GameRoom created!', options);

    this.setState({
      players: {},
    });
  }

  onJoin(client, options) {
    console.log(client.sessionId, 'joined!');
    this.state.players[client.sessionId] = { x: 0, y: 0 };
  }

  onMessage(client, message) {
    console.log(client.sessionId, 'sent message:', message);
    this.broadcast('messages', `${client.sessionId} says: ${message}`);
  }

  onLeave(client, consented) {
    console.log(client.sessionId, 'left!');
    delete this.state.players[client.sessionId];
  }

  onDispose() {
    console.log('Disposing GameRoom...');
  }
}

module.exports = { GameRoom };
