import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  root: '.',
  base: '/',
  mode: 'production',
  
  // Production ES2022 target for optimal performance
  esbuild: {
    target: 'es2022',
    supported: {
      'top-level-await': true
    },
    drop: ['console', 'debugger'],
    minify: true
  },
  
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@core': path.resolve(__dirname, './src/core'),
      '@rendering': path.resolve(__dirname, './src/rendering'),
      '@gameplay': path.resolve(__dirname, './src/gameplay'),
      '@assets': path.resolve(__dirname, './public/assets'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@ecs': path.resolve(__dirname, './src/ecs'),
      '@pathfinding': path.resolve(__dirname, './src/pathfinding')
    },
    extensions: ['.js', '.mjs', '.ts', '.json']
  },
  
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false, // Disable sourcemaps in production
    minify: 'terser',
    
    // Aggressive optimization for production
    target: ['es2022', 'chrome89', 'firefox89', 'safari15'],
    reportCompressedSize: true,
    cssCodeSplit: true,
    chunkSizeWarningLimit: 2000,
    
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info', 'console.debug'],
        passes: 2
      },
      mangle: {
        keep_classnames: false,
        keep_fnames: false
      },
      format: {
        comments: false
      }
    },
    
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html')
      },
      output: {
        // Production chunking strategy
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            if (id.includes('pixi.js')) return 'vendor-pixi';
            if (id.includes('@tensorflow/tfjs')) return 'vendor-ml';
            if (id.includes('matter-js')) return 'vendor-physics';
            if (id.includes('howler')) return 'vendor-audio';
            if (id.includes('pathfinding')) return 'vendor-pathfinding';
            return 'vendor';
          }
          
          if (id.includes('/src/core/')) return 'game-core';
          if (id.includes('/src/ecs/')) return 'game-ecs';
          if (id.includes('/src/rendering/')) return 'game-rendering';
          if (id.includes('/src/pathfinding/')) return 'game-pathfinding';
          if (id.includes('/src/utils/')) return 'game-utils';
        },
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]'
      }
    }
  },
  
  // Production environment variables
  define: {
    'process.env.NODE_ENV': '"production"',
    '__DEV__': 'false',
    '__PROD__': 'true',
    'process.platform': '"browser"',
    'process.version': '"browser"'
  },
  
  // Aggressive dependency optimization
  optimizeDeps: {
    include: [
      'pixi.js',
      'matter-js', 
      'howler',
      'pathfinding',
      '@tensorflow/tfjs'
    ],
    exclude: [
      'colyseus',
      'ollama'
    ]
  },
  
  // Production logging
  logLevel: 'warn',
  clearScreen: false
});