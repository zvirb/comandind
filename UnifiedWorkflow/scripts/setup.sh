#!/bin/bash
# UnifiedWorkflow Setup Script
# Initializes the orchestration system in a new project

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="${1:-$(pwd)}"

echo "🤖 UnifiedWorkflow Setup"
echo "========================"
echo "Workflow source: $WORKFLOW_DIR"
echo "Target project: $PROJECT_DIR"
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository. Please run 'git init' first."
    exit 1
fi

# Create .claude directory structure
echo "📁 Creating .claude directory structure..."
mkdir -p "$PROJECT_DIR/.claude"
mkdir -p "$PROJECT_DIR/.claude/context-packages"
mkdir -p "$PROJECT_DIR/.claude/agents"
mkdir -p "$PROJECT_DIR/.claude/monitoring"

# Copy CLAUDE.md to project root
echo "📋 Copying CLAUDE.md workflow instructions..."
cp "$WORKFLOW_DIR/CLAUDE.md" "$PROJECT_DIR/CLAUDE.md"

# Copy workflow configuration
echo "⚙️  Setting up workflow configuration..."
cp "$WORKFLOW_DIR/workflows/12-phase-workflow.yaml" "$PROJECT_DIR/.claude/unified-orchestration-config.yaml"

# Initialize orchestration todos
echo "📝 Initializing orchestration todos..."
if [ ! -f "$PROJECT_DIR/.claude/orchestration_todos.json" ]; then
    echo "[]" > "$PROJECT_DIR/.claude/orchestration_todos.json"
fi

# Copy context package templates
echo "📦 Installing context package templates..."
cp "$WORKFLOW_DIR/templates/context-package-templates.yaml" "$PROJECT_DIR/.claude/"

# Copy agent specifications
echo "🤖 Installing agent specifications..."
cp -r "$WORKFLOW_DIR/agents/"* "$PROJECT_DIR/.claude/agents/"

# Copy monitoring tools
echo "📊 Installing monitoring tools..."
cp "$WORKFLOW_DIR/monitoring/orchestration-monitor.py" "$PROJECT_DIR/.claude/monitoring/"

# Create MCP configuration directory
echo "🔧 Setting up MCP configurations..."
mkdir -p "$PROJECT_DIR/.claude/mcp"
cp -r "$WORKFLOW_DIR/mcps/"* "$PROJECT_DIR/.claude/mcp/"

# Create .gitignore for orchestration files
echo "📝 Setting up .gitignore..."
if [ ! -f "$PROJECT_DIR/.gitignore" ]; then
    touch "$PROJECT_DIR/.gitignore"
fi

# Add orchestration-specific ignores if not already present
grep -q "^# UnifiedWorkflow" "$PROJECT_DIR/.gitignore" || cat >> "$PROJECT_DIR/.gitignore" << 'EOF'

# UnifiedWorkflow Orchestration
.claude/monitoring/*.log
.claude/monitoring/*.json
.claude/context-packages/*.json
.claude/checkpoints/
.claude/temp/
.monitoring/
EOF

# Check for required dependencies
echo "🔍 Checking dependencies..."

# Check for Redis (optional)
if command -v redis-cli &> /dev/null; then
    echo "✅ Redis found (for agent coordination)"
else
    echo "⚠️  Redis not found - agent coordination will use fallback mode"
fi

# Check for Python (for monitoring)
if command -v python3 &> /dev/null; then
    echo "✅ Python 3 found (for monitoring tools)"
else
    echo "⚠️  Python 3 not found - monitoring tools unavailable"
fi

# Check for Docker (optional)
if command -v docker &> /dev/null; then
    echo "✅ Docker found (for containerized deployments)"
else
    echo "⚠️  Docker not found - container features unavailable"
fi

# Create example orchestration trigger
echo "📋 Creating example orchestration trigger..."
cat > "$PROJECT_DIR/.claude/example-triggers.md" << 'EOF'
# UnifiedWorkflow Orchestration Triggers

Use any of these phrases in Claude Code to start the orchestration workflow:

## Basic Triggers
- `start flow`
- `orchestration` 
- `agentic flow`
- `start agent(s)`

## Specific Examples
- `start orchestration for new feature development`
- `begin agentic flow for performance optimization`
- `initiate workflow for security audit`
- `start agents for full-stack implementation`

## What Happens Next
1. Phase 0: Todo context integration loads from .claude/orchestration_todos.json
2. Phase 1: Agent ecosystem validation checks all systems
3. Phase 2: Strategic planning creates implementation approach
4. ... continues through all 12 phases
5. Phase 12: Loop control decides whether to continue or complete

## Monitoring
Check `.claude/monitoring/` for execution logs and metrics
EOF

# Create example todo file with setup tasks
echo "📝 Creating initial setup todos..."
cat > "$PROJECT_DIR/.claude/orchestration_todos_example.json" << 'EOF'
[
  {
    "id": "setup-validation",
    "content": "Validate UnifiedWorkflow setup and agent ecosystem",
    "priority": "high",
    "status": "pending",
    "context_tags": ["setup", "validation", "system-check"],
    "urgency_score": 80,
    "impact_score": 85,
    "created_date": "2025-01-19",
    "updated_date": "2025-01-19"
  },
  {
    "id": "mcp-integration-test",
    "content": "Test MCP server integrations for memory and Redis",
    "priority": "medium",
    "status": "pending", 
    "context_tags": ["mcp", "integration", "testing"],
    "urgency_score": 60,
    "impact_score": 70,
    "created_date": "2025-01-19",
    "updated_date": "2025-01-19"
  },
  {
    "id": "agent-capability-audit",
    "content": "Audit all 35+ agent capabilities and tool access",
    "priority": "medium",
    "status": "pending",
    "context_tags": ["agents", "audit", "capabilities"],
    "urgency_score": 65,
    "impact_score": 75,
    "created_date": "2025-01-19", 
    "updated_date": "2025-01-19"
  }
]
EOF

# Create setup validation script
echo "🧪 Creating setup validation script..."
cat > "$PROJECT_DIR/.claude/validate-setup.py" << 'EOF'
#!/usr/bin/env python3
"""
UnifiedWorkflow Setup Validation
Validates that the orchestration system is properly installed
"""

import json
import os
import sys
from pathlib import Path

def validate_setup():
    """Validate UnifiedWorkflow setup"""
    project_dir = Path.cwd()
    claude_dir = project_dir / ".claude"
    
    print("🔍 Validating UnifiedWorkflow Setup")
    print("=" * 40)
    
    checks = [
        ("CLAUDE.md exists", lambda: (project_dir / "CLAUDE.md").exists()),
        ("Orchestration config", lambda: (claude_dir / "unified-orchestration-config.yaml").exists()),
        ("Todo system", lambda: (claude_dir / "orchestration_todos.json").exists()),
        ("Context templates", lambda: (claude_dir / "context-package-templates.yaml").exists()),
        ("Agent specifications", lambda: (claude_dir / "agents").is_dir()),
        ("Monitoring tools", lambda: (claude_dir / "monitoring").is_dir()),
        ("MCP configurations", lambda: (claude_dir / "mcp").is_dir()),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, check_func in checks:
        try:
            if check_func():
                print(f"✅ {check_name}")
                passed += 1
            else:
                print(f"❌ {check_name}")
                failed += 1
        except Exception as e:
            print(f"❌ {check_name} (error: {e})")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 UnifiedWorkflow setup is complete!")
        print("\nNext steps:")
        print("1. Start Claude Code in this project directory")
        print("2. Use any trigger phrase: 'start flow', 'orchestration', etc.")
        print("3. The system will automatically begin with Phase 0 todo integration")
        return True
    else:
        print("❌ Setup incomplete. Please run setup.sh again.")
        return False

if __name__ == "__main__":
    success = validate_setup()
    sys.exit(0 if success else 1)
EOF

chmod +x "$PROJECT_DIR/.claude/validate-setup.py"

echo ""
echo "✅ UnifiedWorkflow setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Review CLAUDE.md for complete workflow documentation"
echo "2. Run validation: python3 .claude/validate-setup.py"
echo "3. Start Claude Code in this project directory"
echo "4. Trigger orchestration with: 'start flow'"
echo ""
echo "📊 Monitoring:"
echo "- Execution logs: .claude/monitoring/"
echo "- Todo management: .claude/orchestration_todos.json"
echo "- Context packages: .claude/context-packages/"
echo ""
echo "🔧 Configuration:"
echo "- Workflow config: .claude/unified-orchestration-config.yaml"
echo "- Context templates: .claude/context-package-templates.yaml"
echo "- Agent specs: .claude/agents/"
echo ""
echo "Happy orchestrating! 🚀"