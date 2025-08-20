# Agent Outputs Directory

**⚠️ IMPORTANT: This directory is for emergency file storage only.**

## Memory MCP First Policy

All agent outputs should be stored in **Memory MCP** using the structured entity naming convention:
```
{agent-name}-{output-type}-{YYYYMMDD-HHMMSS}
```

## Emergency File Storage

Only use this directory if Memory MCP is unavailable or for:
- Large binary files that cannot be stored in Memory MCP
- Temporary files during processing
- Legacy files being migrated to Memory MCP

## Organization

If files must be created here, organize by:
- agent-type/
- date/
- output-type/

## Migration

All files in this directory should be:
1. Migrated to Memory MCP when possible
2. Regularly cleaned up by project-janitor
3. Documented in memory for searchability