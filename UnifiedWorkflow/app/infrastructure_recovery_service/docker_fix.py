#!/usr/bin/env python3
"""Docker connection fix using low-level API"""
import os
import sys
import json
import socket
import http.client

def test_docker_socket():
    """Test Docker socket directly without Python library"""
    sock_path = '/var/run/docker.sock'
    
    if not os.path.exists(sock_path):
        print(f"Docker socket not found at {sock_path}")
        return False
    
    # Create a Unix socket connection
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(sock_path)
        
        # Build HTTP request
        request = b"GET /version HTTP/1.1\r\nHost: localhost\r\n\r\n"
        sock.send(request)
        
        # Read response
        response = b""
        while True:
            data = sock.recv(1024)
            if not data:
                break
            response += data
            if b"\r\n\r\n" in response and len(response.split(b"\r\n\r\n", 1)) > 1:
                headers, body = response.split(b"\r\n\r\n", 1)
                if b"Content-Length:" in headers:
                    content_length = int([h for h in headers.split(b"\r\n") if b"Content-Length:" in h][0].split(b": ")[1])
                    if len(body) >= content_length:
                        break
        
        # Parse response
        if b"200 OK" in response:
            body = response.split(b"\r\n\r\n")[1]
            version_info = json.loads(body.decode('utf-8'))
            print("✓ Docker socket is working!")
            print(f"  Docker version: {version_info.get('Version', 'unknown')}")
            return True
        else:
            print("✗ Docker socket responded but with error")
            print(response[:500].decode('utf-8', errors='ignore'))
            return False
            
    except Exception as e:
        print(f"✗ Failed to connect to Docker socket: {e}")
        return False
    finally:
        sock.close()

def get_docker_client_workaround():
    """Get a working Docker client using a workaround"""
    import docker
    from docker.transport import UnixHTTPAdapter
    import requests
    
    # Create a custom session with Unix socket adapter
    session = requests.Session()
    session.mount('http+docker://', UnixHTTPAdapter('unix:///var/run/docker.sock'))
    
    # Create Docker client with custom session
    client = docker.DockerClient(
        base_url='unix:///var/run/docker.sock',
        version='auto',
        timeout=60
    )
    
    return client

if __name__ == "__main__":
    print("Testing Docker socket directly...")
    socket_works = test_docker_socket()
    
    if socket_works:
        print("\nTrying workaround for Docker client...")
        try:
            client = get_docker_client_workaround()
            print("✓ Workaround successful!")
            print(f"  Containers running: {len(client.containers.list())}")
        except Exception as e:
            print(f"✗ Workaround failed: {e}")