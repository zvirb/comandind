#!/usr/bin/env python3
"""Test Docker connection methods"""
import os
import sys
import docker

print("Testing Docker connection...")
print(f"Python version: {sys.version}")
print(f"Docker library version: {docker.__version__}")
print(f"Environment DOCKER_HOST: {os.environ.get('DOCKER_HOST', 'NOT SET')}")

# Method 1: from_env()
try:
    print("\nMethod 1: docker.from_env()")
    client1 = docker.from_env()
    print("SUCCESS: Connected via from_env()")
    print(f"Docker version: {client1.version()}")
except Exception as e:
    print(f"FAILED: {e}")

# Method 2: Explicit unix socket
try:
    print("\nMethod 2: DockerClient with unix socket")
    client2 = docker.DockerClient(base_url='unix:///var/run/docker.sock')
    print("SUCCESS: Connected via unix socket")
    print(f"Docker version: {client2.version()}")
except Exception as e:
    print(f"FAILED: {e}")

# Method 3: APIClient
try:
    print("\nMethod 3: APIClient with unix socket")
    from docker import APIClient
    client3 = APIClient(base_url='unix:///var/run/docker.sock')
    print("SUCCESS: Connected via APIClient")
    print(f"Docker version: {client3.version()}")
except Exception as e:
    print(f"FAILED: {e}")

# Check Docker socket
print("\nDocker socket check:")
if os.path.exists('/var/run/docker.sock'):
    print("✓ Docker socket exists")
    import stat
    mode = os.stat('/var/run/docker.sock').st_mode
    print(f"  Socket mode: {oct(stat.S_IMODE(mode))}")
else:
    print("✗ Docker socket not found")