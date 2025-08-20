import React, { memo, useRef, useMemo, useEffect, useCallback, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import webglPerformanceManager from '../utils/webglPerformanceManager';

const memoize = (Component) => memo(Component);

// Enhanced performance monitoring with React isolation - TARGET 60 FPS
function usePerformanceMonitorIsolated() {
  const frameTimesRef = useRef([]);
  const lastFrameTimeRef = useRef(performance.now());
  const fpsRef = useRef(60);
  const performanceWarningRef = useRef(false);
  const qualityLevelRef = useRef(1.0);
  const consecutiveLowFramesRef = useRef(0);
  const lastLogTimeRef = useRef(0);
  const logThrottleInterval = 30000; // Throttle logs to prevent React cascades
  
  // Isolated frame skipping that doesn't trigger React updates
  const adaptiveFrameSkip = (fps) => {
    if (fps >= 58) return 1;
    if (fps >= 50) return 2;
    if (fps >= 40) return 3;
    if (fps >= 30) return 4;
    return 5;
  };
  
  const checkFrameRate = useCallback(() => {
    const now = performance.now();
    const frameTime = now - lastFrameTimeRef.current;
    lastFrameTimeRef.current = now;
    
    frameTimesRef.current.push(frameTime);
    if (frameTimesRef.current.length > 30) {
      frameTimesRef.current.shift();
    }
    
    if (frameTimesRef.current.length >= 5) {
      const avgFrameTime = frameTimesRef.current.reduce((a, b) => a + b, 0) / frameTimesRef.current.length;
      fpsRef.current = Math.round(1000 / avgFrameTime);
      
      // Adaptive quality to maintain 60fps target - isolated from React
      if (fpsRef.current < 55) {
        consecutiveLowFramesRef.current++;
        if (consecutiveLowFramesRef.current > 10) {
          qualityLevelRef.current = Math.max(0.3, qualityLevelRef.current - 0.15);
          consecutiveLowFramesRef.current = 0;
          
          // Throttled logging to prevent React interference
          const currentTime = Date.now();
          if (!performanceWarningRef.current && currentTime - lastLogTimeRef.current > logThrottleInterval) {
            console.log(`Galaxy animation adapting for 60fps target: current ${fpsRef.current}fps, quality: ${qualityLevelRef.current.toFixed(2)} (React-isolated)`);
            performanceWarningRef.current = true;
            lastLogTimeRef.current = currentTime;
          }
        }
      } else if (fpsRef.current >= 58) {
        consecutiveLowFramesRef.current = 0;
        if (qualityLevelRef.current < 1.0) {
          qualityLevelRef.current = Math.min(1.0, qualityLevelRef.current + 0.02);
        }
        performanceWarningRef.current = false;
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

// WebGL Context Recovery Hook with React isolation
function useWebGLContextRecoveryIsolated() {
  const { gl, invalidate } = useThree();
  const [contextLost, setContextLost] = useState(false);
  const recoveryTimeoutRef = useRef(null);

  useEffect(() => {
    if (!gl || !gl.domElement) return;

    const handleContextLost = (event) => {
      console.warn('WebGL context lost. Attempting recovery... (React-isolated)');
      event.preventDefault();
      
      // Batch state update to prevent multiple React renders
      if (recoveryTimeoutRef.current) {
        clearTimeout(recoveryTimeoutRef.current);
      }
      
      recoveryTimeoutRef.current = setTimeout(() => {
        setContextLost(true);
        recoveryTimeoutRef.current = null;
      }, 100); // Debounce context lost events
    };

    const handleContextRestored = () => {
      console.log('WebGL context restored successfully (React-isolated)');
      
      if (recoveryTimeoutRef.current) {
        clearTimeout(recoveryTimeoutRef.current);
        recoveryTimeoutRef.current = null;
      }
      
      // Batch the state updates
      requestAnimationFrame(() => {
        setContextLost(false);
        invalidate();
      });
    };

    gl.domElement.addEventListener('webglcontextlost', handleContextLost);
    gl.domElement.addEventListener('webglcontextrestored', handleContextRestored);

    return () => {
      if (recoveryTimeoutRef.current) {
        clearTimeout(recoveryTimeoutRef.current);
      }
      if (gl && gl.domElement) {
        gl.domElement.removeEventListener('webglcontextlost', handleContextLost);
        gl.domElement.removeEventListener('webglcontextrestored', handleContextRestored);
      }
    };
  }, [gl, invalidate]);

  return contextLost;
}

// Face-on Galaxy Stars with React isolation
const OptimizedStars = React.memo(memoize(function OptimizedStars({ count = 400, scrollVelocity = 0 }) {
  const mesh = useRef();
  const geometryRef = useRef();
  const materialRef = useRef();
  const mouse = useRef({ x: 0, y: 0 });
  const rafIdRef = useRef(null);
  const { viewport, gl } = useThree();
  const contextLost = useWebGLContextRecoveryIsolated();
  const { checkFrameRate, getQualityLevel } = usePerformanceMonitorIsolated();

  // Face-on galaxy spiral generation - memoized to prevent recalculation
  const starData = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const velocities = new Float32Array(count * 3);
    const orbitalData = [];
    
    for (let i = 0; i < count; i++) {
      const spiralArm = Math.floor(Math.random() * 2);
      const armAngle = spiralArm * Math.PI;
      const distanceFromCenter = Math.pow(Math.random(), 0.8) * viewport.width * 0.4;
      const spiralTightness = 0.3;
      const spiralAngle = armAngle + (distanceFromCenter * spiralTightness);
      const angleNoise = (Math.random() - 0.5) * 0.6;
      const radiusNoise = (Math.random() - 0.5) * distanceFromCenter * 0.3;
      const finalAngle = spiralAngle + angleNoise;
      const finalRadius = distanceFromCenter + radiusNoise;
      
      const x = Math.cos(finalAngle) * finalRadius;
      const y = Math.sin(finalAngle) * finalRadius;
      const z = (Math.random() - 0.5) * 0.2;
      
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      
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

  // React-isolated mouse tracking with RAF throttling
  useEffect(() => {
    const handleMouseMove = (event) => {
      if (rafIdRef.current) return;
      
      rafIdRef.current = requestAnimationFrame(() => {
        mouse.current.x = (event.clientX / window.innerWidth) * 2 - 1;
        mouse.current.y = -(event.clientY / window.innerHeight) * 2 + 1;
        rafIdRef.current = null;
      });
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, []);

  // Cleanup isolated from React lifecycle
  useEffect(() => {
    return () => {
      if (geometryRef.current) {
        geometryRef.current.dispose();
      }
      if (materialRef.current) {
        materialRef.current.dispose();
      }
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, []);

  // Ultra-optimized animation loop with React isolation
  useFrame((state) => {
    if (!mesh.current || contextLost) return;

    const { fps, frameSkip } = checkFrameRate();
    const quality = getQualityLevel();
    const performanceMultiplier = quality;
    
    // Skip frames based on performance to maintain isolation
    if (state.frame % frameSkip !== 0) return;
    
    const positions = mesh.current.geometry.attributes.position.array;
    const velocities = starData.velocities;
    const time = state.clock.getElapsedTime();

    // Batch all position updates to minimize GPU communication
    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      const orbital = starData.orbitalData[i];
      
      const baseOrbitalSpeed = orbital.orbitalSpeed * performanceMultiplier;
      const scrollSpeedMultiplier = 1 + (scrollVelocity * 0.3);
      const currentAngle = orbital.initialAngle + (time * baseOrbitalSpeed * scrollSpeedMultiplier) + orbital.phaseOffset;
      
      const breathingFreq = 0.00174 * performanceMultiplier;
      const starSpecificTiming = orbital.phaseOffset * 2.5;
      const breathingAmp = orbital.initialRadius * 0.003;
      const radiusVariation = Math.sin(time * breathingFreq + starSpecificTiming) * breathingAmp;
      const currentRadius = orbital.initialRadius + radiusVariation;
      
      const orbitalX = Math.cos(currentAngle) * currentRadius;
      const orbitalY = Math.sin(currentAngle) * currentRadius;
      
      // Simplified mouse interaction for React isolation
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
    
    const baseRotationSpeed = 0.001 * performanceMultiplier;
    const scrollBoost = scrollVelocity * 0.0003;
    mesh.current.rotation.z = time * (baseRotationSpeed + scrollBoost);
    mesh.current.rotation.x = Math.PI / 4;
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

// Nebula Background with React isolation
const NebulaBackground = React.memo(memoize(function NebulaBackground({ count = 8 }) {
  const meshRef = useRef();
  const geometryRef = useRef();
  const materialRef = useRef();
  const { viewport } = useThree();
  const contextLost = useWebGLContextRecoveryIsolated();

  const nebulaData = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    
    const nebulaColors = [
      [1.0, 0.4, 0.7], [0.7, 0.3, 1.0], [0.3, 0.6, 1.0],
      [1.0, 0.6, 0.8], [0.5, 0.2, 0.9], [0.2, 0.8, 1.0],
    ];
    
    for (let i = 0; i < count; i++) {
      const x = (Math.random() - 0.5) * viewport.width * 2;
      const y = (Math.random() - 0.5) * viewport.height * 2;
      const z = -5 - Math.random() * 10;
      
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      
      const colorIndex = Math.floor(Math.random() * nebulaColors.length);
      const color = nebulaColors[colorIndex];
      colors[i * 3] = color[0];
      colors[i * 3 + 1] = color[1];
      colors[i * 3 + 2] = color[2];
      
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

  // Optimized nebula animation with React isolation
  useFrame((state) => {
    if (!meshRef.current || contextLost) return;
    
    // Much less frequent updates to prevent React interference
    if (state.frame % 20 !== 0) return;
    
    const time = state.clock.getElapsedTime();
    const positions = meshRef.current.geometry.attributes.position.array;
    
    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      const originalX = nebulaData.positions[i3];
      const originalY = nebulaData.positions[i3 + 1];
      
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

// Main Galaxy component with React isolation
const GalaxyConstellationOptimizedReactIsolated = React.memo(memoize(function GalaxyConstellationOptimizedReactIsolated({ scrollVelocity = 0 }) {
  const [webglSupported, setWebglSupported] = useState(true);
  const [performanceMode, setPerformanceMode] = useState('high');
  const initializationRef = useRef(false); // Prevent multiple initializations

  useEffect(() => {
    // Prevent multiple WebGL detection runs
    if (initializationRef.current) return;
    initializationRef.current = true;

    const detectPerformanceMode = () => {
      try {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('webgl2') || canvas.getContext('webgl');
        
        if (!context) {
          setWebglSupported(false);
          return 'low';
        }

        const debugInfo = context.getExtension('WEBGL_debug_renderer_info');
        const systemMemory = navigator.deviceMemory || 4;
        const hardwareConcurrency = navigator.hardwareConcurrency || 4;

        if (debugInfo) {
          const renderer = context.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
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

  // Optimized quality settings with React isolation
  const getQualitySettings = useMemo(() => {
    switch (performanceMode) {
      case 'high':
        return { starCount: 200, ballCount: 0, dpr: [1, 1.5] }; // Remove balls for isolation
      case 'medium':
        return { starCount: 120, ballCount: 0, dpr: [1, 1.2] };
      case 'low':
        return { starCount: 60, ballCount: 0, dpr: [1, 1] };
      default:
        return { starCount: 200, ballCount: 0, dpr: [1, 1.5] };
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
          debounce: 200 // Increased debounce for React isolation
        }}
        onCreated={({ gl, scene, camera }) => {
          // Initialize WebGL Performance Manager with React isolation
          webglPerformanceManager.init(gl, scene, camera);
          
          gl.setClearColor(0x000000, 0);
          gl.sortObjects = false;
          gl.setPixelRatio(Math.min(window.devicePixelRatio, 2));
          
          if (gl.getExtension) {
            gl.getExtension('OES_vertex_array_object');
            gl.getExtension('ANGLE_instanced_arrays');
            gl.getExtension('EXT_disjoint_timer_query');
          }
          
          scene.autoUpdate = false;
          camera.updateProjectionMatrix();
          
          console.log(`Galaxy animation initialized: TARGET 60 FPS (React-isolated)`);
          console.log(`Starting with ${qualitySettings.starCount} stars, performance mode: ${performanceMode}`);
        }}
        onError={(error) => {
          console.error('Canvas Error (React-isolated):', error);
          setPerformanceMode('low');
        }}
      >
        <ambientLight intensity={0.3} />
        <NebulaBackground count={4} />
        <OptimizedStars count={qualitySettings.starCount} scrollVelocity={scrollVelocity} />
      </Canvas>
    </div>
  );
}));

export default memoize(GalaxyConstellationOptimizedReactIsolated);