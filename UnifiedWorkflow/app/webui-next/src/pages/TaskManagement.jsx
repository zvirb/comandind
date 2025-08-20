import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  CheckSquare, 
  Plus, 
  Calendar, 
  User, 
  Clock, 
  Flag,
  MoreVertical,
  Edit,
  Trash2,
  Filter,
  Search,
  Home,
  LogOut
} from 'lucide-react';
import { SecureAuth } from '../utils/secureAuth';

const TaskManagement = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState([]);
  const [filteredTasks, setFilteredTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterPriority, setFilterPriority] = useState('all');

  useEffect(() => {
    fetchTasks();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [tasks, searchTerm, filterStatus, filterPriority]);

  const fetchTasks = async () => {
    try {
      const response = await SecureAuth.makeSecureRequest('/api/v1/tasks', {
        method: 'GET'
      });

      if (response.status === 401) {
        SecureAuth.handleAuthenticationFailure();
        return;
      }

      if (!response.ok) {
        throw new Error('Failed to fetch tasks');
      }

      const data = await response.json();
      setTasks(data.tasks || []);
    } catch (error) {
      console.error('Task fetch error:', error);
      // Use mock data for development
      setTasks([
        {
          id: 1,
          title: "Implement user authentication",
          description: "Add JWT-based authentication system",
          status: "in_progress",
          priority: "high",
          assignee: "john.doe@example.com",
          due_date: "2024-01-15",
          created_at: "2024-01-01T10:00:00Z"
        },
        {
          id: 2,
          title: "Design API documentation",
          description: "Create comprehensive API documentation",
          status: "pending",
          priority: "medium",
          assignee: "jane.smith@example.com",
          due_date: "2024-01-20",
          created_at: "2024-01-02T09:00:00Z"
        },
        {
          id: 3,
          title: "Database optimization",
          description: "Optimize database queries for better performance",
          status: "completed",
          priority: "low",
          assignee: "bob.wilson@example.com",
          due_date: "2024-01-10",
          created_at: "2023-12-28T14:00:00Z"
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = tasks;

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(task => 
        task.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        task.description.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter(task => task.status === filterStatus);
    }

    // Priority filter
    if (filterPriority !== 'all') {
      filtered = filtered.filter(task => task.priority === filterPriority);
    }

    setFilteredTasks(filtered);
  };

  const handleLogout = () => {
    SecureAuth.logout();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'text-green-400 bg-green-900/30 border-green-600/50';
      case 'in_progress': return 'text-blue-400 bg-blue-900/30 border-blue-600/50';
      case 'pending': return 'text-yellow-400 bg-yellow-900/30 border-yellow-600/50';
      default: return 'text-gray-400 bg-gray-900/30 border-gray-600/50';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'text-red-400';
      case 'medium': return 'text-yellow-400';
      case 'low': return 'text-green-400';
      default: return 'text-gray-400';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400">Loading tasks...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-green-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse delay-1000"></div>
      </div>

      {/* Header */}
      <header className="border-b border-gray-800 bg-black/50 backdrop-blur-lg sticky top-0 z-20">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <CheckSquare className="w-8 h-8 text-green-400" />
              <h1 className="text-2xl font-bold bg-gradient-to-r from-green-400 to-blue-400 bg-clip-text text-transparent">
                Task Management
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 transition"
              >
                <Plus className="w-4 h-4" />
                <span className="text-sm">New Task</span>
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
        {/* Filters and Search */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gray-900/50 backdrop-blur-lg rounded-lg p-6 border border-gray-800 mb-8"
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search tasks..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
              />
            </div>

            {/* Status Filter */}
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-green-500"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
            </select>

            {/* Priority Filter */}
            <select
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value)}
              className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-green-500"
            >
              <option value="all">All Priority</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            {/* Task Count */}
            <div className="flex items-center justify-end">
              <span className="text-sm text-gray-400">
                {filteredTasks.length} of {tasks.length} tasks
              </span>
            </div>
          </div>
        </motion.div>

        {/* Task Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          <AnimatePresence>
            {filteredTasks.map((task, index) => (
              <motion.div
                key={task.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ delay: index * 0.1 }}
                className="bg-gray-900/50 backdrop-blur-lg rounded-lg p-6 border border-gray-800 hover:border-green-500/50 transition group"
              >
                {/* Task Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg mb-1 group-hover:text-green-400 transition">
                      {task.title}
                    </h3>
                    <p className="text-sm text-gray-400 line-clamp-2">
                      {task.description}
                    </p>
                  </div>
                  <button className="p-1 hover:bg-gray-800 rounded transition">
                    <MoreVertical className="w-4 h-4 text-gray-400" />
                  </button>
                </div>

                {/* Status and Priority */}
                <div className="flex items-center space-x-2 mb-4">
                  <span className={`px-2 py-1 rounded-full text-xs border ${getStatusColor(task.status)}`}>
                    {task.status.replace('_', ' ')}
                  </span>
                  <Flag className={`w-4 h-4 ${getPriorityColor(task.priority)}`} />
                  <span className={`text-xs ${getPriorityColor(task.priority)}`}>
                    {task.priority}
                  </span>
                </div>

                {/* Task Details */}
                <div className="space-y-2 text-sm text-gray-400">
                  <div className="flex items-center space-x-2">
                    <User className="w-4 h-4" />
                    <span>{task.assignee}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Calendar className="w-4 h-4" />
                    <span>Due: {formatDate(task.due_date)}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Clock className="w-4 h-4" />
                    <span>Created: {formatDate(task.created_at)}</span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center space-x-2 mt-4 pt-4 border-t border-gray-800">
                  <button className="flex items-center space-x-1 px-3 py-1 bg-blue-900/30 text-blue-400 rounded hover:bg-blue-900/50 transition text-xs">
                    <Edit className="w-3 h-3" />
                    <span>Edit</span>
                  </button>
                  <button className="flex items-center space-x-1 px-3 py-1 bg-red-900/30 text-red-400 rounded hover:bg-red-900/50 transition text-xs">
                    <Trash2 className="w-3 h-3" />
                    <span>Delete</span>
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>

        {/* Empty State */}
        {filteredTasks.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-12"
          >
            <CheckSquare className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-400 mb-2">No tasks found</h3>
            <p className="text-gray-500 mb-4">
              {searchTerm || filterStatus !== 'all' || filterPriority !== 'all' 
                ? 'Try adjusting your filters or search term.' 
                : 'Create your first task to get started.'}
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-6 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition"
            >
              Create Task
            </button>
          </motion.div>
        )}
      </main>

      {/* Create Task Modal Placeholder */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-lg p-6 border border-gray-800 max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold mb-4">Create New Task</h3>
            <p className="text-gray-400 mb-4">Task creation form coming soon!</p>
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskManagement;