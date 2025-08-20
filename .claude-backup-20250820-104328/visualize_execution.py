#!/usr/bin/env python3
"""
Execution Trace Visualizer
Shows the complete execution flow and detects recursion patterns
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class ExecutionVisualizer:
    """Visualize agent execution flows and detect patterns"""
    
    def __init__(self):
        self.logs_dir = Path(".claude/logs").resolve()
        self.execution_data = {}
        self.recursion_errors = []
        self.agent_interactions = defaultdict(list)
        
    def load_all_logs(self):
        """Load all log files and parse execution data"""
        print("📊 Loading execution logs...")
        
        # Load main execution log
        execution_log = self.logs_dir / "execution.log"
        if execution_log.exists():
            with open(execution_log, 'r') as f:
                self.execution_data['main'] = f.readlines()
        
        # Load agent-specific logs
        agents_dir = self.logs_dir / "agents"
        if agents_dir.exists():
            for log_file in agents_dir.glob("*.log"):
                agent_name = log_file.stem.split('-')[0]  # Extract agent name from filename
                
                with open(log_file, 'r') as f:
                    try:
                        # Parse JSON log entries
                        entries = []
                        for line in f:
                            if line.strip():
                                entries.append(json.loads(line))
                        self.execution_data[agent_name] = entries
                    except json.JSONDecodeError:
                        # Fallback to raw text
                        f.seek(0)
                        self.execution_data[agent_name] = f.readlines()
        
        # Load orchestration logs
        orchestration_log = self.logs_dir / "orchestration.log"
        if orchestration_log.exists():
            with open(orchestration_log, 'r') as f:
                try:
                    entries = []
                    for line in f:
                        if line.strip():
                            entries.append(json.loads(line))
                    self.execution_data['orchestration'] = entries
                except json.JSONDecodeError:
                    f.seek(0)
                    self.execution_data['orchestration'] = f.readlines()
        
        # Load recursion errors
        recursion_log = self.logs_dir / "RECURSION_ERRORS.log"
        if recursion_log.exists():
            with open(recursion_log, 'r') as f:
                self.recursion_errors = f.readlines()
    
    def analyze_execution_flow(self):
        """Analyze the execution flow and create visual representation"""
        print("\n🔍 Analyzing execution flow...\n")
        
        # Show orchestration phase
        if 'orchestration' in self.execution_data:
            print("📋 ORCHESTRATION PHASE:")
            for entry in self.execution_data['orchestration']:
                if isinstance(entry, dict):
                    timestamp = entry.get('timestamp', 'unknown')[:19]  # Truncate microseconds
                    agents = ', '.join(entry.get('agents_involved', []))
                    print(f"  [{timestamp}] Plan created involving: {agents}")
                    if 'plan' in entry:
                        plan_preview = entry['plan'][:100] + "..." if len(entry['plan']) > 100 else entry['plan']
                        print(f"     Plan: {plan_preview}")
        
        print("\n🤖 AGENT EXECUTION PHASE:")
        
        # Show agent activities
        for agent_name, entries in self.execution_data.items():
            if agent_name in ['main', 'orchestration']:
                continue
                
            if not entries:
                continue
                
            print(f"  └─ {agent_name}:")
            
            if isinstance(entries[0], dict):
                # JSON format logs
                for entry in entries[-5:]:  # Show last 5 actions
                    timestamp = entry.get('timestamp', 'unknown')[:19]
                    action = entry.get('action', 'unknown action')
                    tools = ', '.join(entry.get('tools_used', []))
                    success = "✅" if entry.get('success') else "❌"
                    
                    print(f"     [{timestamp}] {success} {action}")
                    if tools:
                        print(f"        Tools: {tools}")
            else:
                # Raw text format logs
                for line in entries[-5:]:  # Show last 5 lines
                    line = line.strip()
                    if line:
                        print(f"     {line}")
        
        # Show verification phase
        validation_log = self.logs_dir / "validation.log"
        if validation_log.exists():
            print(f"\n🔍 VERIFICATION PHASE:")
            try:
                with open(validation_log, 'r') as f:
                    for line in f:
                        if line.strip():
                            try:
                                entry = json.loads(line)
                                timestamp = entry.get('timestamp', 'unknown')[:19]
                                agent = entry.get('agent', 'unknown')
                                verification = entry.get('verification_type', 'unknown')
                                result = "✅" if entry.get('result') else "❌"
                                
                                print(f"  [{timestamp}] {result} {agent}: {verification}")
                                
                                if 'evidence' in entry and entry['evidence']:
                                    print(f"      Evidence: {entry['evidence']}")
                                    
                            except json.JSONDecodeError:
                                # Raw text fallback
                                print(f"  {line.strip()}")
                                
            except Exception as e:
                print(f"  Error reading validation log: {e}")
    
    def check_recursion_violations(self):
        """Check for and display recursion violations"""
        print(f"\n🛡️ RECURSION CHECK:")
        
        if self.recursion_errors:
            print("⚠️  RECURSION VIOLATIONS DETECTED:")
            for error in self.recursion_errors:
                if "RECURSION DETECTED" in error or "VIOLATION" in error:
                    print(f"  🚨 {error.strip()}")
        else:
            print("✅ No recursion detected - agent hierarchy properly enforced")
    
    def generate_execution_tree(self):
        """Generate a visual tree of execution flow"""
        print(f"\n🌳 EXECUTION TREE:")
        
        print("User Request")
        print("│")
        
        # Check if orchestrator was called
        if 'orchestration' in self.execution_data:
            print("├─ project-orchestrator (planning)")
            print("│   └─ Plan created")
            print("│")
            print("├─ Main Claude (execution)")
            
            # Show specialist agents called
            specialist_count = len([k for k in self.execution_data.keys() 
                                 if k not in ['main', 'orchestration']])
            
            if specialist_count > 0:
                for i, agent_name in enumerate(self.execution_data.keys()):
                    if agent_name in ['main', 'orchestration']:
                        continue
                    
                    connector = "├─" if i < specialist_count - 1 else "└─"
                    action_count = len(self.execution_data.get(agent_name, []))
                    
                    print(f"│   {connector} {agent_name} ({action_count} actions)")
        else:
            print("⚠️  No orchestrator logs found - may indicate direct agent calls")
        
        print("│")
        print("└─ Results returned to user")
    
    def show_performance_metrics(self):
        """Show performance and success metrics"""
        print(f"\n📈 PERFORMANCE METRICS:")
        
        total_actions = 0
        successful_actions = 0
        agents_used = 0
        
        for agent_name, entries in self.execution_data.items():
            if agent_name in ['main', 'orchestration']:
                continue
                
            if entries:
                agents_used += 1
                
                if isinstance(entries[0], dict):
                    for entry in entries:
                        total_actions += 1
                        if entry.get('success'):
                            successful_actions += 1
                else:
                    total_actions += len(entries)
        
        success_rate = (successful_actions / total_actions * 100) if total_actions > 0 else 0
        
        print(f"  Total Agents Used: {agents_used}")
        print(f"  Total Actions: {total_actions}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Recursion Errors: {len(self.recursion_errors)}")
        
        # Check for evidence files
        screenshot_dir = self.logs_dir / "screenshots"
        screenshots = len(list(screenshot_dir.glob("*.png"))) if screenshot_dir.exists() else 0
        print(f"  Screenshots Captured: {screenshots}")
    
    def generate_full_report(self):
        """Generate comprehensive execution report"""
        print("=" * 80)
        print("🔍 CLAUDE AGENT EXECUTION ANALYSIS")
        print("=" * 80)
        
        self.load_all_logs()
        self.analyze_execution_flow()
        self.generate_execution_tree()
        self.check_recursion_violations()
        self.show_performance_metrics()
        
        # Save report to file
        report_file = self.logs_dir / f"execution-analysis-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        
        # Redirect stdout to capture the report
        import io
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        
        # Re-run analysis to capture output
        self.analyze_execution_flow()
        self.generate_execution_tree()
        self.check_recursion_violations()
        self.show_performance_metrics()
        
        # Restore stdout and save report
        sys.stdout = old_stdout
        report_content = buffer.getvalue()
        
        with open(report_file, 'w') as f:
            f.write("CLAUDE AGENT EXECUTION ANALYSIS\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write(report_content)
        
        print(f"\n💾 Full report saved to: {report_file}")
        
        return report_file


def main():
    """Main execution"""
    if not Path(".claude/logs").resolve().exists():
        print("❌ No logs directory found. Run some agents first to generate logs.")
        return
    
    visualizer = ExecutionVisualizer()
    visualizer.generate_full_report()


if __name__ == "__main__":
    main()