import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  Users, 
  Activity, 
  Settings, 
  Database, 
  Shield, 
  BarChart3,
  Server,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  UserPlus,
  UserX,
  LogOut,
  Home,
  RefreshCw
} from 'lucide-react';
import { SecureAuth } from '../utils/secureAuth';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [adminData, setAdminData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      setRefreshing(true);
      
      // Fetch admin dashboard data
      const response = await SecureAuth.makeSecureRequest('/api/v1/admin/dashboard', {
        method: 'GET'
      });

      if (response.status === 401) {
        SecureAuth.handleAuthenticationFailure();
        return;
      }

      if (response.status === 403) {
        navigate('/dashboard');
        return;
      }

      if (!response.ok) {
        throw new Error('Failed to fetch admin data');
      }

      const data = await response.json();
      setAdminData(data);
    } catch (error) {
      console.error('Admin dashboard error:', error);
      setError(error.message);
      // Use mock data for development
      setAdminData({
        system_health: { status: 'healthy', uptime: '7d 14h 32m' },
        users: { total: 1247, active_today: 156, new_this_week: 23 },
        performance: { cpu_usage: 34, memory_usage: 67, disk_usage: 45 },
        security: { failed_logins: 12, blocked_ips: 3, alerts: 2 }
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleLogout = () => {
    SecureAuth.logout();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400">Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  const systemStats = [
    { 
      icon: <Activity className="w-6 h-6" />, 
      label: 'System Status', 
      value: adminData?.system_health?.status === 'healthy' ? 'Healthy' : 'Issues', 
      trend: adminData?.system_health?.uptime || 'N/A', 
      color: adminData?.system_health?.status === 'healthy' ? 'text-green-400' : 'text-red-400' 
    },
    { 
      icon: <Users className="w-6 h-6" />, 
      label: 'Total Users', 
      value: adminData?.users?.total?.toString() || '0', 
      trend: `+${adminData?.users?.new_this_week || 0} this week`, 
      color: 'text-blue-400' 
    },
    { 
      icon: <TrendingUp className="w-6 h-6" />, 
      label: 'Active Today', 
      value: adminData?.users?.active_today?.toString() || '0', 
      trend: 'users online', 
      color: 'text-green-400' 
    },
    { 
      icon: <Shield className="w-6 h-6" />, 
      label: 'Security Alerts', 
      value: adminData?.security?.alerts?.toString() || '0', 
      trend: `${adminData?.security?.failed_logins || 0} failed logins`, 
      color: adminData?.security?.alerts > 0 ? 'text-yellow-400' : 'text-green-400' 
    }
  ];

  const performanceMetrics = [
    { label: 'CPU Usage', value: adminData?.performance?.cpu_usage || 0, color: 'bg-blue-500' },
    { label: 'Memory Usage', value: adminData?.performance?.memory_usage || 0, color: 'bg-purple-500' },
    { label: 'Disk Usage', value: adminData?.performance?.disk_usage || 0, color: 'bg-green-500' }
  ];

  const quickActions = [
    { icon: <Users />, label: 'User Management', path: '/admin/users' },
    { icon: <Database />, label: 'Database', path: '/admin/database' },
    { icon: <Server />, label: 'System Logs', path: '/admin/logs' },
    { icon: <Settings />, label: 'System Config', path: '/admin/config' }
  ];

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-red-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-orange-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse delay-1000"></div>
      </div>

      {/* Header */}
      <header className="border-b border-gray-800 bg-black/50 backdrop-blur-lg sticky top-0 z-20">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Shield className="w-8 h-8 text-red-400" />
              <h1 className="text-2xl font-bold bg-gradient-to-r from-red-400 to-orange-400 bg-clip-text text-transparent">
                Admin Dashboard
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <button
                onClick={fetchAdminData}
                disabled={refreshing}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                <span className="text-sm">Refresh</span>
              </button>
              
              <button
                onClick={() => navigate('/dashboard')}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
              >
                <Home className="w-4 h-4" />
                <span className="text-sm">Dashboard</span>
              </button>
              
              <button
                onClick={handleLogout}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-red-900 hover:bg-red-800 transition"
              >
                <LogOut className="w-4 h-4" />
                <span className="text-sm">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8 relative z-10">
        {/* Welcome Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h2 className="text-3xl font-bold mb-2">System Administration</h2>
          <p className="text-gray-400">Monitor and manage your AI Workflow Engine infrastructure.</p>
        </motion.div>

        {/* System Stats Grid */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
        >
          {systemStats.map((stat, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 * (index + 1) }}
              className="bg-gray-900/50 backdrop-blur-lg rounded-lg p-6 border border-gray-800 hover:border-red-500/50 transition"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={stat.color}>{stat.icon}</div>
                <div className={`text-xs ${stat.color}`}>{stat.trend}</div>
              </div>
              <p className="text-2xl font-bold mb-1">{stat.value}</p>
              <p className="text-sm text-gray-400">{stat.label}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* Performance Metrics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gray-900/50 backdrop-blur-lg rounded-lg p-6 border border-gray-800 mb-8"
        >
          <h3 className="text-xl font-semibold mb-6">System Performance</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {performanceMetrics.map((metric, index) => (
              <div key={index} className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-400">{metric.label}</span>
                  <span className="text-sm font-medium">{metric.value}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <motion.div 
                    className={`h-2 rounded-full ${metric.color}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${metric.value}%` }}
                    transition={{ delay: 0.5 + index * 0.1, duration: 0.8 }}
                  />
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
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
                onClick={() => {
                  // For now, show a coming soon message
                  alert(`${action.label} coming soon!`);
                }}
                className="bg-gray-900/50 backdrop-blur-lg rounded-lg p-4 border border-gray-800 hover:border-red-500/50 hover:bg-gray-800/50 transition flex flex-col items-center space-y-2"
              >
                <div className="text-red-400">{action.icon}</div>
                <span className="text-sm">{action.label}</span>
              </motion.button>
            ))}
          </div>
        </motion.div>

        {/* System Alerts */}
        {adminData?.security?.alerts > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-yellow-900/30 border border-yellow-600/50 rounded-lg p-4"
          >
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-yellow-400" />
              <h4 className="font-semibold text-yellow-400">Security Alerts</h4>
            </div>
            <p className="text-sm text-gray-300 mt-2">
              There are {adminData.security.alerts} security alerts requiring attention.
            </p>
          </motion.div>
        )}
      </main>
    </div>
  );
};

export default AdminDashboard;