#!/usr/bin/env python3
"""
This script collates the content of specified agent-related documentation
and configuration files into a single text file for context dumping.
"""
from datetime import datetime
from pathlib import Path

# Define the root of the project
PROJECT_ROOT = Path(__file__).parent.parent

# List of files to be included in the dump
# Core files are listed here. Agent-specific markdown files in docs/agents/
# will be discovered automatically.
CORE_SOURCE_FILES = [
    ".claude/agent_logger.py",
    "app/worker/services/helios_pm_orchestration_engine.py",
    "docs/MIGRATION_PLAN.md",
    "docs/legacy/CLAUDE.md",
    ".gemini/multi_agent_orchestration.md",
]

def discover_agent_files():
    """Dynamically discovers all agent markdown files in docs/agents."""
    agent_docs_path = PROJECT_ROOT / "docs" / "agents"
    if not agent_docs_path.is_dir():
        print(f"⚠️  Warning: Agent documentation directory not found at {agent_docs_path}")
        return []
    
    # Use glob to find all .md files, then convert to relative string paths
    return [str(p.relative_to(PROJECT_ROOT)) for p in agent_docs_path.glob("*.md")]

def create_agent_dump():
    """
    Reads the content of all source files and writes them into a single
    timestamped dump file in the 'contextdump' directory.
    """
    output_dir = PROJECT_ROOT / "contextdump"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%d%m%Y-%H%M%S")
    output_filename = f"agentdump{timestamp}.txt"
    output_filepath = output_dir / output_filename

    # Combine core files with discovered agent files
    agent_files = discover_agent_files()
    all_source_files = sorted(list(set(CORE_SOURCE_FILES + agent_files)))
    
    print(f"Found {len(agent_files)} agent documentation files to include.")

    with open(output_filepath, "w", encoding="utf-8") as outfile:
        for file_path_str in all_source_files:
            file_path = PROJECT_ROOT / file_path_str
            if file_path.exists():
                header = f"--- FILE: {file_path.as_posix()} ---\n"
                footer = f"\n--- END OF FILE: {file_path.as_posix()} ---\n\n"
                outfile.write(header)
                outfile.write(file_path.read_text(encoding="utf-8"))
                outfile.write(footer)
            else:
                print(f"⚠️  Warning: File not found and will be skipped: {file_path_str}")

    print(f"✅ Successfully created agent dump file at: {output_filepath.as_posix()}")
    print(f"   Included {len(all_source_files)} total files.")

if __name__ == "__main__":
    create_agent_dump()
