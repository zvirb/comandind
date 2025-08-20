import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  HomeIcon,
  ChatBubbleLeftRightIcon,
  BriefcaseIcon,
  ChartBarIcon,
  CogIcon,
  BugAntIcon,
  DocumentTextIcon,
  UserGroupIcon,
  LightBulbIcon,
  AcademicCapIcon,
  HeartIcon,
  ChevronDownIcon,
  Bars3Icon,
  XMarkIcon
} from '@heroicons/react/24/outline';

const FloatingUserNav = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeDropdown, setActiveDropdown] = useState(null);
  const navigate = useNavigate();
  const navRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (navRef.current && !navRef.current.contains(event.target)) {
        setActiveDropdown(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const navigationItems = [
    {
      id: 'dashboard',
      icon: HomeIcon,
      label: 'Dashboard & Chat',
      items: [
        { label: 'Main Dashboard', path: '/dashboard', icon: HomeIcon },
        { label: 'Chat Interface', path: '/chat', icon: ChatBubbleLeftRightIcon },
        { label: 'Dashboard with Chat', path: '/dashboard-with-chat', icon: DocumentTextIcon }
      ]
    },
    {
      id: 'projects',
      icon: BriefcaseIcon,
      label: 'Projects & Opportunities',
      items: [
        { label: 'Project Management', path: '/projects', icon: BriefcaseIcon },
        { label: 'Task Management', path: '/tasks', icon: DocumentTextIcon },
        { label: 'Calendar & Scheduling', path: '/calendar', icon: AcademicCapIcon },
        { label: 'Documents', path: '/documents', icon: DocumentTextIcon },
        { label: 'Team Collaboration', path: '/team', icon: UserGroupIcon },
        { label: 'Innovation Hub', path: '/innovation', icon: LightBulbIcon }
      ]
    },
    {
      id: 'analytics',
      icon: ChartBarIcon,
      label: 'Analytics & Insights',
      items: [
        { label: 'Performance Analytics', path: '/analytics', icon: ChartBarIcon },
        { label: 'Reflective Dashboard', path: '/reflective', icon: HeartIcon },
        { label: 'Socratic Analysis', path: '/socratic', icon: AcademicCapIcon },
        { label: 'Psychological Insights', path: '/psychology', icon: HeartIcon },
        { label: 'Maps & Visualization', path: '/maps', icon: ChartBarIcon }
      ]
    },
    {
      id: 'settings',
      icon: CogIcon,
      label: 'Settings & Config',
      items: [
        { label: 'User Settings', path: '/settings', icon: CogIcon },
        { label: 'Account Preferences', path: '/account', icon: UserGroupIcon },
        { label: 'Notifications', path: '/notifications', icon: DocumentTextIcon },
        { label: 'Security & Privacy', path: '/security', icon: CogIcon },
        { label: 'Performance Demo', path: '/performance-demo', icon: ChartBarIcon }
      ]
    },
    {
      id: 'support',
      icon: BugAntIcon,
      label: 'Submit Bug Report',
      path: '/bug-report',
      standalone: true
    }
  ];

  const handleNavigation = (path) => {
    navigate(path);
    setActiveDropdown(null);
    setIsExpanded(false);
  };

  const toggleDropdown = (itemId) => {
    setActiveDropdown(activeDropdown === itemId ? null : itemId);
  };

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
    setActiveDropdown(null);
  };

  return (
    <motion.div
      ref={navRef}
      className="fixed top-6 right-6 z-50"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Compact Mode */}
      <AnimatePresence>
        {!isExpanded && (
          <motion.button
            onClick={toggleExpanded}
            className="w-14 h-14 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 shadow-lg hover:shadow-xl flex items-center justify-center text-white hover:scale-105 transition-all duration-200"
            initial={{ opacity: 0, rotate: -90 }}
            animate={{ opacity: 1, rotate: 0 }}
            exit={{ opacity: 0, rotate: 90 }}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
          >
            <Bars3Icon className="w-6 h-6" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Expanded Mode */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            className="glass-morphism rounded-2xl p-4 border border-white/20 min-w-[320px]"
            initial={{ opacity: 0, scale: 0.8, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Navigation</h3>
              <button
                onClick={toggleExpanded}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
              >
                <XMarkIcon className="w-5 h-5 text-white" />
              </button>
            </div>

            {/* Navigation Items */}
            <div className="space-y-2">
              {navigationItems.map((item) => (
                <div key={item.id} className="relative">
                  {item.standalone ? (
                    // Standalone item (Bug Report)
                    <motion.button
                      onClick={() => handleNavigation(item.path)}
                      className="w-full flex items-center gap-3 p-3 rounded-xl bg-red-500/20 border border-red-400/30 text-red-300 hover:bg-red-500/30 transition-all duration-200"
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <item.icon className="w-5 h-5" />
                      <span className="font-medium">{item.label}</span>
                    </motion.button>
                  ) : (
                    // Dropdown item
                    <>
                      <motion.button
                        onClick={() => toggleDropdown(item.id)}
                        className={`w-full flex items-center justify-between p-3 rounded-xl transition-all duration-200 ${
                          activeDropdown === item.id
                            ? 'bg-blue-500/20 border border-blue-400/30 text-blue-300'
                            : 'bg-white/5 border border-white/10 text-white hover:bg-white/10'
                        }`}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        <div className="flex items-center gap-3">
                          <item.icon className="w-5 h-5" />
                          <span className="font-medium">{item.label}</span>
                        </div>
                        <motion.div
                          animate={{ rotate: activeDropdown === item.id ? 180 : 0 }}
                          transition={{ duration: 0.2 }}
                        >
                          <ChevronDownIcon className="w-4 h-4" />
                        </motion.div>
                      </motion.button>

                      {/* Dropdown Menu */}
                      <AnimatePresence>
                        {activeDropdown === item.id && (
                          <motion.div
                            className="mt-2 ml-4 space-y-1"
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.2 }}
                          >
                            {item.items.map((subItem, index) => (
                              <motion.button
                                key={subItem.path}
                                onClick={() => handleNavigation(subItem.path)}
                                className="w-full flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10 hover:text-white transition-all duration-200"
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.05 }}
                                whileHover={{ scale: 1.02, x: 4 }}
                                whileTap={{ scale: 0.98 }}
                              >
                                <subItem.icon className="w-4 h-4" />
                                <span className="text-sm">{subItem.label}</span>
                              </motion.button>
                            ))}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </>
                  )}
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="mt-4 pt-4 border-t border-white/10">
              <div className="text-xs text-gray-400 text-center">
                AI Workflow Engine v2.0
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default FloatingUserNav;