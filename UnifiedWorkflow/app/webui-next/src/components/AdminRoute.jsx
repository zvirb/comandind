import React, { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { SecureAuth } from '../utils/secureAuth';

const AdminRoute = ({ children }) => {
  const [isAuthorized, setIsAuthorized] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAdminAccess();
  }, []);

  const checkAdminAccess = async () => {
    try {
      // Check if user is authenticated first
      const isAuthenticated = await SecureAuth.isAuthenticated();
      
      if (!isAuthenticated) {
        setIsAuthorized(false);
        setLoading(false);
        return;
      }

      // Check admin status via secure endpoint
      const response = await SecureAuth.makeSecureRequest('/api/v1/auth/admin-status');
      
      if (response.ok) {
        const data = await response.json();
        setIsAuthorized(data.is_admin || false);
      } else {
        setIsAuthorized(false);
      }
    } catch (error) {
      console.error('Admin access check error:', error);
      setIsAuthorized(false);
    } finally {
      setLoading(false);
    }
  };

  // Show loading state while checking authorization
  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400">Checking admin access...</p>
        </div>
      </div>
    );
  }

  // If not authorized, redirect to dashboard
  if (!isAuthorized) {
    return <Navigate to="/dashboard" replace state={{ error: 'Admin access required' }} />;
  }

  // If authorized, render the admin component
  return children;
};

export default AdminRoute;