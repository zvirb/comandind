import React, { useEffect, useState, useRef, Suspense, lazy } from 'react';
import { motion } from 'framer-motion';
import HamburgerMenu from '../components/HamburgerMenu';
import FloatingNavbar from '../components/FloatingNavbar';
import FeatureCard from '../components/FeatureCard';
import PlanetaryHorizon from '../components/PlanetaryHorizon';

// Lazy load the heavy three.js component
const GalaxyConstellation = lazy(() => import('../components/GalaxyConstellationOptimized'));

const CosmicHero = () => {
  const [scrollProgress, setScrollProgress] = useState(0);
  const [scrollVelocity, setScrollVelocity] = useState(0);
  const lastScrollTime = useRef(Date.now());
  const lastScrollY = useRef(0);

  useEffect(() => {
    let animationFrameId;
    let velocityDecayTimeout;
    
    const handleScroll = () => {
      // Use requestAnimationFrame for smooth performance
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
      
      animationFrameId = requestAnimationFrame(() => {
        const currentTime = Date.now();
        const currentScrollY = window.scrollY;
        const timeDelta = currentTime - lastScrollTime.current;
        const scrollDelta = Math.abs(currentScrollY - lastScrollY.current);
        
        // Calculate scroll velocity (pixels per millisecond)
        const velocity = timeDelta > 0 ? scrollDelta / timeDelta : 0;
        
        // Normalize and smooth the velocity (0-1 range)
        const normalizedVelocity = Math.min(velocity * 0.3, 1); // Reduced from 0.5 for smoother effect
        setScrollVelocity(normalizedVelocity);
        
        // Update scroll progress
        const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
        const progress = currentScrollY / totalHeight;
        setScrollProgress(Math.min(progress, 1));
        
        // Update references
        lastScrollTime.current = currentTime;
        lastScrollY.current = currentScrollY;
      });
      
      // Clear previous decay timeout and set new one
      if (velocityDecayTimeout) {
        clearTimeout(velocityDecayTimeout);
      }
      
      // Gradually reduce velocity when not scrolling (performance optimized)
      velocityDecayTimeout = setTimeout(() => {
        setScrollVelocity(prev => Math.max(prev * 0.85, 0));
      }, 150);
    };

    // Use passive listener for better performance
    window.addEventListener('scroll', handleScroll, { passive: true });
    
    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
      if (velocityDecayTimeout) {
        clearTimeout(velocityDecayTimeout);
      }
    };
  }, []);

  const features = [
    {
      icon: '🤖',
      title: 'AI-Powered Automation',
      description: 'Harness the power of advanced artificial intelligence to automate complex workflows and boost productivity by 10x. Our cutting-edge algorithms learn from your patterns and optimize processes continuously.',
    },
    {
      icon: '⚡',
      title: 'Lightning Fast Processing',
      description: 'Experience unprecedented speed with our optimized engine that processes millions of operations per second. Real-time data analysis and instant feedback loops keep you ahead of the competition.',
    },
    {
      icon: '🔐',
      title: 'Enterprise Security',
      description: 'Bank-grade encryption and multi-layer security protocols protect your sensitive data. Compliance with global standards including SOC 2, HIPAA, and GDPR ensures your peace of mind.',
    },
    {
      icon: '🌍',
      title: 'Global Scalability',
      description: 'Deploy across multiple regions with automatic load balancing and infinite scalability. Our infrastructure grows with your needs, from startup to enterprise.',
    },
    {
      icon: '📊',
      title: 'Advanced Analytics',
      description: 'Deep insights and predictive analytics powered by machine learning. Visualize complex data patterns and make informed decisions with our comprehensive dashboard.',
    },
    {
      icon: '🎯',
      title: 'Precision Targeting',
      description: 'Smart targeting algorithms ensure your workflows reach the right outcomes at the right time. Maximize efficiency with intelligent resource allocation.',
    },
  ];

  return (
    <div className="min-h-screen relative">
      {/* Enhanced Cosmic Gradient Background - Bright at top transitioning to pure black */}
      <div 
        className="fixed inset-0 transition-opacity duration-1000"
        style={{
          background: `linear-gradient(to bottom, 
            rgba(255, 255, 255, ${0.15 - scrollProgress * 0.1}) 0%,
            rgba(147, 197, 253, ${0.6 - scrollProgress * 0.4}) 5%,
            rgba(139, 92, 246, ${0.5 - scrollProgress * 0.35}) 15%,
            rgba(102, 126, 234, ${0.4 - scrollProgress * 0.3}) 25%,
            rgba(118, 75, 162, ${0.3 - scrollProgress * 0.2}) 40%,
            rgba(240, 147, 251, ${0.15 - scrollProgress * 0.1}) 55%,
            rgba(59, 7, 100, ${0.08 - scrollProgress * 0.05}) 75%,
            rgba(20, 5, 40, ${0.03 - scrollProgress * 0.02}) 90%,
            rgb(0, 0, 0) 100%)`,
        }}
      />

      {/* Galaxy Constellation Background - Positioned below all interactive elements */}
      <Suspense fallback={
        <div className="fixed inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      }>
        <GalaxyConstellation scrollVelocity={scrollVelocity} />
      </Suspense>

      {/* Interactive Navigation Elements - Above galaxy animation */}
      <div className="relative z-50">
        {/* Floating Navigation */}
        <FloatingNavbar />

        {/* Hamburger Menu */}
        <HamburgerMenu />
      </div>

      {/* Hero Section */}
      <section id="home" className="relative min-h-screen flex items-center justify-center px-8">
        <motion.div
          className="text-center relative z-10"
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1 }}
        >
          <motion.h1
            className="text-7xl md:text-9xl font-bold mb-6 bg-gradient-to-r from-cosmic-300 via-cosmic-500 to-cosmic-700 bg-clip-text text-transparent"
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            AI Workflow Engine
          </motion.h1>
          
          <motion.p
            className="text-2xl md:text-3xl text-gray-300 mb-12 max-w-3xl mx-auto"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            Orchestrate the future with intelligent automation
          </motion.p>

          <motion.div
            className="flex gap-6 justify-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
          >
            <motion.button
              className="px-8 py-4 text-lg font-semibold bg-gradient-to-r from-cosmic-500 to-cosmic-700 rounded-full hover-glow"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => window.location.href = '/register'}
            >
              Get Started
            </motion.button>
            <motion.button
              className="px-8 py-4 text-lg font-semibold glass-morphism rounded-full hover-glow"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => document.getElementById('features').scrollIntoView({ behavior: 'smooth' })}
            >
              Learn More
            </motion.button>
          </motion.div>
        </motion.div>

        {/* Scroll Indicator */}
        <motion.div
          className="absolute bottom-10 left-1/2 transform -translate-x-1/2"
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="w-6 h-10 border-2 border-white/30 rounded-full flex justify-center">
            <div className="w-1 h-3 bg-white/50 rounded-full mt-2"></div>
          </div>
        </motion.div>
      </section>

      {/* Features Section */}
      <section id="features" className="relative py-32 px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            className="text-center mb-20"
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-cosmic-400 to-cosmic-600 bg-clip-text text-transparent">
              Powerful Features
            </h2>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto">
              Everything you need to transform your workflow into an intelligent, automated powerhouse
            </p>
          </motion.div>

          <div className="space-y-12">
            {features.map((feature, index) => (
              <FeatureCard key={index} feature={feature} index={index} />
            ))}
          </div>
        </div>
      </section>

      {/* About Section */}
      <section id="about" className="relative py-32 px-8">
        <div className="max-w-6xl mx-auto">
          <motion.div
            className="glass-morphism rounded-3xl p-12"
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-5xl font-bold mb-8 bg-gradient-to-r from-cosmic-400 to-cosmic-600 bg-clip-text text-transparent">
              About AI Workflow Engine
            </h2>
            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <p className="text-gray-300 text-lg leading-relaxed mb-6">
                  We're pioneering the future of intelligent automation. Our platform combines cutting-edge AI with intuitive design to create workflows that think, learn, and evolve.
                </p>
                <p className="text-gray-300 text-lg leading-relaxed">
                  Founded by industry veterans and AI researchers, we're on a mission to democratize advanced automation and make it accessible to businesses of all sizes.
                </p>
              </div>
              <div className="space-y-6">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-cosmic-500 to-cosmic-700 flex items-center justify-center text-2xl">
                    🚀
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white">10M+ Workflows</h3>
                    <p className="text-gray-400">Processed daily across our platform</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-cosmic-500 to-cosmic-700 flex items-center justify-center text-2xl">
                    🌍
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white">150+ Countries</h3>
                    <p className="text-gray-400">Trusted by users worldwide</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-cosmic-500 to-cosmic-700 flex items-center justify-center text-2xl">
                    ⚡
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white">99.99% Uptime</h3>
                    <p className="text-gray-400">Enterprise-grade reliability</p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Planetary Horizon CTA */}
      <PlanetaryHorizon />
    </div>
  );
};

export default CosmicHero;