#!/usr/bin/env node
/**
 * React Authentication Performance Profiler
 * Analyzes React component re-render patterns and memory usage during authentication flows
 */

const fs = require('fs');
const path = require('path');

class ReactAuthPerformanceProfiler {
  constructor() {
    this.performanceData = {
      timestamp: new Date().toISOString(),
      reRenderAnalysis: {},
      memoryLeakPatterns: [],
      componentOptimizations: [],
      authFlowBottlenecks: []
    };
  }

  /**
   * Analyze React component patterns that could cause re-renders
   */
  analyzeReRenderPatterns(sourceCode, componentName) {
    const reRenderTriggers = [];
    
    // Pattern 1: Inline object creation in props/deps
    const inlineObjectRegex = /(\w+)=\{\{[^}]+\}\}|deps:\s*\[[^\]]*\{[^}]*\}[^\]]*\]/g;
    let match;
    while ((match = inlineObjectRegex.exec(sourceCode)) !== null) {
      reRenderTriggers.push({
        type: 'inline_object_creation',
        line: sourceCode.substring(0, match.index).split('\n').length,
        pattern: match[0],
        severity: 'high',
        impact: 'Causes re-render on every parent render'
      });
    }

    // Pattern 2: Inline function creation
    const inlineFunctionRegex = /(\w+)=\{(\([^)]*\)|\w+)\s*=>\s*[^}]+\}|onClick=\{.*?=>/g;
    while ((match = inlineFunctionRegex.exec(sourceCode)) !== null) {
      reRenderTriggers.push({
        type: 'inline_function_creation',
        line: sourceCode.substring(0, match.index).split('\n').length,
        pattern: match[0].substring(0, 50) + '...',
        severity: 'medium',
        impact: 'Creates new function reference on each render'
      });
    }

    // Pattern 3: Missing dependencies in useEffect/useCallback
    const effectHookRegex = /use(Effect|Callback|Memo)\([^,]+,\s*\[([^\]]*)\]/g;
    while ((match = effectHookRegex.exec(sourceCode)) !== null) {
      const deps = match[2];
      const hookType = match[1];
      
      // Check for complex objects in dependencies
      if (deps.includes('.') || deps.includes('current') || deps.includes('state')) {
        reRenderTriggers.push({
          type: 'complex_dependencies',
          hook: `use${hookType}`,
          line: sourceCode.substring(0, match.index).split('\n').length,
          dependencies: deps,
          severity: 'high',
          impact: 'May cause excessive re-renders due to object/ref dependencies'
        });
      }
    }

    // Pattern 4: State updates in render cycle
    const stateUpdateRegex = /set\w+\([^)]*\)[^;]*(?=.*return|.*\<)/g;
    while ((match = stateUpdateRegex.exec(sourceCode)) !== null) {
      const lineContent = sourceCode.split('\n')[sourceCode.substring(0, match.index).split('\n').length - 1];
      if (!lineContent.includes('useEffect') && !lineContent.includes('useCallback')) {
        reRenderTriggers.push({
          type: 'render_cycle_state_update',
          line: sourceCode.substring(0, match.index).split('\n').length,
          pattern: match[0],
          severity: 'critical',
          impact: 'State update during render can cause infinite loops'
        });
      }
    }

    return {
      component: componentName,
      reRenderTriggers,
      riskScore: this.calculateRiskScore(reRenderTriggers)
    };
  }

  /**
   * Analyze memory leak patterns in authentication components
   */
  analyzeMemoryLeakPatterns(sourceCode, componentName) {
    const memoryLeakRisks = [];

    // Pattern 1: Missing cleanup in useEffect
    const effectWithoutCleanupRegex = /useEffect\(\(\)\s*=>\s*{[^}]*(?:setInterval|setTimeout|addEventListener)[^}]*}\s*,\s*\[[^\]]*\]\)/g;
    let match;
    while ((match = effectWithoutCleanupRegex.exec(sourceCode)) !== null) {
      const hasReturn = match[0].includes('return');
      if (!hasReturn) {
        memoryLeakRisks.push({
          type: 'missing_effect_cleanup',
          line: sourceCode.substring(0, match.index).split('\n').length,
          severity: 'high',
          risk: 'Timer/event listener not cleaned up'
        });
      }
    }

    // Pattern 2: Ref usage without cleanup
    const refUsageRegex = /const\s+(\w+Ref)\s*=\s*useRef/g;
    const refCallbacks = [];
    while ((match = refUsageRegex.exec(sourceCode)) !== null) {
      refCallbacks.push(match[1]);
    }

    refCallbacks.forEach(refName => {
      if (sourceCode.includes(`${refName}.current.add`) || sourceCode.includes(`${refName}.current.set`)) {
        if (!sourceCode.includes(`${refName}.current.clear`) && !sourceCode.includes(`${refName}.current.delete`)) {
          memoryLeakRisks.push({
            type: 'ref_accumulation',
            refName,
            severity: 'medium',
            risk: `Ref ${refName} accumulates data without cleanup`
          });
        }
      }
    });

    // Pattern 3: Closure with large objects
    const closureRegex = /useCallback\([^,]*,[^,\]]*(\w+)[^,\]]*\]/g;
    while ((match = closureRegex.exec(sourceCode)) !== null) {
      const capturedVar = match[1];
      if (/state|context|data|result/i.test(capturedVar)) {
        memoryLeakRisks.push({
          type: 'large_closure_capture',
          line: sourceCode.substring(0, match.index).split('\n').length,
          capturedVariable: capturedVar,
          severity: 'medium',
          risk: 'useCallback may capture large objects in closure'
        });
      }
    }

    return {
      component: componentName,
      memoryLeakRisks,
      riskScore: this.calculateMemoryRiskScore(memoryLeakRisks)
    };
  }

  /**
   * Calculate risk score based on re-render triggers
   */
  calculateRiskScore(triggers) {
    const severityScores = { critical: 10, high: 7, medium: 4, low: 2 };
    return triggers.reduce((score, trigger) => score + (severityScores[trigger.severity] || 0), 0);
  }

  /**
   * Calculate memory risk score
   */
  calculateMemoryRiskScore(risks) {
    const severityScores = { high: 8, medium: 5, low: 2 };
    return risks.reduce((score, risk) => score + (severityScores[risk.severity] || 0), 0);
  }

  /**
   * Generate optimization recommendations
   */
  generateOptimizationRecommendations(analysis) {
    const recommendations = [];

    analysis.reRenderTriggers.forEach(trigger => {
      switch (trigger.type) {
        case 'inline_object_creation':
          recommendations.push({
            type: 'memoization',
            priority: 'high',
            component: analysis.component,
            recommendation: 'Move inline objects to useMemo or useState',
            example: 'const config = useMemo(() => ({ ...props }), [props.key])'
          });
          break;

        case 'inline_function_creation':
          recommendations.push({
            type: 'callback_optimization',
            priority: 'medium',
            component: analysis.component,
            recommendation: 'Use useCallback for inline functions',
            example: 'const handleClick = useCallback(() => {}, [deps])'
          });
          break;

        case 'complex_dependencies':
          recommendations.push({
            type: 'dependency_optimization',
            priority: 'high',
            component: analysis.component,
            recommendation: 'Simplify useEffect dependencies or use refs',
            example: 'Use useRef for mutable values, primitive values for deps'
          });
          break;

        case 'render_cycle_state_update':
          recommendations.push({
            type: 'state_management',
            priority: 'critical',
            component: analysis.component,
            recommendation: 'Move state updates to event handlers or effects',
            example: 'Use useEffect or event handlers, not render function'
          });
          break;
      }
    });

    return recommendations;
  }

  /**
   * Analyze authentication flow bottlenecks
   */
  analyzeAuthFlowBottlenecks(componentAnalysis) {
    const bottlenecks = [];

    // High re-render components in auth flow
    componentAnalysis.forEach(analysis => {
      if (analysis.riskScore > 15) {
        bottlenecks.push({
          type: 'high_rerender_component',
          component: analysis.component,
          riskScore: analysis.riskScore,
          impact: 'Component re-renders excessively during auth operations'
        });
      }

      // Check for auth-specific patterns
      analysis.reRenderTriggers.forEach(trigger => {
        if (trigger.pattern.includes('isAuthenticated') || trigger.pattern.includes('authState')) {
          bottlenecks.push({
            type: 'auth_state_rerender',
            component: analysis.component,
            trigger: trigger.pattern,
            impact: 'Authentication state changes trigger unnecessary re-renders'
          });
        }
      });
    });

    return bottlenecks;
  }

  /**
   * Analyze specific authentication components
   */
  async analyzeAuthComponents() {
    const authComponentPaths = [
      'app/webui-next/src/components/PrivateRoute.jsx',
      'app/webui-next/src/context/AuthContext.jsx',
      'app/webui-next/src/context/AuthContext.js',
      'app/webui-next/src/utils/authStateMachine.js',
      'app/webui-next/src/components/LoginForm.jsx'
    ];

    const componentAnalysis = [];

    for (const relativePath of authComponentPaths) {
      const fullPath = path.join(process.cwd(), relativePath);
      
      try {
        if (fs.existsSync(fullPath)) {
          const sourceCode = fs.readFileSync(fullPath, 'utf8');
          const componentName = path.basename(fullPath, path.extname(fullPath));

          // Analyze re-render patterns
          const reRenderAnalysis = this.analyzeReRenderPatterns(sourceCode, componentName);
          
          // Analyze memory leak patterns
          const memoryAnalysis = this.analyzeMemoryLeakPatterns(sourceCode, componentName);
          
          // Generate recommendations
          const recommendations = this.generateOptimizationRecommendations(reRenderAnalysis);

          const analysis = {
            ...reRenderAnalysis,
            memoryAnalysis,
            recommendations,
            filePath: relativePath,
            size: sourceCode.length,
            complexity: sourceCode.split('\n').length
          };

          componentAnalysis.push(analysis);
          console.log(`✓ Analyzed ${componentName} (Risk Score: ${reRenderAnalysis.riskScore})`);
        }
      } catch (error) {
        console.log(`✗ Failed to analyze ${relativePath}: ${error.message}`);
      }
    }

    return componentAnalysis;
  }

  /**
   * Generate comprehensive performance report
   */
  async generatePerformanceReport() {
    console.log('React Authentication Performance Analysis');
    console.log('==========================================\n');

    // Analyze authentication components
    const componentAnalysis = await this.analyzeAuthComponents();
    
    // Analyze auth flow bottlenecks
    const authFlowBottlenecks = this.analyzeAuthFlowBottlenecks(componentAnalysis);

    // Compile performance data
    this.performanceData.reRenderAnalysis = componentAnalysis;
    this.performanceData.authFlowBottlenecks = authFlowBottlenecks;
    
    // Extract all memory leak patterns and optimizations
    this.performanceData.memoryLeakPatterns = componentAnalysis
      .flatMap(analysis => analysis.memoryAnalysis.memoryLeakRisks);
      
    this.performanceData.componentOptimizations = componentAnalysis
      .flatMap(analysis => analysis.recommendations);

    // Calculate summary statistics
    const totalRiskScore = componentAnalysis.reduce((sum, analysis) => sum + analysis.riskScore, 0);
    const averageRiskScore = componentAnalysis.length > 0 ? totalRiskScore / componentAnalysis.length : 0;
    
    const highRiskComponents = componentAnalysis.filter(analysis => analysis.riskScore > 15);
    const criticalIssues = componentAnalysis.reduce((count, analysis) => {
      return count + analysis.reRenderTriggers.filter(trigger => trigger.severity === 'critical').length;
    }, 0);

    this.performanceData.summary = {
      totalComponents: componentAnalysis.length,
      totalRiskScore,
      averageRiskScore: Math.round(averageRiskScore * 100) / 100,
      highRiskComponents: highRiskComponents.length,
      criticalIssues,
      totalOptimizations: this.performanceData.componentOptimizations.length,
      totalMemoryRisks: this.performanceData.memoryLeakPatterns.length
    };

    return this.performanceData;
  }

  /**
   * Print performance report to console
   */
  printReport(data) {
    console.log('=== REACT AUTH PERFORMANCE SUMMARY ===\n');
    
    if (data.summary) {
      const s = data.summary;
      console.log(`Components Analyzed: ${s.totalComponents}`);
      console.log(`Total Risk Score: ${s.totalRiskScore}`);
      console.log(`Average Risk Score: ${s.averageRiskScore}`);
      console.log(`High Risk Components: ${s.highRiskComponents}`);
      console.log(`Critical Issues: ${s.criticalIssues}`);
      console.log(`Total Optimizations Needed: ${s.totalOptimizations}`);
      console.log(`Memory Leak Risks: ${s.totalMemoryRisks}\n`);
    }

    if (data.authFlowBottlenecks.length > 0) {
      console.log('=== AUTH FLOW BOTTLENECKS ===\n');
      data.authFlowBottlenecks.forEach((bottleneck, index) => {
        console.log(`${index + 1}. ${bottleneck.type.toUpperCase()}`);
        console.log(`   Component: ${bottleneck.component}`);
        console.log(`   Impact: ${bottleneck.impact}`);
        if (bottleneck.riskScore) console.log(`   Risk Score: ${bottleneck.riskScore}`);
        console.log();
      });
    }

    if (data.componentOptimizations.length > 0) {
      console.log('=== TOP OPTIMIZATION RECOMMENDATIONS ===\n');
      const prioritized = data.componentOptimizations
        .sort((a, b) => (b.priority === 'critical' ? 2 : b.priority === 'high' ? 1 : 0) - 
                        (a.priority === 'critical' ? 2 : a.priority === 'high' ? 1 : 0))
        .slice(0, 10);

      prioritized.forEach((opt, index) => {
        console.log(`${index + 1}. [${opt.priority.toUpperCase()}] ${opt.component}`);
        console.log(`   Type: ${opt.type}`);
        console.log(`   Recommendation: ${opt.recommendation}`);
        console.log(`   Example: ${opt.example}`);
        console.log();
      });
    }
  }
}

// Main execution
async function main() {
  const profiler = new ReactAuthPerformanceProfiler();
  
  try {
    const performanceData = await profiler.generatePerformanceReport();
    profiler.printReport(performanceData);
    
    // Save detailed report
    const reportPath = '.claude/test_results/performance/react_auth_performance_report.json';
    fs.writeFileSync(reportPath, JSON.stringify(performanceData, null, 2));
    console.log(`Detailed report saved to: ${reportPath}`);
    
  } catch (error) {
    console.error('Performance analysis failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { ReactAuthPerformanceProfiler };