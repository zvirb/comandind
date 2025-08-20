import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Mail, Lock, Eye, EyeOff, AlertCircle, CheckCircle, LogIn } from 'lucide-react';

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [formData, setFormData] = useState({
    emailOrUsername: '',
    password: '',
    rememberMe: false
  });

  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');

  // Check for registration success message
  useEffect(() => {
    if (location.state?.message) {
      setSuccessMessage(location.state.message);
      // Clear the message from location state
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  const validateForm = () => {
    const newErrors = {};

    // Enhanced field validation
    if (!formData.emailOrUsername.trim()) {
      newErrors.emailOrUsername = 'Email or username is required';
    } else {
      // Validate email format if it contains @
      const isEmail = formData.emailOrUsername.includes('@');
      if (isEmail) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(formData.emailOrUsername)) {
          newErrors.emailOrUsername = 'Please enter a valid email address';
        }
      } else {
        // Validate username format (alphanumeric and underscores, 3+ chars)
        const usernameRegex = /^[a-zA-Z0-9_]{3,}$/;
        if (!usernameRegex.test(formData.emailOrUsername)) {
          newErrors.emailOrUsername = 'Username must be at least 3 characters (letters, numbers, underscores only)';
        }
      }
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    
    // Clear error for this field when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus(null);
    setSuccessMessage('');

    try {
      // Determine if input is email or username
      const isEmail = formData.emailOrUsername.includes('@');
      
      const loginResponse = await fetch('/api/v1/auth/jwt/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: isEmail ? formData.emailOrUsername : undefined,
          username: !isEmail ? formData.emailOrUsername : undefined,
          password: formData.password
        }),
        credentials: 'include' // Important for cookies
      });

      if (!loginResponse.ok) {
        const errorData = await loginResponse.json().catch(() => ({}));
        
        if (loginResponse.status === 401) {
          throw new Error('Incorrect email/username or password');
        } else if (loginResponse.status === 403) {
          throw new Error('Your account is not active. Please contact support.');
        } else {
          throw new Error(errorData.detail || 'Login failed. Please try again.');
        }
      }

      const loginData = await loginResponse.json();
      
      // Authentication is now handled via secure httpOnly cookies
      // No token storage needed in localStorage for security

      // Store remember me preference (non-sensitive data)
      if (formData.rememberMe) {
        localStorage.setItem('rememberMe', 'true');
      } else {
        localStorage.removeItem('rememberMe');
      }

      setSubmitStatus('success');
      
      // Store the access token in localStorage as fallback for authentication
      // This ensures the frontend can check authentication immediately after login
      if (loginData.access_token) {
        localStorage.setItem('authToken', loginData.access_token);
      }
      
      // Optimized redirect to dashboard or intended page
      setTimeout(() => {
        // Check if there's a redirect URL in the query params or location state
        const params = new URLSearchParams(location.search);
        const redirectTo = params.get('redirect') || 
                          location.state?.from || 
                          '/dashboard';
        
        console.log('Login: Redirecting to:', redirectTo);
        navigate(redirectTo, { replace: true }); // Use replace to prevent back button issues
      }, 1000); // Reduced delay for better UX
      
    } catch (error) {
      console.error('Login error:', error);
      setSubmitStatus('error');
      
      // Enhanced error handling with user-friendly messages
      let errorMessage = 'Login failed. Please try again.';
      if (error.message.includes('Incorrect')) {
        errorMessage = 'Invalid email/username or password. Please check your credentials.';
      } else if (error.message.includes('network') || error.message.includes('fetch')) {
        errorMessage = 'Network error. Please check your connection and try again.';
      } else if (error.message.includes('timeout')) {
        errorMessage = 'Request timed out. Please try again.';
      }
      
      setErrors({ submit: errorMessage });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      {/* Background Effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse"></div>
        <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-pink-600 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-violet-600 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
      </div>

      {/* Login Form Container */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="glass-morphism rounded-3xl p-8 md:p-10">
          {/* Logo/Icon */}
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
            className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center"
          >
            <LogIn size={32} className="text-white" />
          </motion.div>

          {/* Header */}
          <div className="text-center mb-8">
            <motion.h1
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent mb-2"
            >
              Welcome Back
            </motion.h1>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="text-gray-300"
            >
              Sign in to continue to your account
            </motion.p>
          </div>

          {/* Success Message from Registration */}
          {successMessage && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-green-500/10 border border-green-500/30 rounded-lg"
            >
              <p className="text-green-400 flex items-center">
                <CheckCircle className="mr-2" size={18} />
                {successMessage}
              </p>
            </motion.div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Email/Username Field */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 }}
            >
              <label className="block text-sm font-medium text-gray-300 mb-2">
                <Mail className="inline mr-1" size={16} />
                Email or Username
                <span className="text-xs text-gray-400 block mt-1">
                  {formData.emailOrUsername.includes('@') ? 'Email format: user@domain.com' : 'Username format: letters, numbers, underscores (3+ chars)'}
                </span>
              </label>
              <input
                type="text"
                name="emailOrUsername"
                value={formData.emailOrUsername}
                onChange={handleChange}
                autoComplete="username"
                className={`w-full px-4 py-3 bg-white/10 border ${
                  errors.emailOrUsername ? 'border-red-400' : 
                  formData.emailOrUsername && !errors.emailOrUsername ? 'border-green-400' :
                  'border-white/20'
                } rounded-lg focus:outline-none focus:border-purple-400 text-white placeholder-gray-400 transition-colors`}
                placeholder="Enter your email or username"
              />
              {errors.emailOrUsername && (
                <p className="mt-2 text-sm text-red-400 flex items-center">
                  <AlertCircle size={14} className="mr-1" />
                  {errors.emailOrUsername}
                </p>
              )}
            </motion.div>

            {/* Password Field */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 }}
            >
              <label className="block text-sm font-medium text-gray-300 mb-2">
                <Lock className="inline mr-1" size={16} />
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  autoComplete="current-password"
                  className={`w-full px-4 py-3 pr-12 bg-white/10 border ${
                    errors.password ? 'border-red-400' : 
                    formData.password && !errors.password ? 'border-green-400' :
                    'border-white/20'
                  } rounded-lg focus:outline-none focus:border-purple-400 text-white placeholder-gray-400 transition-colors`}
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
              {errors.password && (
                <p className="mt-2 text-sm text-red-400 flex items-center">
                  <AlertCircle size={14} className="mr-1" />
                  {errors.password}
                </p>
              )}
            </motion.div>

            {/* Remember Me & Forgot Password */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
              className="flex items-center justify-between"
            >
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  name="rememberMe"
                  checked={formData.rememberMe}
                  onChange={handleChange}
                  className="w-4 h-4 bg-white/10 border border-white/20 rounded focus:ring-purple-400 focus:ring-2 text-purple-500"
                />
                <span className="ml-2 text-sm text-gray-300">Remember me</span>
              </label>
              
              <Link
                to="/forgot-password"
                className="text-sm text-purple-400 hover:text-purple-300 transition-colors"
              >
                Forgot password?
              </Link>
            </motion.div>

            {/* Submit Error */}
            {errors.submit && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg"
              >
                <p className="text-red-400 flex items-center">
                  <AlertCircle className="mr-2" />
                  {errors.submit}
                </p>
              </motion.div>
            )}

            {/* Success Message */}
            {submitStatus === 'success' && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg"
              >
                <p className="text-green-400 flex items-center">
                  <CheckCircle className="mr-2" />
                  Login successful! Redirecting...
                </p>
              </motion.div>
            )}

            {/* Submit Button */}
            <motion.button
              type="submit"
              disabled={isSubmitting || Object.keys(errors).length > 0}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
              whileHover={{ scale: isSubmitting ? 1 : 1.02 }}
              whileTap={{ scale: isSubmitting ? 1 : 0.98 }}
              className={`w-full py-3 px-6 rounded-lg font-medium transition-all ${
                isSubmitting || Object.keys(errors).length > 0
                  ? 'bg-gray-600 cursor-not-allowed opacity-60'
                  : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 hover:shadow-lg hover:shadow-purple-500/25'
              } text-white`}
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span className="animate-pulse">Authenticating...</span>
                </span>
              ) : (
                <span className="flex items-center justify-center">
                  <LogIn className="mr-2" size={18} />
                  Sign In
                </span>
              )}
            </motion.button>


            {/* Footer Link */}
            <p className="text-center text-gray-300 mt-6">
              Don't have an account?{' '}
              <Link to="/register" className="text-purple-400 hover:text-purple-300 font-medium transition-colors">
                Register here.
              </Link>
            </p>
          </form>
        </div>
      </motion.div>

      {/* Animated Background Gradient */}
      <style jsx>{`
        @keyframes blob {
          0% {
            transform: translate(0px, 0px) scale(1);
          }
          33% {
            transform: translate(30px, -50px) scale(1.1);
          }
          66% {
            transform: translate(-20px, 20px) scale(0.9);
          }
          100% {
            transform: translate(0px, 0px) scale(1);
          }
        }
        .animate-blob {
          animation: blob 7s infinite;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
      `}</style>
    </div>
  );
};

export default Login;