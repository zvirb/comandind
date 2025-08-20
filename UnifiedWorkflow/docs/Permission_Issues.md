# File Permission Issues Guide

This guide explains how to handle file permission issues that commonly occur with Docker operations.

## Common Issue

When running Docker containers, files can be created with root ownership, causing permission errors like:
```
chmod: changing permissions of '/home/user/ai_workflow_engine/scripts/auto_update.sh': Operation not permitted
```

## Why This Happens

1. **Docker Volume Mounts**: Files created by Docker containers are often owned by root
2. **Container Operations**: Scripts run inside containers may create files with root ownership
3. **Build Processes**: Docker builds can change file ownership

## Quick Fix

**Run the permission fix script:**
```bash
sudo ./scripts/fix_permissions.sh
```

This script will:
- Change ownership of all project files to your user
- Set correct permissions on scripts (755) and files (644)
- Secure the secrets directory (700/600)
- Fix any root-owned files

## Alternative Solutions

### 1. Manual Fix
```bash
# Change ownership of entire project
sudo chown -R $USER:$USER /path/to/ai_workflow_engine

# Make scripts executable
find /path/to/ai_workflow_engine -name "*.sh" -exec chmod +x {} \;

# Secure secrets
chmod 700 /path/to/ai_workflow_engine/secrets
chmod 600 /path/to/ai_workflow_engine/secrets/*
```

### 2. Docker Group Setup
Ensure your user is in the docker group:
```bash
sudo usermod -aG docker $USER
# Log out and log back in for changes to take effect
```

### 3. Use Docker with User Mapping
When running Docker commands, map your user ID:
```bash
docker run --user $(id -u):$(id -g) ...
```

## Prevention

### 1. Regular Permission Checks
The updated `run.sh` now checks for permission issues and warns you.

### 2. Proper Docker Configuration
The project is configured to minimize permission issues, but they can still occur.

### 3. Avoid Running as Root
Don't run the main scripts as root unless specifically needed for permission fixes.

## Troubleshooting

### Issue: "Operation not permitted" on scripts
**Solution:** Run `sudo ./scripts/fix_permissions.sh`

### Issue: Docker commands fail with permission errors
**Solution:** 
1. Check if you're in the docker group: `groups`
2. If not: `sudo usermod -aG docker $USER`
3. Log out and log back in

### Issue: Secrets directory has wrong permissions
**Solution:** 
```bash
sudo chmod 700 secrets/
sudo chmod 600 secrets/*
sudo chown -R $USER:$USER secrets/
```

### Issue: Files keep getting wrong permissions
**Solution:** 
1. Check Docker compose file for volume mounts
2. Consider using user mapping in Docker containers
3. Run permission fix script after major operations

## Safe Workflow

1. **After git pull:**
   ```bash
   # Check if permission fix is needed
   ls -la scripts/
   
   # If files are owned by root, fix permissions
   sudo ./scripts/fix_permissions.sh
   ```

2. **After Docker operations:**
   ```bash
   # Run permission fix if needed
   sudo ./scripts/fix_permissions.sh
   
   # Then run normal operations
   ./run.sh
   ```

3. **Regular maintenance:**
   ```bash
   # Check for permission issues
   ./run.sh --check-permissions  # (if you add this flag)
   
   # Or manually check
   ls -la scripts/ docker/ config/
   ```

## Security Considerations

- The `secrets/` directory should be accessible only to your user (700/600)
- Scripts should be executable (755) but not writable by others
- Configuration files should be readable (644) but not executable
- Never run the main application as root unless absolutely necessary

## Environment-Specific Notes

### Development Environment
- Permission issues are common due to frequent Docker operations
- Use the fix script regularly
- Consider setting up proper user mapping in Docker

### Production Environment
- Ensure consistent user ownership
- Use proper service accounts
- Consider using Docker user mapping or rootless Docker
- Implement proper file permission monitoring

## Automated Solutions

The project now includes:
- Automatic permission checking in `run.sh`
- Improved setup script that handles common permission issues
- Universal fix script that works on both local and server environments

## Getting Help

If permission issues persist:
1. Check the output of `ls -la` in the project directory
2. Verify your user is in the docker group: `groups`
3. Try running the fix script: `sudo ./scripts/fix_permissions.sh`
4. Check for any custom Docker configurations that might affect permissions

Remember: Permission issues are common with Docker-based projects and are usually easy to fix with the provided tools.