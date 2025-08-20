import express from 'express';
import compression from 'compression';
import cors from 'cors';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { createProxyMiddleware } from 'http-proxy-middleware';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(compression());
app.use(cors());

// Proxy API requests to backend
app.use('/api', createProxyMiddleware({
  target: process.env.API_URL || 'http://api:5000',
  changeOrigin: true,
  logLevel: 'warn',
}));

// Proxy WebSocket connections
app.use('/ws', createProxyMiddleware({
  target: process.env.WS_URL || 'ws://api:5000',
  ws: true,
  changeOrigin: true,
  logLevel: 'warn',
}));

// Health check endpoint (must be before catch-all route)
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'webui-next' });
});

// Serve static files from the dist directory
app.use(express.static(join(__dirname, 'dist')));

// Handle client-side routing (must be last)
app.get('*', (req, res) => {
  res.sendFile(join(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`WebUI Next server running on port ${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
});