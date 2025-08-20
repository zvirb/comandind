import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  Folder, 
  Plus, 
  Users, 
  Calendar, 
  BarChart3, 
  Clock,
  Star,
  GitBranch,
  Activity,
  Settings,
  Eye,
  Edit,
  Trash2,
  Filter,
  Search,
  Home,
  LogOut,
  AlertCircle,
  Wifi,
  WifiOff
} from 'lucide-react';
import { SecureAuth } from '../utils/secureAuth';
import { notifications } from '../utils/notificationSystem';
import { offline } from '../utils/offlineManager';
import { 
  withMemo, 
  listPropsEqual, 
  useVirtualScrolling, 
  useDebounce, 
  useOptimisticUpdate,
  usePerformanceMonitor 
} from '../utils/performanceOptimization';

const ProjectManagement = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [isOnline, setIsOnline] = useState(offline.isOnline());
  const [mockDataMode, setMockDataMode] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  // Performance monitoring in development
  usePerformanceMonitor('ProjectManagement');

  // Debounced search term for performance
  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  // Optimistic updates for better UX
  const {
    data: optimisticProjects,
    isUpdating: isOptimisticUpdating,
    optimisticUpdate
  } = useOptimisticUpdate(projects, async (newData) => {
    // This will be used for project operations
    return newData;
  });

  // Filtered projects with memoization for performance
  const filteredProjects = useMemo(() => {
    let filtered = optimisticProjects;

    // Search filter
    if (debouncedSearchTerm) {
      filtered = filtered.filter(project => 
        project.name.toLowerCase().includes(debouncedSearchTerm.toLowerCase()) ||
        project.description.toLowerCase().includes(debouncedSearchTerm.toLowerCase()) ||
        project.tags.some(tag => tag.toLowerCase().includes(debouncedSearchTerm.toLowerCase()))
      );
    }

    // Status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter(project => project.status === filterStatus);
    }

    return filtered;
  }, [optimisticProjects, debouncedSearchTerm, filterStatus]);

  useEffect(() => {
    fetchProjects();
    
    // Setup offline status listener
    const unsubscribeOffline = offline.addListener((status) => {
      setIsOnline(status);
      if (status && retryCount > 0) {
        // Retry failed requests when back online
        notifications.info('Connection restored, retrying failed requests...', {
          duration: 3000
        });
        setTimeout(() => {
          fetchProjects();
        }, 1000);
      }
    });

    return unsubscribeOffline;
  }, [retryCount]);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const result = await offline.makeRequest('/api/v1/projects', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${SecureAuth.getAuthToken()}`,
          'Content-Type': 'application/json'
        }
      }, {
        cacheKey: 'projects_list',
        useCache: true,
        cacheFirst: false
      });

      if (result.fromCache && !isOnline) {
        notifications.info('Showing cached project data', {
          title: 'Offline Mode',
          duration: 4000
        });
        setMockDataMode(true);
      } else {
        setMockDataMode(false);
      }

      // Handle authentication errors
      if (result.response && result.response.status === 401) {
        notifications.handleAuthError();
        return;
      }

      setProjects(result.data.projects || result.data || []);
      setRetryCount(0); // Reset retry count on success
    } catch (error) {
      console.error('Project fetch error:', error);
      setRetryCount(prev => prev + 1);
      
      // Check if we have cached data as fallback
      const cachedData = offline.getCachedData('projects_list');
      if (cachedData) {
        setProjects(cachedData.projects || cachedData);
        setMockDataMode(true);
        notifications.warning('Using cached data due to connection issues', {
          title: 'Connection Problems',
          duration: 5000
        });
      } else {
        // Use mock data as final fallback
        setProjects(getMockProjects());
        setMockDataMode(true);
        notifications.handleApiError(error, {
          title: 'Failed to Load Projects',
          action: {
            label: 'Retry',
            callback: () => fetchProjects()
          }
        });
      }
    } finally {
      setLoading(false);
    }
  }, [isOnline]);

  const getMockProjects = () => [
    {
      id: 1,
      name: "AI Workflow Engine",
      description: "Comprehensive AI workflow automation platform",
      status: "active",
      progress: 75,
      team_size: 8,
      start_date: "2023-12-01",
      end_date: "2024-03-01",
      priority: "high",
      tags: ["AI", "Automation", "Backend"],
      owner: "john.doe@example.com"
    },
    {
      id: 2,
      name: "Data Analytics Dashboard",
      description: "Real-time analytics and reporting dashboard",
      status: "planning",
      progress: 15,
      team_size: 5,
      start_date: "2024-01-15",
      end_date: "2024-05-15",
      priority: "medium",
      tags: ["Analytics", "Dashboard", "Frontend"],
      owner: "jane.smith@example.com"
    },
    {
      id: 3,
      name: "Mobile App Integration",
      description: "Mobile application for workflow management",
      status: "completed",
      progress: 100,
      team_size: 6,
      start_date: "2023-09-01",
      end_date: "2023-12-15",
      priority: "low",
      tags: ["Mobile", "Integration", "React Native"],
      owner: "bob.wilson@example.com"
    },
    {
      id: 4,
      name: "Security Enhancement",
      description: "Advanced security features and compliance updates",
      status: "on_hold",
      progress: 40,
      team_size: 3,
      start_date: "2023-11-01",
      end_date: "2024-02-01",
      priority: "high",
      tags: ["Security", "Compliance", "Backend"],
      owner: "alice.johnson@example.com"
    }
  ];

  const handleSearchChange = useCallback((e) => {
    setSearchTerm(e.target.value);
  }, []);

  const handleStatusFilterChange = useCallback((e) => {
    setFilterStatus(e.target.value);
  }, []);

  const handleViewModeChange = useCallback((mode) => {
    setViewMode(mode);
  }, []);

  const handleLogout = () => {
    SecureAuth.logout();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'text-green-400 bg-green-900/30 border-green-600/50';
      case 'planning': return 'text-blue-400 bg-blue-900/30 border-blue-600/50';
      case 'completed': return 'text-purple-400 bg-purple-900/30 border-purple-600/50';
      case 'on_hold': return 'text-yellow-400 bg-yellow-900/30 border-yellow-600/50';
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

  const getProgressColor = (progress) => {
    if (progress >= 80) return 'bg-green-500';
    if (progress >= 50) return 'bg-blue-500';
    if (progress >= 25) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400">Loading projects...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-pink-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse delay-1000"></div>
      </div>

      {/* Header */}
      <header className="border-b border-gray-800 bg-black/50 backdrop-blur-lg sticky top-0 z-20">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Folder className="w-8 h-8 text-purple-400" />
              <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                Project Management
              </h1>
              {mockDataMode && (
                <div className="flex items-center space-x-2 px-3 py-1 bg-yellow-900/30 border border-yellow-600/50 rounded-lg">
                  <AlertCircle className="w-4 h-4 text-yellow-400" />
                  <span className="text-yellow-300 text-sm font-medium">
                    {isOnline ? 'Demo Data' : 'Offline Mode'}
                  </span>
                </div>
              )}
              <div className="flex items-center space-x-2">
                {isOnline ? (
                  <Wifi className="w-5 h-5 text-green-400" title="Online" />
                ) : (
                  <WifiOff className="w-5 h-5 text-red-400" title="Offline" />
                )}
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 transition"
              >
                <Plus className="w-4 h-4" />
                <span className="text-sm">New Project</span>
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
                placeholder="Search projects..."
                value={searchTerm}
                onChange={handleSearchChange}
                className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
              />
            </div>

            {/* Status Filter */}
            <select
              value={filterStatus}
              onChange={handleStatusFilterChange}
              className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
            >
              <option value="all">All Status</option>
              <option value="planning">Planning</option>
              <option value="active">Active</option>
              <option value="on_hold">On Hold</option>
              <option value="completed">Completed</option>
            </select>

            {/* View Mode Toggle */}
            <div className="flex space-x-2">
              <button
                onClick={() => handleViewModeChange('grid')}
                className={`flex-1 px-4 py-2 rounded-lg border transition ${
                  viewMode === 'grid' 
                    ? 'bg-purple-600 border-purple-600 text-white' 
                    : 'bg-gray-800 border-gray-700 text-gray-400'
                }`}
              >
                Grid
              </button>
              <button
                onClick={() => handleViewModeChange('list')}
                className={`flex-1 px-4 py-2 rounded-lg border transition ${
                  viewMode === 'list' 
                    ? 'bg-purple-600 border-purple-600 text-white' 
                    : 'bg-gray-800 border-gray-700 text-gray-400'
                }`}
              >
                List
              </button>
            </div>

            {/* Project Count */}
            <div className="flex items-center justify-end">
              <span className="text-sm text-gray-400">
                {filteredProjects.length} of {optimisticProjects.length} projects
                {isOptimisticUpdating && (
                  <span className="ml-2 text-purple-400">(updating...)</span>
                )}
              </span>
            </div>
          </div>
        </motion.div>

        {/* Project Cards - Optimized with Memoization */}
        <ProjectList
          projects={filteredProjects}
          viewMode={viewMode}
          mockDataMode={mockDataMode}
          isOnline={isOnline}
        />

        {/* Empty State */}
        {filteredProjects.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-12"
          >
            <Folder className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-400 mb-2">No projects found</h3>
            <p className="text-gray-500 mb-4">
              {searchTerm || filterStatus !== 'all' 
                ? 'Try adjusting your filters or search term.' 
                : 'Create your first project to get started.'}
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-6 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition"
            >
              Create Project
            </button>
          </motion.div>
        )}
      </main>

      {/* Create Project Modal */}
      {showCreateModal && <CreateProjectModal onClose={() => setShowCreateModal(false)} onProjectCreated={fetchProjects} />}
    </div>
  );
};

// Enhanced Create Project Modal Component with Error Handling
const CreateProjectModal = ({ onClose, onProjectCreated }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    priority: 'medium',
    status: 'planning',
    start_date: '',
    end_date: '',
    tags: '',
    owner: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitAttempted, setSubmitAttempted] = useState(false);

  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear errors as user types (but only after first submit attempt)
    if (errors[name] && submitAttempted) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  }, [errors, submitAttempted]);

  const validateForm = () => {
    const newErrors = {};
    if (!formData.name.trim()) newErrors.name = 'Project name is required';
    if (!formData.description.trim()) newErrors.description = 'Description is required';
    if (!formData.start_date) newErrors.start_date = 'Start date is required';
    if (!formData.end_date) newErrors.end_date = 'End date is required';
    if (!formData.owner.trim()) newErrors.owner = 'Project owner is required';
    
    if (formData.start_date && formData.end_date && formData.start_date >= formData.end_date) {
      newErrors.end_date = 'End date must be after start date';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    setSubmitAttempted(true);
    
    if (!validateForm()) {
      notifications.error('Please fix the form errors before submitting', {
        title: 'Form Validation Failed',
        duration: 4000
      });
      return;
    }

    if (!offline.isOnline()) {
      notifications.warning('Cannot create projects while offline', {
        title: 'Offline Mode',
        duration: 5000
      });
      return;
    }

    setIsSubmitting(true);
    const loadingId = notifications.loading('Creating project...', {
      title: 'Please Wait'
    });

    try {
      const result = await offline.makeRequest('/api/v1/projects', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${SecureAuth.getAuthToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          tags: formData.tags.split(',').map(tag => tag.trim()).filter(tag => tag)
        })
      }, {
        cacheKey: 'projects_list', // Invalidate cache
        useCache: false
      });

      if (result.response && result.response.status === 401) {
        notifications.handleAuthError();
        return;
      }

      if (result.response && !result.response.ok) {
        throw new Error(`Failed to create project: ${result.response.status}`);
      }

      notifications.success('Project created successfully!', {
        title: 'Success',
        duration: 4000
      });
      
      onProjectCreated();
      onClose();
    } catch (error) {
      console.error('Project creation error:', error);
      notifications.handleApiError(error, {
        title: 'Project Creation Failed'
      });
      setErrors({ submit: error.message });
    } finally {
      notifications.dismiss(loadingId);
      setIsSubmitting(false);
    }
  }, [formData, onProjectCreated, onClose, submitAttempted]);

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="bg-gray-900 rounded-lg p-6 border border-gray-800 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
      >
        <h3 className="text-2xl font-bold mb-6 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
          Create New Project
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Project Name */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Project Name *</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                className={`w-full px-3 py-2 bg-gray-800 border ${errors.name ? 'border-red-500' : 'border-gray-700'} rounded-lg text-white focus:outline-none focus:border-purple-500`}
                placeholder="Enter project name"
              />
              {errors.name && <p className="text-red-400 text-sm mt-1">{errors.name}</p>}
            </div>

            {/* Owner */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Project Owner *</label>
              <input
                type="email"
                name="owner"
                value={formData.owner}
                onChange={handleChange}
                className={`w-full px-3 py-2 bg-gray-800 border ${errors.owner ? 'border-red-500' : 'border-gray-700'} rounded-lg text-white focus:outline-none focus:border-purple-500`}
                placeholder="owner@example.com"
              />
              {errors.owner && <p className="text-red-400 text-sm mt-1">{errors.owner}</p>}
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Description *</label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              rows={3}
              className={`w-full px-3 py-2 bg-gray-800 border ${errors.description ? 'border-red-500' : 'border-gray-700'} rounded-lg text-white focus:outline-none focus:border-purple-500`}
              placeholder="Describe your project..."
            />
            {errors.description && <p className="text-red-400 text-sm mt-1">{errors.description}</p>}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Priority */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Priority</label>
              <select
                name="priority"
                value={formData.priority}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>

            {/* Status */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Status</label>
              <select
                name="status"
                value={formData.status}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
              >
                <option value="planning">Planning</option>
                <option value="active">Active</option>
                <option value="on_hold">On Hold</option>
                <option value="completed">Completed</option>
              </select>
            </div>

            {/* Tags */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Tags</label>
              <input
                type="text"
                name="tags"
                value={formData.tags}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                placeholder="tag1, tag2, tag3"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Start Date */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Start Date *</label>
              <input
                type="date"
                name="start_date"
                value={formData.start_date}
                onChange={handleChange}
                className={`w-full px-3 py-2 bg-gray-800 border ${errors.start_date ? 'border-red-500' : 'border-gray-700'} rounded-lg text-white focus:outline-none focus:border-purple-500`}
              />
              {errors.start_date && <p className="text-red-400 text-sm mt-1">{errors.start_date}</p>}
            </div>

            {/* End Date */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">End Date *</label>
              <input
                type="date"
                name="end_date"
                value={formData.end_date}
                onChange={handleChange}
                className={`w-full px-3 py-2 bg-gray-800 border ${errors.end_date ? 'border-red-500' : 'border-gray-700'} rounded-lg text-white focus:outline-none focus:border-purple-500`}
              />
              {errors.end_date && <p className="text-red-400 text-sm mt-1">{errors.end_date}</p>}
            </div>
          </div>

          {/* Submit Error */}
          {errors.submit && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-red-400 text-sm">{errors.submit}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className={`px-6 py-2 rounded-lg transition ${
                isSubmitting
                  ? 'bg-gray-600 cursor-not-allowed'
                  : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600'
              } text-white`}
            >
              {isSubmitting ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};

// Memoized Project List Component for Performance
const ProjectList = ({ projects, viewMode, mockDataMode, isOnline }) => {
  const getStatusColor = useCallback((status) => {
    switch (status) {
      case 'active': return 'text-green-400 bg-green-900/30 border-green-600/50';
      case 'planning': return 'text-blue-400 bg-blue-900/30 border-blue-600/50';
      case 'completed': return 'text-purple-400 bg-purple-900/30 border-purple-600/50';
      case 'on_hold': return 'text-yellow-400 bg-yellow-900/30 border-yellow-600/50';
      default: return 'text-gray-400 bg-gray-900/30 border-gray-600/50';
    }
  }, []);

  const getPriorityColor = useCallback((priority) => {
    switch (priority) {
      case 'high': return 'text-red-400';
      case 'medium': return 'text-yellow-400';
      case 'low': return 'text-green-400';
      default: return 'text-gray-400';
    }
  }, []);

  const getProgressColor = useCallback((progress) => {
    if (progress >= 80) return 'bg-green-500';
    if (progress >= 50) return 'bg-blue-500';
    if (progress >= 25) return 'bg-yellow-500';
    return 'bg-red-500';
  }, []);

  const formatDate = useCallback((dateString) => {
    return new Date(dateString).toLocaleDateString();
  }, []);

  if (projects.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-center py-12"
      >
        <Folder className="w-16 h-16 text-gray-600 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-gray-400 mb-2">No projects found</h3>
        <p className="text-gray-500 mb-4">
          {mockDataMode 
            ? 'No cached projects available. Try refreshing when online.' 
            : 'Create your first project to get started.'}
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className={viewMode === 'grid' 
        ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" 
        : "space-y-4"
      }
    >
      <AnimatePresence mode="popLayout">
        {projects.map((project, index) => (
          <ProjectCard
            key={project.id}
            project={project}
            index={index}
            viewMode={viewMode}
            mockDataMode={mockDataMode}
            getStatusColor={getStatusColor}
            getPriorityColor={getPriorityColor}
            getProgressColor={getProgressColor}
            formatDate={formatDate}
          />
        ))}
      </AnimatePresence>
    </motion.div>
  );
};

// Individual Project Card Component
const ProjectCard = ({ 
  project, 
  index, 
  viewMode, 
  mockDataMode,
  getStatusColor,
  getPriorityColor, 
  getProgressColor, 
  formatDate 
}) => {
  const handleActionClick = useCallback((action, projectId) => {
    if (mockDataMode) {
      notifications.warning(`${action} is not available in ${offline.isOnline() ? 'demo' : 'offline'} mode`, {
        title: 'Limited Functionality',
        duration: 3000
      });
      return;
    }
    // Handle actual actions when online
    console.log(`${action} clicked for project ${projectId}`);
  }, [mockDataMode]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ delay: index * 0.05 }}
      className={`bg-gray-900/50 backdrop-blur-lg rounded-lg p-6 border border-gray-800 hover:border-purple-500/50 transition group ${
        viewMode === 'list' ? 'flex items-center space-x-6' : ''
      } ${mockDataMode ? 'border-yellow-600/30' : ''}`}
    >
      {/* Project Header */}
      <div className={viewMode === 'list' ? 'flex-1' : 'mb-4'}>
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-semibold text-lg group-hover:text-purple-400 transition">
            {project.name}
          </h3>
          <Star className="w-4 h-4 text-gray-400 hover:text-yellow-400 cursor-pointer transition" />
        </div>
        <p className="text-sm text-gray-400 mb-3">
          {project.description}
        </p>

        {/* Status and Priority */}
        <div className="flex items-center space-x-2 mb-3">
          <span className={`px-2 py-1 rounded-full text-xs border ${getStatusColor(project.status)}`}>
            {project.status.replace('_', ' ')}
          </span>
          <span className={`text-xs ${getPriorityColor(project.priority)}`}>
            {project.priority} priority
          </span>
          {mockDataMode && (
            <span className="px-2 py-1 rounded-full text-xs bg-yellow-900/30 border-yellow-600/50 text-yellow-300">
              {offline.isOnline() ? 'Demo' : 'Cached'}
            </span>
          )}
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1 mb-3">
          {project.tags.map((tag, idx) => (
            <span key={idx} className="px-2 py-1 bg-gray-800 text-xs rounded text-gray-300">
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Project Stats */}
      <div className={viewMode === 'list' ? 'flex items-center space-x-8' : 'space-y-3'}>
        {/* Progress */}
        <div className={viewMode === 'list' ? 'w-24' : ''}>
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-gray-400">Progress</span>
            <span className="text-xs font-medium">{project.progress}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <motion.div 
              className={`h-2 rounded-full ${getProgressColor(project.progress)}`}
              initial={{ width: 0 }}
              animate={{ width: `${project.progress}%` }}
              transition={{ delay: 0.5 + index * 0.05, duration: 0.8 }}
            />
          </div>
        </div>

        {/* Project Details */}
        <div className={`text-sm text-gray-400 ${viewMode === 'list' ? 'flex space-x-6' : 'space-y-2'}`}>
          <div className="flex items-center space-x-2">
            <Users className="w-4 h-4" />
            <span>{project.team_size} members</span>
          </div>
          <div className="flex items-center space-x-2">
            <Calendar className="w-4 h-4" />
            <span>{formatDate(project.end_date)}</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className={`flex items-center space-x-2 ${viewMode === 'list' ? '' : 'mt-4 pt-4 border-t border-gray-800'}`}>
          <button 
            onClick={() => handleActionClick('View', project.id)}
            className="flex items-center space-x-1 px-3 py-1 bg-blue-900/30 text-blue-400 rounded hover:bg-blue-900/50 transition text-xs"
          >
            <Eye className="w-3 h-3" />
            <span>View</span>
          </button>
          <button 
            onClick={() => handleActionClick('Edit', project.id)}
            className="flex items-center space-x-1 px-3 py-1 bg-purple-900/30 text-purple-400 rounded hover:bg-purple-900/50 transition text-xs"
          >
            <Edit className="w-3 h-3" />
            <span>Edit</span>
          </button>
          <button 
            onClick={() => handleActionClick('Settings', project.id)}
            className="flex items-center space-x-1 px-3 py-1 bg-gray-900/30 text-gray-400 rounded hover:bg-gray-900/50 transition text-xs"
          >
            <Settings className="w-3 h-3" />
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export default ProjectManagement;