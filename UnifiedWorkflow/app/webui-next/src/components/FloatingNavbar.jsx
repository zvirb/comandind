import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const FloatingNavbar = () => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navItems = [
    { label: 'Home', href: '#home' },
    { label: 'Features', href: '#features' },
    { label: 'About', href: '#about' },
    { label: 'Get Started', href: '#cta' },
  ];

  return (
    <motion.nav
      className={`fixed top-6 z-40 transition-all duration-300 ${
        scrolled ? 'glass-morphism' : 'bg-transparent'
      } rounded-full px-8 py-4`}
      style={{
        left: '50%',
        transform: 'translateX(-50%)',
        position: 'fixed'
      }}
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <ul className="flex items-center justify-center space-x-8 whitespace-nowrap">
        {navItems.map((item) => (
          <li key={item.href}>
            <a
              href={item.href}
              className="text-white hover:text-cosmic-400 transition-colors duration-300 font-medium"
            >
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </motion.nav>
  );
};

export default FloatingNavbar;