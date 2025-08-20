import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { SecureAuth } from '../utils/secureAuth';

const HamburgerMenu = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Check authentication status
    const token = null /* DEPRECATED: Use SecureAuth.makeSecureRequest() */;
    setIsAuthenticated(!!token);
  }, []);

  const publicMenuItems = [
    { label: 'Register', path: '/register' },
    { label: 'Login', path: '/login' },
  ];

  const authenticatedMenuItems = [
    { label: 'Dashboard', path: '/dashboard' },
    { label: 'Tasks', path: '/tasks' },
    { label: 'Projects', path: '/projects' },
    { label: 'Documents', path: '/documents' },
    { label: 'Calendar', path: '/calendar' },
    { label: 'Settings', path: '/settings' },
  ];

  const menuItems = isAuthenticated ? authenticatedMenuItems : publicMenuItems;

  return (
    <div className="fixed top-6 right-6 z-50">
      {/* Hamburger Button */}
      <motion.button
        className="relative w-12 h-12 glass-morphism rounded-full p-3 hover-glow"
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
      >
        <div className="flex flex-col justify-center items-center">
          <motion.span
            className="block w-6 h-0.5 bg-white mb-1"
            animate={{
              rotate: isOpen ? 45 : 0,
              y: isOpen ? 6 : 0,
            }}
            transition={{ duration: 0.3 }}
          />
          <motion.span
            className="block w-6 h-0.5 bg-white mb-1"
            animate={{
              opacity: isOpen ? 0 : 1,
            }}
            transition={{ duration: 0.3 }}
          />
          <motion.span
            className="block w-6 h-0.5 bg-white"
            animate={{
              rotate: isOpen ? -45 : 0,
              y: isOpen ? -6 : 0,
            }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </motion.button>

      {/* Menu Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.2 }}
            className="absolute top-16 right-0 glass-morphism rounded-2xl p-2 min-w-[200px]"
          >
            {menuItems.map((item, index) => (
              <motion.div
                key={item.path}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Link
                  to={item.path}
                  className="block px-4 py-3 text-white hover:bg-white/10 rounded-lg transition-colors"
                  onClick={() => setIsOpen(false)}
                >
                  {item.label}
                </Link>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default HamburgerMenu;