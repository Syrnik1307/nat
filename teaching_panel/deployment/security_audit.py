#!/usr/bin/env python3
"""
Security Audit Script for Teaching Panel
Checks production readiness and security configuration
"""

import os
import sys
from pathlib import Path

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_header(text):
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}{text:^60}{NC}")
    print(f"{BLUE}{'=' * 60}{NC}\n")

def print_check(passed, message):
    status = f"{GREEN}[✓]" if passed else f"{RED}[✗]"
    print(f"{status}{NC} {message}")

def print_warning(message):
    print(f"{YELLOW}[!]{NC} {message}")

def check_env_file():
    """Check if .env file exists and has required variables"""
    print_header("Environment Configuration")
    
    env_path = Path('.env')
    if not env_path.exists():
        print_check(False, ".env file not found")
        print_warning("Copy .env.example to .env and configure it")
        return False
    
    print_check(True, ".env file exists")
    
    # Check for required variables
    required_vars = [
        'SECRET_KEY',
        'DEBUG',
        'ALLOWED_HOSTS',
        'DATABASE_URL',
        'CELERY_BROKER_URL',
        'EMAIL_BACKEND',
        'DEFAULT_FROM_EMAIL',
    ]
    
    from dotenv import load_dotenv
    load_dotenv()
    
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value or value == '':
            missing_vars.append(var)
            print_check(False, f"{var} is not set")
        else:
            print_check(True, f"{var} is configured")
    
    return len(missing_vars) == 0

def check_secret_key():
    """Check if SECRET_KEY is secure"""
    print_header("Secret Key Security")
    
    secret_key = os.environ.get('SECRET_KEY', '')
    
    # Check if default key is used
    if 'django-insecure' in secret_key or 'your-secret-key' in secret_key or len(secret_key) < 50:
        print_check(False, "SECRET_KEY is not secure or is default")
        print_warning("Generate new key: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\"")
        return False
    
    print_check(True, "SECRET_KEY appears to be secure")
    return True

def check_debug_mode():
    """Check if DEBUG is disabled"""
    print_header("Debug Mode")
    
    debug = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')
    
    if debug:
        print_check(False, "DEBUG=True (DANGEROUS in production!)")
        print_warning("Set DEBUG=False in production .env")
        return False
    
    print_check(True, "DEBUG=False (production mode)")
    return True

def check_allowed_hosts():
    """Check ALLOWED_HOSTS configuration"""
    print_header("Allowed Hosts")
    
    allowed_hosts = os.environ.get('ALLOWED_HOSTS', '')
    
    if not allowed_hosts or allowed_hosts == 'localhost,127.0.0.1,testserver':
        print_check(False, "ALLOWED_HOSTS not configured for production")
        print_warning("Set ALLOWED_HOSTS to your domain: ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com")
        return False
    
    print_check(True, f"ALLOWED_HOSTS configured: {allowed_hosts}")
    return True

def check_database():
    """Check database configuration"""
    print_header("Database Configuration")
    
    database_url = os.environ.get('DATABASE_URL', '')
    
    if not database_url:
        print_warning("DATABASE_URL not set, using SQLite (not recommended for production)")
        print_warning("Use PostgreSQL: DATABASE_URL=postgresql://user:password@localhost:5432/teaching_panel")
        return False
    
    if 'postgresql' in database_url or 'mysql' in database_url:
        print_check(True, f"Production database configured")
        return True
    else:
        print_check(False, "SQLite database detected (not recommended for production)")
        return False

def check_ssl_security():
    """Check SSL/HTTPS security settings"""
    print_header("SSL/HTTPS Security")
    
    ssl_redirect = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() in ('true', '1', 'yes')
    session_cookie_secure = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')
    csrf_cookie_secure = os.environ.get('CSRF_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')
    hsts_seconds = int(os.environ.get('SECURE_HSTS_SECONDS', '0'))
    
    checks_passed = 0
    total_checks = 4
    
    if ssl_redirect:
        print_check(True, "SECURE_SSL_REDIRECT enabled")
        checks_passed += 1
    else:
        print_check(False, "SECURE_SSL_REDIRECT disabled")
        print_warning("Enable: SECURE_SSL_REDIRECT=True")
    
    if session_cookie_secure:
        print_check(True, "SESSION_COOKIE_SECURE enabled")
        checks_passed += 1
    else:
        print_check(False, "SESSION_COOKIE_SECURE disabled")
        print_warning("Enable: SESSION_COOKIE_SECURE=True")
    
    if csrf_cookie_secure:
        print_check(True, "CSRF_COOKIE_SECURE enabled")
        checks_passed += 1
    else:
        print_check(False, "CSRF_COOKIE_SECURE disabled")
        print_warning("Enable: CSRF_COOKIE_SECURE=True")
    
    if hsts_seconds >= 31536000:
        print_check(True, f"SECURE_HSTS_SECONDS set to {hsts_seconds}")
        checks_passed += 1
    else:
        print_check(False, f"SECURE_HSTS_SECONDS not set or too low ({hsts_seconds})")
        print_warning("Set: SECURE_HSTS_SECONDS=31536000")
    
    return checks_passed == total_checks

def check_email_config():
    """Check email configuration"""
    print_header("Email Configuration")
    
    email_backend = os.environ.get('EMAIL_BACKEND', '')
    email_host = os.environ.get('EMAIL_HOST', '')
    email_user = os.environ.get('EMAIL_HOST_USER', '')
    
    if 'console' in email_backend:
        print_check(False, "Email backend is console (development only)")
        print_warning("Configure SMTP: EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend")
        return False
    
    if email_backend == 'django.core.mail.backends.smtp.EmailBackend':
        print_check(True, "SMTP email backend configured")
        
        if email_host and email_user:
            print_check(True, f"Email host: {email_host}, User: {email_user}")
            return True
        else:
            print_check(False, "SMTP credentials incomplete")
            return False
    
    return False

def check_recaptcha():
    """Check reCAPTCHA configuration"""
    print_header("reCAPTCHA Configuration")
    
    recaptcha_enabled = os.environ.get('RECAPTCHA_ENABLED', 'false').lower() == 'true'
    public_key = os.environ.get('RECAPTCHA_PUBLIC_KEY', '')
    private_key = os.environ.get('RECAPTCHA_PRIVATE_KEY', '')
    
    # Check for test keys
    test_public_key = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'
    
    if not recaptcha_enabled:
        print_check(False, "reCAPTCHA is disabled")
        print_warning("Enable: RECAPTCHA_ENABLED=true")
        return False
    
    if public_key == test_public_key:
        print_check(False, "Using reCAPTCHA test keys")
        print_warning("Get production keys: https://www.google.com/recaptcha/admin")
        return False
    
    if public_key and private_key:
        print_check(True, "reCAPTCHA configured with production keys")
        return True
    
    print_check(False, "reCAPTCHA keys not configured")
    return False

def check_zoom_credentials():
    """Check Zoom API credentials"""
    print_header("Zoom API Configuration")
    
    zoom_account_id = os.environ.get('ZOOM_ACCOUNT_ID', '')
    zoom_client_id = os.environ.get('ZOOM_CLIENT_ID', '')
    zoom_client_secret = os.environ.get('ZOOM_CLIENT_SECRET', '')
    
    if zoom_account_id and zoom_client_id and zoom_client_secret:
        print_check(True, "Zoom API credentials configured")
        return True
    else:
        print_check(False, "Zoom API credentials incomplete")
        print_warning("Configure all: ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET")
        return False

def check_redis():
    """Check Redis connection"""
    print_header("Redis/Celery Configuration")
    
    celery_broker = os.environ.get('CELERY_BROKER_URL', '')
    
    if not celery_broker or 'memory' in celery_broker:
        print_check(False, "Redis not configured (using in-memory fallback)")
        print_warning("Install Redis and set: CELERY_BROKER_URL=redis://127.0.0.1:6379/0")
        return False
    
    # Try to connect to Redis
    try:
        import redis
        r = redis.from_url(celery_broker)
        r.ping()
        print_check(True, "Redis connection successful")
        return True
    except Exception as e:
        print_check(False, f"Redis connection failed: {e}")
        return False

def check_static_files():
    """Check static files configuration"""
    print_header("Static Files")
    
    staticfiles_dir = Path('staticfiles')
    
    if staticfiles_dir.exists() and any(staticfiles_dir.iterdir()):
        print_check(True, "Static files collected")
        return True
    else:
        print_check(False, "Static files not collected")
        print_warning("Run: python manage.py collectstatic")
        return False

def main():
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}Teaching Panel - Production Security Audit{NC}")
    print(f"{BLUE}{'=' * 60}{NC}")
    
    # Change to Django project directory
    os.chdir(Path(__file__).parent.parent)
    
    # Load Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
    
    # Run all checks
    checks = [
        ('Environment File', check_env_file),
        ('Secret Key', check_secret_key),
        ('Debug Mode', check_debug_mode),
        ('Allowed Hosts', check_allowed_hosts),
        ('Database', check_database),
        ('SSL/HTTPS', check_ssl_security),
        ('Email', check_email_config),
        ('reCAPTCHA', check_recaptcha),
        ('Zoom API', check_zoom_credentials),
        ('Redis', check_redis),
        ('Static Files', check_static_files),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            passed = check_func()
            results.append((name, passed))
        except Exception as e:
            print_check(False, f"Error checking {name}: {e}")
            results.append((name, False))
    
    # Summary
    print_header("Security Audit Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    percentage = (passed / total) * 100
    
    print(f"\nPassed: {passed}/{total} ({percentage:.1f}%)\n")
    
    if percentage == 100:
        print(f"{GREEN}✓ All security checks passed! Ready for production.{NC}\n")
        return 0
    elif percentage >= 80:
        print(f"{YELLOW}⚠ Most checks passed, but some improvements needed.{NC}\n")
        return 1
    else:
        print(f"{RED}✗ Multiple security issues found. NOT ready for production!{NC}\n")
        return 2

if __name__ == '__main__':
    sys.exit(main())
