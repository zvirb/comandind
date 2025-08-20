import React, { memo, useRef, useMemo, useEffect, useCallback, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

const memoize = (Component) => memo(Component);

// WebGL Context Recovery Hook
function useWebGLContextRecovery() {
  const { gl, invalidate } = useThree();
  const [contextLost, setContextLost] = useState(false);

  useEffect(() => {
    if (!gl || !gl.domElement) return;

    const handleContextLost = (event) => {
      console.warn('WebGL context lost. Attempting recovery...');
      event.preventDefault();
      setContextLost(true);
    };

    const handleContextRestored = () => {
      console.log('WebGL context restored successfully');
      setContextLost(false);
      // Force re-render of the scene
      invalidate();
    };

    // Add event listeners for context loss/recovery
    gl.domElement.addEventListener('webglcontextlost', handleContextLost);
    gl.domElement.addEventListener('webglcontextrestored', handleContextRestored);

    return () => {
      if (gl && gl.domElement) {
        gl.domElement.removeEventListener('webglcontextlost', handleContextLost);
        gl.domElement.removeEventListener('webglcontextrestored', handleContextRestored);
      }
    };
  }, [gl, invalidate]);

  return contextLost;
}

// WebGL Error Boundary Component
function WebGLErrorBoundary({ children }) {
  const [hasError, setHasError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const maxRetries = 3;

  const handleWebGLError = useCallback((error) => {
    console.error('WebGL Error:', error);
    if (retryCount < maxRetries) {
      setRetryCount(prev => prev + 1);
      setTimeout(() => {
        setHasError(false);
      }, 2000); // Retry after 2 seconds
    } else {
      setHasError(true);
    }
  }, [retryCount, maxRetries]);

  useEffect(() => {
    const originalConsoleError = console.error;
    console.error = function(...args) {
      const errorMessage = args.join(' ');
      if (errorMessage.includes('WebGL') || errorMessage.includes('Context Lost')) {
        handleWebGLError(new Error(errorMessage));
      }
      originalConsoleError.apply(console, args);
    };

    return () => {
      console.error = originalConsoleError;
    };
  }, [handleWebGLError]);

  if (hasError) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-gradient-to-b from-slate-900 to-black">
        <div className="text-center text-white p-8">
          <div className="text-6xl mb-4">✨</div>
          <h3 className="text-xl font-semibold mb-2">Cosmic Animation Unavailable</h3>
          <p className="text-gray-400">Displaying fallback cosmic background</p>
        </div>
      </div>
    );
  }

  return children;
}

const Stars = React.memo(memoize(function Stars({ count = 250, scrollVelocity = 0 }) { // Face-on galaxy view
  const mesh = useRef();
  const ballsRef = useRef();
  const mouse = useRef({ x: 0, y: 0 });
  const { viewport } = useThree();
  const contextLost = useWebGLContextRecovery();

  // Galaxy center point
  const galaxyCenter = { x: 0, y: 0 };

  // Generate classic face-on spiral galaxy
  const starData = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const orbitalData = [];
    
    for (let i = 0; i < count; i++) {
      // Create classic 2-arm spiral galaxy structure like Milky Way
      const spiralArm = Math.floor(Math.random() * 2); // 2 main arms
      const armAngle = spiralArm * Math.PI; // 180 degrees apart
      
      // Galaxy radius distribution - more stars in center
      const distanceFromCenter = Math.pow(Math.random(), 0.8) * viewport.width * 0.4;
      
      // Classic spiral formula for face-on view
      const spiralTightness = 0.3; // Looser spiral for classic look
      const spiralAngle = armAngle + (distanceFromCenter * spiralTightness);
      
      // Add some randomness for realistic star distribution
      const angleNoise = (Math.random() - 0.5) * 0.6;
      const radiusNoise = (Math.random() - 0.5) * distanceFromCenter * 0.3;
      
      const finalAngle = spiralAngle + angleNoise;
      const finalRadius = distanceFromCenter + radiusNoise;
      
      // Calculate initial position
      const x = Math.cos(finalAngle) * finalRadius;
      const y = Math.sin(finalAngle) * finalRadius;
      const z = (Math.random() - 0.5) * 0.2; // Much flatter disk
      
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      
      // Store orbital data for physics simulation
      orbitalData.push({
        initialRadius: finalRadius,
        initialAngle: finalAngle,
        orbitalSpeed: Math.sqrt(1 / Math.max(finalRadius, 0.1)) * 0.005, // Slower, more realistic
        spiralArm: spiralArm,
        phaseOffset: Math.random() * Math.PI * 2, // Random phase for variation
      });
    }
    
    return { positions, orbitalData };
  }, [count, viewport.width]);

  // Generate star sizes with galaxy-like distribution
  const sizes = useMemo(() => {
    const sizes = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      // Larger stars near center, smaller towards edges
      const distanceFromCenter = starData.orbitalData[i].initialRadius;
      const maxRadius = viewport.width * 0.8;
      const centerFactor = 1 - (distanceFromCenter / maxRadius);
      sizes[i] = (Math.random() * 1.5 + 0.3) * (1 + centerFactor * 2);
    }
    return sizes;
  }, [count, starData.orbitalData, viewport.width]);

  // Subtle mouse interaction (reduced influence to preserve orbital motion)
  useEffect(() => {
    const handleMouseMove = (event) => {
      mouse.current.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouse.current.y = -(event.clientY / window.innerHeight) * 2 + 1;
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Add cleanup when component unmounts or context is lost
  useEffect(() => {
    return () => {
      // Cleanup geometries and materials when component unmounts
      if (mesh.current) {
        if (mesh.current.geometry) {
          mesh.current.geometry.dispose();
        }
        if (mesh.current.material) {
          if (Array.isArray(mesh.current.material)) {
            mesh.current.material.forEach(material => material.dispose());
          } else {
            mesh.current.material.dispose();
          }
        }
      }
    };
  }, []);

  // Proper orbital physics animation with context loss handling
  useFrame((state) => {
    if (!mesh.current || contextLost) return;

    const positions = mesh.current.geometry.attributes.position.array;
    const time = state.clock.getElapsedTime();

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      const orbital = starData.orbitalData[i];
      
      // Responsive orbital movement with scroll interaction
      const baseOrbitalSpeed = orbital.orbitalSpeed * 1.0; // Normal speed for galaxy animation
      const scrollSpeedMultiplier = 1 + (scrollVelocity * 0.5); // Reduced scroll effect
      const currentAngle = orbital.initialAngle + (time * baseOrbitalSpeed * scrollSpeedMultiplier) + orbital.phaseOffset;
      
      // Ultra-slow breathing animation - 3 minutes per half cycle, each star different
      const breathingFreq = 0.00174; // 3 minutes = 180 seconds per half cycle (1/180*π = 0.00174)
      const starSpecificTiming = orbital.phaseOffset * 2.5; // Different timing per star
      const breathingAmp = orbital.initialRadius * 0.004; // Reduced amplitude for subtlety
      const radiusVariation = Math.sin(time * breathingFreq + starSpecificTiming) * breathingAmp;
      const currentRadius = orbital.initialRadius + radiusVariation;
      
      // Calculate new orbital position
      const orbitalX = Math.cos(currentAngle) * currentRadius;
      const orbitalY = Math.sin(currentAngle) * currentRadius;
      
      // Very subtle mouse interaction that doesn't break orbital flow
      const mouseInfluence = 0.03; // Much reduced influence
      const dx = orbitalX - mouse.current.x * viewport.width * 0.3;
      const dy = orbitalY - mouse.current.y * viewport.height * 0.3;
      const mouseDistance = Math.sqrt(dx * dx + dy * dy);
      
      let finalX = orbitalX;
      let finalY = orbitalY;
      
      // Only apply mouse effect when very close and keep it minimal
      if (mouseDistance < 1.5) {
        const mouseForce = (1.5 - mouseDistance) * mouseInfluence;
        finalX += (dx / mouseDistance) * mouseForce;
        finalY += (dy / mouseDistance) * mouseForce;
      }
      
      // Smooth position updates
      positions[i3] = finalX;
      positions[i3 + 1] = finalY;
      // Keep Z position with ultra-slow breathing effect, each star different
      const zBreathingFreq = 0.00087; // 6 minutes per full cycle for Z movement
      positions[i3 + 2] = starData.positions[i * 3 + 2] + Math.sin(time * zBreathingFreq + starSpecificTiming) * 0.015;
    }

    mesh.current.geometry.attributes.position.needsUpdate = true;
    
    // Classic galaxy view at 45-degree angle
    const baseRotationSpeed = 0.001; // Slower, more realistic rotation
    const scrollBoost = scrollVelocity * 0.0003;
    mesh.current.rotation.z = time * (baseRotationSpeed + scrollBoost);
    mesh.current.rotation.x = Math.PI / 4; // 45-degree tilt for classic galaxy view
  });

  return (
    <points ref={mesh}>
      <bufferGeometry>
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
const NebulaBackground = React.memo(memoize(function NebulaBackground({ count = 6 }) {
  const meshRef = useRef();
  const { viewport } = useThree();
  const contextLost = useWebGLContextRecovery();

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
      if (meshRef.current) {
        if (meshRef.current.geometry) {
          meshRef.current.geometry.dispose();
        }
        if (meshRef.current.material) {
          if (Array.isArray(meshRef.current.material)) {
            meshRef.current.material.forEach(material => material.dispose());
          } else {
            meshRef.current.material.dispose();
          }
        }
      }
    };
  }, []);

  // Slow drift animation for nebulae
  useFrame((state) => {
    if (!meshRef.current || contextLost) return;
    
    const time = state.clock.getElapsedTime();
    const positions = meshRef.current.geometry.attributes.position.array;
    
    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      const originalX = nebulaData.positions[i3];
      const originalY = nebulaData.positions[i3 + 1];
      
      // Very slow drift
      const driftX = Math.sin(time * 0.0001 + i) * 0.1;
      const driftY = Math.cos(time * 0.0001 + i * 1.3) * 0.1;
      
      positions[i3] = originalX + driftX;
      positions[i3 + 1] = originalY + driftY;
    }
    
    meshRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={meshRef}>
      <bufferGeometry>
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

// Floating Balls Component for subtle movement
const FloatingBalls = React.memo(memoize(function FloatingBalls({ count = 4, scrollVelocity = 0 }) { // Minimal ball count
  const meshRef = useRef();
  const { viewport } = useThree();
  const contextLost = useWebGLContextRecovery();

  // Generate ball data
  const ballData = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const ballInfo = [];
    
    for (let i = 0; i < count; i++) {
      // Random positions across the viewport
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
        driftSpeedX: (Math.random() - 0.5) * 0.01, // Enhanced drift speed
        driftSpeedY: (Math.random() - 0.5) * 0.01,
        driftSpeedZ: (Math.random() - 0.5) * 0.006,
        phaseOffset: Math.random() * Math.PI * 2,
        size: Math.random() * 0.8 + 0.4, // Varying ball sizes
      });
    }
    
    return { positions, ballInfo };
  }, [count, viewport.width, viewport.height]);

  // Add cleanup for FloatingBalls component
  useEffect(() => {
    return () => {
      // Cleanup geometries and materials when component unmounts
      if (meshRef.current) {
        if (meshRef.current.geometry) {
          meshRef.current.geometry.dispose();
        }
        if (meshRef.current.material) {
          if (Array.isArray(meshRef.current.material)) {
            meshRef.current.material.forEach(material => material.dispose());
          } else {
            meshRef.current.material.dispose();
          }
        }
      }
    };
  }, []);

  // Animate balls with imperceptible movement that responds to scroll (with context loss handling)
  useFrame((state) => {
    if (!meshRef.current || contextLost) return;

    const positions = meshRef.current.geometry.attributes.position.array;
    const time = state.clock.getElapsedTime();

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      const ball = ballData.ballInfo[i];
      
      // Ultra-slow movement - each ball has different unsynchronized timing
      const ballSpecificTiming = ball.phaseOffset * 3.7; // Different timing per ball
      const scrollDriftMultiplier = 1 + (scrollVelocity * 0.3); // Much reduced scroll effect
      
      // EXTREMELY slow floating motion - 10-15 minute cycles for imperceptible background
      const floatFreqX = 0.000058 + (ball.phaseOffset * 0.00001); // ~12 minute cycle, varied per ball
      const floatFreqY = 0.000046 + (ball.phaseOffset * 0.000008); // ~15 minute cycle, varied per ball
      const floatFreqZ = 0.000070 + (ball.phaseOffset * 0.000005); // ~10 minute cycle, varied per ball
      
      const floatX = Math.sin(time * floatFreqX + ballSpecificTiming) * 0.2 * scrollDriftMultiplier;
      const floatY = Math.cos(time * floatFreqY + ballSpecificTiming) * 0.18 * scrollDriftMultiplier;
      const floatZ = Math.sin(time * floatFreqZ + ballSpecificTiming) * 0.12 * scrollDriftMultiplier;
      
      // Ultra-slow drift motion - each ball moves at different speeds
      const driftSpeedX = ball.driftSpeedX * 0.001; // 1000x slower for imperceptible background
      const driftSpeedY = ball.driftSpeedY * 0.001; // 1000x slower for imperceptible background
      const driftSpeedZ = ball.driftSpeedZ * 0.001; // 1000x slower for imperceptible background
      
      const driftX = Math.sin(time * driftSpeedX + ballSpecificTiming) * 0.4;
      const driftY = Math.cos(time * driftSpeedY + ballSpecificTiming) * 0.4;
      const driftZ = Math.sin(time * driftSpeedZ + ballSpecificTiming) * 0.25;
      
      // Update positions with combined motion
      positions[i3] = ball.initialX + floatX + driftX;
      positions[i3 + 1] = ball.initialY + floatY + driftY;
      positions[i3 + 2] = ball.initialZ + floatZ + driftZ;
    }

    meshRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={meshRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={ballData.positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.04}
        sizeAttenuation={true}
        color="#FFD700"
        transparent={true}
        opacity={0.7}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}));

const GalaxyConstellation = React.memo(memoize(function GalaxyConstellation({ scrollVelocity = 0 }) {
  const [webglSupported, setWebglSupported] = useState(true);

  // Check WebGL support on mount
  useEffect(() => {
    const testWebGL = () => {
      try {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!context) {
          setWebglSupported(false);
          return false;
        }
        return true;
      } catch (e) {
        console.warn('WebGL not supported:', e);
        setWebglSupported(false);
        return false;
      }
    };

    testWebGL();
  }, []);

  // Fallback for when WebGL is not supported
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
      <WebGLErrorBoundary>
        <Canvas
          camera={{ position: [0, 0, 5], fov: 75 }}
          style={{ background: 'transparent' }}
          gl={{ 
            antialias: false, // Disable for better performance
            powerPreference: "high-performance",
            alpha: true,
            premultipliedAlpha: false,
            preserveDrawingBuffer: false,
            failIfMajorPerformanceCaveat: false, // Allow fallback renderers
            stencil: false, // Disable stencil buffer for performance
            depth: true, // Keep depth buffer for proper rendering
          }}
          dpr={[1, 1.5]} // Reduced max DPR for better performance
          frameloop="always"
          performance={{ 
            min: 0.2, // Increased threshold for better degradation
            max: Infinity,
            debounce: 200 // Add debounce for performance monitoring
          }}
          onCreated={({ gl, scene, camera }) => {
            // Advanced performance optimizations
            gl.setClearColor(0x000000, 0);
            gl.sortObjects = false; // Disable sorting for better performance
            
            // Minimal debug setup to reduce overhead
            gl.debug = {
              checkShaderErrors: false, // Disable for performance
              onShaderError: null // Remove error handler
            };
            
            // Reduce render calls and computational complexity
            scene.autoUpdate = false;
            camera.updateProjectionMatrix(); // One-time update
          }}
          onError={(error) => {
            console.error('Canvas Error:', error);
            // Error will be handled by WebGLErrorBoundary
          }}
        >
          <ambientLight intensity={0.3} />
          <NebulaBackground count={6} />
          <Stars count={600} scrollVelocity={scrollVelocity} />
          <FloatingBalls count={8} scrollVelocity={scrollVelocity} />
        </Canvas>
      </WebGLErrorBoundary>
    </div>
  );
}));

// Progressive enhancement wrapper
const GalaxyConstellationWithProgressive = React.memo((props) => {
  const [shouldRender, setShouldRender] = useState(false);
  const [performanceGood, setPerformanceGood] = useState(true);
  const frameTimeRef = useRef([]);
  const performanceCheckRef = useRef(null);

  // Progressive enhancement check
  useEffect(() => {
    const checkPerformance = () => {
      // Check device capabilities
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
      
      if (!gl) {
        console.log('WebGL not supported, skipping 3D rendering');
        setShouldRender(false);
        return;
      }

      // Check for reduced motion preference
      const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (prefersReducedMotion) {
        console.log('User prefers reduced motion, using fallback');
        setShouldRender(false);
        return;
      }

      // Check device memory (if available)
      const deviceMemory = navigator.deviceMemory;
      if (deviceMemory && deviceMemory < 4) {
        console.log('Low device memory detected, using fallback');
        setShouldRender(false);
        return;
      }

      // Check if device is likely mobile with limited resources
      const isMobile = /Mobi|Android/i.test(navigator.userAgent);
      const hasLowHardwareConcurrency = navigator.hardwareConcurrency && navigator.hardwareConcurrency < 4;
      
      if (isMobile && hasLowHardwareConcurrency) {
        console.log('Mobile device with limited resources, using fallback');
        setShouldRender(false);
        return;
      }

      // All checks passed, enable 3D rendering
      setShouldRender(true);
    };

    // Delay the check to not block initial render
    const timeoutId = setTimeout(checkPerformance, 100);
    return () => clearTimeout(timeoutId);
  }, []);

  // Performance monitoring
  useEffect(() => {
    if (!shouldRender) return;

    let frameCount = 0;
    let lastTime = performance.now();
    const targetFPS = 30; // Minimum acceptable FPS
    const checkInterval = 5000; // Check every 5 seconds

    const monitorPerformance = () => {
      const now = performance.now();
      frameCount++;
      
      if (now - lastTime >= checkInterval) {
        const fps = (frameCount * 1000) / (now - lastTime);
        
        if (fps < targetFPS) {
          console.log(`Low FPS detected (${fps.toFixed(1)}), switching to fallback`);
          setPerformanceGood(false);
          setShouldRender(false);
          return;
        }
        
        frameCount = 0;
        lastTime = now;
      }
      
      if (shouldRender && performanceGood) {
        performanceCheckRef.current = requestAnimationFrame(monitorPerformance);
      }
    };

    performanceCheckRef.current = requestAnimationFrame(monitorPerformance);

    return () => {
      if (performanceCheckRef.current) {
        cancelAnimationFrame(performanceCheckRef.current);
      }
    };
  }, [shouldRender, performanceGood]);

  // Fallback component for low-performance devices
  const FallbackBackground = () => (
    <div className="fixed inset-0 pointer-events-none" style={{ zIndex: -1 }}>
      <div className="w-full h-full bg-gradient-to-b from-slate-900/20 via-purple-900/15 to-black/10">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-purple-900/30 via-slate-900/15 to-transparent animate-pulse"></div>
        {/* Add some CSS stars for minimal animation */}
        <div className="absolute inset-0 overflow-hidden">
          {[...Array(20)].map((_, i) => (
            <div
              key={i}
              className="absolute w-1 h-1 bg-white rounded-full opacity-60"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                animationDelay: `${Math.random() * 3}s`,
                animation: `twinkle ${3 + Math.random() * 2}s infinite`
              }}
            />
          ))}
        </div>
      </div>
      <style jsx>{`
        @keyframes twinkle {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );

  if (!shouldRender || !performanceGood) {
    return <FallbackBackground />;
  }

  return <GalaxyConstellation {...props} />;
});

GalaxyConstellationWithProgressive.displayName = 'GalaxyConstellationWithProgressive';

export default memoize(GalaxyConstellationWithProgressive);