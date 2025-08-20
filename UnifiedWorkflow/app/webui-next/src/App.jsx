import React, { Suspense, useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Monitor } from 'lucide-react';
import { withErrorBoundary } from './utils/performanceOptimization.jsx';
import { createOptimizedLazyComponent } from './utils/reactPerformanceOptimizer';
import apiOptimizer, { useOptimizedAPI } from './utils/apiOptimizer';
import webglPerformanceManager from './utils/webglPerformanceManager';
import developmentToolsDetector from './utils/developmentToolsDetector';
import PerformanceDashboard from './components/PerformanceDashboard';
import { AuthProvider } from './context/AuthContext';
import AuthStatusIndicator from './components/AuthStatusIndicator';

// Lazy load components with optimization
const CosmicHero = createOptimizedLazyComponent(() => import('./pages/CosmicHero'), {
  preloadDelay: 1000
});

const Register = createOptimizedLazyComponent(() => import('./pages/Register'));
const Login = createOptimizedLazyComponent(() => import('./pages/Login'));
const ForgotPassword = createOptimizedLazyComponent(() => import('./pages/ForgotPassword'));

const DashboardWithChat = createOptimizedLazyComponent(() => import('./pages/DashboardWithChat'), {
  preloadDelay: 500 // Preload faster for critical pages
});

const Chat = createOptimizedLazyComponent(() => import('./pages/Chat'));
const Documents = createOptimizedLazyComponent(() => import('./pages/Documents'));
const Calendar = createOptimizedLazyComponent(() => import('./pages/Calendar'));
const Settings = createOptimizedLazyComponent(() => import('./pages/Settings'));
const Reflective = createOptimizedLazyComponent(() => import('./pages/Reflective'));
const AdminDashboard = createOptimizedLazyComponent(() => import('./pages/AdminDashboard'));
const TaskManagement = createOptimizedLazyComponent(() => import('./pages/TaskManagement'));
const ProjectManagement = createOptimizedLazyComponent(() => import('./pages/ProjectManagement'));
const MapsDemoPage = createOptimizedLazyComponent(() => import('./pages/MapsDemoPage'));
const BugSubmission = createOptimizedLazyComponent(() => import('./pages/BugSubmission'));
const NotFound = createOptimizedLazyComponent(() => import('./pages/NotFound'));

// Components loaded immediately
import PrivateRoute from './components/PrivateRoute';
import AdminRoute from './components/AdminRoute';
import NotificationToast from './components/NotificationToast';

function App() {
  const [showPerformanceDashboard, setShowPerformanceDashboard] = useState(false);
  const { stats } = useOptimizedAPI(apiOptimizer);

  // Initialize performance managers
  useEffect(() => {
    // API optimizer is already initialized
    // WebGL Performance Manager is now handled by individual components to prevent React cascade issues
    console.log('App performance monitoring initialized (WebGL isolated from React lifecycle)');
  }, []);

  // Keyboard shortcut for performance dashboard
  useEffect(() => {
    const handleKeyDown = (event) => {
      // Ctrl/Cmd + Shift + P to toggle performance dashboard
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'P') {
        event.preventDefault();
        setShowPerformanceDashboard(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <AuthProvider>
      <Suspense fallback={
        <div className="min-h-screen bg-black flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-400">Loading application...</p>
            <p className="text-gray-500 text-sm mt-2">Optimizing performance...</p>
          </div>
        </div>
      }>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<CosmicHero />} />
          <Route path="/register" element={<Register />} />
          <Route path="/login" element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          
          {/* Protected Routes - Require Authentication */}
          <Route path="/dashboard" element={
            <PrivateRoute>
              <DashboardWithChat />
            </PrivateRoute>
          } />
          <Route path="/chat" element={
            <PrivateRoute>
              <Chat />
            </PrivateRoute>
          } />
          <Route path="/documents" element={
            <PrivateRoute>
              <Documents />
            </PrivateRoute>
          } />
          <Route path="/calendar" element={
            <PrivateRoute>
              <Calendar />
            </PrivateRoute>
          } />
          <Route path="/settings" element={
            <PrivateRoute>
              <Settings />
            </PrivateRoute>
          } />
          <Route path="/oauth/callback" element={
            <PrivateRoute>
              <Settings />
            </PrivateRoute>
          } />
          <Route path="/reflective" element={
            <PrivateRoute>
              <Reflective />
            </PrivateRoute>
          } />
          
          {/* Admin Routes - Require admin privileges */}
          <Route path="/admin" element={
            <PrivateRoute>
              <AdminRoute>
                <AdminDashboard />
              </AdminRoute>
            </PrivateRoute>
          } />
          
          {/* Task and Project Management Routes */}
          <Route path="/tasks" element={
            <PrivateRoute>
              <TaskManagement />
            </PrivateRoute>
          } />
          <Route path="/projects" element={
            <PrivateRoute>
              <ProjectManagement />
            </PrivateRoute>
          } />
          
          {/* Maps and Weather Demo */}
          <Route path="/maps" element={
            <PrivateRoute>
              <MapsDemoPage />
            </PrivateRoute>
          } />
          <Route path="/bug-report" element={
            <PrivateRoute>
              <BugSubmission />
            </PrivateRoute>
          } />
          
          {/* 404 Catch-all Route - Must be last */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
      
      {/* Global Notification System */}
      <NotificationToast />
      
      {/* Performance Dashboard Toggle Button */}
      <button
        onClick={() => setShowPerformanceDashboard(true)}
        className="fixed bottom-4 right-4 bg-gray-800 hover:bg-gray-700 text-white p-3 rounded-full shadow-lg transition-colors z-40"
        title="Open Performance Dashboard (Ctrl+Shift+P)"
      >
        <Monitor size={20} />
      </button>
      
      {/* Performance Dashboard */}
      <PerformanceDashboard
        isOpen={showPerformanceDashboard}
        onClose={() => setShowPerformanceDashboard(false)}
      />
      
      {/* Authentication Status Indicator */}
      <div className="fixed top-4 right-4 z-50">
        <AuthStatusIndicator />
      </div>
    </AuthProvider>
  );
}

// Wrap App with error boundary
const AppWithErrorBoundary = withErrorBoundary(App, (error, errorInfo) => {
  console.error('Application error:', error, errorInfo);
  // You could send error reports here
});

export default AppWithErrorBoundary;