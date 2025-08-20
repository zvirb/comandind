
import logging
import os
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

def create_certificate_package(user_email: str, platform: str):
    """
    Creates a platform-specific certificate package for a user.
    Packages existing certificates from the private directory.
    """
    try:
        # Certificate source paths (from the project's private directory)
        private_dir = Path("/project/private")
        
        # Create temporary directory for packaging
        temp_dir = Path(tempfile.mkdtemp(prefix=f"{user_email.replace('@', '_')}_certs_"))
        
        if platform == "windows":
            # Copy .pfx file for Windows
            source_pfx = private_dir / "webui-client.pfx"
            if source_pfx.exists():
                dest_pfx = temp_dir / "ai-workflow-client.pfx"
                shutil.copy2(source_pfx, dest_pfx)
                
                # Create installation instructions
                instructions = temp_dir / "INSTALLATION_INSTRUCTIONS.txt"
                with open(instructions, "w") as f:
                    f.write("""AI Workflow Engine Client Certificate Installation (Windows)

1. Double-click on ai-workflow-client.pfx
2. Follow the Certificate Import Wizard
3. Install the certificate in your Personal certificate store
4. The certificate will be automatically used by the desktop client

Note: You may need to provide a password if prompted. Contact your administrator if needed.
""")
                
                # Create ZIP package with both files
                package_path = temp_dir / "ai-workflow-client-windows.zip"
                shutil.make_archive(str(package_path).replace('.zip', ''), 'zip', temp_dir)
                return str(package_path)
            else:
                logger.error(f"Source PFX file not found: {source_pfx}")
                raise FileNotFoundError("Certificate files not available")
                
        elif platform == "macos":
            # Copy .p12 file for macOS
            source_p12 = private_dir / "webui-client.p12"
            if source_p12.exists():
                dest_p12 = temp_dir / "ai-workflow-client.p12"
                shutil.copy2(source_p12, dest_p12)
                
                # Create installation instructions
                instructions = temp_dir / "INSTALLATION_INSTRUCTIONS.txt"
                with open(instructions, "w") as f:
                    f.write("""AI Workflow Engine Client Certificate Installation (macOS)

1. Double-click on ai-workflow-client.p12
2. Enter your macOS password when prompted
3. The certificate will be imported into your Keychain
4. The desktop client will automatically use this certificate

Note: You may need to provide a certificate password if prompted. Contact your administrator if needed.
""")
                
                # Create ZIP package
                package_path = temp_dir / "ai-workflow-client-macos.zip"
                shutil.make_archive(str(package_path).replace('.zip', ''), 'zip', temp_dir)
                return str(package_path)
            else:
                logger.error(f"Source P12 file not found: {source_p12}")
                raise FileNotFoundError("Certificate files not available")
                
        else:  # linux
            # Copy separate .crt and .key files for Linux
            source_crt = private_dir / "webui-client.crt"
            source_key = private_dir / "webui-client-key.pem"
            ca_cert = private_dir / "rootCA.pem"
            
            if source_crt.exists() and source_key.exists():
                dest_crt = temp_dir / "client.crt"
                dest_key = temp_dir / "client.key"
                dest_ca = temp_dir / "rootCA.pem"
                
                shutil.copy2(source_crt, dest_crt)
                shutil.copy2(source_key, dest_key)
                
                if ca_cert.exists():
                    shutil.copy2(ca_cert, dest_ca)
                
                # Create installation instructions
                instructions = temp_dir / "INSTALLATION_INSTRUCTIONS.txt"
                with open(instructions, "w") as f:
                    f.write("""AI Workflow Engine Client Certificate Installation (Linux)

Files included:
- client.crt: Client certificate
- client.key: Private key  
- rootCA.pem: Root CA certificate

Installation steps:
1. Copy these files to a secure location (e.g., ~/.ai-workflow-certs/)
2. Set appropriate permissions:
   chmod 600 client.key
   chmod 644 client.crt rootCA.pem
3. Configure your client application to use these certificates

For the desktop client:
- Place files in ~/.ai-workflow-certs/ directory
- The client will automatically detect and use them

Security note: Keep the client.key file secure and never share it.
""")
                
                # Create ZIP package
                package_path = temp_dir / "ai-workflow-client-linux.zip"
                shutil.make_archive(str(package_path).replace('.zip', ''), 'zip', temp_dir)
                return str(package_path)
            else:
                logger.error(f"Source certificate files not found: {source_crt}, {source_key}")
                raise FileNotFoundError("Certificate files not available")
        
    except Exception as e:
        logger.error(f"Error creating certificate package for {user_email}: {str(e)}")
        raise
