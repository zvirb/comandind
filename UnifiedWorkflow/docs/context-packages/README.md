# Context Packages Directory

**⚠️ IMPORTANT: This directory is for emergency file storage only.**

## Memory MCP First Policy

All context packages should be stored in **Memory MCP** using:
```
context-package-{domain}-{timestamp}
```

## Context Package Types

Store in Memory MCP with these entity types:
- `strategic-context-{phase}-{timestamp}`
- `technical-context-{domain}-{timestamp}`
- `synthesis-results-{phase}-{timestamp}`
- `validation-evidence-{type}-{timestamp}`

## Size Limits

- Context packages: Maximum 4000 tokens each
- Strategic packages: Maximum 3000 tokens
- Memory MCP entities: Maximum 8000 tokens per entity

## Emergency Storage

Only use this directory for:
- Context packages too large for Memory MCP
- Temporary processing files
- Backup during Memory MCP maintenance