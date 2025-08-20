import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Bot, User, Loader, AlertCircle, X, Mic, Settings } from 'lucide-react';
import { SecureAuth } from '../utils/secureAuth';
import websocketSessionManager from '../utils/websocketSessionManager';
import { useAuth } from '../context/AuthContext';
import VoiceInteraction from '../components/VoiceInteraction';
import ServiceStatusIndicator from '../components/ServiceStatusIndicator';

// Valid chat modes from backend ChatMode enum
const VALID_CHAT_MODES = ['smart-router', 'socratic-interview', 'expert-group', 'direct'];

// Request validation utility
const validateChatRequest = (request) => {
  const errors = [];
  
  if (!request.message || typeof request.message !== 'string' || request.message.trim().length === 0) {
    errors.push('Message is required and cannot be empty');
  }
  
  if (request.message && request.message.length > 10000) {
    errors.push('Message is too long (max 10000 characters)');
  }
  
  if (request.mode && !VALID_CHAT_MODES.includes(request.mode)) {
    errors.push(`Invalid mode. Must be one of: ${VALID_CHAT_MODES.join(', ')}`);
  }
  
  if (request.current_graph_state !== undefined && typeof request.current_graph_state !== 'object') {
    errors.push('current_graph_state must be an object or undefined');
  }
  
  if (request.message_history !== undefined && !Array.isArray(request.message_history)) {
    errors.push('message_history must be an array or undefined');
  }
  
  if (request.user_preferences !== undefined && typeof request.user_preferences !== 'object') {
    errors.push('user_preferences must be an object or undefined');
  }
  
  return errors;
};

const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [showVoicePanel, setShowVoicePanel] = useState(false);
  const [showServiceStatus, setShowServiceStatus] = useState(false);
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);
  const { isAuthenticated, isRestoring, restoreSession } = useAuth();

  useEffect(() => {
    // Initialize WebSocket connection with session management
    const initializeWebSocket = async () => {
      if (!isAuthenticated || isRestoring) {
        console.log('Chat: Waiting for authentication to complete...');
        if (!isAuthenticated && !isRestoring) {
          setError('Please log in to use the chat feature.');
          setMessages([{
            id: 'auth-required',
            role: 'assistant',
            content: 'Authentication required. Please log in to start chatting with your AI assistant.',
            timestamp: new Date().toISOString()
          }]);
        }
        return;
      }

      try {
        console.log('Chat: Authentication confirmed, connecting WebSocket with session management');
        
        // Use WebSocket session manager for persistent connections with new chat service endpoint
        const ws = await websocketSessionManager.getConnection('/ws/chat');
        wsRef.current = ws;
        
        // Set up session-aware event handlers
        setupWebSocketHandlers(ws);
        
        setIsConnected(ws.readyState === WebSocket.OPEN);
        setError(null);
        
        // Add welcome message with session continuity
        setMessages([{
          id: 'welcome',
          role: 'assistant',
          content: 'Hello! I\'m your AI assistant. Your session is now active and will persist across navigation. How can I help you today?',
          timestamp: new Date().toISOString(),
          metadata: {
            auth_verified: true,
            session_managed: true,
            connection_persistent: true
          }
        }]);
        
      } catch (error) {
        console.error('Chat: WebSocket connection failed:', error);
        setError('Failed to connect to chat service. Please refresh and try again.');
        setIsConnected(false);
      }
    };
    
    initializeWebSocket();

    // Handle authentication changes
    const handleAuthChange = (authState) => {
      if (!authState.isAuthenticated) {
        setIsConnected(false);
        wsRef.current = null;
        setMessages(prev => [...prev, {
          id: 'session-ended',
          role: 'assistant',
          content: 'Session ended. Please log in again to continue chatting.',
          timestamp: new Date().toISOString()
        }]);
      }
    };

    // Listen for auth changes
    const unsubscribe = websocketSessionManager.addSessionListener(handleAuthChange);

    return () => {
      unsubscribe();
      // Note: Don't close connection here - let session manager handle persistence
    };
  }, []); // Remove auth dependencies to prevent re-initialization loops

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Set up WebSocket event handlers for session-managed connections
  const setupWebSocketHandlers = (ws) => {
    ws.onopen = () => {
      console.log('WebSocket connected with session management');
      setIsConnected(true);
      setError(null);
      
      // Send ready signal with session information
      const token = SecureAuth.getAuthToken();
      if (token) {
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          ws.send(JSON.stringify({ 
            type: 'ready', 
            session_id: payload.session_id || payload.sub || Date.now().toString(),
            user_id: payload.id || payload.sub,
            auth_method: 'integration_layer_session',
            integration_layer: true
          }));
        } catch (error) {
          console.error('Failed to parse token for session info:', error);
          ws.send(JSON.stringify({ 
            type: 'ready', 
            session_id: Date.now().toString(),
            auth_method: 'integration_layer_fallback',
            integration_layer: true
          }));
        }
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message received:', data.type);
        
        switch (data.type) {
          case 'connection_confirmed':
            console.log('WebSocket connection confirmed with session continuity');
            break;
            
          case 'session_restoration':
            console.log('Session restored successfully');
            setMessages(prev => [...prev, {
              id: 'session-restored',
              role: 'assistant',
              content: 'Session restored. You can continue where you left off.',
              timestamp: new Date().toISOString(),
              metadata: {
                session_restored: true
              }
            }]);
            break;
            
          case 'ready_confirmed':
            console.log('Ready confirmed by server');
            break;
            
          case 'message_received':
            console.log('Message received by server');
            break;
            
          case 'chat_response':
            if (data.content) {
              setMessages(prev => [...prev, {
                id: `assistant-${Date.now()}`,
                role: 'assistant',
                content: data.content,
                timestamp: new Date().toISOString(),
                metadata: data.metadata || {}
              }]);
            }
            setIsLoading(false);
            break;
            
          case 'error':
            console.error('WebSocket error:', data.message);
            setError(data.message || 'An error occurred');
            setIsLoading(false);
            break;
            
          default:
            console.log('Unknown message type:', data.type);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
        setError('Error parsing server response');
        setIsLoading(false);
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocket closed with session management:', event.code, event.reason);
      setIsConnected(false);
      
      // Only show error for unexpected closures (session manager handles reconnection)
      if (event.code !== 1000 && event.code !== 1001) {
        setError('Connection lost. Attempting to reconnect...');
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error with session management:', error);
      setError('Connection error. Please check your network and try again.');
      setIsConnected(false);
    };
  };

  const connectWebSocket = () => {
    const token = SecureAuth.getAuthToken();
    if (!token) {
      setError('Authentication required. Please log in.');
      return;
    }

    try {
      // Connect to new chat service WebSocket endpoint with JWT query parameter authentication
      const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/chat?token=${encodeURIComponent(token)}`;
      
      // Create WebSocket connection with JWT query parameter authentication
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected with unified authentication');
        setIsConnected(true);
        setError(null);
        
        // Send ready signal with session information for integration layer
        wsRef.current.send(JSON.stringify({ 
          type: 'ready', 
          session_id: Date.now().toString(),
          auth_method: 'integration_layer_direct',
          integration_layer: true
        }));
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data.type);
          
          switch (data.type) {
            case 'connection_confirmed':
              console.log('WebSocket connection confirmed');
              break;
              
            case 'ready_confirmed':
              console.log('Ready confirmed by server');
              break;
              
            case 'message_received':
              console.log('Message received by server');
              break;
              
            case 'typing_start':
              setIsLoading(true);
              break;
              
            case 'message_start':
              setIsLoading(true);
              // Initialize empty assistant message for streaming
              setMessages(prev => [...prev, {
                id: `assistant_${Date.now()}`,
                role: 'assistant',
                content: '',
                timestamp: data.timestamp || new Date().toISOString(),
                isStreaming: true
              }]);
              break;
              
            case 'message_chunk':
              // Update the streaming message with new content chunk
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMessage = newMessages[newMessages.length - 1];
                if (lastMessage && lastMessage.role === 'assistant' && lastMessage.isStreaming) {
                  lastMessage.content = data.accumulated_content || lastMessage.content + (data.content || '');
                }
                return newMessages;
              });
              break;
              
            case 'message_complete':
              // Finalize the streaming message
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMessage = newMessages[newMessages.length - 1];
                if (lastMessage && lastMessage.role === 'assistant' && lastMessage.isStreaming) {
                  lastMessage.content = data.content || lastMessage.content;
                  lastMessage.isStreaming = false;
                  lastMessage.metadata = data.metadata;
                }
                return newMessages;
              });
              setIsLoading(false);
              break;
              
            case 'typing_stop':
              setIsLoading(false);
              break;
              
            case 'error':
              console.error('WebSocket error message:', data.message);
              setError(data.message || 'An error occurred while processing your message');
              setIsLoading(false);
              break;
              
            case 'message':
              // Fallback for legacy message format
              setMessages(prev => [...prev, {
                id: Date.now().toString(),
                role: 'assistant',
                content: data.content,
                timestamp: new Date().toISOString()
              }]);
              setIsLoading(false);
              break;
              
            default:
              console.log('Unknown message type:', data.type, data);
          }
        } catch (parseError) {
          console.error('Failed to parse WebSocket message:', parseError, event.data);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Connection error. Please check your internet connection and try again.');
        setIsConnected(false);
      };

      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        
        // Handle different close codes
        if (event.code === 1008) {
          // Policy violation - likely authentication issue
          setError('Authentication failed. Please log in again.');
          SecureAuth.clearAuthToken();
          return;
        }
        
        if (event.code === 1011) {
          // Internal error
          setError('Server error. Please try again in a moment.');
        }
        
        // Attempt to reconnect after 3 seconds (unless it was an auth failure)
        if (event.code !== 1008) {
          setTimeout(() => {
            if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
              console.log('Attempting WebSocket reconnection...');
              connectWebSocket();
            }
          }, 3000);
        }
      };
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
      setError('Failed to connect to chat service');
    }
  };

  // Poll task status until completion
  const pollTaskStatus = async (taskId, messageId, maxAttempts = 30) => {
    let attempts = 0;
    
    const poll = async () => {
      try {
        attempts++;
        const response = await SecureAuth.makeSecureRequest(`/api/v1/chat/status/${taskId}`);
        
        if (!response.ok) {
          throw new Error('Failed to check task status');
        }
        
        const statusData = await response.json();
        
        if (statusData.status === 'SUCCESS' && statusData.response) {
          // Update the processing message with the final response
          setMessages(prev => prev.map(msg => 
            msg.id === messageId 
              ? { ...msg, content: statusData.response, isProcessing: false }
              : msg
          ));
          setIsLoading(false);
          return;
        } else if (statusData.status === 'FAILURE' || statusData.error_message) {
          // Handle task failure
          setMessages(prev => prev.map(msg => 
            msg.id === messageId 
              ? { ...msg, content: `Error: ${statusData.error_message || 'Task failed'}`, isProcessing: false }
              : msg
          ));
          setIsLoading(false);
          return;
        } else if (attempts < maxAttempts) {
          // Continue polling
          setTimeout(poll, 1000); // Poll every second
        } else {
          // Max attempts reached
          setMessages(prev => prev.map(msg => 
            msg.id === messageId 
              ? { ...msg, content: 'Response timeout. Please try again.', isProcessing: false }
              : msg
          ));
          setIsLoading(false);
        }
      } catch (error) {
        console.error('Error polling task status:', error);
        setMessages(prev => prev.map(msg => 
          msg.id === messageId 
            ? { ...msg, content: 'Error retrieving response. Please try again.', isProcessing: false }
            : msg
        ));
        setIsLoading(false);
      }
    };
    
    // Start polling after a short delay
    setTimeout(poll, 1000);
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setError(null);

    // If WebSocket is connected, use it
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'chat_message',
        message: userMessage.content,
        session_id: Date.now().toString(),
        mode: 'smart-router'  // Fixed: Use valid ChatMode enum value
      }));
    } else {
      // Fallback to REST API
      try {
        // Create and validate chat request
        const chatRequest = {
          message: userMessage.content,
          session_id: Date.now().toString(),
          mode: 'smart-router',  // Fixed: Use valid ChatMode enum value
          current_graph_state: {},  // Fixed: Use empty object instead of null
          message_history: [],
          user_preferences: {}
        };
        
        // Validate request before sending
        const validationErrors = validateChatRequest(chatRequest);
        if (validationErrors.length > 0) {
          console.error('Chat request validation failed:', validationErrors);
          setError(`Request validation failed: ${validationErrors.join(', ')}`);
          setIsLoading(false);
          return;
        }
        
        console.log('Chat request validated successfully:', chatRequest);
        
        // Use new chat service endpoint (port 8007 routed through main API)
        const response = await SecureAuth.makeSecureRequest('/api/v1/chat', {
          method: 'POST',
          body: JSON.stringify(chatRequest)
        });

        if (!response.ok) {
          // Enhanced error handling with specific status codes
          let errorMessage = 'Failed to send message';
          if (response.status === 422) {
            errorMessage = 'Invalid message format. Please try again.';
          } else if (response.status === 401) {
            errorMessage = 'Authentication expired. Please log in again.';
            SecureAuth.handleAuthenticationFailure();
            return;
          } else if (response.status === 429) {
            errorMessage = 'Too many requests. Please wait a moment.';
          } else if (response.status >= 500) {
            errorMessage = 'Server error. Please try again in a moment.';
          }
          throw new Error(errorMessage);
        }

        const data = await response.json();
        
        // Enhanced success feedback with evidence display
        console.log('Chat API Success:', {
          status: response.status,
          hasTaskId: !!data.task_id,
          responsePresent: !!data.response,
          messageId: data.message_id || 'N/A'
        });
        
        // If we get a task_id, poll for the final result
        if (data.task_id) {
          // Show initial processing message with evidence
          const processingMessageId = Date.now().toString();
          setMessages(prev => [...prev, {
            id: processingMessageId,
            role: 'assistant',
            content: data.response || 'Your message is being processed...',
            timestamp: new Date().toISOString(),
            isProcessing: true,
            metadata: {
              task_id: data.task_id,
              api_success: true,
              processing_started: new Date().toISOString()
            }
          }]);
          
          // Poll for task completion
          pollTaskStatus(data.task_id, processingMessageId);
        } else {
          // Direct response (fallback behavior) with success evidence
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: 'assistant',
            content: data.response || data.message,
            timestamp: new Date().toISOString(),
            metadata: {
              api_success: true,
              response_type: 'direct',
              message_id: data.message_id
            }
          }]);
        }
      } catch (err) {
        console.error('Failed to send message:', err);
        setError('Failed to send message. Please try again.');
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleVoiceTranscription = (text, result) => {
    if (text) {
      setInputMessage(text);
      // Optionally auto-send voice messages
      // sendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none" style={{ zIndex: -1 }}>
        <div className="absolute top-1/3 left-1/3 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse"></div>
        <div className="absolute bottom-1/3 right-1/3 w-96 h-96 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse delay-1000"></div>
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-gray-800 bg-black/50 backdrop-blur-lg">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Bot className="w-8 h-8 text-purple-400" />
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                  AI Chat Assistant
                </h1>
                <div className="flex items-center space-x-2 text-xs">
                  <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
                  <span className="text-gray-400">{isConnected ? 'Connected' : 'Connecting...'}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {/* Service Status Indicator */}
              <div className="relative">
                <ServiceStatusIndicator compact={true} />
              </div>
              
              {/* Voice Toggle */}
              <button
                onClick={() => setShowVoicePanel(!showVoicePanel)}
                className={`p-2 rounded-lg transition ${
                  showVoicePanel 
                    ? 'bg-purple-600 text-white' 
                    : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
                }`}
                title="Toggle Voice Interaction"
              >
                <Mic className="w-5 h-5" />
              </button>
              
              {/* Close Button */}
              <button
                onClick={() => window.history.back()}
                className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Chat Messages */}
      <main className="relative z-10 flex-1 overflow-hidden flex flex-col">
        {/* Voice Interaction Panel */}
        <AnimatePresence>
          {showVoicePanel && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="border-b border-gray-800 px-6 py-4"
            >
              <VoiceInteraction 
                onTranscription={handleVoiceTranscription}
                className="max-w-4xl mx-auto"
              />
            </motion.div>
          )}
        </AnimatePresence>
        
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="max-w-4xl mx-auto space-y-4">
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex items-start space-x-3 max-w-2xl ${message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      message.role === 'user' 
                        ? 'bg-gradient-to-r from-blue-500 to-purple-500' 
                        : 'bg-gradient-to-r from-purple-500 to-pink-500'
                    }`}>
                      {message.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                    </div>
                    <div className={`rounded-lg px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-blue-900/50 backdrop-blur-lg border border-blue-800'
                        : 'bg-gray-900/50 backdrop-blur-lg border border-gray-800'
                    }`}>
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      {message.isStreaming && (
                        <div className="flex items-center space-x-1 mt-2">
                          <div className="w-1 h-1 bg-purple-400 rounded-full animate-pulse"></div>
                          <div className="w-1 h-1 bg-purple-400 rounded-full animate-pulse delay-75"></div>
                          <div className="w-1 h-1 bg-purple-400 rounded-full animate-pulse delay-150"></div>
                          <span className="text-xs text-purple-400 ml-2">AI is typing...</span>
                        </div>
                      )}
                      <div className="flex justify-between items-center mt-2">
                        <p className="text-xs text-gray-500">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </p>
                        {message.metadata && (
                          <p className="text-xs text-gray-600">
                            {message.metadata.processing_time_ms && `${Math.round(message.metadata.processing_time_ms)}ms`}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center">
                    <Bot className="w-5 h-5" />
                  </div>
                  <div className="bg-gray-900/50 backdrop-blur-lg border border-gray-800 rounded-lg px-4 py-3">
                    <Loader className="w-5 h-5 animate-spin text-purple-400" />
                  </div>
                </div>
              </motion.div>
            )}

            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-center"
              >
                <div className="bg-red-900/20 border border-red-800 rounded-lg px-4 py-3 flex items-center space-x-2">
                  <AlertCircle className="w-5 h-5 text-red-400" />
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-800 bg-black/50 backdrop-blur-lg px-6 py-4">
          <div className="max-w-4xl mx-auto">
            {isAuthenticated === false ? (
              // Authentication required UI
              <div className="flex items-center justify-center space-x-4 py-4">
                <button
                  onClick={() => window.location.href = '/login'}
                  className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 rounded-lg font-medium transition"
                >
                  Log In to Chat
                </button>
                <button
                  onClick={() => window.location.href = '/'}
                  className="px-6 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg font-medium transition"
                >
                  Go to Dashboard
                </button>
              </div>
            ) : (
              // Chat input UI
              <div className="flex items-end space-x-4">
                <div className="flex-1">
                  <textarea
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={isConnected ? "Type your message..." : "Connecting to chat..."}
                    rows="1"
                    disabled={!isConnected}
                    className="w-full bg-gray-900/50 backdrop-blur-lg border border-gray-800 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition resize-none disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ minHeight: '48px', maxHeight: '120px' }}
                    onInput={(e) => {
                      e.target.style.height = 'auto';
                      e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                    }}
                  />
                </div>
                <div className="flex items-center space-x-2">
                  {/* Voice Input Toggle */}
                  <button
                    onClick={() => setShowVoicePanel(!showVoicePanel)}
                    className={`p-3 rounded-lg transition ${
                      showVoicePanel
                        ? 'bg-purple-600 hover:bg-purple-700'
                        : 'bg-gray-800 hover:bg-gray-700'
                    }`}
                    title="Voice Input"
                  >
                    <Mic className="w-5 h-5" />
                  </button>
                  
                  {/* Send Button */}
                  <button
                    onClick={sendMessage}
                    disabled={!inputMessage.trim() || isLoading || !isConnected}
                    className={`p-3 rounded-lg transition ${
                      inputMessage.trim() && !isLoading && isConnected
                        ? 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
                        : 'bg-gray-800 cursor-not-allowed opacity-50'
                    }`}
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

// Memoize Chat component to prevent unnecessary re-renders that trigger auth loops
export default memo(Chat);