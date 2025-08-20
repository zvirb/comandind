#!/usr/bin/env python3
"""
SSL Certificate Automation System for aiwfe.com
Provides comprehensive certificate monitoring, backup, and renewal automation
"""

import json
import os
import sys
import subprocess
import datetime
import logging
import shutil
import time
import smtplib
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography import x509
from cryptography.hazmat.backends import default_backend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/marku/ai_workflow_engine/logs/ssl_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SSLCertificateAutomation:
    """Main SSL certificate automation class"""
    
    def __init__(self, domain: str = "aiwfe.com"):
        self.domain = domain
        self.caddy_container = "ai_workflow_engine-caddy_reverse_proxy-1"
        self.cert_base_path = "/data/caddy/certificates"
        self.backup_dir = Path("/home/marku/ai_workflow_engine/ssl_backups")
        self.config_dir = Path("/home/marku/ai_workflow_engine/config")
        self.metrics_file = Path("/home/marku/ai_workflow_engine/metrics/ssl_metrics.json")
        
        # Create necessary directories
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Alert thresholds
        self.renewal_threshold_days = 30  # Renew when 30 days remaining
        self.critical_threshold_days = 7   # Critical alert when 7 days remaining
        
    def get_certificate_info(self) -> Optional[Dict]:
        """Get certificate information from Caddy container"""
        try:
            # Get certificate metadata
            cmd = f"docker exec {self.caddy_container} cat {self.cert_base_path}/acme-v02.api.letsencrypt.org-directory/{self.domain}/{self.domain}.json"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to get certificate metadata: {result.stderr}")
                return None
                
            metadata = json.loads(result.stdout)
            
            # Get certificate file for expiry check
            cert_cmd = f"docker exec {self.caddy_container} cat {self.cert_base_path}/acme-v02.api.letsencrypt.org-directory/{self.domain}/{self.domain}.crt"
            cert_result = subprocess.run(cert_cmd, shell=True, capture_output=True, text=True)
            
            if cert_result.returncode == 0:
                cert_data = cert_result.stdout.encode()
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                
                expiry_date = cert.not_valid_after_utc
                days_remaining = (expiry_date - datetime.datetime.now(datetime.timezone.utc)).days
                
                return {
                    "domain": self.domain,
                    "sans": metadata.get("sans", []),
                    "issuer": metadata.get("issuer_data", {}).get("ca"),
                    "expiry_date": expiry_date.isoformat(),
                    "days_remaining": days_remaining,
                    "renewal_window": metadata.get("issuer_data", {}).get("renewal_info", {}).get("suggestedWindow"),
                    "certificate_serial": cert.serial_number,
                    "subject": cert.subject.rfc4514_string(),
                    "issuer_name": cert.issuer.rfc4514_string()
                }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting certificate info: {e}")
            return None
    
    def check_certificate_expiry(self) -> Tuple[str, int]:
        """Check certificate expiry status"""
        cert_info = self.get_certificate_info()
        
        if not cert_info:
            return "ERROR", -1
            
        days_remaining = cert_info.get("days_remaining", -1)
        
        if days_remaining < 0:
            return "EXPIRED", days_remaining
        elif days_remaining <= self.critical_threshold_days:
            return "CRITICAL", days_remaining
        elif days_remaining <= self.renewal_threshold_days:
            return "RENEW_NEEDED", days_remaining
        else:
            return "HEALTHY", days_remaining
    
    def backup_certificates(self) -> bool:
        """Backup current certificates"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"cert_backup_{self.domain}_{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Copy certificate files from container
            cert_files = [
                f"{self.domain}.crt",
                f"{self.domain}.key",
                f"{self.domain}.json"
            ]
            
            for cert_file in cert_files:
                src_path = f"{self.cert_base_path}/acme-v02.api.letsencrypt.org-directory/{self.domain}/{cert_file}"
                dest_path = backup_path / cert_file
                
                cmd = f"docker exec {self.caddy_container} cat {src_path}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    dest_path.write_text(result.stdout)
                    logger.info(f"Backed up {cert_file} to {dest_path}")
                else:
                    logger.error(f"Failed to backup {cert_file}: {result.stderr}")
                    return False
            
            # Clean old backups (keep last 30 days)
            self._cleanup_old_backups()
            
            logger.info(f"Certificate backup completed: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    def _cleanup_old_backups(self, days_to_keep: int = 30):
        """Clean up old backup directories"""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
        
        for backup_dir in self.backup_dir.glob("cert_backup_*"):
            if backup_dir.is_dir():
                # Parse timestamp from directory name
                try:
                    timestamp_str = backup_dir.name.split("_")[-2] + "_" + backup_dir.name.split("_")[-1]
                    backup_date = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if backup_date < cutoff_date:
                        shutil.rmtree(backup_dir)
                        logger.info(f"Removed old backup: {backup_dir}")
                except Exception as e:
                    logger.warning(f"Could not parse backup date for {backup_dir}: {e}")
    
    def trigger_renewal(self) -> bool:
        """Trigger certificate renewal through Caddy"""
        try:
            # Force Caddy to reload and check for renewal
            cmd = f"docker exec {self.caddy_container} caddy reload --config /etc/caddy/Caddyfile"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to reload Caddy: {result.stderr}")
                return False
            
            logger.info("Caddy reloaded successfully - renewal check triggered")
            
            # Wait and verify renewal
            time.sleep(30)
            status, days = self.check_certificate_expiry()
            
            if status in ["HEALTHY", "RENEW_NEEDED"] and days > self.renewal_threshold_days:
                logger.info(f"Certificate renewed successfully. Days remaining: {days}")
                return True
            else:
                logger.warning(f"Certificate may not have renewed. Status: {status}, Days: {days}")
                return False
                
        except Exception as e:
            logger.error(f"Renewal trigger failed: {e}")
            return False
    
    def verify_ssl_endpoint(self) -> Dict:
        """Verify SSL endpoint is working correctly"""
        results = {
            "https_accessible": False,
            "certificate_valid": False,
            "redirect_working": False,
            "response_time_ms": None,
            "ssl_protocol": None
        }
        
        try:
            # Test HTTPS endpoint
            start_time = time.time()
            response = requests.get(f"https://{self.domain}", timeout=10, verify=True)
            response_time = (time.time() - start_time) * 1000
            
            results["https_accessible"] = response.status_code < 500
            results["certificate_valid"] = True  # If we got here, cert is valid
            results["response_time_ms"] = round(response_time, 2)
            
            # Test HTTP to HTTPS redirect
            redirect_response = requests.get(f"http://{self.domain}", timeout=10, allow_redirects=False)
            results["redirect_working"] = redirect_response.status_code in [301, 302, 308]
            
            logger.info(f"SSL endpoint verification results: {results}")
            
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL verification failed: {e}")
            results["certificate_valid"] = False
        except Exception as e:
            logger.error(f"Endpoint verification failed: {e}")
            
        return results
    
    def update_monitoring_metrics(self):
        """Update monitoring metrics for Prometheus/Grafana"""
        try:
            cert_info = self.get_certificate_info()
            endpoint_status = self.verify_ssl_endpoint()
            status, days_remaining = self.check_certificate_expiry()
            
            metrics = {
                "timestamp": datetime.datetime.now().isoformat(),
                "domain": self.domain,
                "certificate": {
                    "days_remaining": days_remaining,
                    "status": status,
                    "expiry_date": cert_info.get("expiry_date") if cert_info else None,
                    "issuer": cert_info.get("issuer_name") if cert_info else None
                },
                "endpoint": endpoint_status,
                "last_backup": self._get_last_backup_time(),
                "automation": {
                    "renewal_threshold_days": self.renewal_threshold_days,
                    "critical_threshold_days": self.critical_threshold_days,
                    "auto_renewal_enabled": True
                }
            }
            
            # Write metrics to file for Prometheus textfile collector
            self.metrics_file.write_text(json.dumps(metrics, indent=2))
            
            # Also write Prometheus format metrics
            prom_metrics_file = self.metrics_file.parent / "ssl_metrics.prom"
            prom_metrics = self._format_prometheus_metrics(metrics)
            prom_metrics_file.write_text(prom_metrics)
            
            logger.info("Monitoring metrics updated")
            
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
    
    def _format_prometheus_metrics(self, metrics: Dict) -> str:
        """Format metrics in Prometheus text format"""
        lines = []
        
        # Certificate metrics
        cert = metrics.get("certificate", {})
        lines.append(f'ssl_cert_days_remaining{{domain="{self.domain}"}} {cert.get("days_remaining", -1)}')
        lines.append(f'ssl_cert_status{{domain="{self.domain}",status="{cert.get("status", "UNKNOWN")}"}} 1')
        
        # Endpoint metrics
        endpoint = metrics.get("endpoint", {})
        lines.append(f'ssl_endpoint_https_accessible{{domain="{self.domain}"}} {1 if endpoint.get("https_accessible") else 0}')
        lines.append(f'ssl_endpoint_cert_valid{{domain="{self.domain}"}} {1 if endpoint.get("certificate_valid") else 0}')
        lines.append(f'ssl_endpoint_redirect_working{{domain="{self.domain}"}} {1 if endpoint.get("redirect_working") else 0}')
        
        if endpoint.get("response_time_ms"):
            lines.append(f'ssl_endpoint_response_time_ms{{domain="{self.domain}"}} {endpoint["response_time_ms"]}')
        
        return "\n".join(lines)
    
    def _get_last_backup_time(self) -> Optional[str]:
        """Get timestamp of last successful backup"""
        try:
            backups = list(self.backup_dir.glob("cert_backup_*"))
            if backups:
                latest = max(backups, key=lambda p: p.stat().st_mtime)
                return datetime.datetime.fromtimestamp(latest.stat().st_mtime).isoformat()
        except Exception:
            pass
        return None
    
    def send_alert(self, alert_type: str, message: str):
        """Send alert notification (implement based on your notification system)"""
        logger.warning(f"ALERT [{alert_type}]: {message}")
        
        # TODO: Implement actual alerting (email, Slack, PagerDuty, etc.)
        # For now, just log the alert
        
    def run_automation_cycle(self):
        """Run complete automation cycle"""
        logger.info("Starting SSL automation cycle")
        
        try:
            # 1. Check certificate status
            status, days_remaining = self.check_certificate_expiry()
            logger.info(f"Certificate status: {status}, Days remaining: {days_remaining}")
            
            # 2. Take action based on status
            if status == "EXPIRED":
                self.send_alert("CRITICAL", f"Certificate for {self.domain} has EXPIRED!")
                self.trigger_renewal()
                
            elif status == "CRITICAL":
                self.send_alert("CRITICAL", f"Certificate expires in {days_remaining} days!")
                self.trigger_renewal()
                
            elif status == "RENEW_NEEDED":
                self.send_alert("WARNING", f"Certificate renewal needed - {days_remaining} days remaining")
                if self.trigger_renewal():
                    self.send_alert("INFO", "Certificate renewed successfully")
                    
            elif status == "HEALTHY":
                logger.info(f"Certificate healthy - {days_remaining} days remaining")
            
            # 3. Backup certificates
            if status != "ERROR":
                if self.backup_certificates():
                    logger.info("Certificate backup completed")
                else:
                    self.send_alert("WARNING", "Certificate backup failed")
            
            # 4. Verify endpoints
            endpoint_status = self.verify_ssl_endpoint()
            if not endpoint_status.get("certificate_valid"):
                self.send_alert("CRITICAL", "SSL endpoint verification failed!")
            
            # 5. Update monitoring metrics
            self.update_monitoring_metrics()
            
            logger.info("SSL automation cycle completed")
            
        except Exception as e:
            logger.error(f"Automation cycle failed: {e}")
            self.send_alert("ERROR", f"SSL automation cycle failed: {e}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SSL Certificate Automation for aiwfe.com")
    parser.add_argument("--domain", default="aiwfe.com", help="Domain to manage")
    parser.add_argument("--check", action="store_true", help="Check certificate status only")
    parser.add_argument("--backup", action="store_true", help="Backup certificates only")
    parser.add_argument("--renew", action="store_true", help="Trigger renewal")
    parser.add_argument("--verify", action="store_true", help="Verify SSL endpoint")
    parser.add_argument("--monitor", action="store_true", help="Update monitoring metrics")
    parser.add_argument("--run", action="store_true", help="Run full automation cycle")
    
    args = parser.parse_args()
    
    automation = SSLCertificateAutomation(domain=args.domain)
    
    if args.check:
        status, days = automation.check_certificate_expiry()
        print(f"Status: {status}, Days remaining: {days}")
        cert_info = automation.get_certificate_info()
        if cert_info:
            print(json.dumps(cert_info, indent=2))
            
    elif args.backup:
        if automation.backup_certificates():
            print("Backup completed successfully")
        else:
            print("Backup failed")
            sys.exit(1)
            
    elif args.renew:
        if automation.trigger_renewal():
            print("Renewal triggered successfully")
        else:
            print("Renewal failed")
            sys.exit(1)
            
    elif args.verify:
        results = automation.verify_ssl_endpoint()
        print(json.dumps(results, indent=2))
        
    elif args.monitor:
        automation.update_monitoring_metrics()
        print("Monitoring metrics updated")
        
    elif args.run:
        automation.run_automation_cycle()
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()