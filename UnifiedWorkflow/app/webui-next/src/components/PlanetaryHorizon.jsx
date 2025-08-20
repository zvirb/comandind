import React from 'react';
import { motion } from 'framer-motion';

const PlanetaryHorizon = () => {
  return (
    <section id="cta" className="relative min-h-screen flex items-end overflow-hidden">
      {/* Curved Horizon */}
      <div className="absolute bottom-0 left-0 right-0">
        <svg
          viewBox="0 0 1440 320"
          className="w-full"
          preserveAspectRatio="none"
          style={{ height: '400px' }}
        >
          <defs>
            <linearGradient id="horizonGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#667eea" stopOpacity="0.3" />
              <stop offset="50%" stopColor="#764ba2" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#000000" stopOpacity="1" />
            </linearGradient>
          </defs>
          <path
            fill="url(#horizonGradient)"
            d="M0,96L48,112C96,128,192,160,288,160C384,160,480,128,576,122.7C672,117,768,139,864,138.7C960,139,1056,117,1152,106.7C1248,96,1344,96,1392,96L1440,96L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"
          />
        </svg>
      </div>

      {/* Floating Planets */}
      <div className="absolute inset-0 pointer-events-none">
        <motion.div
          className="absolute top-20 left-20 w-32 h-32 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 opacity-30 blur-xl"
          animate={{
            y: [0, -20, 0],
            x: [0, 10, 0],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        <motion.div
          className="absolute top-40 right-32 w-24 h-24 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 opacity-30 blur-xl"
          animate={{
            y: [0, 20, 0],
            x: [0, -10, 0],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        <motion.div
          className="absolute bottom-60 left-1/3 w-40 h-40 rounded-full bg-gradient-to-br from-orange-500 to-red-500 opacity-20 blur-2xl"
          animate={{
            y: [0, -30, 0],
            rotate: [0, 360],
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      </div>

      {/* CTA Content */}
      <div className="relative z-10 w-full px-8 pb-32">
        <motion.div
          className="max-w-4xl mx-auto text-center"
          initial={{ opacity: 0, y: 50 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <h2 className="text-6xl font-bold mb-6 bg-gradient-to-r from-cosmic-300 to-cosmic-500 bg-clip-text text-transparent">
            Begin Your Journey
          </h2>
          <p className="text-xl text-gray-300 mb-12 max-w-2xl mx-auto">
            Step into a universe of possibilities. Join thousands of explorers who are already transforming their workflows with AI-powered intelligence.
          </p>
          <motion.button
            className="px-12 py-6 text-xl font-bold bg-gradient-to-r from-cosmic-500 to-cosmic-700 rounded-full hover-glow transform transition-all duration-300"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => window.location.href = '/register'}
          >
            Register Now
          </motion.button>
          
          <div className="mt-12 flex justify-center space-x-8 text-sm text-gray-400">
            <span className="flex items-center">
              <span className="text-cosmic-400 text-2xl mr-2">✨</span>
              Free to Start
            </span>
            <span className="flex items-center">
              <span className="text-cosmic-400 text-2xl mr-2">🚀</span>
              No Credit Card Required
            </span>
            <span className="flex items-center">
              <span className="text-cosmic-400 text-2xl mr-2">🛡️</span>
              Enterprise Ready
            </span>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default PlanetaryHorizon;