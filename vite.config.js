import { defineConfig } from 'vite';
import path from 'path';
import { createServer } from 'net';

// Enhanced function to find available port with better error handling
const findAvailablePort = async (startPort, maxAttempts = 20) => {
  // Generate a wider range of potential ports to avoid conflicts
  const portRanges = [
    startPort, // Original port
    startPort + 1000, // +1000 offset
    startPort + 2000, // +2000 offset
    24680, 24681, 24682, 24683, 24684, // Alternative high ports
    3001, 3002, 3003, 3004, 3005, // Development alternatives
    5173, 5174, 5175, 5176, 5177 // Vite default alternatives
  ];
  
  for (const basePort of portRanges) {
    for (let i = 0; i < Math.min(maxAttempts, 5); i++) {
      const port = basePort + i;
      try {
        await new Promise((resolve, reject) => {
          const server = createServer();
          server.on('error', reject);
          server.listen(port, '127.0.0.1', () => {
            server.close(resolve);
          });
          
          // Add timeout to prevent hanging
          setTimeout(() => {
            server.close();
            reject(new Error('Port check timeout'));
          }, 1000);
        });
        console.log(`✓ Found available HMR port: ${port}`);
        return port;
      } catch (error) {
        // Port is busy or error occurred, continue to next
        continue;
      }
    }
  }
  
  // If all else fails, let Vite handle port allocation
  console.warn(`⚠️  Could not find available HMR port, letting Vite handle allocation`);
  return 0; // Let Vite auto-allocate
};

export default defineConfig(async ({ command, mode }) => {
  const isProduction = mode === 'production';
  const isDevelopment = command === 'serve';
  
  // Dynamic port allocation for HMR
  let hmrPort = 24678;
  if (isDevelopment) {
    try {
      hmrPort = await findAvailablePort(24678);
      console.log(`Using HMR port: ${hmrPort}`);
    } catch (error) {
      console.warn('Failed to find available HMR port, using default:', error.message);
    }
  }

  return {
  root: '.',
  base: '/',
  
  // Enable ES2022 to support top-level await
  esbuild: {
    target: 'es2022',
    supported: {
      'top-level-await': true
    }
  },
  
  server: {
    port: 3000,
    host: '0.0.0.0', // Allow external connections
    strictPort: false, // Allow port switching if 3000 is busy
    open: false, // Don't auto-open browser to prevent issues
    cors: true,
    
    // Enhanced Hot reload configuration with robust conflict prevention
    hmr: isDevelopment ? {
      overlay: true,
      // Let Vite automatically handle port allocation to prevent conflicts
      port: hmrPort === 0 ? undefined : hmrPort,
      host: 'localhost',
      // Don't force clientPort if auto-allocating
      clientPort: hmrPort === 0 ? undefined : hmrPort,
      // Additional HMR optimizations
      timeout: 30000, // 30 second timeout for slow connections
      // Disable port check since we handle it manually
      skipCheck: hmrPort === 0
    } : false,
    
    // Optimized watch configuration
    watch: {
      usePolling: false, // Disable polling unless on Docker/VM
      interval: 300,
      ignored: ['**/node_modules/**', '**/dist/**', '**/public/assets/cnc-extracted/**', '**/*.html']
    },
    
    // Increase timeout for slow systems
    timeout: 120000
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
    // Ensure proper module resolution
    extensions: ['.js', '.mjs', '.ts', '.json']
  },
  
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: true,
    minify: 'terser',
    
    // Enhanced build target configuration
    target: ['es2022', 'chrome89', 'firefox89', 'safari15'],
    
    // Enhanced performance options
    reportCompressedSize: false, // Faster builds
    cssCodeSplit: true, // Enable CSS code splitting
    
    // Optimize chunk size thresholds
    chunkSizeWarningLimit: 1000,
    
    terserOptions: {
      compress: {
        drop_console: false, // Keep console in development builds
        drop_debugger: true,
        pure_funcs: ['console.debug'],
      },
      mangle: {
        keep_classnames: true, // Preserve class names for debugging
        keep_fnames: true
      }
    },
    
    rollupOptions: {
      // Only build from index.html
      input: {
        main: path.resolve(__dirname, 'index.html')
      },
      output: {
        // Optimized manual chunking strategy - only chunk actually used dependencies
        manualChunks: (id) => {
          // Only chunk vendor libraries that are actually imported
          if (id.includes('node_modules')) {
            if (id.includes('pixi.js')) return 'vendor-pixi';
            if (id.includes('@tensorflow/tfjs') && !id.includes('external')) return 'vendor-ml';
            if (id.includes('matter-js') && !id.includes('external')) return 'vendor-physics';
            if (id.includes('howler') && !id.includes('external')) return 'vendor-audio';
            if (id.includes('pathfinding') && !id.includes('external')) return 'vendor-pathfinding';
            if (id.includes('colyseus') && !id.includes('external')) return 'vendor-multiplayer';
            // Group other smaller vendor libraries
            return 'vendor';
          }
          
          // Group game modules by functionality
          if (id.includes('/src/core/')) return 'game-core';
          if (id.includes('/src/ecs/')) return 'game-ecs';
          if (id.includes('/src/rendering/')) return 'game-rendering';
          if (id.includes('/src/pathfinding/')) return 'game-pathfinding';
          if (id.includes('/src/utils/')) return 'game-utils';
        },
        // Optimize chunk file naming
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      },
      // Enhanced external dependencies configuration
      external: (id) => {
        // Node.js built-in modules
        const nodeBuiltins = ['fs', 'path', 'events', 'http', 'https', 'net', 'tls', 
                            'crypto', 'stream', 'util', 'dns', 'os', 'child_process'];
        if (nodeBuiltins.some(builtin => id === builtin || id.startsWith(builtin + '/'))) {
          return true;
        }
        
        // Server-only dependencies
        const serverOnly = ['colyseus', 'ollama', '@colyseus/core', '@pm2/io', 
                          'express', 'socket.io', 'ws', 'node:*'];
        if (serverOnly.some(dep => id === dep || id.startsWith(dep + '/'))) {
          return true;
        }
        
        // Large binary assets and workers
        if (id.includes('.wasm') || id.includes('.worker.js') || 
            id.includes('.worker.ts') || id.endsWith('?worker')) {
          return true;
        }
        
        return false;
      }
    }
  },
  
  optimizeDeps: {
    // Pre-bundle these dependencies for faster dev server startup
    include: [
      'pixi.js',
      'matter-js',
      'howler',
      'pathfinding',
      '@tensorflow/tfjs'
    ],
    // Exclude problematic dependencies
    exclude: [
      'colyseus',
      'ollama',
      '@colyseus/core',
      '@pm2/io'
    ],
    // Force ESM for compatibility
    needsInterop: [],
    esbuildOptions: {
      target: 'es2022'
    }
  },
  
  // Enhanced environment variable handling
  define: {
    'process.env.NODE_ENV': JSON.stringify(mode),
    '__DEV__': JSON.stringify(isDevelopment),
    '__PROD__': JSON.stringify(isProduction),
    '__HMR_PORT__': JSON.stringify(hmrPort),
    // Prevent global process object issues in browser
    'process.platform': JSON.stringify('browser'),
    'process.version': JSON.stringify('browser')
  },
  
  // Plugin configuration
  plugins: [],
  
  // CSS configuration
  css: {
    devSourcemap: true
  },
  
  // Preview server configuration (for build testing)
  preview: {
    port: 4173,
    host: '0.0.0.0',
    strictPort: false,
    cors: true
  },
  
  // Enhanced worker configuration
  worker: {
    format: 'es',
    plugins: () => [],
    rollupOptions: {
      output: {
        format: 'es',
        entryFileNames: 'assets/worker-[name]-[hash].js'
      }
    }
  },
  
  // Enhanced logging configuration
  logLevel: isDevelopment ? 'info' : 'warn',
  clearScreen: false, // Keep terminal history
  
  // Enhanced experimental features
  experimental: {
    renderBuiltUrl: (filename, { hostType }) => {
      if (hostType === 'js') {
        return { js: `/${filename}` };
      }
      return `/${filename}`;
    }
  }
};
});