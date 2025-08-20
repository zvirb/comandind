import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, CheckCircle, AlertCircle, Loader } from 'lucide-react';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState(null); // null, 'success', 'error'
  const [errorMessage, setErrorMessage] = useState('');

  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate email
    if (!email.trim()) {
      setErrorMessage('Please enter your email address');
      setSubmitStatus('error');
      return;
    }
    
    if (!validateEmail(email)) {
      setErrorMessage('Please enter a valid email address');
      setSubmitStatus('error');
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus(null);
    setErrorMessage('');

    try {
      const response = await fetch('/api/v1/auth/forgot-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (response.ok) {
        setSubmitStatus('success');
      } else {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to send reset email');
      }
    } catch (error) {
      console.error('Password reset error:', error);
      setErrorMessage(error.message || 'Failed to send reset email. Please try again.');
      setSubmitStatus('error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-4">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse delay-1000"></div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        {/* Back to Login Link */}
        <Link 
          to="/login" 
          className="inline-flex items-center space-x-2 text-gray-400 hover:text-white transition mb-8"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Login</span>
        </Link>

        <div className="bg-gray-900/50 backdrop-blur-lg rounded-2xl border border-gray-800 p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-r from-purple-600 to-blue-600 rounded-full flex items-center justify-center">
              <Mail className="w-8 h-8" />
            </div>
            <h1 className="text-3xl font-bold mb-2">Forgot Password?</h1>
            <p className="text-gray-400">
              No worries! Enter your email and we'll send you reset instructions.
            </p>
          </div>

          {submitStatus === 'success' ? (
            // Success Message
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center py-8"
            >
              <div className="w-16 h-16 mx-auto mb-4 bg-green-600/20 rounded-full flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-green-400" />
              </div>
              <h2 className="text-xl font-semibold mb-2">Check Your Email</h2>
              <p className="text-gray-400 mb-6">
                We've sent password reset instructions to:
              </p>
              <p className="font-medium text-purple-400 mb-6">{email}</p>
              <p className="text-sm text-gray-500 mb-6">
                Didn't receive the email? Check your spam folder or
              </p>
              <button
                onClick={() => {
                  setSubmitStatus(null);
                  setEmail('');
                }}
                className="text-purple-400 hover:text-purple-300 transition"
              >
                Try with a different email
              </button>
            </motion.div>
          ) : (
            // Reset Form
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Email Input */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-400 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      setSubmitStatus(null);
                      setErrorMessage('');
                    }}
                    placeholder="Enter your email"
                    autoComplete="email"
                    className="w-full pl-12 pr-4 py-3 bg-gray-900/50 border border-gray-800 rounded-lg focus:outline-none focus:border-purple-500 transition"
                    disabled={isSubmitting}
                  />
                </div>
                {submitStatus === 'error' && errorMessage && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-2 flex items-center space-x-2 text-red-400 text-sm"
                  >
                    <AlertCircle className="w-4 h-4" />
                    <span>{errorMessage}</span>
                  </motion.div>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className={`w-full py-3 rounded-lg font-medium transition flex items-center justify-center space-x-2 ${
                  isSubmitting
                    ? 'bg-gray-700 cursor-not-allowed'
                    : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
                }`}
              >
                {isSubmitting ? (
                  <>
                    <Loader className="w-5 h-5 animate-spin" />
                    <span>Sending...</span>
                  </>
                ) : (
                  <span>Send Reset Instructions</span>
                )}
              </button>

              {/* Additional Links */}
              <div className="text-center space-y-2">
                <p className="text-gray-400 text-sm">
                  Remember your password?{' '}
                  <Link to="/login" className="text-purple-400 hover:text-purple-300 transition">
                    Sign in
                  </Link>
                </p>
                <p className="text-gray-400 text-sm">
                  Don't have an account?{' '}
                  <Link to="/register" className="text-purple-400 hover:text-purple-300 transition">
                    Sign up
                  </Link>
                </p>
              </div>
            </form>
          )}
        </div>

        {/* Help Text */}
        <p className="text-center text-gray-500 text-sm mt-6">
          Need help? Contact{' '}
          <a href="mailto:support@aiwfe.com" className="text-purple-400 hover:text-purple-300 transition">
            support@aiwfe.com
          </a>
        </p>
      </motion.div>
    </div>
  );
};

export default ForgotPassword;