#!/usr/bin/env python3
"""Dependency Validator for ML-Enhanced Orchestrator

Validates that all required dependencies are available and provides helpful
error messages if any are missing. Includes graceful degradation information.
"""

import sys
import importlib
from typing import List, Dict, Any, Tuple

def check_dependency(module_name: str, optional: bool = False) -> Tuple[bool, str]:
    """Check if a module is available."""
    try:
        importlib.import_module(module_name)
        return True, f"✓ {module_name} is available"
    except ImportError as e:
        if optional:
            return False, f"⚠ {module_name} is not available (optional): {e}"
        else:
            return False, f"✗ {module_name} is missing (required): {e}"

def validate_dependencies() -> Dict[str, Any]:
    """Validate all dependencies for the ML-Enhanced Orchestrator."""
    
    # Core Python dependencies (required)
    core_deps = [
        'asyncio',
        'json', 
        'time',
        'typing',
        'pathlib',
        'dataclasses',
        'enum',
        'uuid'
    ]
    
    # Optional dependencies with fallbacks
    optional_deps = [
        'numpy',
        'structlog'
    ]
    
    # Test imports of our modules
    local_modules = [
        'ml_enhanced_orchestrator',
        'mcp_integration_layer'
    ]
    
    results = {
        'core_dependencies': {},
        'optional_dependencies': {},
        'local_modules': {},
        'all_passed': True,
        'warnings': [],
        'errors': []
    }
    
    # Check core dependencies
    print("Checking core Python dependencies...")
    for dep in core_deps:
        success, message = check_dependency(dep)
        results['core_dependencies'][dep] = success
        print(f"  {message}")
        if not success:
            results['all_passed'] = False
            results['errors'].append(message)
    
    # Check optional dependencies
    print("\nChecking optional dependencies...")
    for dep in optional_deps:
        success, message = check_dependency(dep, optional=True)
        results['optional_dependencies'][dep] = success
        print(f"  {message}")
        if not success:
            results['warnings'].append(message)
    
    # Check local modules
    print("\nChecking local modules...")
    sys.path.append('.')
    
    for module in local_modules:
        success, message = check_dependency(module)
        results['local_modules'][module] = success
        print(f"  {message}")
        if not success:
            results['all_passed'] = False
            results['errors'].append(message)
    
    # Test ML functionality
    print("\nTesting ML functionality...")
    try:
        from ml_enhanced_orchestrator import MLDecisionEngine, MLEnhancedOrchestrator
        
        # Test instantiation
        engine = MLDecisionEngine()
        orchestrator = MLEnhancedOrchestrator()
        
        print("  ✓ ML classes can be instantiated successfully")
        
        # Test numpy fallback
        import ml_enhanced_orchestrator
        np = ml_enhanced_orchestrator.np
        
        test_data = [1, 2, 3, 4, 5]
        mean_val = np.mean(test_data)
        std_val = np.std(test_data)
        
        print(f"  ✓ Math functions working (mean: {mean_val}, std: {std_val:.2f})")
        
        if not ml_enhanced_orchestrator.HAS_NUMPY:
            print("  ⚠ Using fallback numpy implementation")
            results['warnings'].append("Using fallback numpy implementation")
        else:
            print("  ✓ Using real numpy library")
        
    except Exception as e:
        results['all_passed'] = False
        error_msg = f"ML functionality test failed: {e}"
        results['errors'].append(error_msg)
        print(f"  ✗ {error_msg}")
    
    return results

def print_summary(results: Dict[str, Any]) -> None:
    """Print summary of validation results."""
    print("\n" + "="*60)
    print("DEPENDENCY VALIDATION SUMMARY")
    print("="*60)
    
    if results['all_passed']:
        print("✓ All required dependencies are available!")
        print("  The ML-Enhanced Orchestrator is ready to use.")
    else:
        print("✗ Some required dependencies are missing!")
        print("  Please install missing dependencies before using the orchestrator.")
    
    if results['warnings']:
        print(f"\n⚠ Warnings ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"  - {warning}")
        print("  The system will use fallback implementations.")
    
    if results['errors']:
        print(f"\n✗ Errors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  - {error}")
    
    print("\nInstallation recommendations:")
    if not results['optional_dependencies'].get('numpy', True):
        print("  pip install numpy  # For better performance")
    if not results['optional_dependencies'].get('structlog', True):
        print("  pip install structlog  # For better logging")
    
    print("\nGraceful degradation features:")
    print("  - Fallback numpy implementation using built-in math")
    print("  - Fallback logging using standard library")
    print("  - Fallback MCP integration layer")

if __name__ == "__main__":
    print("ML-Enhanced Orchestrator Dependency Validator")
    print("=" * 50)
    
    results = validate_dependencies()
    print_summary(results)
    
    # Exit with appropriate code
    sys.exit(0 if results['all_passed'] else 1)