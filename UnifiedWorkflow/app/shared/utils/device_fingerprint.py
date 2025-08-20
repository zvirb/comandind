"""Device fingerprinting utilities for device recognition and security."""

import hashlib
import json
from typing import Dict, Any, Optional
from user_agents import parse
from fastapi import Request


class DeviceFingerprinter:
    """Handles device fingerprinting for device recognition."""
    
    @staticmethod
    def generate_fingerprint(request: Request, client_fingerprint: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a unique device fingerprint based on request headers and client data.
        
        Args:
            request: FastAPI request object
            client_fingerprint: Additional client-side fingerprint data
            
        Returns:
            Unique device fingerprint hash
        """
        # Server-side fingerprint components
        user_agent = request.headers.get('user-agent', '')
        accept_language = request.headers.get('accept-language', '')
        accept_encoding = request.headers.get('accept-encoding', '')
        accept = request.headers.get('accept', '')
        
        # Create base fingerprint from headers
        server_components = {
            'user_agent': user_agent,
            'accept_language': accept_language,
            'accept_encoding': accept_encoding,
            'accept': accept,
        }
        
        # Add client-side fingerprint if provided
        if client_fingerprint:
            server_components.update({
                'screen_resolution': client_fingerprint.get('screen_resolution', ''),
                'timezone': client_fingerprint.get('timezone', ''),
                'language': client_fingerprint.get('language', ''),
                'platform': client_fingerprint.get('platform', ''),
                'color_depth': client_fingerprint.get('color_depth', ''),
                'pixel_ratio': client_fingerprint.get('pixel_ratio', ''),
                'canvas_hash': client_fingerprint.get('canvas_hash', ''),
                'webgl_hash': client_fingerprint.get('webgl_hash', ''),
                'fonts_hash': client_fingerprint.get('fonts_hash', ''),
                'plugins': client_fingerprint.get('plugins', ''),
            })
        
        # Create deterministic hash
        fingerprint_string = json.dumps(server_components, sort_keys=True)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    @staticmethod
    def parse_user_agent(user_agent: str) -> Dict[str, Any]:
        """Parse user agent string to extract device information."""
        try:
            parsed_ua = parse(user_agent)
            return {
                'browser': parsed_ua.browser.family,
                'browser_version': parsed_ua.browser.version_string,
                'os': parsed_ua.os.family,
                'os_version': parsed_ua.os.version_string,
                'device': parsed_ua.device.family,
                'device_brand': parsed_ua.device.brand,
                'device_model': parsed_ua.device.model,
                'is_mobile': parsed_ua.is_mobile,
                'is_tablet': parsed_ua.is_tablet,
                'is_pc': parsed_ua.is_pc,
                'is_bot': parsed_ua.is_bot,
            }
        except Exception:
            return {
                'browser': 'Unknown',
                'browser_version': 'Unknown',
                'os': 'Unknown',
                'os_version': 'Unknown',
                'device': 'Unknown',
                'device_brand': 'Unknown',
                'device_model': 'Unknown',
                'is_mobile': False,
                'is_tablet': False,
                'is_pc': True,
                'is_bot': False,
            }
    
    @staticmethod
    def determine_device_type(user_agent_info: Dict[str, Any]) -> str:
        """Determine device type from user agent information."""
        if user_agent_info.get('is_mobile', False):
            return 'mobile'
        elif user_agent_info.get('is_tablet', False):
            return 'tablet'
        elif user_agent_info.get('is_pc', False):
            return 'desktop'
        else:
            return 'unknown'
    
    @staticmethod
    def generate_device_name(user_agent_info: Dict[str, Any], ip_address: Optional[str] = None) -> str:
        """Generate a user-friendly device name."""
        device_type = DeviceFingerprinter.determine_device_type(user_agent_info)
        browser = user_agent_info.get('browser', 'Unknown')
        os = user_agent_info.get('os', 'Unknown')
        
        # Create base name
        if device_type == 'mobile':
            device_name = f"📱 {os} Mobile"
        elif device_type == 'tablet':
            device_name = f"📱 {os} Tablet"
        elif device_type == 'desktop':
            device_name = f"💻 {os} Desktop"
        else:
            device_name = f"🖥️ {os} Device"
        
        # Add browser info
        if browser != 'Unknown':
            device_name += f" ({browser})"
        
        # Add location info if available (simplified)
        if ip_address and not ip_address.startswith('127.'):
            # In a real implementation, you'd use a GeoIP service
            device_name += f" - {ip_address[:8]}..."
        
        return device_name
    
    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Get client IP address from request, handling proxies."""
        # Check for forwarded headers (common in reverse proxy setups)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip.strip()
        
        # Fallback to client host
        return request.client.host if request.client else '127.0.0.1'


def create_device_fingerprint_js() -> str:
    """
    Generate JavaScript code for client-side device fingerprinting.
    This should be included in the frontend to collect browser-specific data.
    """
    return """
// Device Fingerprinting Client-Side Collection
function collectDeviceFingerprint() {
    const fingerprint = {};
    
    // Screen information
    fingerprint.screen_resolution = `${screen.width}x${screen.height}`;
    fingerprint.color_depth = screen.colorDepth;
    fingerprint.pixel_ratio = window.devicePixelRatio || 1;
    
    // Browser information
    fingerprint.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    fingerprint.language = navigator.language;
    fingerprint.platform = navigator.platform;
    
    // Canvas fingerprinting
    try {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillText('Device fingerprint canvas test 🔒', 2, 2);
        fingerprint.canvas_hash = canvas.toDataURL().slice(-50);
    } catch (e) {
        fingerprint.canvas_hash = 'unavailable';
    }
    
    // WebGL fingerprinting
    try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (gl) {
            const renderer = gl.getParameter(gl.RENDERER);
            const vendor = gl.getParameter(gl.VENDOR);
            fingerprint.webgl_hash = btoa(renderer + vendor).slice(-20);
        } else {
            fingerprint.webgl_hash = 'unavailable';
        }
    } catch (e) {
        fingerprint.webgl_hash = 'unavailable';
    }
    
    // Font detection (simplified)
    try {
        const testString = 'mmmmmmmmlli';
        const testSize = '48px';
        const baseFontSize = 'Arial';
        
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        ctx.font = testSize + ' ' + baseFontSize;
        const baseWidth = ctx.measureText(testString).width;
        
        const fontsToTest = ['Calibri', 'Helvetica', 'Times', 'Courier', 'Verdana'];
        const detectedFonts = [];
        
        fontsToTest.forEach(font => {
            ctx.font = testSize + ' ' + font + ', ' + baseFontSize;
            const width = ctx.measureText(testString).width;
            if (width !== baseWidth) {
                detectedFonts.push(font);
            }
        });
        
        fingerprint.fonts_hash = btoa(detectedFonts.join(',')).slice(-20);
    } catch (e) {
        fingerprint.fonts_hash = 'unavailable';
    }
    
    // Plugins (simplified)
    fingerprint.plugins = Array.from(navigator.plugins)
        .map(p => p.name)
        .sort()
        .join('|')
        .slice(0, 100);
    
    return fingerprint;
}

// Function to send fingerprint to server
function sendDeviceFingerprint() {
    const fingerprint = collectDeviceFingerprint();
    
    // Store in sessionStorage for use during authentication
    sessionStorage.setItem('deviceFingerprint', JSON.stringify(fingerprint));
    
    return fingerprint;
}

// Auto-collect on page load
document.addEventListener('DOMContentLoaded', sendDeviceFingerprint);
"""