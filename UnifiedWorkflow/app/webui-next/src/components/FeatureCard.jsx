import React, { useRef, useEffect, useState } from 'react';
import { motion, useInView } from 'framer-motion';

const FeatureCard = ({ feature, index }) => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, threshold: 0.2 });
  const [hasAnimated, setHasAnimated] = useState(false);

  useEffect(() => {
    if (isInView && !hasAnimated) {
      setHasAnimated(true);
    }
  }, [isInView, hasAnimated]);

  const isEven = index % 2 === 0;

  const imageVariants = {
    hidden: {
      x: isEven ? -100 : 100,
      opacity: 0,
    },
    visible: {
      x: 0,
      opacity: 1,
      transition: {
        duration: 0.8,
        ease: 'easeOut',
      },
    },
  };

  const textVariants = {
    hidden: {
      y: 50,
      opacity: 0,
    },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        duration: 0.6,
        delay: 0.4,
        ease: 'easeOut',
      },
    },
  };

  return (
    <div
      ref={ref}
      className={`flex items-center gap-12 mb-24 ${
        isEven ? 'flex-row' : 'flex-row-reverse'
      }`}
    >
      {/* Circular Image */}
      <motion.div
        className="flex-shrink-0"
        variants={imageVariants}
        initial="hidden"
        animate={hasAnimated ? 'visible' : 'hidden'}
      >
        <div className="relative w-64 h-64">
          <div className="absolute inset-0 cosmic-gradient rounded-full opacity-20 blur-xl"></div>
          <div className="relative w-full h-full rounded-full overflow-hidden glass-morphism p-1">
            <div className="w-full h-full rounded-full bg-gradient-to-br from-cosmic-500 to-cosmic-700 flex items-center justify-center">
              <span className="text-6xl">{feature.icon}</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Text Content */}
      <motion.div
        className="flex-1"
        variants={textVariants}
        initial="hidden"
        animate={hasAnimated ? 'visible' : 'hidden'}
      >
        <h3 className="text-4xl font-bold mb-4 bg-gradient-to-r from-cosmic-400 to-cosmic-600 bg-clip-text text-transparent">
          {feature.title}
        </h3>
        <p className="text-gray-300 text-lg leading-relaxed mb-6">
          {feature.description}
        </p>
        <motion.button
          className="px-6 py-3 glass-morphism rounded-full hover-glow font-medium"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          Learn More
        </motion.button>
      </motion.div>
    </div>
  );
};

export default FeatureCard;