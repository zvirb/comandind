import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  Brain, 
  MessageCircle, 
  TrendingUp, 
  Target, 
  Clock, 
  ArrowLeft, 
  Send,
  Lightbulb,
  Heart,
  Award,
  Compass
} from 'lucide-react';
import { SecureAuth } from '../utils/secureAuth';

const Reflective = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [lifeProgress, setLifeProgress] = useState({
    personal: 65,
    career: 78,
    relationships: 82,
    health: 70,
    learning: 85
  });
  const [currentTopic, setCurrentTopic] = useState('general');
  const messagesEndRef = useRef(null);

  const reflectiveTopics = [
    { id: 'general', label: 'General Reflection', icon: <Brain className="w-4 h-4" /> },
    { id: 'goals', label: 'Goals & Aspirations', icon: <Target className="w-4 h-4" /> },
    { id: 'relationships', label: 'Relationships', icon: <Heart className="w-4 h-4" /> },
    { id: 'growth', label: 'Personal Growth', icon: <TrendingUp className="w-4 h-4" /> },
    { id: 'achievements', label: 'Achievements', icon: <Award className="w-4 h-4" /> },
    { id: 'direction', label: 'Life Direction', icon: <Compass className="w-4 h-4" /> }
  ];

  useEffect(() => {
    // Initialize with welcome message based on current topic
    initializeReflectiveSession();
  }, [currentTopic]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const initializeReflectiveSession = () => {
    const welcomeMessages = {
      general: "Welcome to your reflective space. I'm here to guide you through thoughtful self-exploration. What's on your mind today?",
      goals: "Let's explore your aspirations. What goals are most important to you right now, and what's driving you toward them?",
      relationships: "Relationships shape our lives in profound ways. What relationships in your life bring you the most joy or challenge?",
      growth: "Personal growth is a lifelong journey. What areas of yourself would you like to develop or understand better?",
      achievements: "Celebrating our achievements helps us recognize our progress. What accomplishment are you most proud of lately?",
      direction: "Life's direction isn't always clear. What questions are you asking yourself about your path forward?"
    };

    setMessages([{
      id: 'welcome-' + currentTopic,
      role: 'assistant',
      content: welcomeMessages[currentTopic],
      timestamp: new Date().toISOString(),
      type: 'reflective'
    }]);
  };

  const sendReflectiveMessage = async () => {
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

    try {
      const response = await SecureAuth.makeSecureRequest('/api/v1/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: userMessage.content,
          session_id: 'reflective-' + Date.now().toString(),
          mode: 'reflective',
          current_graph_state: { 
            reflection_topic: currentTopic,
            life_progress: lifeProgress 
          },
          message_history: messages.slice(-5), // Last 5 messages for context
          user_preferences: { 
            conversation_style: 'socratic',
            reflection_depth: 'deep',
            focus_area: currentTopic
          }
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get reflective response');
      }

      const data = await response.json();
      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response || data.message,
        timestamp: new Date().toISOString(),
        type: 'reflective',
        insights: data.insights || []
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Update life progress if insights are provided
      if (data.life_progress_update) {
        setLifeProgress(prev => ({ ...prev, ...data.life_progress_update }));
      }

    } catch (error) {
      console.error('Reflective chat error:', error);
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "I'm having trouble connecting right now. In the meantime, take a moment to reflect on your thoughts. Sometimes the most profound insights come from within.",
        timestamp: new Date().toISOString(),
        type: 'error'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendReflectiveMessage();
    }
  };

  const LifeProgressCard = ({ label, value, icon, color }) => (
    <div className="bg-gray-900/30 backdrop-blur-lg rounded-lg p-4 border border-gray-800">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div className={`${color} opacity-80`}>{icon}</div>
          <span className="text-sm font-medium">{label}</span>
        </div>
        <span className="text-lg font-bold">{value}%</span>
      </div>
      <div className="w-full bg-gray-800 rounded-full h-2">
        <motion.div 
          className={`h-2 rounded-full ${color.replace('text-', 'bg-')}`}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600 rounded-full mix-blend-multiply filter blur-3xl opacity-8 animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl opacity-8 animate-pulse delay-1000"></div>
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-gray-800 bg-black/50 backdrop-blur-lg">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div className="flex items-center space-x-3">
                <Lightbulb className="w-8 h-8 text-indigo-400" />
                <div>
                  <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                    Reflective Journey
                  </h1>
                  <p className="text-sm text-gray-400">Deep self-exploration through guided reflection</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="relative z-10 container mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar - Life Progress & Topics */}
        <aside className="lg:col-span-1 space-y-6">
          {/* Life Progress Overview */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gray-900/40 backdrop-blur-lg rounded-lg p-6 border border-gray-800"
          >
            <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-indigo-400" />
              <span>Life Progress</span>
            </h3>
            <div className="space-y-4">
              <LifeProgressCard 
                label="Personal" 
                value={lifeProgress.personal} 
                icon={<Brain className="w-4 h-4" />}
                color="text-indigo-400"
              />
              <LifeProgressCard 
                label="Career" 
                value={lifeProgress.career} 
                icon={<Target className="w-4 h-4" />}
                color="text-purple-400"
              />
              <LifeProgressCard 
                label="Relationships" 
                value={lifeProgress.relationships} 
                icon={<Heart className="w-4 h-4" />}
                color="text-pink-400"
              />
              <LifeProgressCard 
                label="Health" 
                value={lifeProgress.health} 
                icon={<Award className="w-4 h-4" />}
                color="text-green-400"
              />
              <LifeProgressCard 
                label="Learning" 
                value={lifeProgress.learning} 
                icon={<Lightbulb className="w-4 h-4" />}
                color="text-yellow-400"
              />
            </div>
          </motion.div>

          {/* Reflection Topics */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-gray-900/40 backdrop-blur-lg rounded-lg p-6 border border-gray-800"
          >
            <h3 className="text-lg font-semibold mb-4">Reflection Topics</h3>
            <div className="space-y-2">
              {reflectiveTopics.map((topic) => (
                <button
                  key={topic.id}
                  onClick={() => setCurrentTopic(topic.id)}
                  className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition text-sm ${
                    currentTopic === topic.id
                      ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                      : 'hover:bg-gray-800 text-gray-300'
                  }`}
                >
                  {topic.icon}
                  <span>{topic.label}</span>
                </button>
              ))}
            </div>
          </motion.div>
        </aside>

        {/* Main Chat Area */}
        <main className="lg:col-span-3">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-gray-900/40 backdrop-blur-lg rounded-lg border border-gray-800 h-[70vh] flex flex-col"
          >
            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-6">
                <AnimatePresence>
                  {messages.map((message) => (
                    <motion.div
                      key={message.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`max-w-3xl ${message.role === 'user' ? 'text-right' : 'text-left'}`}>
                        <div className={`inline-block rounded-lg px-4 py-3 ${
                          message.role === 'user'
                            ? 'bg-indigo-600/20 border border-indigo-500/30 text-indigo-100'
                            : 'bg-gray-800/50 border border-gray-700 text-gray-100'
                        }`}>
                          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                          {message.insights && message.insights.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-gray-600">
                              <p className="text-xs text-gray-400 mb-2">Insights:</p>
                              <ul className="text-sm text-gray-300 space-y-1">
                                {message.insights.map((insight, idx) => (
                                  <li key={idx} className="flex items-start space-x-2">
                                    <Lightbulb className="w-3 h-3 mt-0.5 text-yellow-400 flex-shrink-0" />
                                    <span>{insight}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </p>
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
                    <div className="bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-3 flex items-center space-x-2">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce delay-100"></div>
                        <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce delay-200"></div>
                      </div>
                      <span className="text-sm text-gray-400">Reflecting...</span>
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Input Area */}
            <div className="border-t border-gray-800 bg-gray-900/20 p-4">
              <div className="flex items-end space-x-4">
                <div className="flex-1">
                  <textarea
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Share your thoughts, feelings, or questions for reflection..."
                    rows="2"
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition resize-none"
                    style={{ minHeight: '60px', maxHeight: '120px' }}
                    onInput={(e) => {
                      e.target.style.height = 'auto';
                      e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                    }}
                  />
                </div>
                <button
                  onClick={sendReflectiveMessage}
                  disabled={!inputMessage.trim() || isLoading}
                  className={`p-3 rounded-lg transition ${
                    inputMessage.trim() && !isLoading
                      ? 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700'
                      : 'bg-gray-800 cursor-not-allowed opacity-50'
                  }`}
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </motion.div>
        </main>
      </div>
    </div>
  );
};

export default Reflective;