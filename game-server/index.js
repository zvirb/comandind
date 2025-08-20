const http = require('http');
const express = require('express');
const { Server } = require('colyseus');
const { GameRoom } = require('./rooms/GameRoom');

const port = process.env.PORT || 2567;
const app = express();

app.use(express.json());

const server = http.createServer(app);
const gameServer = new Server({
  server,
});

// Define "game" room
gameServer.define('game', GameRoom);

gameServer.listen(port);
console.log(`Listening on ws://localhost:${port}`);
