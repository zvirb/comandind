import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { Calendar, User, Mail, Lock, Eye, EyeOff, AlertCircle, CheckCircle } from 'lucide-react';

const Register = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    firstName: '',
    middleName: '',
    lastName: '',
    dateOfBirth: '',
    gender: '',
    email: '',
    role: '',
    intendedUse: '',
    username: '',
    password: '',
    confirmPassword: ''
  });

  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState(null);

  const roleOptions = [
    { value: '', label: 'Select your role' },
    { value: 'student', label: 'Student' },
    { value: 'teacher', label: 'Teacher' },
    { value: 'researcher', label: 'Researcher' },
    { value: 'professional', label: 'Professional' },
    { value: 'industry', label: 'Industry' },
    { value: 'other', label: 'Other' }
  ];

  const intendedUseOptions = [
    { value: '', label: 'Select intended use' },
    { value: 'professional', label: 'Professional' },
    { value: 'learning', label: 'Learning' },
    { value: 'teaching', label: 'Teaching' },
    { value: 'research', label: 'Research' },
    { value: 'development', label: 'Development' },
    { value: 'hobby', label: 'Hobby' },
    { value: 'personal', label: 'Personal' }
  ];

  const genderOptions = [
    { value: '', label: 'Select Gender' },
    { value: 'male', label: 'Male' },
    { value: 'female', label: 'Female' },
    { value: 'other', label: 'Other' },
    { value: 'prefer_not_to_say', label: 'Prefer not to say' }
  ];

  const validateForm = () => {
    const newErrors = {};

    // Required field validation
    if (!formData.firstName.trim()) newErrors.firstName = 'First name is required';
    if (!formData.lastName.trim()) newErrors.lastName = 'Last name is required';
    if (!formData.dateOfBirth) newErrors.dateOfBirth = 'Date of birth is required';
    if (!formData.gender) newErrors.gender = 'Please select a gender';
    if (!formData.email.trim()) newErrors.email = 'Email is required';
    if (!formData.role) newErrors.role = 'Please select your role';
    if (!formData.intendedUse) newErrors.intendedUse = 'Please select intended use';
    if (!formData.username.trim()) newErrors.username = 'Username is required';
    if (!formData.password) newErrors.password = 'Password is required';
    if (!formData.confirmPassword) newErrors.confirmPassword = 'Please confirm your password';

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (formData.email && !emailRegex.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    // Username validation (min 3 characters, alphanumeric + underscore)
    if (formData.username && formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters';
    }
    if (formData.username && !/^[a-zA-Z0-9_]+$/.test(formData.username)) {
      newErrors.username = 'Username can only contain letters, numbers, and underscores';
    }

    // Password strength validation
    if (formData.password) {
      if (formData.password.length < 8) {
        newErrors.password = 'Password must be at least 8 characters';
      } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
        newErrors.password = 'Password must contain uppercase, lowercase, and numbers';
      }
    }

    // Confirm password validation
    if (formData.confirmPassword && formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    // Date of birth validation (must be in the past and user must be at least 13)
    if (formData.dateOfBirth) {
      const dob = new Date(formData.dateOfBirth);
      const today = new Date();
      const age = Math.floor((today - dob) / (365.25 * 24 * 60 * 60 * 1000));
      
      if (dob >= today) {
        newErrors.dateOfBirth = 'Date of birth must be in the past';
      } else if (age < 13) {
        newErrors.dateOfBirth = 'You must be at least 13 years old to register';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
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

    try {
      // First, register the user
      const registerResponse = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password
        }),
      });

      if (!registerResponse.ok) {
        const errorData = await registerResponse.json();
        throw new Error(errorData.detail || 'Registration failed');
      }

      const registerData = await registerResponse.json();
      
      // Store additional user data (this would normally be sent to a profile endpoint)
      localStorage.setItem('userProfile', JSON.stringify({
        firstName: formData.firstName,
        middleName: formData.middleName,
        lastName: formData.lastName,
        dateOfBirth: formData.dateOfBirth,
        gender: formData.gender,
        role: formData.role,
        intendedUse: formData.intendedUse,
        username: formData.username
      }));

      setSubmitStatus('success');
      
      // Redirect to login page after successful registration
      setTimeout(() => {
        navigate('/login', { state: { message: 'Registration successful! Please log in.' } });
      }, 2000);
      
    } catch (error) {
      console.error('Registration error:', error);
      setSubmitStatus('error');
      setErrors({ submit: error.message || 'Registration failed. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Format date for display (dd/mm/yyyy)
  const formatDateForDisplay = (dateString) => {
    if (!dateString) return '';
    const [year, month, day] = dateString.split('-');
    return `${day}/${month}/${year}`;
  };

  // Parse date from display format to ISO format for input
  const parseDateForInput = (displayDate) => {
    if (!displayDate) return '';
    const [day, month, year] = displayDate.split('/');
    if (day && month && year) {
      return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
    }
    return '';
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      {/* Background Effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-0 -left-4 w-72 h-72 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute top-0 -right-4 w-72 h-72 bg-pink-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-20 w-72 h-72 bg-violet-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      {/* Registration Form Container */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-4xl"
      >
        <div className="glass-morphism rounded-3xl p-8 md:p-12">
          {/* Header */}
          <div className="text-center mb-8">
            <motion.h1
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent mb-3"
            >
              Register User
            </motion.h1>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="text-gray-300"
            >
              Please fill out the form below to create your account.
            </motion.p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Personal Information Section */}
            <div>
              <h2 className="text-xl font-semibold text-purple-300 mb-4 flex items-center">
                <User className="mr-2" size={20} />
                Personal Information
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    First Name <span className="text-pink-400">*</span>
                  </label>
                  <input
                    type="text"
                    name="firstName"
                    value={formData.firstName}
                    onChange={handleChange}
                    autoComplete="given-name"
                    className={`w-full px-4 py-2 bg-white/10 border ${errors.firstName ? 'border-red-400' : 'border-white/20'} rounded-lg focus:outline-none focus:border-purple-400 text-white placeholder-gray-400`}
                    placeholder="John"
                  />
                  {errors.firstName && (
                    <p className="mt-1 text-sm text-red-400 flex items-center">
                      <AlertCircle size={14} className="mr-1" />
                      {errors.firstName}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Middle Name
                  </label>
                  <input
                    type="text"
                    name="middleName"
                    value={formData.middleName}
                    onChange={handleChange}
                    autoComplete="additional-name"
                    className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:border-purple-400 text-white placeholder-gray-400"
                    placeholder="Optional"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Last Name <span className="text-pink-400">*</span>
                  </label>
                  <input
                    type="text"
                    name="lastName"
                    value={formData.lastName}
                    onChange={handleChange}
                    autoComplete="family-name"
                    className={`w-full px-4 py-2 bg-white/10 border ${errors.lastName ? 'border-red-400' : 'border-white/20'} rounded-lg focus:outline-none focus:border-purple-400 text-white placeholder-gray-400`}
                    placeholder="Doe"
                  />
                  {errors.lastName && (
                    <p className="mt-1 text-sm text-red-400 flex items-center">
                      <AlertCircle size={14} className="mr-1" />
                      {errors.lastName}
                    </p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    <Calendar className="inline mr-1" size={16} />
                    Date of Birth (dd/mm/yyyy) <span className="text-pink-400">*</span>
                  </label>
                  <input
                    type="date"
                    name="dateOfBirth"
                    value={formData.dateOfBirth}
                    onChange={handleChange}
                    autoComplete="bday"
                    className={`w-full px-4 py-2 bg-white/10 border ${errors.dateOfBirth ? 'border-red-400' : 'border-white/20'} rounded-lg focus:outline-none focus:border-purple-400 text-white placeholder-gray-400`}
                  />
                  {errors.dateOfBirth && (
                    <p className="mt-1 text-sm text-red-400 flex items-center">
                      <AlertCircle size={14} className="mr-1" />
                      {errors.dateOfBirth}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Gender <span className="text-pink-400">*</span>
                  </label>
                  <select
                    name="gender"
                    value={formData.gender}
                    onChange={handleChange}
                    autoComplete="sex"
                    className={`w-full px-4 py-2 bg-white/10 border ${errors.gender ? 'border-red-400' : 'border-white/20'} rounded-lg focus:outline-none focus:border-purple-400 text-white`}
                  >
                    {genderOptions.map(option => (
                      <option key={option.value} value={option.value} className="bg-gray-800">
                        {option.label}
                      </option>
                    ))}
                  </select>
                  {errors.gender && (
                    <p className="mt-1 text-sm text-red-400 flex items-center">
                      <AlertCircle size={14} className="mr-1" />
                      {errors.gender}
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  <Mail className="inline mr-1" size={16} />
                  Email <span className="text-pink-400">*</span>
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  autoComplete="email"
                  className={`w-full px-4 py-2 bg-white/10 border ${errors.email ? 'border-red-400' : 'border-white/20'} rounded-lg focus:outline-none focus:border-purple-400 text-white placeholder-gray-400`}
                  placeholder="john.doe@example.com"
                />
                {errors.email && (
                  <p className="mt-1 text-sm text-red-400 flex items-center">
                    <AlertCircle size={14} className="mr-1" />
                    {errors.email}
                  </p>
                )}
              </div>
            </div>

            {/* Professional Role Section */}
            <div>
              <h2 className="text-xl font-semibold text-purple-300 mb-4">Professional Role</h2>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  What role best describes you? <span className="text-pink-400">*</span>
                </label>
                <select
                  name="role"
                  value={formData.role}
                  onChange={handleChange}
                  autoComplete="organization-title"
                  className={`w-full px-4 py-2 bg-white/10 border ${errors.role ? 'border-red-400' : 'border-white/20'} rounded-lg focus:outline-none focus:border-purple-400 text-white`}
                >
                  {roleOptions.map(option => (
                    <option key={option.value} value={option.value} className="bg-gray-800">
                      {option.label}
                    </option>
                  ))}
                </select>
                {errors.role && (
                  <p className="mt-1 text-sm text-red-400 flex items-center">
                    <AlertCircle size={14} className="mr-1" />
                    {errors.role}
                  </p>
                )}
              </div>
            </div>

            {/* Intended Use Section */}
            <div>
              <h2 className="text-xl font-semibold text-purple-300 mb-4">Intended Use</h2>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  How do you intend to use this service? <span className="text-pink-400">*</span>
                </label>
                <select
                  name="intendedUse"
                  value={formData.intendedUse}
                  onChange={handleChange}
                  autoComplete="off"
                  className={`w-full px-4 py-2 bg-white/10 border ${errors.intendedUse ? 'border-red-400' : 'border-white/20'} rounded-lg focus:outline-none focus:border-purple-400 text-white`}
                >
                  {intendedUseOptions.map(option => (
                    <option key={option.value} value={option.value} className="bg-gray-800">
                      {option.label}
                    </option>
                  ))}
                </select>
                {errors.intendedUse && (
                  <p className="mt-1 text-sm text-red-400 flex items-center">
                    <AlertCircle size={14} className="mr-1" />
                    {errors.intendedUse}
                  </p>
                )}
              </div>
            </div>

            {/* Create Your Account Section */}
            <div>
              <h2 className="text-xl font-semibold text-purple-300 mb-4 flex items-center">
                <Lock className="mr-2" size={20} />
                Create Your Account
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Username <span className="text-pink-400">*</span>
                  </label>
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    autoComplete="username"
                    className={`w-full px-4 py-2 bg-white/10 border ${errors.username ? 'border-red-400' : 'border-white/20'} rounded-lg focus:outline-none focus:border-purple-400 text-white placeholder-gray-400`}
                    placeholder="johndoe123"
                  />
                  {errors.username && (
                    <p className="mt-1 text-sm text-red-400 flex items-center">
                      <AlertCircle size={14} className="mr-1" />
                      {errors.username}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Password <span className="text-pink-400">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      autoComplete="new-password"
                      className={`w-full px-4 py-2 pr-10 bg-white/10 border ${errors.password ? 'border-red-400' : 'border-white/20'} rounded-lg focus:outline-none focus:border-purple-400 text-white placeholder-gray-400`}
                      placeholder="Enter a strong password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                    >
                      {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                    </button>
                  </div>
                  {errors.password && (
                    <p className="mt-1 text-sm text-red-400 flex items-center">
                      <AlertCircle size={14} className="mr-1" />
                      {errors.password}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Confirm Password <span className="text-pink-400">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirmPassword ? "text" : "password"}
                      name="confirmPassword"
                      value={formData.confirmPassword}
                      onChange={handleChange}
                      autoComplete="new-password"
                      className={`w-full px-4 py-2 pr-10 bg-white/10 border ${errors.confirmPassword ? 'border-red-400' : 'border-white/20'} rounded-lg focus:outline-none focus:border-purple-400 text-white placeholder-gray-400`}
                      placeholder="Re-enter your password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                    >
                      {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                    </button>
                  </div>
                  {errors.confirmPassword && (
                    <p className="mt-1 text-sm text-red-400 flex items-center">
                      <AlertCircle size={14} className="mr-1" />
                      {errors.confirmPassword}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Submit Error */}
            {errors.submit && (
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                <p className="text-red-400 flex items-center">
                  <AlertCircle className="mr-2" />
                  {errors.submit}
                </p>
              </div>
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
                  Registration successful! Redirecting to login...
                </p>
              </motion.div>
            )}

            {/* Submit Button */}
            <motion.button
              type="submit"
              disabled={isSubmitting}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={`w-full py-3 px-6 rounded-lg font-medium transition-all ${
                isSubmitting
                  ? 'bg-gray-600 cursor-not-allowed'
                  : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600'
              } text-white`}
            >
              {isSubmitting ? 'Creating Account...' : 'Register'}
            </motion.button>

            {/* Footer Link */}
            <p className="text-center text-gray-300">
              Already have an account?{' '}
              <Link to="/login" className="text-purple-400 hover:text-purple-300 font-medium">
                Login here.
              </Link>
            </p>
          </form>
        </div>
      </motion.div>
    </div>
  );
};

export default Register;