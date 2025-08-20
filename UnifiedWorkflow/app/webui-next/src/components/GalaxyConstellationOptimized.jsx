import React, { memo, useRef, useMemo, useEffect, useCallback, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import webglPerformanceManager from '../utils/webglPerformanceManager';

const memoize = (Component) => memo(Component);

// Enhanced performance monitoring with adaptive quality - TARGET 60 FPS WITH STABILITY
function usePerformanceMonitor() {
  const frameTimesRef = useRef([]);
  const lastFrameTimeRef = useRef(performance.now());
  const fpsRef = useRef(60);
  const performanceWarningRef = useRef(false);
  const qualityLevelRef = useRef(1.0); // 1.0 = full quality, 0.5 = reduced
  const consecutiveLowFramesRef = useRef(0);
  const qualityStableFramesRef = useRef(0); // STABILITY: Track stable frames at current quality
  const lastQualityChangeRef = useRef(Date.now());
  const minQualityChangeIntervalRef = useRef(5000); // STABILITY: Minimum 5 seconds between quality changes
  
  // Adaptive frame skipping strategy - more conservative to prevent loops
  const adaptiveFrameSkip = (fps) => {
    if (fps >= 55) return 1;    // Stable performance - was 58, now more forgiving
    if (fps >= 45) return 2;    // Good performance - was 50, now more forgiving
    if (fps >= 35) return 3;    // Moderate performance - was 40, now more forgiving
    if (fps >= 25) return 4;    // Low performance - was 30, now more forgiving
    return 5;                   // Critical performance, maximum frame skip
  };
  
  const checkFrameRate = useCallback(() => {
    const now = performance.now();
    const frameTime = now - lastFrameTimeRef.current;
    lastFrameTimeRef.current = now;
    
    // Keep rolling average of last 30 frames for faster response
    frameTimesRef.current.push(frameTime);
    if (frameTimesRef.current.length > 30) {
      frameTimesRef.current.shift();
    }
    
    // Calculate FPS from average frame time
    if (frameTimesRef.current.length >= 5) {
      const avgFrameTime = frameTimesRef.current.reduce((a, b) => a + b, 0) / frameTimesRef.current.length;
      fpsRef.current = Math.round(1000 / avgFrameTime);
      
      // STABLE adaptive quality to prevent continuous adaptation loops
      const now = Date.now();
      const timeSinceLastQualityChange = now - lastQualityChangeRef.current;
      
      if (fpsRef.current < 50) { // Lowered threshold to be less aggressive
        consecutiveLowFramesRef.current++;
        qualityStableFramesRef.current = 0; // Reset stability counter
        
        // Only adjust quality if enough time has passed AND we have sustained low performance
        if (consecutiveLowFramesRef.current > 30 && timeSinceLastQualityChange > minQualityChangeIntervalRef.current) {
          // More conservative quality reduction to prevent rapid cycling
          const newQuality = Math.max(0.5, qualityLevelRef.current - 0.1); // Smaller steps, higher minimum
          if (newQuality !== qualityLevelRef.current) {
            qualityLevelRef.current = newQuality;
            lastQualityChangeRef.current = now;
            consecutiveLowFramesRef.current = 0;
            if (!performanceWarningRef.current) {
              console.log(`Galaxy animation: Quality reduced to ${qualityLevelRef.current.toFixed(2)} for stable ${fpsRef.current}fps`);
              performanceWarningRef.current = true;
            }
          }
        }
      } else if (fpsRef.current >= 55) { // Higher threshold for quality increases
        consecutiveLowFramesRef.current = 0;
        qualityStableFramesRef.current++;
        
        // Only restore quality after sustained good performance AND time interval
        if (qualityStableFramesRef.current > 150 && // Require more stable frames
            qualityLevelRef.current < 1.0 && 
            timeSinceLastQualityChange > minQualityChangeIntervalRef.current * 2) { // Longer interval for increases
          
          const newQuality = Math.min(1.0, qualityLevelRef.current + 0.05); // Smaller increments
          qualityLevelRef.current = newQuality;
          lastQualityChangeRef.current = now;
          qualityStableFramesRef.current = 0;
          console.log(`Galaxy animation: Quality restored to ${qualityLevelRef.current.toFixed(2)} after sustained good performance`);
        }
        
        // Only clear warning after sustained good performance
        if (qualityStableFramesRef.current > 60) {
          performanceWarningRef.current = false;
        }
      }
    }
    
    return { 
      fps: fpsRef.current, 
      frameSkip: adaptiveFrameSkip(fpsRef.current) 
    };
  }, []);
  
  return { 
    checkFrameRate, 
    getCurrentFPS: () => fpsRef.current,
    getQualityLevel: () => qualityLevelRef.current
  };
}

// Enhanced WebGL Context Recovery Hook with fallbacks
function useWebGLContextRecovery() {
  const { gl, invalidate, scene, camera } = useThree();
  const [contextLost, setContextLost] = useState(false);
  const [recoveryAttempts, setRecoveryAttempts] = useState(0);
  const [degradedMode, setDegradedMode] = useState(false);
  const recoveryTimeoutRef = useRef(null);

  useEffect(() => {
    if (!gl || !gl.domElement) return;

    const handleContextLost = (event) => {
      console.warn('[GalaxyConstellation] WebGL context lost. Initiating recovery...');
      event.preventDefault();
      setContextLost(true);
      
      // Notify performance manager
      if (webglPerformanceManager && webglPerformanceManager.isContextLost !== undefined) {
        webglPerformanceManager.isContextLost = true;
      }
      
      // Start recovery timeout
      if (recoveryTimeoutRef.current) {
        clearTimeout(recoveryTimeoutRef.current);
      }
      
      recoveryTimeoutRef.current = setTimeout(() => {
        if (contextLost) {
          console.warn('[GalaxyConstellation] Context recovery timeout - enabling degraded mode');
          setDegradedMode(true);
        }
      }, 5000);
    };

    const handleContextRestored = () => {
      console.log('[GalaxyConstellation] WebGL context restored successfully');
      setContextLost(false);
      setRecoveryAttempts(prev => prev + 1);
      
      // Clear recovery timeout
      if (recoveryTimeoutRef.current) {
        clearTimeout(recoveryTimeoutRef.current);
        recoveryTimeoutRef.current = null;
      }
      
      // Notify performance manager
      if (webglPerformanceManager && webglPerformanceManager.isContextLost !== undefined) {
        webglPerformanceManager.isContextLost = false;
      }
      
      // Reinitialize performance manager if available
      if (webglPerformanceManager && gl && scene && camera) {
        try {
          webglPerformanceManager.init(gl, scene, camera);
        } catch (error) {
          console.warn('[GalaxyConstellation] Failed to reinitialize performance manager:', error);
        }
      }
      
      // Force re-render
      invalidate();
    };

    // Enhanced error handling
    const handleWebGLError = (event) => {
      console.error('[GalaxyConstellation] WebGL error:', event);
      
      // If too many recovery attempts, enable degraded mode
      if (recoveryAttempts > 3) {
        console.warn('[GalaxyConstellation] Too many context losses - enabling permanent degraded mode');
        setDegradedMode(true);
      }
    };

    gl.domElement.addEventListener('webglcontextlost', handleContextLost);
    gl.domElement.addEventListener('webglcontextrestored', handleContextRestored);
    gl.domElement.addEventListener('webglcontextcreationerror', handleWebGLError);

    return () => {
      if (recoveryTimeoutRef.current) {
        clearTimeout(recoveryTimeoutRef.current);
      }
      
      if (gl && gl.domElement) {
        gl.domElement.removeEventListener('webglcontextlost', handleContextLost);
        gl.domElement.removeEventListener('webglcontextrestored', handleContextRestored);
        gl.domElement.removeEventListener('webglcontextcreationerror', handleWebGLError);
      }
    };
  }, [gl, invalidate, scene, camera, contextLost, recoveryAttempts]);

  return { contextLost, degradedMode, recoveryAttempts };
}

// Face-on Galaxy Stars - Classic view from above
const OptimizedStars = React.memo(memoize(function OptimizedStars({ count = 400, scrollVelocity = 0 }) {
  const mesh = useRef();
  const geometryRef = useRef();
  const materialRef = useRef();
  const mouse = useRef({ x: 0, y: 0 });
  const { viewport, gl } = useThree();
  const { contextLost, degradedMode } = useWebGLContextRecovery();
  const { checkFrameRate, getQualityLevel } = usePerformanceMonitor();

  // Face-on galaxy spiral generation - like classic galaxy photos
  const starData = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const velocities = new Float32Array(count * 3);
    const orbitalData = [];
    
    for (let i = 0; i < count; i++) {
      // Create classic 2-arm spiral galaxy structure
      const spiralArm = Math.floor(Math.random() * 2); // 2 main arms like Milky Way
      const armAngle = spiralArm * Math.PI; // 180 degrees apart
      
      // Galaxy radius distribution - more stars in center, fewer at edges
      const distanceFromCenter = Math.pow(Math.random(), 0.8) * viewport.width * 0.4;
      
      // Classic spiral formula for face-on view
      const spiralTightness = 0.3; // Looser spiral for classic look
      const spiralAngle = armAngle + (distanceFromCenter * spiralTightness);
      
      // Add some randomness to create realistic star distribution
      const angleNoise = (Math.random() - 0.5) * 0.6;
      const radiusNoise = (Math.random() - 0.5) * distanceFromCenter * 0.3;
      const finalAngle = spiralAngle + angleNoise;
      const finalRadius = distanceFromCenter + radiusNoise;
      
      const x = Math.cos(finalAngle) * finalRadius;
      const y = Math.sin(finalAngle) * finalRadius;
      // Keep Z very small for flat disk appearance
      const z = (Math.random() - 0.5) * 0.2; // Much flatter disk
      
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      
      // Realistic orbital velocities - inner stars orbit faster
      const orbitalSpeed = Math.sqrt(1 / Math.max(finalRadius, 0.1)) * 0.005;
      velocities[i * 3] = Math.cos(finalAngle + Math.PI / 2) * orbitalSpeed;
      velocities[i * 3 + 1] = Math.sin(finalAngle + Math.PI / 2) * orbitalSpeed;
      velocities[i * 3 + 2] = 0;
      
      orbitalData.push({
        initialRadius: finalRadius,
        initialAngle: finalAngle,
        orbitalSpeed,
        spiralArm,
        phaseOffset: Math.random() * Math.PI * 2,
      });
    }
    
    return { positions, velocities, orbitalData };
  }, [count, viewport.width]);

  // Optimized sizes calculation
  const sizes = useMemo(() => {
    const sizes = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      const distanceFromCenter = starData.orbitalData[i].initialRadius;
      const maxRadius = viewport.width * 0.8;
      const centerFactor = 1 - (distanceFromCenter / maxRadius);
      sizes[i] = (Math.random() * 1.5 + 0.3) * (1 + centerFactor * 2);
    }
    return sizes;
  }, [count, starData.orbitalData, viewport.width]);

  // Optimized mouse tracking with throttling
  useEffect(() => {
    let animationFrame;
    const handleMouseMove = (event) => {
      if (animationFrame) return; // Throttle mouse updates
      animationFrame = requestAnimationFrame(() => {
        mouse.current.x = (event.clientX / window.innerWidth) * 2 - 1;
        mouse.current.y = -(event.clientY / window.innerHeight) * 2 + 1;
        animationFrame = null;
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (animationFrame) cancelAnimationFrame(animationFrame);
    };
  }, []);

  // Optimized cleanup
  useEffect(() => {
    return () => {
      if (geometryRef.current) {
        geometryRef.current.dispose();
      }
      if (materialRef.current) {
        materialRef.current.dispose();
      }
    };
  }, []);

  // Ultra-optimized animation loop targeting 60fps
  useFrame((state) => {
    if (!mesh.current || contextLost || degradedMode) return;

    const { fps, frameSkip } = checkFrameRate();
    const quality = getQualityLevel();
    
    // Dynamic performance scaling based on quality level
    const performanceMultiplier = quality;
    
    if (state.frame % frameSkip !== 0) return;
    
    const positions = mesh.current.geometry.attributes.position.array;
    const velocities = starData.velocities;
    const time = state.clock.getElapsedTime();

    // Use WebGL-optimized batch operations where possible
    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      const orbital = starData.orbitalData[i];
      
      // Optimized orbital calculation with performance scaling
      const baseOrbitalSpeed = orbital.orbitalSpeed * performanceMultiplier;
      const scrollSpeedMultiplier = 1 + (scrollVelocity * 0.3);
      const currentAngle = orbital.initialAngle + (time * baseOrbitalSpeed * scrollSpeedMultiplier) + orbital.phaseOffset;
      
      // Reduced complexity breathing animation
      const breathingFreq = 0.00174 * performanceMultiplier;
      const starSpecificTiming = orbital.phaseOffset * 2.5;
      const breathingAmp = orbital.initialRadius * 0.003;
      const radiusVariation = Math.sin(time * breathingFreq + starSpecificTiming) * breathingAmp;
      const currentRadius = orbital.initialRadius + radiusVariation;
      
      // Batch position calculations
      const orbitalX = Math.cos(currentAngle) * currentRadius;
      const orbitalY = Math.sin(currentAngle) * currentRadius;
      
      // Simplified mouse interaction for performance
      const mouseInfluence = 0.02 * performanceMultiplier;
      const dx = orbitalX - mouse.current.x * viewport.width * 0.2;
      const dy = orbitalY - mouse.current.y * viewport.height * 0.2;
      const mouseDistance = Math.sqrt(dx * dx + dy * dy);
      
      let finalX = orbitalX;
      let finalY = orbitalY;
      
      if (mouseDistance < 1.2) {
        const mouseForce = (1.2 - mouseDistance) * mouseInfluence;
        finalX += (dx / mouseDistance) * mouseForce;
        finalY += (dy / mouseDistance) * mouseForce;
      }
      
      positions[i3] = finalX;
      positions[i3 + 1] = finalY;
      positions[i3 + 2] = starData.positions[i * 3 + 2] + 
        Math.sin(time * 0.00087 * performanceMultiplier + starSpecificTiming) * 0.01;
    }

    mesh.current.geometry.attributes.position.needsUpdate = true;
    
    // Classic galaxy view at 45-degree angle
    const baseRotationSpeed = 0.001 * performanceMultiplier; // Slower, more realistic
    const scrollBoost = scrollVelocity * 0.0003;
    mesh.current.rotation.z = time * (baseRotationSpeed + scrollBoost);
    mesh.current.rotation.x = Math.PI / 4; // 45-degree tilt for classic galaxy view
  });

  return (
    <points ref={mesh}>
      <bufferGeometry ref={geometryRef}>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={starData.positions}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-size"
          count={count}
          array={sizes}
          itemSize={1}
        />
      </bufferGeometry>
      <pointsMaterial
        ref={materialRef}
        size={0.015}
        sizeAttenuation={true}
        color="#ffffff"
        transparent={true}
        opacity={0.9}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}));

// Nebula Background Component - Creates colorful gas clouds
const NebulaBackground = React.memo(memoize(function NebulaBackground({ count = 8 }) {
  const meshRef = useRef();
  const geometryRef = useRef();
  const materialRef = useRef();
  const { viewport } = useThree();
  const { contextLost, degradedMode } = useWebGLContextRecovery();

  const nebulaData = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    
    // Nebula color palette - pinks, purples, blues
    const nebulaColors = [
      [1.0, 0.4, 0.7], // Pink
      [0.7, 0.3, 1.0], // Purple  
      [0.3, 0.6, 1.0], // Blue
      [1.0, 0.6, 0.8], // Light pink
      [0.5, 0.2, 0.9], // Deep purple
      [0.2, 0.8, 1.0], // Cyan
    ];
    
    for (let i = 0; i < count; i++) {
      // Place nebulae in background, spread across wide area
      const x = (Math.random() - 0.5) * viewport.width * 2;
      const y = (Math.random() - 0.5) * viewport.height * 2;
      const z = -5 - Math.random() * 10; // Behind galaxy
      
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      
      // Random nebula color
      const colorIndex = Math.floor(Math.random() * nebulaColors.length);
      const color = nebulaColors[colorIndex];
      colors[i * 3] = color[0];
      colors[i * 3 + 1] = color[1];
      colors[i * 3 + 2] = color[2];
      
      // Large, varied sizes for nebula clouds
      sizes[i] = Math.random() * 3 + 2;
    }
    
    return { positions, colors, sizes };
  }, [count, viewport.width, viewport.height]);

  useEffect(() => {
    return () => {
      if (geometryRef.current) geometryRef.current.dispose();
      if (materialRef.current) materialRef.current.dispose();
    };
  }, []);

  // Ultra-slow drift animation for nebulae - optimized for performance
  useFrame((state) => {
    if (!meshRef.current || contextLost || degradedMode) return;
    
    // Update nebulae much less frequently
    if (state.frame % 10 !== 0) return;
    
    const time = state.clock.getElapsedTime();
    const positions = meshRef.current.geometry.attributes.position.array;
    
    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      const originalX = nebulaData.positions[i3];
      const originalY = nebulaData.positions[i3 + 1];
      
      // Very slow drift - reduced computation
      const driftX = Math.sin(time * 0.00005 + i) * 0.05;
      const driftY = Math.cos(time * 0.00005 + i * 1.3) * 0.05;
      
      positions[i3] = originalX + driftX;
      positions[i3 + 1] = originalY + driftY;
    }
    
    meshRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={meshRef}>
      <bufferGeometry ref={geometryRef}>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={nebulaData.positions}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-color"
          count={count}
          array={nebulaData.colors}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-size"
          count={count}
          array={nebulaData.sizes}
          itemSize={1}
        />
      </bufferGeometry>
      <pointsMaterial
        ref={materialRef}
        size={0.8}
        sizeAttenuation={true}
        vertexColors={true}
        transparent={true}
        opacity={0.3}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}));

// Optimized Floating Balls with reduced count
const OptimizedFloatingBalls = React.memo(memoize(function OptimizedFloatingBalls({ count = 6, scrollVelocity = 0 }) {
  const meshRef = useRef();
  const geometryRef = useRef();
  const materialRef = useRef();
  const { viewport } = useThree();
  const { contextLost, degradedMode } = useWebGLContextRecovery();
  const { checkFrameRate } = usePerformanceMonitor();

  const ballData = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const ballInfo = [];
    
    for (let i = 0; i < count; i++) {
      const x = (Math.random() - 0.5) * viewport.width * 0.8;
      const y = (Math.random() - 0.5) * viewport.height * 0.8;
      const z = (Math.random() - 0.5) * 4;
      
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      
      ballInfo.push({
        initialX: x,
        initialY: y,
        initialZ: z,
        driftSpeedX: (Math.random() - 0.5) * 0.008,
        driftSpeedY: (Math.random() - 0.5) * 0.008,
        driftSpeedZ: (Math.random() - 0.5) * 0.005,
        phaseOffset: Math.random() * Math.PI * 2,
        size: Math.random() * 0.8 + 0.4,
      });
    }
    
    return { positions, ballInfo };
  }, [count, viewport.width, viewport.height]);

  useEffect(() => {
    return () => {
      if (geometryRef.current) geometryRef.current.dispose();
      if (materialRef.current) materialRef.current.dispose();
    };
  }, []);

  useFrame((state) => {
    if (!meshRef.current || contextLost || degradedMode) return;

    const { fps, frameSkip } = checkFrameRate();
    const performanceMultiplier = fps >= 50 ? 1 : fps >= 30 ? 0.8 : 0.6;
    
    if (state.frame % frameSkip !== 0) return;
    
    const positions = meshRef.current.geometry.attributes.position.array;
    const time = state.clock.getElapsedTime();

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      const ball = ballData.ballInfo[i];
      
      const ballSpecificTiming = ball.phaseOffset * 3.7;
      const scrollDriftMultiplier = 1 + (scrollVelocity * 0.2);
      
      // EXTREMELY slow animation frequencies - 8+ minute cycles for imperceptible background
      const floatFreqX = (0.000058 + (ball.phaseOffset * 0.00001)) * performanceMultiplier; // ~12 minute cycle
      const floatFreqY = (0.000046 + (ball.phaseOffset * 0.000008)) * performanceMultiplier; // ~15 minute cycle  
      const floatFreqZ = (0.000070 + (ball.phaseOffset * 0.000005)) * performanceMultiplier; // ~10 minute cycle
      
      // Debug log on first ball to verify extremely slow timing
      if (i === 0 && state.frame % 300 === 0) {
        console.log(`Ball animation EXTREMELY slow: freqX=${floatFreqX.toFixed(8)}, should be ~0.00006 for 12min cycle`);
      }
      
      const floatX = Math.sin(time * floatFreqX + ballSpecificTiming) * 0.15 * scrollDriftMultiplier;
      const floatY = Math.cos(time * floatFreqY + ballSpecificTiming) * 0.13 * scrollDriftMultiplier;
      const floatZ = Math.sin(time * floatFreqZ + ballSpecificTiming) * 0.1 * scrollDriftMultiplier;
      
      const driftSpeedX = ball.driftSpeedX * 0.001 * performanceMultiplier; // 8x slower drift - imperceptible
      const driftSpeedY = ball.driftSpeedY * 0.001 * performanceMultiplier; // 8x slower drift - imperceptible
      const driftSpeedZ = ball.driftSpeedZ * 0.001 * performanceMultiplier; // 8x slower drift - imperceptible
      
      const driftX = Math.sin(time * driftSpeedX + ballSpecificTiming) * 0.3;
      const driftY = Math.cos(time * driftSpeedY + ballSpecificTiming) * 0.3;
      const driftZ = Math.sin(time * driftSpeedZ + ballSpecificTiming) * 0.2;
      
      positions[i3] = ball.initialX + floatX + driftX;
      positions[i3 + 1] = ball.initialY + floatY + driftY;
      positions[i3 + 2] = ball.initialZ + floatZ + driftZ;
    }

    meshRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={meshRef}>
      <bufferGeometry ref={geometryRef}>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={ballData.positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        ref={materialRef}
        size={0.025}
        sizeAttenuation={true}
        color="#FFD700"
        transparent={true}
        opacity={0.8}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}));

const GalaxyConstellationOptimized = React.memo(memoize(function GalaxyConstellationOptimized({ scrollVelocity = 0 }) {
  const [webglSupported, setWebglSupported] = useState(true);
  const [performanceMode, setPerformanceMode] = useState('high'); // high, medium, low

  useEffect(() => {
    const detectPerformanceMode = () => {
      try {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('webgl2') || canvas.getContext('webgl');
        
        if (!context) {
          setWebglSupported(false);
          return 'low';
        }

        const debugInfo = context.getExtension('WEBGL_debug_renderer_info');
        const systemMemory = navigator.deviceMemory || 4; // Fallback to 4GB
        const hardwareConcurrency = navigator.hardwareConcurrency || 4; // Fallback to 4 cores

        if (debugInfo) {
          const renderer = context.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
          const vendor = context.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
          
          // Comprehensive performance mode detection
          const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
          const isLowEnd = 
            renderer.includes('Mali') || 
            renderer.includes('Adreno') || 
            renderer.includes('PowerVR') || 
            renderer.includes('Intel') || 
            systemMemory < 8 || 
            hardwareConcurrency < 6;

          if (isMobile && isLowEnd) return 'low';
          if (systemMemory <= 8 || hardwareConcurrency <= 4) return 'medium';
          return 'high';
        }

        canvas.remove();
        return 'medium';
      } catch (error) {
        console.warn('Performance detection failed:', error);
        return 'low';
      }
    };
    
    const testWebGL = () => {
      try {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('webgl2') || canvas.getContext('webgl');
        if (!context) {
          setWebglSupported(false);
          return false;
        }
        
        const performanceMode = detectPerformanceMode();
        setPerformanceMode(performanceMode);
        canvas.remove();
        return true;
      } catch (e) {
        console.warn('WebGL not supported:', e);
        setWebglSupported(false);
        return false;
      }
    };

    testWebGL();
  }, []);

  // Optimized quality settings for 60fps target
  const getQualitySettings = useMemo(() => {
    switch (performanceMode) {
      case 'high':
        return { starCount: 250, ballCount: 3, dpr: [1, 1.5] }; // Reduced for 60fps
      case 'medium':
        return { starCount: 150, ballCount: 2, dpr: [1, 1.2] };
      case 'low':
        return { starCount: 80, ballCount: 1, dpr: [1, 1] };
      default:
        return { starCount: 250, ballCount: 3, dpr: [1, 1.5] };
    }
  }, [performanceMode]);

  const qualitySettings = getQualitySettings;

  if (!webglSupported) {
    return (
      <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 1 }}>
        <div className="w-full h-full bg-gradient-to-b from-slate-900/20 via-purple-900/10 to-black/5">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-purple-900/20 via-slate-900/10 to-transparent"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 pointer-events-none" style={{ zIndex: -1 }}>
      <Canvas
        camera={{ position: [0, 0, 5], fov: 75 }}
        style={{ background: 'transparent' }}
        gl={{ 
          antialias: performanceMode === 'high',
          powerPreference: "high-performance",
          alpha: true,
          premultipliedAlpha: false,
          preserveDrawingBuffer: false,
          failIfMajorPerformanceCaveat: false,
          stencil: false,
          depth: true,
        }}
        dpr={qualitySettings.dpr}
        frameloop="always"
        performance={{ 
          min: 0.5,
          max: Infinity,
          debounce: 100
        }}
        onCreated={({ gl, scene, camera }) => {
          // Initialize WebGL Performance Manager
          webglPerformanceManager.init(gl, scene, camera);
          
          // GPU optimization settings
          gl.setClearColor(0x000000, 0);
          gl.sortObjects = false;
          gl.setPixelRatio(Math.min(window.devicePixelRatio, 2));
          
          // Enable GPU optimizations
          if (gl.getExtension) {
            gl.getExtension('OES_vertex_array_object');
            gl.getExtension('ANGLE_instanced_arrays');
            gl.getExtension('EXT_disjoint_timer_query');
          }
          
          scene.autoUpdate = false;
          camera.updateProjectionMatrix();
          
          console.log(`Galaxy animation initialized: TARGET 60 FPS`);
          console.log(`Starting with ${qualitySettings.starCount} stars, ${qualitySettings.ballCount} balls`);
          console.log(`Performance mode: ${performanceMode}, will adapt quality to maintain 60fps`);
          console.log('WebGL Performance Manager with adaptive quality enabled');
        }}
        onError={(error) => {
          console.error('Canvas Error:', error);
          setPerformanceMode('low');
        }}
      >
        <ambientLight intensity={0.3} />
        <NebulaBackground count={4} />
        <OptimizedStars count={qualitySettings.starCount} scrollVelocity={scrollVelocity} />
        <OptimizedFloatingBalls count={qualitySettings.ballCount} scrollVelocity={scrollVelocity} />
      </Canvas>
    </div>
  );
}));

export default memoize(GalaxyConstellationOptimized);