import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  root: '.',
  base: '/',
  
  server: {
    port: 3000,
    host: true,
    open: true,
    cors: true,
    
    // Hot reload configuration
    hmr: {
      overlay: true,
      port: 3001
    },
    
    // Watch for changes
    watch: {
      usePolling: true,
      interval: 100
    }
  },
  
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@core': path.resolve(__dirname, './src/core'),
      '@rendering': path.resolve(__dirname, './src/rendering'),
      '@gameplay': path.resolve(__dirname, './src/gameplay'),
      '@assets': path.resolve(__dirname, './public/assets'),
      '@utils': path.resolve(__dirname, './src/utils')
    }
  },
  
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: true,
    minify: 'terser',
    
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    },
    
    rollupOptions: {
      output: {
        manualChunks: {
          'pixi': ['pixi.js'],
          'game-core': [
            './src/core/Application.js',
            './src/core/GameLoop.js',
            './src/core/Camera.js'
          ]
        }
      }
    }
  },
  
  optimizeDeps: {
    include: ['pixi.js']
  },
  
  define: {
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV)
  }
});