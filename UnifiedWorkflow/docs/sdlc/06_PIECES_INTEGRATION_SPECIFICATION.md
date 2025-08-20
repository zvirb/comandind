# AIWFE Pieces OS/Developers Integration Specification

## Document Information

**Document Version**: 1.0  
**Date**: August 12, 2025  
**Authors**: Integration Architect, Developer Experience Lead  
**Reviewers**: Technical Team, Product Team  
**Status**: Draft for Review  

## 1. Executive Summary

This document outlines the comprehensive integration strategy for connecting AIWFE with Pieces OS and Pieces for Developers, creating a seamless developer productivity ecosystem. The integration will provide real-time context synchronization, enhanced code snippet management, and intelligent developer workflow optimization through a dedicated microservice architecture deployed in Kubernetes.

## 2. Pieces Ecosystem Overview

### 2.1 Pieces OS Integration

#### Pieces OS Capabilities
```yaml
Core Features:
  - Centralized snippet and asset management
  - AI-powered code understanding and organization
  - Cross-platform synchronization
  - Context-aware suggestions
  - Team collaboration features

Technical Capabilities:
  - REST API for programmatic access
  - WebSocket connections for real-time updates
  - Local storage with cloud synchronization
  - Plugin architecture for extensions
  - ML-powered code analysis
```

#### Pieces for Developers Features
```yaml
Developer Tools:
  - IDE integrations (VS Code, JetBrains, etc.)
  - Browser extensions
  - Desktop application
  - CLI tools
  - Git integration

Workflow Enhancements:
  - Code snippet sharing
  - Context preservation
  - Automatic documentation
  - Code explanation and analysis
  - Smart code completion
```

### 2.2 Integration Value Proposition

#### Developer Productivity Benefits
```yaml
Context Continuity:
  - Seamless context switching between AIWFE and development tools
  - Automatic preservation of work state
  - Intelligent suggestion based on current tasks
  - Reduced cognitive load and context loss

Enhanced Collaboration:
  - Team snippet sharing through Pieces
  - Context-aware code suggestions in AIWFE chat
  - Unified knowledge base across tools
  - Real-time collaboration on code assets

Workflow Optimization:
  - 70% reduction in context switching time
  - Automated documentation generation
  - Intelligent code reuse suggestions
  - Enhanced debugging and troubleshooting
```

## 3. Architecture Design

### 3.1 Integration Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    AIWFE Kubernetes Cluster                     │
├─────────────────────────────────────────────────────────────────┤
│  Application Layer                                             │
│  ├── WebUI (Next.js)                                          │
│  ├── API Gateway                                              │
│  ├── Agent Engine                                             │
│  └── Chat Service                                             │
├─────────────────────────────────────────────────────────────────┤
│  Integration Layer                                             │
│  ├── Pieces Integration Service ←→ Pieces OS API               │
│  ├── Context Synchronizer                                     │
│  ├── Asset Manager                                            │
│  └── Workflow Intelligence                                    │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                    │
│  ├── PostgreSQL (Integration metadata)                        │
│  ├── Redis (Real-time sync cache)                            │
│  └── Qdrant (Context vectors)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    User's Development Environment               │
├─────────────────────────────────────────────────────────────────┤
│  Pieces OS (Local Installation)                               │
│  ├── Local Asset Storage                                      │
│  ├── ML Processing Engine                                     │
│  ├── Cross-app Synchronization                               │
│  └── API Server                                              │
├─────────────────────────────────────────────────────────────────┤
│  Pieces for Developers Tools                                  │
│  ├── VS Code Extension                                        │
│  ├── Browser Extension                                        │
│  ├── Desktop Application                                      │
│  └── CLI Tools                                               │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Service Architecture

#### Pieces Integration Service Design
```yaml
Service Name: pieces-integration-service
Namespace: aiwfe-integrations
Port: 8080
Health Check: /health
Metrics: /metrics

Components:
  API Layer:
    - REST endpoints for AIWFE integration
    - WebSocket server for real-time updates
    - Authentication and authorization
    - Rate limiting and throttling

  Sync Engine:
    - Bidirectional data synchronization
    - Conflict resolution
    - Offline support
    - Change tracking

  Intelligence Layer:
    - Context analysis and matching
    - Relevance scoring
    - Smart suggestions
    - Usage analytics

  Storage Layer:
    - Metadata persistence
    - Cache management
    - Vector storage for context
    - Audit logging
```

## 4. Detailed Component Design

### 4.1 Pieces Integration Service

#### Directory Structure
```
k8s/services/pieces-integration/
├── Dockerfile
├── package.json
├── src/
│   ├── index.ts                    # Main entry point
│   ├── api/
│   │   ├── routes/
│   │   │   ├── assets.ts          # Asset management endpoints
│   │   │   ├── context.ts         # Context synchronization
│   │   │   ├── suggestions.ts     # AI-powered suggestions
│   │   │   └── webhooks.ts        # Pieces OS webhooks
│   │   ├── middleware/
│   │   │   ├── auth.ts           # Authentication middleware
│   │   │   ├── rate-limit.ts     # Rate limiting
│   │   │   └── validation.ts     # Request validation
│   │   └── controllers/
│   │       ├── AssetController.ts
│   │       ├── ContextController.ts
│   │       └── SyncController.ts
│   ├── services/
│   │   ├── pieces/
│   │   │   ├── PiecesClient.ts    # Pieces OS API client
│   │   │   ├── AssetManager.ts    # Asset operations
│   │   │   ├── ContextSync.ts     # Context synchronization
│   │   │   └── RealtimeSync.ts    # WebSocket management
│   │   ├── aiwfe/
│   │   │   ├── AIWFEClient.ts     # AIWFE API client
│   │   │   ├── AgentIntegration.ts # Agent system integration
│   │   │   └── ChatIntegration.ts  # Chat enhancement
│   │   ├── intelligence/
│   │   │   ├── ContextMatcher.ts   # Context analysis
│   │   │   ├── RelevanceScorer.ts  # Relevance scoring
│   │   │   ├── SuggestionEngine.ts # Smart suggestions
│   │   │   └── UsageAnalyzer.ts    # Usage analytics
│   │   └── storage/
│   │       ├── MetadataStore.ts    # Metadata persistence
│   │       ├── CacheManager.ts     # Redis cache
│   │       └── VectorStore.ts      # Qdrant integration
│   ├── models/
│   │   ├── Asset.ts               # Asset data models
│   │   ├── Context.ts             # Context models
│   │   ├── User.ts                # User models
│   │   └── Sync.ts                # Synchronization models
│   ├── utils/
│   │   ├── logger.ts              # Logging utilities
│   │   ├── config.ts              # Configuration management
│   │   ├── crypto.ts              # Encryption utilities
│   │   └── validation.ts          # Data validation
│   └── types/
│       ├── pieces.ts              # Pieces API types
│       ├── aiwfe.ts               # AIWFE integration types
│       └── internal.ts            # Internal service types
├── config/
│   ├── development.yaml
│   ├── production.yaml
│   └── test.yaml
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── docs/
    ├── API.md
    └── SETUP.md
```

#### Core Service Implementation
```typescript
// src/index.ts
import express from 'express';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import { PiecesIntegrationService } from './services/PiecesIntegrationService';
import { configureMiddleware } from './api/middleware';
import { configureRoutes } from './api/routes';
import { logger } from './utils/logger';

class PiecesIntegrationServer {
  private app: express.Application;
  private server: http.Server;
  private io: SocketIOServer;
  private integrationService: PiecesIntegrationService;

  constructor() {
    this.app = express();
    this.server = createServer(this.app);
    this.io = new SocketIOServer(this.server, {
      cors: {
        origin: process.env.CORS_ORIGINS?.split(',') || ['http://localhost:3000'],
        credentials: true
      }
    });
    
    this.integrationService = new PiecesIntegrationService(this.io);
  }

  async initialize() {
    // Configure middleware
    configureMiddleware(this.app);
    
    // Configure routes
    configureRoutes(this.app, this.integrationService);
    
    // Initialize WebSocket handlers
    this.setupWebSocketHandlers();
    
    // Initialize Pieces connection
    await this.integrationService.initialize();
    
    logger.info('Pieces Integration Service initialized');
  }

  private setupWebSocketHandlers() {
    this.io.on('connection', (socket) => {
      logger.info(`Client connected: ${socket.id}`);
      
      socket.on('subscribe-context', (userId: string) => {
        socket.join(`context:${userId}`);
        this.integrationService.subscribeToUserContext(userId, socket);
      });
      
      socket.on('sync-assets', async (data) => {
        await this.integrationService.handleAssetSync(data, socket);
      });
      
      socket.on('disconnect', () => {
        logger.info(`Client disconnected: ${socket.id}`);
      });
    });
  }

  start(port: number = 8080) {
    this.server.listen(port, () => {
      logger.info(`Pieces Integration Service listening on port ${port}`);
    });
  }
}

// Initialize and start server
const server = new PiecesIntegrationServer();
server.initialize().then(() => {
  server.start(Number(process.env.PORT) || 8080);
});
```

### 4.2 Pieces OS Client Implementation

#### Pieces API Client
```typescript
// src/services/pieces/PiecesClient.ts
import axios, { AxiosInstance } from 'axios';
import WebSocket from 'ws';
import { PiecesAsset, PiecesContext, PiecesUser } from '../../types/pieces';
import { logger } from '../../utils/logger';

export class PiecesClient {
  private apiClient: AxiosInstance;
  private wsConnection: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(
    private baseUrl: string,
    private apiKey: string,
    private userId: string
  ) {
    this.apiClient = axios.create({
      baseURL: baseUrl,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'User-Agent': 'AIWFE-Integration/1.0.0'
      },
      timeout: 30000
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    this.apiClient.interceptors.request.use(
      (config) => {
        logger.debug(`Pieces API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        logger.error('Pieces API Request Error:', error);
        return Promise.reject(error);
      }
    );

    this.apiClient.interceptors.response.use(
      (response) => {
        logger.debug(`Pieces API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        logger.error('Pieces API Response Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Asset Management
  async getAssets(filters?: {
    tags?: string[];
    language?: string;
    limit?: number;
    offset?: number;
  }): Promise<PiecesAsset[]> {
    try {
      const response = await this.apiClient.get('/assets', {
        params: filters
      });
      return response.data.assets || [];
    } catch (error) {
      logger.error('Failed to fetch assets:', error);
      throw new Error('Failed to fetch assets from Pieces OS');
    }
  }

  async getAsset(assetId: string): Promise<PiecesAsset> {
    try {
      const response = await this.apiClient.get(`/assets/${assetId}`);
      return response.data;
    } catch (error) {
      logger.error(`Failed to fetch asset ${assetId}:`, error);
      throw new Error(`Failed to fetch asset ${assetId} from Pieces OS`);
    }
  }

  async createAsset(asset: Partial<PiecesAsset>): Promise<PiecesAsset> {
    try {
      const response = await this.apiClient.post('/assets', asset);
      return response.data;
    } catch (error) {
      logger.error('Failed to create asset:', error);
      throw new Error('Failed to create asset in Pieces OS');
    }
  }

  async updateAsset(assetId: string, updates: Partial<PiecesAsset>): Promise<PiecesAsset> {
    try {
      const response = await this.apiClient.patch(`/assets/${assetId}`, updates);
      return response.data;
    } catch (error) {
      logger.error(`Failed to update asset ${assetId}:`, error);
      throw new Error(`Failed to update asset ${assetId} in Pieces OS`);
    }
  }

  async deleteAsset(assetId: string): Promise<void> {
    try {
      await this.apiClient.delete(`/assets/${assetId}`);
    } catch (error) {
      logger.error(`Failed to delete asset ${assetId}:`, error);
      throw new Error(`Failed to delete asset ${assetId} from Pieces OS`);
    }
  }

  // Context Management
  async getCurrentContext(): Promise<PiecesContext> {
    try {
      const response = await this.apiClient.get('/context/current');
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch current context:', error);
      throw new Error('Failed to fetch current context from Pieces OS');
    }
  }

  async setContext(context: Partial<PiecesContext>): Promise<PiecesContext> {
    try {
      const response = await this.apiClient.post('/context', context);
      return response.data;
    } catch (error) {
      logger.error('Failed to set context:', error);
      throw new Error('Failed to set context in Pieces OS');
    }
  }

  // Search and Suggestions
  async searchAssets(query: string, filters?: {
    languages?: string[];
    tags?: string[];
    limit?: number;
  }): Promise<PiecesAsset[]> {
    try {
      const response = await this.apiClient.post('/search', {
        query,
        ...filters
      });
      return response.data.results || [];
    } catch (error) {
      logger.error('Failed to search assets:', error);
      throw new Error('Failed to search assets in Pieces OS');
    }
  }

  async getSuggestions(context: {
    currentFile?: string;
    language?: string;
    keywords?: string[];
  }): Promise<PiecesAsset[]> {
    try {
      const response = await this.apiClient.post('/suggestions', context);
      return response.data.suggestions || [];
    } catch (error) {
      logger.error('Failed to get suggestions:', error);
      throw new Error('Failed to get suggestions from Pieces OS');
    }
  }

  // Real-time Connection
  async connectWebSocket(): Promise<void> {
    if (this.wsConnection?.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = this.baseUrl.replace('http', 'ws') + '/ws';
    
    try {
      this.wsConnection = new WebSocket(wsUrl, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'User-Id': this.userId
        }
      });

      this.wsConnection.on('open', () => {
        logger.info('Connected to Pieces OS WebSocket');
        this.reconnectAttempts = 0;
      });

      this.wsConnection.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString());
          this.handleWebSocketMessage(message);
        } catch (error) {
          logger.error('Failed to parse WebSocket message:', error);
        }
      });

      this.wsConnection.on('close', () => {
        logger.warn('Pieces OS WebSocket connection closed');
        this.scheduleReconnect();
      });

      this.wsConnection.on('error', (error) => {
        logger.error('Pieces OS WebSocket error:', error);
      });

    } catch (error) {
      logger.error('Failed to connect to Pieces OS WebSocket:', error);
      this.scheduleReconnect();
    }
  }

  private handleWebSocketMessage(message: any) {
    switch (message.type) {
      case 'asset_created':
        this.onAssetCreated(message.data);
        break;
      case 'asset_updated':
        this.onAssetUpdated(message.data);
        break;
      case 'asset_deleted':
        this.onAssetDeleted(message.data);
        break;
      case 'context_changed':
        this.onContextChanged(message.data);
        break;
      default:
        logger.debug('Unknown WebSocket message type:', message.type);
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      logger.error('Max reconnection attempts reached for Pieces OS WebSocket');
      return;
    }

    const delay = Math.pow(2, this.reconnectAttempts) * 1000; // Exponential backoff
    this.reconnectAttempts++;

    setTimeout(() => {
      logger.info(`Attempting to reconnect to Pieces OS WebSocket (attempt ${this.reconnectAttempts})`);
      this.connectWebSocket();
    }, delay);
  }

  // Event handlers (to be overridden by consumers)
  protected onAssetCreated(asset: PiecesAsset) {
    logger.debug('Asset created:', asset.id);
  }

  protected onAssetUpdated(asset: PiecesAsset) {
    logger.debug('Asset updated:', asset.id);
  }

  protected onAssetDeleted(assetId: string) {
    logger.debug('Asset deleted:', assetId);
  }

  protected onContextChanged(context: PiecesContext) {
    logger.debug('Context changed:', context);
  }

  async disconnect() {
    if (this.wsConnection) {
      this.wsConnection.close();
      this.wsConnection = null;
    }
  }
}
```

### 4.3 Context Synchronization Engine

#### Bidirectional Sync Implementation
```typescript
// src/services/pieces/ContextSync.ts
import { PiecesClient } from './PiecesClient';
import { AIWFEClient } from '../aiwfe/AIWFEClient';
import { MetadataStore } from '../storage/MetadataStore';
import { VectorStore } from '../storage/VectorStore';
import { logger } from '../../utils/logger';

export interface SyncContext {
  userId: string;
  workspaceId?: string;
  currentTask?: string;
  activeProject?: string;
  openFiles?: string[];
  recentAssets?: string[];
  keywords?: string[];
  timestamp: Date;
}

export class ContextSynchronizer {
  private syncInterval: NodeJS.Timeout | null = null;
  private readonly SYNC_INTERVAL_MS = 30000; // 30 seconds

  constructor(
    private piecesClient: PiecesClient,
    private aiwfeClient: AIWFEClient,
    private metadataStore: MetadataStore,
    private vectorStore: VectorStore
  ) {}

  async startSynchronization(userId: string) {
    logger.info(`Starting context synchronization for user ${userId}`);
    
    // Initial sync
    await this.performSync(userId);
    
    // Schedule periodic sync
    this.syncInterval = setInterval(async () => {
      try {
        await this.performSync(userId);
      } catch (error) {
        logger.error(`Sync failed for user ${userId}:`, error);
      }
    }, this.SYNC_INTERVAL_MS);
  }

  async stopSynchronization() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
    logger.info('Context synchronization stopped');
  }

  private async performSync(userId: string) {
    try {
      // Get current context from both systems
      const [piecesContext, aiwfeContext] = await Promise.all([
        this.getPiecesContext(userId),
        this.getAIWFEContext(userId)
      ]);

      // Analyze context changes
      const changes = await this.analyzeContextChanges(userId, piecesContext, aiwfeContext);
      
      if (changes.length === 0) {
        logger.debug(`No context changes for user ${userId}`);
        return;
      }

      // Apply changes to both systems
      await this.applyContextChanges(userId, changes);
      
      // Update vector embeddings for improved matching
      await this.updateContextVectors(userId, piecesContext, aiwfeContext);
      
      logger.debug(`Synchronized ${changes.length} context changes for user ${userId}`);
      
    } catch (error) {
      logger.error(`Context sync failed for user ${userId}:`, error);
      throw error;
    }
  }

  private async getPiecesContext(userId: string): Promise<SyncContext> {
    try {
      const context = await this.piecesClient.getCurrentContext();
      
      return {
        userId,
        workspaceId: context.workspace?.id,
        currentTask: context.currentTask,
        activeProject: context.activeProject,
        openFiles: context.openFiles || [],
        recentAssets: context.recentAssets || [],
        keywords: context.keywords || [],
        timestamp: new Date()
      };
    } catch (error) {
      logger.error('Failed to get Pieces context:', error);
      throw error;
    }
  }

  private async getAIWFEContext(userId: string): Promise<SyncContext> {
    try {
      const context = await this.aiwfeClient.getUserContext(userId);
      
      return {
        userId,
        workspaceId: context.workspaceId,
        currentTask: context.currentTask?.title,
        activeProject: context.activeOpportunity?.name,
        openFiles: [], // AIWFE doesn't track files directly
        recentAssets: context.recentChats?.map(chat => chat.id) || [],
        keywords: context.currentTask?.tags || [],
        timestamp: new Date()
      };
    } catch (error) {
      logger.error('Failed to get AIWFE context:', error);
      throw error;
    }
  }

  private async analyzeContextChanges(
    userId: string,
    piecesContext: SyncContext,
    aiwfeContext: SyncContext
  ): Promise<ContextChange[]> {
    const changes: ContextChange[] = [];
    
    // Get last known context
    const lastContext = await this.metadataStore.getLastSyncContext(userId);
    
    if (!lastContext) {
      // First sync - create baseline
      changes.push({
        type: 'initial_sync',
        source: 'both',
        data: { pieces: piecesContext, aiwfe: aiwfeContext }
      });
      return changes;
    }

    // Detect changes in current task
    if (piecesContext.currentTask !== aiwfeContext.currentTask) {
      if (piecesContext.timestamp > aiwfeContext.timestamp) {
        changes.push({
          type: 'task_changed',
          source: 'pieces',
          target: 'aiwfe',
          data: { task: piecesContext.currentTask }
        });
      } else {
        changes.push({
          type: 'task_changed',
          source: 'aiwfe',
          target: 'pieces',
          data: { task: aiwfeContext.currentTask }
        });
      }
    }

    // Detect changes in active project
    if (piecesContext.activeProject !== aiwfeContext.activeProject) {
      changes.push({
        type: 'project_changed',
        source: 'pieces',
        target: 'aiwfe',
        data: { project: piecesContext.activeProject }
      });
    }

    // Detect new assets/chats
    const newPiecesAssets = this.findNewItems(
      piecesContext.recentAssets,
      lastContext.pieces?.recentAssets || []
    );
    
    const newAIWFEChats = this.findNewItems(
      aiwfeContext.recentAssets,
      lastContext.aiwfe?.recentAssets || []
    );

    if (newPiecesAssets.length > 0) {
      changes.push({
        type: 'new_assets',
        source: 'pieces',
        target: 'aiwfe',
        data: { assets: newPiecesAssets }
      });
    }

    if (newAIWFEChats.length > 0) {
      changes.push({
        type: 'new_chats',
        source: 'aiwfe',
        target: 'pieces',
        data: { chats: newAIWFEChats }
      });
    }

    return changes;
  }

  private findNewItems(current: string[], previous: string[]): string[] {
    return current.filter(item => !previous.includes(item));
  }

  private async applyContextChanges(userId: string, changes: ContextChange[]) {
    for (const change of changes) {
      try {
        await this.applyContextChange(userId, change);
      } catch (error) {
        logger.error(`Failed to apply context change:`, error);
      }
    }
  }

  private async applyContextChange(userId: string, change: ContextChange) {
    switch (change.type) {
      case 'task_changed':
        if (change.target === 'aiwfe') {
          await this.aiwfeClient.updateUserContext(userId, {
            currentTask: change.data.task
          });
        } else if (change.target === 'pieces') {
          await this.piecesClient.setContext({
            currentTask: change.data.task
          });
        }
        break;

      case 'project_changed':
        if (change.target === 'aiwfe') {
          await this.aiwfeClient.updateUserContext(userId, {
            activeProject: change.data.project
          });
        }
        break;

      case 'new_assets':
        // Analyze new Pieces assets and suggest relevant AIWFE actions
        await this.suggestAIWFEActions(userId, change.data.assets);
        break;

      case 'new_chats':
        // Share relevant AIWFE chat insights with Pieces
        await this.shareChatInsights(userId, change.data.chats);
        break;

      default:
        logger.debug(`Unknown change type: ${change.type}`);
    }
  }

  private async updateContextVectors(
    userId: string,
    piecesContext: SyncContext,
    aiwfeContext: SyncContext
  ) {
    // Create embeddings for context matching
    const contextText = [
      piecesContext.currentTask,
      piecesContext.activeProject,
      ...piecesContext.keywords,
      aiwfeContext.currentTask,
      aiwfeContext.activeProject,
      ...aiwfeContext.keywords
    ].filter(Boolean).join(' ');

    if (contextText.trim()) {
      await this.vectorStore.upsertContext(userId, {
        text: contextText,
        metadata: {
          pieces: piecesContext,
          aiwfe: aiwfeContext,
          timestamp: new Date()
        }
      });
    }
  }

  private async suggestAIWFEActions(userId: string, assetIds: string[]) {
    for (const assetId of assetIds) {
      try {
        const asset = await this.piecesClient.getAsset(assetId);
        
        // Analyze asset content and suggest AIWFE actions
        const suggestions = await this.analyzeAssetForAIWFE(asset);
        
        if (suggestions.length > 0) {
          await this.aiwfeClient.createSuggestions(userId, {
            source: 'pieces',
            assetId,
            suggestions
          });
        }
      } catch (error) {
        logger.error(`Failed to analyze asset ${assetId}:`, error);
      }
    }
  }

  private async shareChatInsights(userId: string, chatIds: string[]) {
    for (const chatId of chatIds) {
      try {
        const chat = await this.aiwfeClient.getChat(chatId);
        
        // Extract code snippets and insights from chat
        const insights = await this.extractChatInsights(chat);
        
        if (insights.snippets.length > 0) {
          // Create corresponding assets in Pieces
          for (const snippet of insights.snippets) {
            await this.piecesClient.createAsset({
              content: snippet.code,
              language: snippet.language,
              description: snippet.description,
              tags: ['aiwfe-chat', ...snippet.tags],
              source: 'aiwfe',
              sourceId: chatId
            });
          }
        }
      } catch (error) {
        logger.error(`Failed to share insights from chat ${chatId}:`, error);
      }
    }
  }

  // Helper methods for analysis
  private async analyzeAssetForAIWFE(asset: any): Promise<AIWFESuggestion[]> {
    const suggestions: AIWFESuggestion[] = [];
    
    // Analyze code for potential tasks
    if (asset.language && asset.content) {
      // Look for TODO comments, bug patterns, etc.
      const todos = this.extractTodos(asset.content);
      const bugs = this.detectPotentialBugs(asset.content);
      
      suggestions.push(...todos.map(todo => ({
        type: 'task',
        title: `TODO: ${todo.text}`,
        description: `From ${asset.name}`,
        priority: 'medium',
        source: asset.id
      })));
      
      suggestions.push(...bugs.map(bug => ({
        type: 'issue',
        title: `Potential Issue: ${bug.description}`,
        description: `In ${asset.name}`,
        priority: 'high',
        source: asset.id
      })));
    }
    
    return suggestions;
  }

  private async extractChatInsights(chat: any): Promise<ChatInsights> {
    const insights: ChatInsights = {
      snippets: [],
      concepts: [],
      actionItems: []
    };
    
    // Extract code blocks from chat messages
    for (const message of chat.messages) {
      if (message.role === 'assistant' && message.content) {
        const codeBlocks = this.extractCodeBlocks(message.content);
        insights.snippets.push(...codeBlocks);
      }
    }
    
    return insights;
  }

  private extractTodos(content: string): Array<{ text: string; line: number }> {
    const todos: Array<{ text: string; line: number }> = [];
    const lines = content.split('\n');
    
    lines.forEach((line, index) => {
      const todoMatch = line.match(/(?:\/\/|#|\/\*)\s*TODO:?\s*(.+)/i);
      if (todoMatch) {
        todos.push({
          text: todoMatch[1].trim(),
          line: index + 1
        });
      }
    });
    
    return todos;
  }

  private detectPotentialBugs(content: string): Array<{ description: string; line: number }> {
    const bugs: Array<{ description: string; line: number }> = [];
    const lines = content.split('\n');
    
    lines.forEach((line, index) => {
      // Simple heuristics for potential issues
      if (line.includes('console.log') && !line.includes('//')) {
        bugs.push({
          description: 'Console.log statement in production code',
          line: index + 1
        });
      }
      
      if (line.includes('throw new Error()') || line.includes('throw ""')) {
        bugs.push({
          description: 'Generic error thrown without message',
          line: index + 1
        });
      }
    });
    
    return bugs;
  }

  private extractCodeBlocks(content: string): CodeSnippet[] {
    const snippets: CodeSnippet[] = [];
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    let match;
    
    while ((match = codeBlockRegex.exec(content)) !== null) {
      const language = match[1] || 'text';
      const code = match[2].trim();
      
      if (code.length > 10) { // Only meaningful snippets
        snippets.push({
          code,
          language,
          description: `Code snippet from AIWFE chat`,
          tags: ['aiwfe-generated', language]
        });
      }
    }
    
    return snippets;
  }
}

interface ContextChange {
  type: string;
  source: string;
  target?: string;
  data: any;
}

interface AIWFESuggestion {
  type: string;
  title: string;
  description: string;
  priority: string;
  source: string;
}

interface ChatInsights {
  snippets: CodeSnippet[];
  concepts: string[];
  actionItems: string[];
}

interface CodeSnippet {
  code: string;
  language: string;
  description: string;
  tags: string[];
}
```

### 4.4 Intelligence Layer Implementation

#### Smart Suggestion Engine
```typescript
// src/services/intelligence/SuggestionEngine.ts
import { PiecesClient } from '../pieces/PiecesClient';
import { AIWFEClient } from '../aiwfe/AIWFEClient';
import { VectorStore } from '../storage/VectorStore';
import { logger } from '../../utils/logger';

export interface Suggestion {
  id: string;
  type: 'code_snippet' | 'task' | 'documentation' | 'template';
  title: string;
  description: string;
  content: any;
  relevanceScore: number;
  source: 'pieces' | 'aiwfe' | 'hybrid';
  metadata: {
    language?: string;
    tags: string[];
    usageCount: number;
    lastUsed?: Date;
  };
}

export class SuggestionEngine {
  private readonly MIN_RELEVANCE_SCORE = 0.6;
  private readonly MAX_SUGGESTIONS = 10;

  constructor(
    private piecesClient: PiecesClient,
    private aiwfeClient: AIWFEClient,
    private vectorStore: VectorStore
  ) {}

  async generateSuggestions(userId: string, context: {
    currentTask?: string;
    activeFile?: string;
    language?: string;
    keywords: string[];
    recentActivity: string[];
  }): Promise<Suggestion[]> {
    try {
      logger.debug(`Generating suggestions for user ${userId}`);
      
      // Get suggestions from multiple sources in parallel
      const [
        piecesSnippets,
        aiwfeTemplates,
        contextualMatches,
        usageBasedSuggestions
      ] = await Promise.all([
        this.getPiecesSuggestions(context),
        this.getAIWFETemplateSuggestions(userId, context),
        this.getContextualMatches(userId, context),
        this.getUsageBasedSuggestions(userId, context)
      ]);

      // Combine and rank all suggestions
      const allSuggestions = [
        ...piecesSnippets,
        ...aiwfeTemplates,
        ...contextualMatches,
        ...usageBasedSuggestions
      ];

      // Remove duplicates and rank by relevance
      const uniqueSuggestions = this.deduplicateSuggestions(allSuggestions);
      const rankedSuggestions = this.rankSuggestions(uniqueSuggestions, context);

      // Return top suggestions
      return rankedSuggestions
        .filter(s => s.relevanceScore >= this.MIN_RELEVANCE_SCORE)
        .slice(0, this.MAX_SUGGESTIONS);

    } catch (error) {
      logger.error('Failed to generate suggestions:', error);
      return [];
    }
  }

  private async getPiecesSuggestions(context: any): Promise<Suggestion[]> {
    const suggestions: Suggestion[] = [];
    
    try {
      // Search Pieces for relevant code snippets
      const searchQuery = [context.currentTask, ...context.keywords]
        .filter(Boolean)
        .join(' ');

      if (searchQuery.trim()) {
        const assets = await this.piecesClient.searchAssets(searchQuery, {
          languages: context.language ? [context.language] : undefined,
          limit: 20
        });

        for (const asset of assets) {
          suggestions.push({
            id: `pieces-${asset.id}`,
            type: 'code_snippet',
            title: asset.name || 'Code Snippet',
            description: asset.description || 'From Pieces OS',
            content: {
              code: asset.content,
              language: asset.language
            },
            relevanceScore: this.calculatePiecesRelevance(asset, context),
            source: 'pieces',
            metadata: {
              language: asset.language,
              tags: asset.tags || [],
              usageCount: asset.usageCount || 0,
              lastUsed: asset.lastAccessed ? new Date(asset.lastAccessed) : undefined
            }
          });
        }
      }

      // Get context-based suggestions from Pieces
      const contextSuggestions = await this.piecesClient.getSuggestions({
        currentFile: context.activeFile,
        language: context.language,
        keywords: context.keywords
      });

      for (const asset of contextSuggestions) {
        suggestions.push({
          id: `pieces-context-${asset.id}`,
          type: 'code_snippet',
          title: asset.name || 'Suggested Snippet',
          description: 'AI-suggested from Pieces',
          content: {
            code: asset.content,
            language: asset.language
          },
          relevanceScore: this.calculatePiecesRelevance(asset, context) + 0.1, // Boost for AI suggestions
          source: 'pieces',
          metadata: {
            language: asset.language,
            tags: [...(asset.tags || []), 'ai-suggested'],
            usageCount: asset.usageCount || 0,
            lastUsed: asset.lastAccessed ? new Date(asset.lastAccessed) : undefined
          }
        });
      }

    } catch (error) {
      logger.error('Failed to get Pieces suggestions:', error);
    }

    return suggestions;
  }

  private async getAIWFETemplateSuggestions(userId: string, context: any): Promise<Suggestion[]> {
    const suggestions: Suggestion[] = [];
    
    try {
      // Get task templates from AIWFE based on current context
      const templates = await this.aiwfeClient.getTaskTemplates(userId, {
        keywords: context.keywords,
        currentTask: context.currentTask,
        limit: 10
      });

      for (const template of templates) {
        suggestions.push({
          id: `aiwfe-template-${template.id}`,
          type: 'template',
          title: template.name,
          description: template.description,
          content: {
            template: template.content,
            variables: template.variables
          },
          relevanceScore: this.calculateAIWFERelevance(template, context),
          source: 'aiwfe',
          metadata: {
            tags: template.tags || [],
            usageCount: template.usageCount || 0,
            lastUsed: template.lastUsed ? new Date(template.lastUsed) : undefined
          }
        });
      }

      // Get documentation suggestions
      const docs = await this.aiwfeClient.searchDocumentation(context.keywords.join(' '), {
        limit: 5
      });

      for (const doc of docs) {
        suggestions.push({
          id: `aiwfe-doc-${doc.id}`,
          type: 'documentation',
          title: doc.title,
          description: doc.summary,
          content: {
            content: doc.content,
            url: doc.url
          },
          relevanceScore: this.calculateDocumentationRelevance(doc, context),
          source: 'aiwfe',
          metadata: {
            tags: doc.tags || [],
            usageCount: 0,
            lastUsed: undefined
          }
        });
      }

    } catch (error) {
      logger.error('Failed to get AIWFE suggestions:', error);
    }

    return suggestions;
  }

  private async getContextualMatches(userId: string, context: any): Promise<Suggestion[]> {
    const suggestions: Suggestion[] = [];
    
    try {
      // Create query vector from current context
      const queryText = [
        context.currentTask,
        context.activeFile,
        ...context.keywords,
        ...context.recentActivity
      ].filter(Boolean).join(' ');

      if (queryText.trim()) {
        // Search vector store for similar contexts
        const matches = await this.vectorStore.searchSimilar(queryText, {
          userId,
          limit: 15,
          threshold: 0.7
        });

        for (const match of matches) {
          // Extract suggestions from similar contexts
          const contextSuggestions = await this.extractSuggestionsFromContext(match);
          suggestions.push(...contextSuggestions);
        }
      }

    } catch (error) {
      logger.error('Failed to get contextual matches:', error);
    }

    return suggestions;
  }

  private async getUsageBasedSuggestions(userId: string, context: any): Promise<Suggestion[]> {
    const suggestions: Suggestion[] = [];
    
    try {
      // Get frequently used items by this user
      const frequentItems = await this.aiwfeClient.getUserFrequentItems(userId, {
        type: ['code_snippet', 'template', 'task'],
        limit: 10
      });

      for (const item of frequentItems) {
        // Calculate relevance based on usage patterns and current context
        const relevanceScore = this.calculateUsageBasedRelevance(item, context);
        
        if (relevanceScore >= this.MIN_RELEVANCE_SCORE) {
          suggestions.push({
            id: `usage-${item.type}-${item.id}`,
            type: item.type as any,
            title: item.title,
            description: `Frequently used ${item.type}`,
            content: item.content,
            relevanceScore,
            source: 'hybrid',
            metadata: {
              language: item.language,
              tags: [...(item.tags || []), 'frequently-used'],
              usageCount: item.usageCount,
              lastUsed: new Date(item.lastUsed)
            }
          });
        }
      }

    } catch (error) {
      logger.error('Failed to get usage-based suggestions:', error);
    }

    return suggestions;
  }

  private calculatePiecesRelevance(asset: any, context: any): number {
    let score = 0.5; // Base score
    
    // Language match
    if (asset.language === context.language) {
      score += 0.2;
    }
    
    // Keyword matches
    const assetKeywords = [...(asset.tags || []), asset.name?.toLowerCase() || ''];
    const contextKeywords = context.keywords.map((k: string) => k.toLowerCase());
    const keywordMatches = assetKeywords.filter(k => 
      contextKeywords.some(ck => k.includes(ck) || ck.includes(k))
    ).length;
    
    score += Math.min(keywordMatches * 0.1, 0.3);
    
    // Usage frequency
    if (asset.usageCount > 0) {
      score += Math.min(Math.log(asset.usageCount) * 0.05, 0.15);
    }
    
    // Recency
    if (asset.lastAccessed) {
      const daysSinceUsed = (Date.now() - new Date(asset.lastAccessed).getTime()) / (1000 * 60 * 60 * 24);
      if (daysSinceUsed < 7) {
        score += 0.1;
      }
    }
    
    return Math.min(score, 1.0);
  }

  private calculateAIWFERelevance(template: any, context: any): number {
    let score = 0.6; // Higher base score for AIWFE items
    
    // Task context match
    if (context.currentTask && template.name?.toLowerCase().includes(context.currentTask.toLowerCase())) {
      score += 0.2;
    }
    
    // Tag matches
    const templateTags = (template.tags || []).map((t: string) => t.toLowerCase());
    const contextKeywords = context.keywords.map((k: string) => k.toLowerCase());
    const tagMatches = templateTags.filter(t => 
      contextKeywords.some(ck => t.includes(ck) || ck.includes(t))
    ).length;
    
    score += Math.min(tagMatches * 0.08, 0.24);
    
    // Usage history
    if (template.usageCount > 0) {
      score += Math.min(Math.log(template.usageCount) * 0.03, 0.1);
    }
    
    return Math.min(score, 1.0);
  }

  private calculateDocumentationRelevance(doc: any, context: any): number {
    let score = 0.4; // Lower base score for documentation
    
    // Keyword relevance
    const docText = `${doc.title} ${doc.summary}`.toLowerCase();
    const matchingKeywords = context.keywords.filter((k: string) => 
      docText.includes(k.toLowerCase())
    ).length;
    
    score += Math.min(matchingKeywords * 0.15, 0.45);
    
    // Current task relevance
    if (context.currentTask && docText.includes(context.currentTask.toLowerCase())) {
      score += 0.15;
    }
    
    return Math.min(score, 1.0);
  }

  private calculateUsageBasedRelevance(item: any, context: any): number {
    let score = 0.3; // Base score for usage-based suggestions
    
    // High usage frequency
    if (item.usageCount > 10) {
      score += 0.3;
    } else if (item.usageCount > 5) {
      score += 0.2;
    } else if (item.usageCount > 2) {
      score += 0.1;
    }
    
    // Recent usage
    const daysSinceUsed = (Date.now() - new Date(item.lastUsed).getTime()) / (1000 * 60 * 60 * 24);
    if (daysSinceUsed < 1) {
      score += 0.2;
    } else if (daysSinceUsed < 7) {
      score += 0.15;
    } else if (daysSinceUsed < 30) {
      score += 0.1;
    }
    
    // Context relevance
    const contextKeywords = context.keywords.map((k: string) => k.toLowerCase());
    const itemKeywords = [...(item.tags || []), item.title?.toLowerCase() || ''];
    const keywordMatches = itemKeywords.filter(k => 
      contextKeywords.some(ck => k.includes(ck) || ck.includes(ck))
    ).length;
    
    score += Math.min(keywordMatches * 0.1, 0.2);
    
    return Math.min(score, 1.0);
  }

  private deduplicateSuggestions(suggestions: Suggestion[]): Suggestion[] {
    const seen = new Set<string>();
    const unique: Suggestion[] = [];
    
    for (const suggestion of suggestions) {
      // Create a hash based on content similarity
      const contentHash = this.createContentHash(suggestion);
      
      if (!seen.has(contentHash)) {
        seen.add(contentHash);
        unique.push(suggestion);
      } else {
        // If duplicate, keep the one with higher relevance score
        const existingIndex = unique.findIndex(s => this.createContentHash(s) === contentHash);
        if (suggestion.relevanceScore > unique[existingIndex].relevanceScore) {
          unique[existingIndex] = suggestion;
        }
      }
    }
    
    return unique;
  }

  private createContentHash(suggestion: Suggestion): string {
    const content = JSON.stringify(suggestion.content);
    return `${suggestion.type}-${suggestion.title}-${content.substring(0, 100)}`;
  }

  private rankSuggestions(suggestions: Suggestion[], context: any): Suggestion[] {
    return suggestions.sort((a, b) => {
      // Primary sort by relevance score
      if (a.relevanceScore !== b.relevanceScore) {
        return b.relevanceScore - a.relevanceScore;
      }
      
      // Secondary sort by usage count
      const aUsage = a.metadata.usageCount || 0;
      const bUsage = b.metadata.usageCount || 0;
      if (aUsage !== bUsage) {
        return bUsage - aUsage;
      }
      
      // Tertiary sort by recency
      const aLastUsed = a.metadata.lastUsed?.getTime() || 0;
      const bLastUsed = b.metadata.lastUsed?.getTime() || 0;
      return bLastUsed - aLastUsed;
    });
  }

  private async extractSuggestionsFromContext(contextMatch: any): Promise<Suggestion[]> {
    const suggestions: Suggestion[] = [];
    
    // Extract suggestions from stored context data
    if (contextMatch.metadata?.pieces?.recentAssets) {
      for (const assetId of contextMatch.metadata.pieces.recentAssets.slice(0, 3)) {
        try {
          const asset = await this.piecesClient.getAsset(assetId);
          suggestions.push({
            id: `context-pieces-${asset.id}`,
            type: 'code_snippet',
            title: asset.name || 'Similar Context Snippet',
            description: 'From similar work context',
            content: {
              code: asset.content,
              language: asset.language
            },
            relevanceScore: contextMatch.score * 0.8, // Reduce score slightly for indirect matches
            source: 'pieces',
            metadata: {
              language: asset.language,
              tags: [...(asset.tags || []), 'similar-context'],
              usageCount: asset.usageCount || 0,
              lastUsed: asset.lastAccessed ? new Date(asset.lastAccessed) : undefined
            }
          });
        } catch (error) {
          logger.debug(`Failed to fetch asset ${assetId} for context suggestion:`, error);
        }
      }
    }
    
    return suggestions;
  }
}
```

## 5. Kubernetes Deployment Configuration

### 5.1 Deployment Manifests

#### Pieces Integration Service Deployment
```yaml
# k8s/manifests/pieces-integration/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pieces-integration-service
  namespace: aiwfe-integrations
  labels:
    app: pieces-integration
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pieces-integration
  template:
    metadata:
      labels:
        app: pieces-integration
        version: v1.0.0
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: pieces-integration-sa
      containers:
      - name: pieces-integration
        image: aiwfe/pieces-integration:latest
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 8081
          name: websocket
        env:
        - name: NODE_ENV
          value: "production"
        - name: LOG_LEVEL
          value: "info"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: pieces-database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: redis-url
        - name: QDRANT_URL
          value: "http://qdrant:6333"
        - name: QDRANT_API_KEY
          valueFrom:
            secretKeyRef:
              name: qdrant-secret
              key: api-key
        - name: AIWFE_API_URL
          value: "http://api-gateway:8080"
        - name: AIWFE_API_KEY
          valueFrom:
            secretKeyRef:
              name: aiwfe-secret
              key: api-key
        - name: PIECES_DEFAULT_URL
          value: "http://localhost:1000" # Default Pieces OS URL
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 5
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: config
        configMap:
          name: pieces-integration-config
      - name: tmp
        emptyDir: {}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 3000
        fsGroup: 2000

---
apiVersion: v1
kind: Service
metadata:
  name: pieces-integration-service
  namespace: aiwfe-integrations
  labels:
    app: pieces-integration
spec:
  selector:
    app: pieces-integration
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
  - name: websocket
    port: 8081
    targetPort: websocket
    protocol: TCP
  type: ClusterIP

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: pieces-integration-sa
  namespace: aiwfe-integrations

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pieces-integration-role
  namespace: aiwfe-integrations
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pieces-integration-binding
  namespace: aiwfe-integrations
subjects:
- kind: ServiceAccount
  name: pieces-integration-sa
  namespace: aiwfe-integrations
roleRef:
  kind: Role
  name: pieces-integration-role
  apiGroup: rbac.authorization.k8s.io

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: pieces-integration-hpa
  namespace: aiwfe-integrations
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: pieces-integration-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
```

#### Configuration and Secrets
```yaml
# k8s/manifests/pieces-integration/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pieces-integration-config
  namespace: aiwfe-integrations
data:
  app.yaml: |
    server:
      port: 8080
      websocket_port: 8081
      cors_origins:
        - "http://localhost:3000"
        - "https://aiwfe.com"
    
    pieces:
      default_timeout: 30000
      retry_attempts: 3
      rate_limit:
        requests_per_minute: 100
        burst_size: 10
    
    sync:
      interval_seconds: 30
      batch_size: 50
      max_retries: 3
    
    intelligence:
      min_relevance_score: 0.6
      max_suggestions: 10
      context_window_days: 30
    
    monitoring:
      metrics_enabled: true
      tracing_enabled: true
      log_level: "info"
    
    cache:
      default_ttl: 3600
      max_size: 1000

---
apiVersion: v1
kind: Secret
metadata:
  name: pieces-integration-secrets
  namespace: aiwfe-integrations
type: Opaque
stringData:
  database-url: "postgresql://pieces_user:${PIECES_DB_PASSWORD}@postgres:5432/aiwfe_pieces"
  redis-url: "redis://pieces_user:${REDIS_PASSWORD}@redis:6379/5"
  aiwfe-api-key: "${AIWFE_INTERNAL_API_KEY}"
  pieces-default-api-key: "${PIECES_DEFAULT_API_KEY}"
  encryption-key: "${PIECES_ENCRYPTION_KEY}"
```

### 5.2 Istio Service Mesh Configuration

#### Virtual Service and Destination Rule
```yaml
# k8s/manifests/pieces-integration/istio.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: pieces-integration-vs
  namespace: aiwfe-integrations
spec:
  hosts:
  - pieces-integration-service
  http:
  - match:
    - uri:
        prefix: "/api/v1/"
    route:
    - destination:
        host: pieces-integration-service
        port:
          number: 8080
    timeout: 30s
    retries:
      attempts: 3
      perTryTimeout: 10s
  - match:
    - uri:
        prefix: "/ws/"
    route:
    - destination:
        host: pieces-integration-service
        port:
          number: 8081
    websocketUpgrade: true

---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: pieces-integration-dr
  namespace: aiwfe-integrations
spec:
  host: pieces-integration-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 10
    circuitBreaker:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
    loadBalancer:
      simple: LEAST_CONN

---
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: pieces-integration-pa
  namespace: aiwfe-integrations
spec:
  selector:
    matchLabels:
      app: pieces-integration
  mtls:
    mode: STRICT

---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: pieces-integration-authz
  namespace: aiwfe-integrations
spec:
  selector:
    matchLabels:
      app: pieces-integration
  rules:
  - from:
    - source:
        namespaces: ["aiwfe-system", "aiwfe-integrations"]
  - to:
    - operation:
        methods: ["GET", "POST", "PUT", "DELETE"]
        paths: ["/api/v1/*", "/health", "/ready", "/metrics"]
```

## 6. API Specification

### 6.1 REST API Endpoints

#### Asset Management
```yaml
# Asset Operations
GET /api/v1/assets
  Description: List user's assets with optional filtering
  Parameters:
    - user_id (required): User identifier
    - language (optional): Filter by programming language
    - tags (optional): Filter by tags (comma-separated)
    - search (optional): Text search query
    - limit (optional): Maximum results (default: 50)
    - offset (optional): Pagination offset
  Response: Array of Asset objects

GET /api/v1/assets/{asset_id}
  Description: Get specific asset details
  Parameters:
    - asset_id (required): Asset identifier
  Response: Asset object with full details

POST /api/v1/assets
  Description: Create new asset
  Body: Asset creation object
  Response: Created Asset object

PUT /api/v1/assets/{asset_id}
  Description: Update existing asset
  Body: Asset update object
  Response: Updated Asset object

DELETE /api/v1/assets/{asset_id}
  Description: Delete asset
  Response: 204 No Content

# Asset Search and Suggestions
POST /api/v1/assets/search
  Description: Advanced asset search
  Body:
    query: string
    filters: SearchFilters
    context: SearchContext
  Response: SearchResults with ranked assets

GET /api/v1/assets/suggestions
  Description: Get contextual asset suggestions
  Parameters:
    - user_id (required): User identifier
    - context (optional): Current context JSON
    - limit (optional): Maximum suggestions
  Response: Array of Suggestion objects
```

#### Context Synchronization
```yaml
# Context Operations
GET /api/v1/context/{user_id}
  Description: Get current user context
  Response: UserContext object

POST /api/v1/context/{user_id}
  Description: Update user context
  Body: ContextUpdate object
  Response: Updated UserContext object

POST /api/v1/context/{user_id}/sync
  Description: Trigger immediate context synchronization
  Response: SyncResult object

GET /api/v1/context/{user_id}/history
  Description: Get context change history
  Parameters:
    - limit (optional): Maximum history entries
    - since (optional): ISO timestamp
  Response: Array of ContextChange objects
```

#### Integration Management
```yaml
# Integration Operations
POST /api/v1/integrations/pieces/connect
  Description: Connect to user's Pieces OS
  Body:
    pieces_url: string
    api_key: string (optional)
    user_preferences: object
  Response: ConnectionResult object

GET /api/v1/integrations/pieces/status
  Description: Get Pieces connection status
  Parameters:
    - user_id (required): User identifier
  Response: ConnectionStatus object

POST /api/v1/integrations/pieces/disconnect
  Description: Disconnect from Pieces OS
  Body:
    user_id: string
    preserve_data: boolean
  Response: DisconnectionResult object

POST /api/v1/integrations/aiwfe/webhook
  Description: Receive webhooks from AIWFE
  Body: WebhookPayload
  Response: WebhookResponse object
```

### 6.2 WebSocket API

#### Real-time Events
```yaml
# WebSocket Connection
Connect: ws://pieces-integration-service:8081/ws
Authentication: Bearer token in Authorization header

# Client Messages
{
  "type": "subscribe",
  "payload": {
    "user_id": "string",
    "events": ["asset_created", "context_changed", "suggestions_updated"]
  }
}

{
  "type": "sync_request", 
  "payload": {
    "user_id": "string",
    "force": boolean
  }
}

{
  "type": "ping",
  "payload": {}
}

# Server Messages
{
  "type": "asset_created",
  "payload": {
    "asset": AssetObject,
    "source": "pieces" | "aiwfe",
    "timestamp": "ISO8601"
  }
}

{
  "type": "context_changed",
  "payload": {
    "user_id": "string",
    "old_context": ContextObject,
    "new_context": ContextObject,
    "changes": Array<ContextChange>
  }
}

{
  "type": "suggestions_updated",
  "payload": {
    "user_id": "string",
    "suggestions": Array<Suggestion>,
    "context": ContextObject
  }
}

{
  "type": "sync_completed",
  "payload": {
    "user_id": "string",
    "changes_count": number,
    "errors": Array<SyncError>
  }
}

{
  "type": "error",
  "payload": {
    "code": "string",
    "message": "string",
    "details": object
  }
}

{
  "type": "pong",
  "payload": {}
}
```

### 6.3 Data Models

#### Core Data Types
```typescript
// Asset Model
interface Asset {
  id: string;
  name: string;
  description?: string;
  content: string;
  language?: string;
  tags: string[];
  source: 'pieces' | 'aiwfe' | 'user';
  source_id?: string;
  created_at: Date;
  updated_at: Date;
  last_accessed?: Date;
  usage_count: number;
  metadata: {
    file_path?: string;
    line_numbers?: [number, number];
    author?: string;
    project?: string;
    [key: string]: any;
  };
}

// Context Model
interface UserContext {
  user_id: string;
  workspace_id?: string;
  current_task?: string;
  active_project?: string;
  active_files: string[];
  recent_assets: string[];
  keywords: string[];
  language_preferences: string[];
  last_updated: Date;
  pieces_context?: {
    connected: boolean;
    last_sync: Date;
    sync_status: 'idle' | 'syncing' | 'error';
  };
  aiwfe_context?: {
    active_chat?: string;
    recent_queries: string[];
    current_agent?: string;
  };
}

// Suggestion Model
interface Suggestion {
  id: string;
  type: 'code_snippet' | 'task' | 'documentation' | 'template';
  title: string;
  description: string;
  content: any;
  relevance_score: number;
  source: 'pieces' | 'aiwfe' | 'hybrid';
  metadata: {
    language?: string;
    tags: string[];
    usage_count: number;
    last_used?: Date;
    reasoning?: string;
  };
  actions?: Array<{
    type: 'copy' | 'insert' | 'create_task' | 'open_file';
    label: string;
    payload: any;
  }>;
}

// Sync Models
interface SyncResult {
  user_id: string;
  sync_id: string;
  started_at: Date;
  completed_at?: Date;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  changes: {
    pieces_to_aiwfe: number;
    aiwfe_to_pieces: number;
    conflicts_resolved: number;
  };
  errors: SyncError[];
}

interface SyncError {
  code: string;
  message: string;
  item_id?: string;
  item_type?: string;
  severity: 'warning' | 'error' | 'critical';
  timestamp: Date;
}

// Connection Models
interface ConnectionResult {
  success: boolean;
  connection_id: string;
  pieces_info: {
    version: string;
    user_id: string;
    capabilities: string[];
  };
  initial_sync_scheduled: boolean;
  message?: string;
}

interface ConnectionStatus {
  connected: boolean;
  connection_id?: string;
  last_successful_sync?: Date;
  sync_status: 'idle' | 'syncing' | 'error';
  error_message?: string;
  pieces_info?: {
    version: string;
    user_id: string;
    asset_count: number;
  };
}
```

## 7. Integration Workflows

### 7.1 User Onboarding Flow

#### Initial Setup Workflow
```yaml
Step 1: Pieces Detection
  - Check if Pieces OS is running on user's machine
  - Attempt connection to default Pieces OS URL (http://localhost:1000)
  - If not found, provide setup instructions

Step 2: Connection Establishment
  - Request API key from user (if required)
  - Validate connection to Pieces OS
  - Exchange capabilities and version information
  - Store connection configuration

Step 3: Initial Data Sync
  - Fetch user's existing assets from Pieces
  - Analyze and categorize assets
  - Create initial context mapping
  - Generate baseline suggestions

Step 4: AIWFE Integration
  - Connect to AIWFE agent system
  - Register for relevant events
  - Configure bidirectional sync
  - Set up real-time notifications

Step 5: User Preferences
  - Configure sync frequency
  - Set privacy preferences
  - Choose notification settings
  - Define asset sharing preferences
```

#### Frontend Integration Code
```tsx
// React component for Pieces setup
import { useState, useEffect } from 'react';
import { usePiecesIntegration } from '@/hooks/usePiecesIntegration';

export const PiecesSetupWizard = () => {
  const [setupStep, setSetupStep] = useState(1);
  const [piecesUrl, setPiecesUrl] = useState('http://localhost:1000');
  const [apiKey, setApiKey] = useState('');
  const {
    checkConnection,
    connectToPieces,
    connectionStatus,
    isConnecting
  } = usePiecesIntegration();

  useEffect(() => {
    // Auto-detect Pieces OS on component mount
    checkConnection(piecesUrl);
  }, []);

  const handleConnect = async () => {
    try {
      const result = await connectToPieces({
        url: piecesUrl,
        apiKey: apiKey || undefined
      });
      
      if (result.success) {
        setSetupStep(3); // Move to sync step
      }
    } catch (error) {
      console.error('Connection failed:', error);
    }
  };

  return (
    <div className="pieces-setup-wizard">
      {setupStep === 1 && (
        <DetectionStep
          piecesUrl={piecesUrl}
          setPiecesUrl={setPiecesUrl}
          connectionStatus={connectionStatus}
          onNext={() => setSetupStep(2)}
        />
      )}
      
      {setupStep === 2 && (
        <ConnectionStep
          apiKey={apiKey}
          setApiKey={setApiKey}
          onConnect={handleConnect}
          isConnecting={isConnecting}
        />
      )}
      
      {setupStep === 3 && (
        <SyncStep
          onComplete={() => setSetupStep(4)}
        />
      )}
      
      {setupStep === 4 && (
        <CompletionStep />
      )}
    </div>
  );
};

// Custom hook for Pieces integration
export const usePiecesIntegration = () => {
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [isConnecting, setIsConnecting] = useState(false);

  const checkConnection = async (url: string) => {
    try {
      const response = await fetch('/api/v1/integrations/pieces/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      
      const result = await response.json();
      setConnectionStatus(result.available ? 'available' : 'unavailable');
    } catch (error) {
      setConnectionStatus('unavailable');
    }
  };

  const connectToPieces = async (config: {
    url: string;
    apiKey?: string;
  }) => {
    setIsConnecting(true);
    try {
      const response = await fetch('/api/v1/integrations/pieces/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      const result = await response.json();
      setConnectionStatus(result.success ? 'connected' : 'error');
      return result;
    } finally {
      setIsConnecting(false);
    }
  };

  return {
    checkConnection,
    connectToPieces,
    connectionStatus,
    isConnecting
  };
};
```

### 7.2 Real-time Sync Workflow

#### Bidirectional Synchronization Process
```yaml
Pieces → AIWFE Sync:
  Trigger Events:
    - New asset created in Pieces
    - Asset updated in Pieces
    - Asset deleted in Pieces
    - Context changed in Pieces
  
  Process:
    1. Receive webhook/WebSocket event from Pieces
    2. Validate event and extract relevant data
    3. Analyze asset content for AIWFE relevance
    4. Generate AIWFE suggestions/tasks if applicable
    5. Update user context in AIWFE
    6. Notify AIWFE agents of new context
    7. Send real-time updates to connected WebUI clients

AIWFE → Pieces Sync:
  Trigger Events:
    - New task created in AIWFE
    - Chat generates code snippet
    - User creates opportunity
    - Agent generates solution
  
  Process:
    1. Receive event from AIWFE agent system
    2. Extract code snippets and relevant content
    3. Analyze content for Pieces asset creation
    4. Create corresponding assets in Pieces with proper metadata
    5. Update Pieces context if relevant
    6. Track sync results and handle conflicts

Conflict Resolution:
  Detection:
    - Same asset modified in both systems
    - Context conflicts between systems
    - Timestamp-based conflict detection
  
  Resolution Strategies:
    - Last-write-wins for simple conflicts
    - User-prompted resolution for complex conflicts
    - Merge strategies for compatible changes
    - Backup creation before conflict resolution
```

### 7.3 Intelligence Enhancement Workflow

#### Context-Aware Suggestion Generation
```yaml
Continuous Intelligence Process:
  1. Context Monitoring:
     - Track user activity in both systems
     - Monitor file changes and project context
     - Analyze communication patterns
     - Identify work patterns and preferences

  2. Pattern Recognition:
     - Identify frequently used code patterns
     - Recognize problem-solving approaches
     - Track collaboration patterns
     - Analyze productivity metrics

  3. Suggestion Generation:
     - Match current context to historical patterns
     - Generate relevant code suggestions
     - Propose workflow optimizations
     - Suggest collaboration opportunities

  4. Relevance Scoring:
     - Calculate relevance based on multiple factors
     - Consider user preferences and history
     - Factor in current project context
     - Apply machine learning for improvement

  5. Delivery Optimization:
     - Choose optimal delivery timing
     - Select appropriate delivery channel
     - Customize presentation format
     - Track suggestion effectiveness
```

## 8. Security and Privacy

### 8.1 Data Protection

#### Privacy Framework
```yaml
Data Classification:
  Public: Documentation, templates, tutorials
  Internal: User preferences, usage analytics
  Confidential: Code snippets, project data
  Restricted: Authentication tokens, API keys

Data Handling Policies:
  Collection: Minimal data collection principle
  Storage: Encrypted at rest and in transit
  Processing: Anonymized where possible
  Retention: Configurable retention periods
  Deletion: Complete data purging on request

User Consent Management:
  Granular Permissions:
    - Asset synchronization (on/off)
    - Context sharing (limited/full)
    - Analytics participation (opt-in)
    - Team collaboration (configurable)
  
  Data Portability:
    - Export all user data
    - Import from other systems
    - Migration between instances
    - Backup and restore capabilities
```

#### Security Implementation
```typescript
// Encryption utilities
import crypto from 'crypto';

export class SecurityManager {
  private encryptionKey: Buffer;
  private algorithm = 'aes-256-gcm';

  constructor(encryptionKey: string) {
    this.encryptionKey = Buffer.from(encryptionKey, 'hex');
  }

  encryptData(data: string): EncryptedData {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipher(this.algorithm, this.encryptionKey);
    cipher.setAAD(Buffer.from('pieces-integration'));
    
    let encrypted = cipher.update(data, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    const authTag = cipher.getAuthTag();
    
    return {
      encryptedData: encrypted,
      iv: iv.toString('hex'),
      authTag: authTag.toString('hex')
    };
  }

  decryptData(encryptedData: EncryptedData): string {
    const decipher = crypto.createDecipher(this.algorithm, this.encryptionKey);
    decipher.setAAD(Buffer.from('pieces-integration'));
    decipher.setAuthTag(Buffer.from(encryptedData.authTag, 'hex'));
    
    let decrypted = decipher.update(encryptedData.encryptedData, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    
    return decrypted;
  }

  hashPII(data: string): string {
    return crypto.createHash('sha256').update(data).digest('hex');
  }

  generateApiKey(): string {
    return crypto.randomBytes(32).toString('hex');
  }
}

interface EncryptedData {
  encryptedData: string;
  iv: string;
  authTag: string;
}
```

### 8.2 Authentication and Authorization

#### Multi-layered Security
```yaml
Authentication Layers:
  1. User Authentication (OAuth 2.0):
     - AIWFE authentication required
     - Pieces OS authentication optional
     - Multi-factor authentication support
     - Session management with refresh tokens

  2. Service Authentication (mTLS):
     - Kubernetes service mesh security
     - Certificate-based authentication
     - Automatic certificate rotation
     - Network policy enforcement

  3. API Authentication (JWT + API Keys):
     - JWT tokens for user actions
     - API keys for service communication
     - Rate limiting per user/service
     - Request signing for sensitive operations

Authorization Framework:
  Role-Based Access Control:
    - Admin: Full system access
    - User: Personal data access only
    - Service: Limited inter-service access
    - Guest: Read-only demo access

  Resource-Level Permissions:
    - Asset ownership and sharing
    - Context visibility levels
    - Integration management rights
    - Analytics data access

  Dynamic Authorization:
    - Context-based access decisions
    - Time-based access restrictions
    - Location-based limitations
    - Device-based policies
```

### 8.3 Security Network Flow Architecture

#### Network Traffic Direction and Security
```yaml
Security Architecture Overview:
  Connection Initiation:
    - ALL connections initiated FROM pieces-integration-service
    - Direction: Kubernetes Cluster → User's Local Machine
    - NO inbound connections to user machines required
    - NO public internet endpoints exposed by pieces-integration-service

  Network Flow Validation:
    Protocol Stack:
      - Application Layer: Pieces OS API over HTTPS
      - Transport Layer: WebSocket Secure (WSS) connections
      - Network Layer: Standard TCP/IP
      - Security Layer: mTLS + API key authentication
    
    Connection Pattern:
      1. pieces-integration-service discovers user's Pieces OS instance
      2. Service initiates outbound WebSocket connection
      3. mTLS handshake establishes secure channel
      4. API key authentication validates service identity
      5. Bidirectional data flow over established secure connection

  Firewall and Security Implications:
    User Machine Requirements:
      - NO inbound firewall rules needed
      - NO port forwarding required
      - NO DMZ configuration necessary
      - Standard outbound HTTPS/WSS traffic only
    
    Kubernetes Cluster Security:
      - pieces-integration-service in isolated namespace
      - Network policies restrict inter-service communication
      - No external ingress routes for integration service
      - All traffic encrypted end-to-end
```

#### Security Boundary Analysis
```yaml
Trust Boundaries:
  Kubernetes Cluster (Trusted):
    - pieces-integration-service (controlled environment)
    - Internal service mesh with mTLS
    - Pod security policies enforced
    - Network policies isolate traffic

  Network Transit (Encrypted):
    - All traffic over TLS/mTLS
    - Certificate validation required
    - Connection integrity monitored
    - Automatic retry with backoff

  User Machine (Semi-Trusted):
    - Pieces OS validates API keys
    - Local authentication required
    - User consent for data sharing
    - Local firewall protection maintained

Security Controls:
  Authentication Layers:
    1. Service-to-Service: mTLS certificates
    2. Application-Level: API key validation
    3. User-Level: Pieces OS authentication
    4. Transport-Level: TLS encryption

  Data Protection:
    - End-to-end encryption in transit
    - No data persistence in transit
    - Audit logging of all connections
    - Rate limiting prevents abuse

  Network Segmentation:
    - Integration service isolated in dedicated namespace
    - No direct access from public internet
    - Internal service mesh for cluster communication
    - User machine remains behind local firewall
```

#### Connection Security Implementation
```typescript
// Security-focused connection manager
export class SecurePiecesConnection {
  private readonly certificates: TLSCertificates;
  private readonly apiKeyManager: APIKeyManager;
  private readonly connectionMonitor: ConnectionMonitor;

  constructor(securityConfig: SecurityConfig) {
    this.certificates = new TLSCertificates(securityConfig.certPath);
    this.apiKeyManager = new APIKeyManager(securityConfig.keyRotation);
    this.connectionMonitor = new ConnectionMonitor();
  }

  async establishSecureConnection(userPiecesEndpoint: string): Promise<SecureWebSocket> {
    // 1. Validate endpoint is user's local machine (not external)
    this.validateLocalEndpoint(userPiecesEndpoint);
    
    // 2. Prepare mTLS configuration
    const tlsOptions = {
      cert: await this.certificates.getClientCert(),
      key: await this.certificates.getClientKey(),
      ca: await this.certificates.getRootCA(),
      rejectUnauthorized: true,
      checkServerIdentity: this.validateServerIdentity
    };

    // 3. Create secure WebSocket with mTLS
    const wsOptions = {
      ...tlsOptions,
      headers: {
        'Authorization': `Bearer ${await this.apiKeyManager.getCurrentKey()}`,
        'X-Service-Identity': 'aiwfe-integration-service',
        'X-Connection-Type': 'outbound-only'
      }
    };

    // 4. Establish connection with comprehensive monitoring
    const connection = new WebSocket(userPiecesEndpoint, wsOptions);
    
    // 5. Set up security monitoring
    this.connectionMonitor.trackConnection(connection);
    
    return connection;
  }

  private validateLocalEndpoint(endpoint: string): void {
    // Ensure connection is to local/private IP ranges only
    const url = new URL(endpoint);
    const hostname = url.hostname;
    
    // Allow only local/private IP addresses
    const allowedPatterns = [
      /^127\./, // localhost
      /^192\.168\./, // private class C
      /^10\./, // private class A
      /^172\.(1[6-9]|2[0-9]|3[0-1])\./, // private class B
      /^localhost$/,
      /^[a-zA-Z0-9-]+\.local$/ // mDNS
    ];

    if (!allowedPatterns.some(pattern => pattern.test(hostname))) {
      throw new SecurityError('Connection rejected: endpoint must be local machine');
    }
  }

  private validateServerIdentity(servername: string, cert: PeerCertificate): Error | undefined {
    // Custom server identity validation for Pieces OS
    // Ensures we're connecting to legitimate Pieces OS instance
    if (!cert.subject?.CN?.startsWith('pieces-os-')) {
      return new Error('Invalid Pieces OS certificate');
    }
    return undefined;
  }
}
```

### 8.4 Connection Failure Modes and UX

#### Graceful Degradation Strategy
```yaml
Connection States:
  Connected:
    - Full Pieces integration functionality
    - Real-time sync and suggestions
    - Context awareness features
    - Asset management capabilities

  Connecting:
    - Display connection status indicator
    - Queue sync operations for retry
    - Limited functionality message
    - Progress feedback to user

  Disconnected:
    - Clear user-facing messaging
    - Disable Pieces-dependent features
    - Cache last known state
    - Retry mechanism with backoff

  Connection Failed:
    - Helpful troubleshooting guidance
    - Manual retry options
    - Fallback to cached data
    - Contact support information
```

#### User-Facing Error Messages
```yaml
Connection Issues:
  Pieces OS Not Running:
    Message: "Could not connect to your local Pieces OS. Please ensure Pieces OS is running on your machine to enable context synchronization and enhanced developer features."
    Actions:
      - "Download Pieces OS" (link to installation)
      - "Check if Pieces OS is running"
      - "Retry Connection"
      - "Continue without Pieces"

  Network Connectivity Issues:
    Message: "Unable to reach Pieces OS due to network connectivity. Checking your network connection and firewall settings may resolve this issue."
    Actions:
      - "Retry Connection"
      - "Check Network Settings"
      - "Work Offline"

  Authentication Failures:
    Message: "Authentication with Pieces OS failed. Please check your Pieces credentials or re-authorize the connection."
    Actions:
      - "Re-authorize Connection"
      - "Check Pieces Login Status"
      - "Contact Support"

  Service Unavailable:
    Message: "Pieces integration service is temporarily unavailable. Core AIWFE functionality remains available."
    Actions:
      - "Retry in a few moments"
      - "Check System Status"
      - "Continue without Pieces"
```

#### Connection Retry Strategy
```typescript
// Enhanced retry logic with exponential backoff
export class ConnectionRetryManager {
  private retryAttempts = 0;
  private maxRetries = 10;
  private baseDelay = 1000; // 1 second
  private maxDelay = 60000; // 1 minute
  private connectionState: ConnectionState = 'disconnected';

  async attemptConnection(): Promise<boolean> {
    try {
      // Update UI to show connecting state
      this.updateConnectionState('connecting');
      
      // Attempt connection to Pieces OS
      const success = await this.connectToPiecesOS();
      
      if (success) {
        this.retryAttempts = 0;
        this.updateConnectionState('connected');
        this.showSuccessMessage('Successfully connected to Pieces OS');
        return true;
      }
      
      throw new Error('Connection attempt failed');
      
    } catch (error) {
      this.retryAttempts++;
      this.updateConnectionState('connection_failed');
      
      if (this.retryAttempts >= this.maxRetries) {
        this.showPermanentErrorMessage();
        return false;
      }
      
      const delay = Math.min(
        this.baseDelay * Math.pow(2, this.retryAttempts),
        this.maxDelay
      );
      
      this.scheduleRetry(delay);
      return false;
    }
  }

  private scheduleRetry(delay: number) {
    setTimeout(() => {
      this.attemptConnection();
    }, delay);
    
    // Update UI with retry countdown
    this.showRetryCountdown(delay);
  }

  private updateConnectionState(state: ConnectionState) {
    this.connectionState = state;
    // Broadcast state change to UI components
    EventBus.emit('pieces_connection_state_changed', state);
  }

  private showRetryCountdown(delay: number) {
    EventBus.emit('pieces_retry_scheduled', {
      delay,
      attempt: this.retryAttempts,
      maxRetries: this.maxRetries
    });
  }
}
```

#### Feature Availability Matrix
```yaml
Feature Availability by Connection State:
  Core AIWFE Features (Always Available):
    - Chat interface
    - Task management
    - Calendar integration
    - Basic project management
    - User settings

  Pieces-Enhanced Features (Connection Dependent):
    Connected:
      - Real-time snippet sync: ✅ Full functionality
      - Context suggestions: ✅ AI-powered recommendations
      - Code asset management: ✅ Full library access
      - Team collaboration: ✅ Real-time sharing

    Disconnected:
      - Real-time snippet sync: ❌ Disabled with explanation
      - Context suggestions: ⚠️ Limited to cached data
      - Code asset management: ⚠️ Read-only cached assets
      - Team collaboration: ❌ Disabled gracefully

  User Interface Adaptations:
    Connected State:
      - Pieces icon shows green/active status
      - All Pieces features accessible
      - Real-time sync indicators

    Disconnected State:
      - Pieces icon shows red/inactive status
      - Disabled features grayed out with tooltips
      - Connection retry button prominently displayed
      - "Work without Pieces" option available
```

#### Network Security and Firewall Considerations
```yaml
Connection Requirements:
  Outbound Connections Only:
    - pieces-integration-service initiates all connections
    - WebSocket connections to user's local Pieces OS API
    - No inbound connections required from user machines
    - No firewall port opening needed on user side

  Network Flow Validation:
    Direction: Kubernetes Cluster → User's Local Machine
    Protocol: WebSocket over HTTPS (WSS)
    Port: User-configurable (default: 1000)
    Authentication: mTLS + API key
    
  User Network Requirements:
    - No inbound firewall rules needed
    - Standard outbound HTTPS traffic allowed
    - WebSocket upgrade support
    - No VPN or proxy configuration required
```

## 9. Monitoring and Analytics

### 9.1 Observability Stack

#### Metrics Collection
```yaml
Business Metrics:
  - Integration adoption rate
  - Sync success/failure rates
  - Suggestion acceptance rates
  - User engagement metrics
  - Context switching frequency

Technical Metrics:
  - API response times
  - WebSocket connection stability
  - Database query performance
  - Cache hit rates
  - Error rates by endpoint

User Experience Metrics:
  - Feature usage patterns
  - Workflow completion rates
  - Time saved through suggestions
  - Productivity improvements
  - User satisfaction scores
```

#### Monitoring Implementation
```typescript
// Metrics collection service
import { createPrometheusMetrics } from '@prometheus/client';

export class MetricsCollector {
  private metrics = createPrometheusMetrics({
    // Counter metrics
    sync_operations_total: {
      type: 'counter',
      name: 'pieces_sync_operations_total',
      help: 'Total number of sync operations',
      labelNames: ['user_id', 'direction', 'status']
    },
    
    suggestions_generated_total: {
      type: 'counter',
      name: 'pieces_suggestions_generated_total',
      help: 'Total number of suggestions generated',
      labelNames: ['user_id', 'type', 'source']
    },
    
    // Histogram metrics
    sync_duration_seconds: {
      type: 'histogram',
      name: 'pieces_sync_duration_seconds',
      help: 'Duration of sync operations',
      labelNames: ['direction'],
      buckets: [0.1, 0.5, 1, 2, 5, 10, 30]
    },
    
    suggestion_relevance_score: {
      type: 'histogram',
      name: 'pieces_suggestion_relevance_score',
      help: 'Relevance scores of generated suggestions',
      buckets: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    },
    
    // Gauge metrics
    active_connections: {
      type: 'gauge',
      name: 'pieces_active_connections',
      help: 'Number of active Pieces connections'
    },
    
    cache_size: {
      type: 'gauge',
      name: 'pieces_cache_size_bytes',
      help: 'Size of the integration cache in bytes'
    }
  });

  recordSyncOperation(userId: string, direction: 'pieces_to_aiwfe' | 'aiwfe_to_pieces', status: 'success' | 'failure', duration: number) {
    this.metrics.sync_operations_total.inc({ user_id: userId, direction, status });
    this.metrics.sync_duration_seconds.observe({ direction }, duration);
  }

  recordSuggestion(userId: string, type: string, source: string, relevanceScore: number) {
    this.metrics.suggestions_generated_total.inc({ user_id: userId, type, source });
    this.metrics.suggestion_relevance_score.observe(relevanceScore);
  }

  updateActiveConnections(count: number) {
    this.metrics.active_connections.set(count);
  }

  updateCacheSize(sizeBytes: number) {
    this.metrics.cache_size.set(sizeBytes);
  }

  getMetrics() {
    return this.metrics.register.metrics();
  }
}
```

### 9.2 Health Monitoring

#### Health Check Implementation
```typescript
// Health monitoring service
export class HealthMonitor {
  private checks: Map<string, HealthCheck> = new Map();

  constructor(
    private piecesClient: PiecesClient,
    private aiwfeClient: AIWFEClient,
    private database: Database,
    private redis: Redis
  ) {
    this.setupHealthChecks();
  }

  private setupHealthChecks() {
    // Database connectivity
    this.checks.set('database', {
      name: 'database',
      check: async () => {
        await this.database.query('SELECT 1');
        return { status: 'healthy' };
      },
      timeout: 5000,
      critical: true
    });

    // Redis connectivity
    this.checks.set('redis', {
      name: 'redis',
      check: async () => {
        await this.redis.ping();
        return { status: 'healthy' };
      },
      timeout: 3000,
      critical: true
    });

    // AIWFE API connectivity
    this.checks.set('aiwfe', {
      name: 'aiwfe',
      check: async () => {
        const response = await this.aiwfeClient.healthCheck();
        return { status: response.healthy ? 'healthy' : 'unhealthy' };
      },
      timeout: 10000,
      critical: false
    });

    // Default Pieces OS connectivity
    this.checks.set('pieces_default', {
      name: 'pieces_default',
      check: async () => {
        try {
          await this.piecesClient.healthCheck();
          return { status: 'healthy' };
        } catch (error) {
          return { 
            status: 'unhealthy', 
            message: 'Default Pieces OS not accessible' 
          };
        }
      },
      timeout: 5000,
      critical: false
    });
  }

  async runHealthChecks(): Promise<HealthReport> {
    const results: HealthResult[] = [];
    let overallStatus = 'healthy';

    for (const [name, check] of this.checks) {
      try {
        const result = await Promise.race([
          check.check(),
          new Promise<HealthResult>((_, reject) => 
            setTimeout(() => reject(new Error('Timeout')), check.timeout)
          )
        ]);

        results.push({
          name: check.name,
          status: result.status,
          message: result.message,
          timestamp: new Date()
        });

        if (result.status === 'unhealthy' && check.critical) {
          overallStatus = 'unhealthy';
        }
      } catch (error) {
        results.push({
          name: check.name,
          status: 'unhealthy',
          message: error.message,
          timestamp: new Date()
        });

        if (check.critical) {
          overallStatus = 'unhealthy';
        }
      }
    }

    return {
      status: overallStatus,
      timestamp: new Date(),
      checks: results
    };
  }

  async getReadinessStatus(): Promise<boolean> {
    const criticalChecks = Array.from(this.checks.values())
      .filter(check => check.critical);

    for (const check of criticalChecks) {
      try {
        const result = await check.check();
        if (result.status !== 'healthy') {
          return false;
        }
      } catch (error) {
        return false;
      }
    }

    return true;
  }
}

interface HealthCheck {
  name: string;
  check: () => Promise<HealthResult>;
  timeout: number;
  critical: boolean;
}

interface HealthResult {
  name: string;
  status: 'healthy' | 'unhealthy';
  message?: string;
  timestamp: Date;
}

interface HealthReport {
  status: 'healthy' | 'unhealthy';
  timestamp: Date;
  checks: HealthResult[];
}
```

## 10. Testing Strategy

### 10.1 Comprehensive Testing Framework

#### Unit Testing
```typescript
// Example unit test for SuggestionEngine
import { SuggestionEngine } from '../src/services/intelligence/SuggestionEngine';
import { MockPiecesClient } from './mocks/MockPiecesClient';
import { MockAIWFEClient } from './mocks/MockAIWFEClient';
import { MockVectorStore } from './mocks/MockVectorStore';

describe('SuggestionEngine', () => {
  let suggestionEngine: SuggestionEngine;
  let mockPiecesClient: MockPiecesClient;
  let mockAIWFEClient: MockAIWFEClient;
  let mockVectorStore: MockVectorStore;

  beforeEach(() => {
    mockPiecesClient = new MockPiecesClient();
    mockAIWFEClient = new MockAIWFEClient();
    mockVectorStore = new MockVectorStore();
    
    suggestionEngine = new SuggestionEngine(
      mockPiecesClient,
      mockAIWFEClient,
      mockVectorStore
    );
  });

  describe('generateSuggestions', () => {
    it('should generate relevant suggestions based on context', async () => {
      // Arrange
      const userId = 'test-user';
      const context = {
        currentTask: 'Implement user authentication',
        language: 'typescript',
        keywords: ['auth', 'login', 'jwt'],
        recentActivity: ['auth.ts', 'user.model.ts']
      };

      mockPiecesClient.setSearchResults([
        {
          id: 'asset-1',
          name: 'JWT Authentication',
          content: 'function generateJWT(payload) { ... }',
          language: 'typescript',
          tags: ['auth', 'jwt'],
          usageCount: 5
        }
      ]);

      // Act
      const suggestions = await suggestionEngine.generateSuggestions(userId, context);

      // Assert
      expect(suggestions).toHaveLength(1);
      expect(suggestions[0].title).toBe('JWT Authentication');
      expect(suggestions[0].relevanceScore).toBeGreaterThan(0.6);
      expect(suggestions[0].source).toBe('pieces');
    });

    it('should filter out low-relevance suggestions', async () => {
      // Test low relevance filtering
      const context = {
        currentTask: 'Database optimization',
        language: 'sql',
        keywords: ['database', 'performance'],
        recentActivity: []
      };

      mockPiecesClient.setSearchResults([
        {
          id: 'asset-1',
          name: 'React Component',
          content: '<div>Hello World</div>',
          language: 'javascript',
          tags: ['react', 'component'],
          usageCount: 1
        }
      ]);

      const suggestions = await suggestionEngine.generateSuggestions('test-user', context);
      
      expect(suggestions).toHaveLength(0); // Should filter out irrelevant React component
    });
  });
});
```

#### Integration Testing
```typescript
// Integration test for Pieces synchronization
import { TestApp } from './helpers/TestApp';
import { MockPiecesOS } from './mocks/MockPiecesOS';

describe('Pieces Integration', () => {
  let testApp: TestApp;
  let mockPiecesOS: MockPiecesOS;

  beforeAll(async () => {
    mockPiecesOS = new MockPiecesOS();
    await mockPiecesOS.start();
    
    testApp = new TestApp({
      pieces: {
        url: mockPiecesOS.getUrl(),
        apiKey: 'test-key'
      }
    });
    await testApp.start();
  });

  afterAll(async () => {
    await testApp.stop();
    await mockPiecesOS.stop();
  });

  describe('Asset Synchronization', () => {
    it('should sync new assets from Pieces to AIWFE', async () => {
      // Create asset in mock Pieces OS
      const asset = await mockPiecesOS.createAsset({
        name: 'Test Function',
        content: 'function test() { return true; }',
        language: 'javascript'
      });

      // Wait for sync to occur
      await testApp.waitForSync('test-user');

      // Verify asset appears in AIWFE suggestions
      const suggestions = await testApp.getSuggestions('test-user', {
        keywords: ['test', 'function']
      });

      expect(suggestions.some(s => s.content.code.includes('function test()'))).toBe(true);
    });

    it('should handle sync conflicts gracefully', async () => {
      // Create conflicting changes in both systems
      const assetId = 'conflict-test-asset';
      
      await Promise.all([
        mockPiecesOS.updateAsset(assetId, { content: 'Version A' }),
        testApp.updateAsset('test-user', assetId, { content: 'Version B' })
      ]);

      // Trigger sync and verify conflict resolution
      const syncResult = await testApp.triggerSync('test-user');
      
      expect(syncResult.conflicts_resolved).toBeGreaterThan(0);
      expect(syncResult.status).toBe('completed');
    });
  });
});
```

### 10.2 Performance Testing

#### Load Testing
```typescript
// Load test for suggestion generation
import { performance } from 'perf_hooks';

describe('Performance Tests', () => {
  describe('Suggestion Generation Performance', () => {
    it('should generate suggestions within performance budget', async () => {
      const suggestionEngine = new SuggestionEngine(/* ... */);
      const context = {
        currentTask: 'API development',
        language: 'typescript',
        keywords: ['api', 'rest', 'endpoint'],
        recentActivity: ['api.ts', 'routes.ts']
      };

      const startTime = performance.now();
      const suggestions = await suggestionEngine.generateSuggestions('test-user', context);
      const endTime = performance.now();

      const duration = endTime - startTime;
      
      expect(duration).toBeLessThan(500); // 500ms budget
      expect(suggestions.length).toBeGreaterThan(0);
    });

    it('should handle concurrent suggestion requests', async () => {
      const concurrentRequests = 50;
      const promises = Array.from({ length: concurrentRequests }, (_, i) => 
        suggestionEngine.generateSuggestions(`user-${i}`, {
          currentTask: `Task ${i}`,
          keywords: ['test'],
          recentActivity: []
        })
      );

      const startTime = performance.now();
      const results = await Promise.all(promises);
      const endTime = performance.now();

      const duration = endTime - startTime;
      const avgDuration = duration / concurrentRequests;

      expect(avgDuration).toBeLessThan(100); // 100ms per request on average
      expect(results.every(r => Array.isArray(r))).toBe(true);
    });
  });
});
```

## 11. Deployment Timeline and Success Metrics

### 11.1 Implementation Schedule

#### Phase 1: Foundation (Weeks 1-4)
```yaml
Week 1: Infrastructure Setup
  - Kubernetes namespace and RBAC configuration
  - Service deployment manifests
  - Basic health checks and monitoring
  - Development environment setup

Week 2: Core Service Implementation
  - Pieces client implementation
  - AIWFE client implementation
  - Basic API endpoints
  - Database schema and models

Week 3: Context Synchronization
  - Bidirectional sync engine
  - Conflict resolution logic
  - Real-time WebSocket connections
  - Initial testing framework

Week 4: Integration Testing
  - End-to-end sync testing
  - Performance baseline establishment
  - Security testing
  - Documentation foundation
```

#### Phase 2: Intelligence Features (Weeks 5-8)
```yaml
Week 5: Suggestion Engine
  - Context analysis implementation
  - Relevance scoring algorithms
  - Multi-source suggestion aggregation
  - Basic machine learning models

Week 6: Advanced Features
  - Usage-based suggestions
  - Pattern recognition
  - User preference learning
  - Collaborative filtering

Week 7: WebUI Integration
  - Frontend components for Pieces features
  - Real-time suggestion display
  - Context visualization
  - User preference interfaces

Week 8: Quality Assurance
  - Comprehensive testing
  - Performance optimization
  - Security audit
  - User acceptance testing
```

### 11.2 Success Criteria

#### Technical Success Metrics
```yaml
Performance Targets:
  - Suggestion generation: < 500ms (95th percentile)
  - Sync operations: < 2 seconds (average)
  - WebSocket latency: < 100ms
  - API availability: > 99.9%

Quality Targets:
  - Test coverage: > 80%
  - Security scan: Zero critical vulnerabilities
  - Code quality: A-grade SonarQube rating
  - Documentation: 100% API coverage

Scalability Targets:
  - Concurrent users: 1,000+
  - Assets per user: 10,000+
  - Sync operations/second: 100+
  - Memory usage: < 512MB per pod
```

#### Business Success Metrics
```yaml
User Adoption:
  - Integration setup completion rate: > 80%
  - Daily active integrations: > 70%
  - Suggestion acceptance rate: > 40%
  - User retention after 30 days: > 85%

Productivity Impact:
  - Time saved per user per day: > 30 minutes
  - Context switching reduction: > 70%
  - Code reuse increase: > 50%
  - Task completion acceleration: > 25%

User Satisfaction:
  - Net Promoter Score: > 7/10
  - Feature usefulness rating: > 8/10
  - Integration reliability score: > 9/10
  - Support ticket reduction: > 60%
```

## 12. Approval and Next Steps

### 12.1 Technical Review Checklist

- [ ] Architecture design reviewed and approved
- [ ] API specifications validated
- [ ] Security framework approved
- [ ] Performance targets confirmed
- [ ] Testing strategy comprehensive
- [ ] Deployment plan feasible
- [ ] Monitoring approach adequate
- [ ] Documentation requirements met

### 12.2 Business Review Checklist

- [ ] User value proposition clear
- [ ] Success metrics defined and measurable
- [ ] Implementation timeline realistic
- [ ] Resource requirements approved
- [ ] Risk mitigation strategies in place
- [ ] Integration with existing roadmap confirmed
- [ ] Privacy and compliance requirements addressed

**Integration Architect Approval**: _____________________ Date: _______

**Security Lead Approval**: _____________________ Date: _______

**Technical Lead Approval**: _____________________ Date: _______

**Product Owner Approval**: _____________________ Date: _______

---

*This Pieces Integration Specification provides a comprehensive blueprint for creating a seamless, intelligent, and highly performant integration between AIWFE and the Pieces ecosystem, enabling unprecedented developer productivity and context continuity across tools and workflows.*