import React, { useState, useEffect, useCallback, useRef, memo } from 'react';
import { motion } from 'framer-motion';
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
  BarChart3,
  Database,
  Shield
} from 'lucide-react';
import { SecureAuth } from '../utils/secureAuth';

const Dashboard = () => {
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const lastFetchRef = useRef(0);
  const isInitialLoad = useRef(true);

  const fetchDashboardData = useCallback(async () => {
    // Aggressive throttling to prevent rapid API calls that cause auth loops
    const now = Date.now();
    const timeSinceLastFetch = now - lastFetchRef.current;
    
    // Only fetch once per 5 minutes unless it's the initial load
    if (!isInitialLoad.current && timeSinceLastFetch < 300000) {
      console.log(`Dashboard: Fetch throttled - ${Math.ceil((300000 - timeSinceLastFetch) / 1000)}s remaining`);
      return;
    }
    
    lastFetchRef.current = now;
    isInitialLoad.current = false;
    try {
      // Fetch multiple endpoints concurrently for comprehensive dashboard data
      const [dashboardResponse, metricsResponse, healthResponse] = await Promise.allSettled([
        SecureAuth.makeSecureRequest('/api/v1/dashboard', { method: 'GET' }),
        SecureAuth.makeSecureRequest('/api/v1/performance_dashboard', { method: 'GET' }),
        SecureAuth.makeSecureRequest('/api/v1/health', { method: 'GET' })
      ]);

      // Handle authentication errors
      if (dashboardResponse.value?.status === 401) {
        SecureAuth.handleAuthenticationFailure();
        return;
      }

      const data = { user: {}, progress: {}, metrics: {}, health: {} };

      // Parse dashboard data
      if (dashboardResponse.status === 'fulfilled' && dashboardResponse.value.ok) {
        const dashboardData = await dashboardResponse.value.json();
        data.user = dashboardData.user || {};
        data.progress = dashboardData.progress || { completed: 0, pending: 0 };
      }

      // Parse performance metrics
      if (metricsResponse.status === 'fulfilled' && metricsResponse.value.ok) {
        const metricsData = await metricsResponse.value.json();
        data.metrics = metricsData;
      }

      // Parse health data
      if (healthResponse.status === 'fulfilled' && healthResponse.value.ok) {
        const healthData = await healthResponse.value.json();
        data.health = healthData;
      }

      setDashboardData(data);
    } catch (error) {
      console.error('Dashboard error:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  }, []); // No dependencies to prevent re-creation and loops

  useEffect(() => {
    // Single fetch on mount only - no periodic fetching to prevent auth loops
    fetchDashboardData();
  }, []); // No dependencies - single execution only

  const handleLogout = () => {
    SecureAuth.logout();
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

  if (error) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <p className="text-red-400">Error: {error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-4 px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const stats = [
    { 
      icon: <Activity className="w-6 h-6" />, 
      label: 'Active Sessions', 
      value: dashboardData?.metrics?.active_sessions?.toString() || '0', 
      trend: dashboardData?.metrics?.session_trend || '0%',
      color: 'text-green-400'
    },
    { 
      icon: <CheckCircle className="w-6 h-6" />, 
      label: 'Tasks Completed', 
      value: dashboardData?.progress?.completed?.toString() || '0', 
      trend: dashboardData?.progress?.completion_trend || '0%',
      color: 'text-blue-400'
    },
    { 
      icon: <Clock className="w-6 h-6" />, 
      label: 'Pending Tasks', 
      value: dashboardData?.progress?.pending?.toString() || '0', 
      trend: dashboardData?.progress?.pending_trend || '0%',
      color: 'text-yellow-400'
    },
    { 
      icon: <TrendingUp className="w-6 h-6" />, 
      label: 'System Health', 
      value: dashboardData?.health?.overall_health || '100%', 
      trend: dashboardData?.health?.health_trend || '0%',
      color: 'text-purple-400'
    }
  ];

  const quickActions = [
    { icon: <FileText />, label: 'Documents', path: '/documents' },
    { icon: <MessageSquare />, label: 'Chat', path: '/chat' },
    { icon: <Calendar />, label: 'Calendar', path: '/calendar' },
    { icon: <Settings />, label: 'Settings', path: '/settings' }
  ];

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none" style={{ zIndex: -1 }}>
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse delay-1000"></div>
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-gray-800 bg-black/50 backdrop-blur-lg">
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

      {/* Main Content */}
      <main className="relative z-10 container mx-auto px-6 py-8">
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
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {quickActions.map((action, index) => (
              <motion.button
                key={index}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.05 * (index + 1) }}
                onClick={() => navigate(action.path)}
                className="bg-gray-900/50 backdrop-blur-lg rounded-lg p-4 border border-gray-800 hover:border-purple-500/50 hover:bg-gray-800/50 transition flex flex-col items-center space-y-2"
              >
                <div className="text-purple-400">{action.icon}</div>
                <span className="text-sm">{action.label}</span>
              </motion.button>
            ))}
          </div>
        </motion.div>

        {/* Recent Activity & System Status */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Activity */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-gray-900/50 backdrop-blur-lg rounded-lg p-6 border border-gray-800"
          >
            <h3 className="text-xl font-semibold mb-4 flex items-center space-x-2">
              <Activity className="w-5 h-5 text-purple-400" />
              <span>Recent Activity</span>
            </h3>
            <div className="space-y-3">
              <div className="flex items-center space-x-3 text-sm">
                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                <span className="text-gray-400">Login successful</span>
                <span className="text-gray-500 ml-auto">Just now</span>
              </div>
              <div className="flex items-center space-x-3 text-sm">
                <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                <span className="text-gray-400">Dashboard loaded</span>
                <span className="text-gray-500 ml-auto">Just now</span>
              </div>
              <div className="flex items-center space-x-3 text-sm">
                <div className="w-2 h-2 bg-yellow-400 rounded-full"></div>
                <span className="text-gray-400">System check pending</span>
                <span className="text-gray-500 ml-auto">2 min ago</span>
              </div>
            </div>
          </motion.div>

          {/* System Status */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-gray-900/50 backdrop-blur-lg rounded-lg p-6 border border-gray-800"
          >
            <h3 className="text-xl font-semibold mb-4 flex items-center space-x-2">
              <Shield className="w-5 h-5 text-purple-400" />
              <span>System Status</span>
            </h3>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-400">API Services</span>
                  <span className="text-sm text-green-400">Operational</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <div className="bg-green-400 h-2 rounded-full" style={{ width: '100%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-400">Database</span>
                  <span className="text-sm text-green-400">Healthy</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <div className="bg-green-400 h-2 rounded-full" style={{ width: '98%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-400">Cache</span>
                  <span className="text-sm text-yellow-400">Warning</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <div className="bg-yellow-400 h-2 rounded-full" style={{ width: '75%' }}></div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
};

// Memoize Dashboard to prevent unnecessary re-renders that trigger API calls
export default memo(Dashboard);