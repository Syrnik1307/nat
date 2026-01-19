#!/usr/bin/env python3
"""
Healthcheck watchdog script for systemd integration.
This script runs as a separate service and restarts teaching_panel if unhealthy.
"""
import subprocess
import time
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

HEALTHCHECK_URL = "http://127.0.0.1:8000/api/health/"
CHECK_INTERVAL = 30  # seconds
FAILURE_THRESHOLD = 3  # restart after N consecutive failures
CURL_TIMEOUT = 10  # seconds


def check_health():
    """Returns True if service is healthy."""
    try:
        result = subprocess.run(
            ['curl', '-sf', '--max-time', str(CURL_TIMEOUT), HEALTHCHECK_URL],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return True, "OK"
        return False, f"HTTP error (exit code {result.returncode})"
    except Exception as e:
        return False, str(e)


def restart_service():
    """Restart teaching_panel service."""
    logger.warning("Restarting teaching_panel service...")
    try:
        subprocess.run(
            ['sudo', 'systemctl', 'restart', 'teaching_panel'],
            check=True
        )
        logger.info("Service restarted successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to restart service: {e}")
        return False


def main():
    logger.info(f"Healthcheck watchdog started. Checking {HEALTHCHECK_URL} every {CHECK_INTERVAL}s")
    failures = 0
    
    # Wait for initial startup
    time.sleep(10)
    
    while True:
        healthy, message = check_health()
        
        if healthy:
            if failures > 0:
                logger.info(f"Service recovered after {failures} failures")
            failures = 0
        else:
            failures += 1
            logger.warning(f"Health check failed ({failures}/{FAILURE_THRESHOLD}): {message}")
            
            if failures >= FAILURE_THRESHOLD:
                logger.error(f"Threshold reached, triggering restart...")
                if restart_service():
                    failures = 0
                    # Wait for service to start
                    time.sleep(15)
                else:
                    # Wait longer if restart failed
                    time.sleep(60)
        
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
