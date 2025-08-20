import React from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { Home, ArrowLeft, Search, AlertTriangle } from 'lucide-react';

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-4">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse delay-1000"></div>
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 text-center max-w-2xl"
      >
        {/* 404 Animation */}
        <motion.div
          initial={{ y: -20 }}
          animate={{ y: 0 }}
          transition={{ 
            repeat: Infinity, 
            repeatType: "reverse", 
            duration: 2,
            ease: "easeInOut"
          }}
          className="mb-8"
        >
          <div className="text-9xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
            404
          </div>
        </motion.div>

        {/* Error Icon */}
        <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-r from-purple-600/20 to-blue-600/20 rounded-full flex items-center justify-center">
          <AlertTriangle className="w-10 h-10 text-purple-400" />
        </div>

        {/* Error Message */}
        <h1 className="text-3xl font-bold mb-4">Page Not Found</h1>
        <p className="text-gray-400 text-lg mb-8 max-w-md mx-auto">
          Oops! The page you're looking for seems to have wandered off into the digital void.
        </p>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate(-1)}
            className="px-6 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition flex items-center space-x-2"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Go Back</span>
          </motion.button>

          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Link 
              to="/"
              className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 rounded-lg transition flex items-center space-x-2 inline-block"
            >
              <Home className="w-5 h-5" />
              <span>Go Home</span>
            </Link>
          </motion.div>
        </div>

        {/* Helpful Links */}
        <div className="mt-12 p-6 bg-gray-900/50 backdrop-blur-lg rounded-xl border border-gray-800">
          <h2 className="text-lg font-semibold mb-4 flex items-center justify-center space-x-2">
            <Search className="w-5 h-5 text-purple-400" />
            <span>Looking for something specific?</span>
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <Link to="/dashboard" className="text-gray-400 hover:text-purple-400 transition">
              Dashboard
            </Link>
            <Link to="/chat" className="text-gray-400 hover:text-purple-400 transition">
              Chat
            </Link>
            <Link to="/documents" className="text-gray-400 hover:text-purple-400 transition">
              Documents
            </Link>
            <Link to="/calendar" className="text-gray-400 hover:text-purple-400 transition">
              Calendar
            </Link>
            <Link to="/settings" className="text-gray-400 hover:text-purple-400 transition">
              Settings
            </Link>
            <Link to="/login" className="text-gray-400 hover:text-purple-400 transition">
              Login
            </Link>
            <Link to="/register" className="text-gray-400 hover:text-purple-400 transition">
              Register
            </Link>
            <a href="mailto:support@aiwfe.com" className="text-gray-400 hover:text-purple-400 transition">
              Support
            </a>
          </div>
        </div>

        {/* Fun Message */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="text-gray-600 text-sm mt-8"
        >
          Error Code: LOST_IN_CYBERSPACE_404 | Time: {new Date().toLocaleTimeString()}
        </motion.p>
      </motion.div>
    </div>
  );
};

export default NotFound;