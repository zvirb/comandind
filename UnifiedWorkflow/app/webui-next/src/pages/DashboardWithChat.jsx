import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useScroll, useTransform } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  User, 
  Activity, 
  CheckCircle, 
  Clock, 
  TrendingUp,
  AlertCircle,
  Calendar,
  FileText,
  MessageSquare,
  Settings,
  LogOut,
  Send,
  Bot,
  Loader,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { SecureAuth } from '../utils/secureAuth';
import FloatingUserNav from '../components/FloatingUserNav';

const DashboardWithChat = () => {
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showChat, setShowChat] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);
  
  // Scroll-based animations
  const { scrollY } = useScroll();
  const dashboardY = useTransform(scrollY, [0, 300], [0, -100]);
  const dashboardOpacity = useTransform(scrollY, [0, 300], [1, 0]);
  const chatY = useTransform(scrollY, [200, 400], [100, 0]);
  const chatOpacity = useTransform(scrollY, [200, 400], [0, 1]);

  useEffect(() => {
    fetchDashboardData();
    // Initialize with welcome message
    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: 'Hello! How can I assist you today?',
      timestamp: new Date().toISOString()
    }]);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchDashboardData = async () => {
    try {
      const response = await SecureAuth.makeSecureRequest('/api/v1/dashboard', {
        method: 'GET'
      });

      if (response.status === 401) {
        SecureAuth.handleAuthenticationFailure();
        return;
      }

      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data');
      }

      const data = await response.json();
      setDashboardData(data);
    } catch (error) {
      console.error('Dashboard error:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    SecureAuth.logout();
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isTyping) return;

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);

    try {
      const response = await SecureAuth.makeSecureRequest('/api/v1/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: userMessage.content,
          mode: 'default'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const data = await response.json();
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: data.response || data.message || 'I received your message!',
        timestamp: new Date().toISOString()
      }]);
    } catch (err) {
      console.error('Failed to send message:', err);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const scrollToChat = () => {
    window.scrollTo({ top: window.innerHeight, behavior: 'smooth' });
    setShowChat(true);
  };

  const scrollToDashboard = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  const stats = [
    { icon: <Activity className="w-6 h-6" />, label: 'Active Sessions', value: '3', trend: '+12%', color: 'text-green-400' },
    { icon: <CheckCircle className="w-6 h-6" />, label: 'Tasks Completed', value: dashboardData?.progress?.completed || '0', trend: '+5%', color: 'text-blue-400' },
    { icon: <Clock className="w-6 h-6" />, label: 'Pending Tasks', value: dashboardData?.progress?.pending || '0', trend: '-2%', color: 'text-yellow-400' },
    { icon: <TrendingUp className="w-6 h-6" />, label: 'System Health', value: '98%', trend: '+1%', color: 'text-purple-400' }
  ];

  const quickActions = [
    { icon: <FileText />, label: 'Documents', path: '/documents' },
    { icon: <MessageSquare />, label: 'Chat', action: scrollToChat },
    { icon: <Calendar />, label: 'Calendar', path: '/calendar' },
    { icon: <CheckCircle />, label: 'Tasks', path: '/tasks' },
    { icon: <Activity />, label: 'Projects', path: '/projects' },
    { icon: <Settings />, label: 'Settings', path: '/settings' }
  ];

  return (
    <div ref={containerRef} className="bg-black text-white">
      {/* Floating User Navigation */}
      <FloatingUserNav />
      
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse delay-1000"></div>
      </div>

      {/* Dashboard Section */}
      <motion.div 
        style={{ y: dashboardY, opacity: dashboardOpacity }}
        className="min-h-screen relative z-10"
      >
        {/* Header */}
        <header className="border-b border-gray-800 bg-black/50 backdrop-blur-lg sticky top-0 z-20">
          <div className="container mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                  AI Workflow Dashboard
                </h1>
              </div>
              
              <div className="flex items-center space-x-6">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center">
                    <User className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{dashboardData?.user?.email || 'User'}</p>
                    <p className="text-xs text-gray-400">{dashboardData?.user?.role || 'Member'}</p>
                  </div>
                </div>
                
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="text-sm">Logout</span>
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Main Dashboard Content */}
        <main className="container mx-auto px-6 py-8">
          {/* Welcome Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <h2 className="text-3xl font-bold mb-2">
              Welcome back, {dashboardData?.user?.email?.split('@')[0] || 'User'}!
            </h2>
            <p className="text-gray-400">Here's what's happening with your AI workflow today.</p>
          </motion.div>

          {/* Stats Grid */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
          >
            {stats.map((stat, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1 * (index + 1) }}
                className="bg-gray-900/50 backdrop-blur-lg rounded-lg p-6 border border-gray-800 hover:border-purple-500/50 transition"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className={stat.color}>{stat.icon}</div>
                  <span className="text-xs text-green-400">{stat.trend}</span>
                </div>
                <p className="text-2xl font-bold mb-1">{stat.value}</p>
                <p className="text-sm text-gray-400">{stat.label}</p>
              </motion.div>
            ))}
          </motion.div>

          {/* Quick Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mb-8"
          >
            <h3 className="text-xl font-semibold mb-4">Quick Actions</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {quickActions.map((action, index) => (
                <motion.button
                  key={index}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.05 * (index + 1) }}
                  onClick={() => action.action ? action.action() : navigate(action.path)}
                  className="bg-gray-900/50 backdrop-blur-lg rounded-lg p-4 border border-gray-800 hover:border-purple-500/50 hover:bg-gray-800/50 transition flex flex-col items-center space-y-2"
                >
                  <div className="text-purple-400">{action.icon}</div>
                  <span className="text-sm">{action.label}</span>
                </motion.button>
              ))}
            </div>
          </motion.div>

          {/* Scroll to Chat Indicator */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="flex justify-center pt-8"
          >
            <button
              onClick={scrollToChat}
              className="flex flex-col items-center space-y-2 text-gray-400 hover:text-purple-400 transition animate-bounce"
            >
              <span className="text-sm">Scroll down for AI Chat</span>
              <ChevronDown className="w-6 h-6" />
            </button>
          </motion.div>
        </main>
      </motion.div>

      {/* Chat Section */}
      <motion.div 
        style={{ y: chatY, opacity: chatOpacity }}
        className="min-h-screen relative z-10 flex flex-col"
      >
        {/* Chat Header */}
        <header className="border-b border-gray-800 bg-black/50 backdrop-blur-lg sticky top-0 z-20">
          <div className="container mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Bot className="w-8 h-8 text-purple-400" />
                <div>
                  <h1 className="text-xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                    AI Chat Assistant
                  </h1>
                  <p className="text-xs text-gray-400">Always here to help</p>
                </div>
              </div>
              <button
                onClick={scrollToDashboard}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
              >
                <ChevronUp className="w-4 h-4" />
                <span className="text-sm">Back to Dashboard</span>
              </button>
            </div>
          </div>
        </header>

        {/* Chat Messages */}
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
                      <p className="text-xs text-gray-500 mt-2">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {isTyping && (
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

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-800 bg-black/50 backdrop-blur-lg px-6 py-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-end space-x-4">
              <div className="flex-1">
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message..."
                  rows="1"
                  className="w-full bg-gray-900/50 backdrop-blur-lg border border-gray-800 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition resize-none"
                  style={{ minHeight: '48px', maxHeight: '120px' }}
                  onInput={(e) => {
                    e.target.style.height = 'auto';
                    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                  }}
                />
              </div>
              <button
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isTyping}
                className={`p-3 rounded-lg transition ${
                  inputMessage.trim() && !isTyping
                    ? 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
                    : 'bg-gray-800 cursor-not-allowed opacity-50'
                }`}
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default DashboardWithChat;