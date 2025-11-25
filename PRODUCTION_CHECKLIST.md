# Teaching Panel - Production Checklist

## 🔐 Security Checklist

### Critical Settings
- [ ] `DEBUG=False` in `.env`
- [ ] Strong `SECRET_KEY` generated (not default)
- [ ] `ALLOWED_HOSTS` set to your domain
- [ ] SSL certificate installed (HTTPS enabled)
- [ ] `SECURE_SSL_REDIRECT=True`
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `CSRF_COOKIE_SECURE=True`
- [ ] `SECURE_HSTS_SECONDS=31536000`

### Database
- [ ] PostgreSQL configured (not SQLite)
- [ ] Strong database password
- [ ] Database backups configured
- [ ] Migrations applied: `python manage.py migrate`

### Authentication & API Keys
- [ ] reCAPTCHA production keys configured
- [ ] `RECAPTCHA_ENABLED=true`
- [ ] Zoom API credentials configured
- [ ] Email SMTP configured (not console backend)
- [ ] Email credentials set

### Services
- [ ] Redis installed and running
- [ ] Celery worker running
- [ ] Celery beat scheduler running
- [ ] Nginx configured and running
- [ ] Systemd services enabled

### Static Files & Media
- [ ] Static files collected: `python manage.py collectstatic`
- [ ] Media directory permissions set
- [ ] WhiteNoise configured for static files

### Monitoring & Backups
- [ ] Log rotation configured
- [ ] Database backups automated
- [ ] Monitoring/alerting set up (optional)
- [ ] Sentry configured (optional)

---

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] Code reviewed and tested locally
- [ ] All tests passing
- [ ] `.env.example` updated with all variables
- [ ] Documentation updated
- [ ] Dependencies up to date

### Server Setup
- [ ] Server provisioned (2GB+ RAM, 2+ CPU cores)
- [ ] Domain DNS configured
- [ ] SSH access configured
- [ ] Firewall configured (UFW/iptables)
- [ ] Non-root user created

### Deployment
- [ ] Code uploaded to server
- [ ] Virtual environment created
- [ ] Dependencies installed: `pip install -r requirements-production.txt`
- [ ] `.env` file created and configured
- [ ] Database created and migrated
- [ ] Superuser created
- [ ] Static files collected
- [ ] Frontend built: `npm run build`

### Service Configuration
- [ ] Gunicorn service configured
- [ ] Celery worker service configured
- [ ] Celery beat service configured
- [ ] Nginx configured
- [ ] SSL certificate obtained (Let's Encrypt)
- [ ] All services started and enabled

### Testing
- [ ] Application accessible via HTTPS
- [ ] Admin panel accessible
- [ ] API endpoints working
- [ ] User registration working
- [ ] Email sending working
- [ ] Zoom integration working
- [ ] Celery tasks executing
- [ ] Static files loading
- [ ] No console errors in browser

---

## 🛠️ Quick Commands

### Run Security Audit
```bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python deployment/security_audit.py
```

### Check Service Status
```bash
sudo systemctl status teaching_panel
sudo systemctl status celery
sudo systemctl status celery-beat
sudo systemctl status nginx
sudo systemctl status redis
```

### View Logs
```bash
# Application logs
sudo tail -f /var/log/teaching_panel/gunicorn.log
sudo journalctl -u teaching_panel -f

# Nginx logs
sudo tail -f /var/log/nginx/teaching_panel_access.log
sudo tail -f /var/log/nginx/teaching_panel_error.log
```

### Restart Services
```bash
sudo systemctl restart teaching_panel
sudo systemctl restart celery
sudo systemctl restart celery-beat
sudo systemctl restart nginx
```

### Database Backup
```bash
# Manual backup
sudo -u postgres pg_dump teaching_panel > backup_$(date +%Y%m%d_%H%M%S).sql

# Using management script
cd /var/www/teaching_panel/teaching_panel
bash deployment/manage_database.sh
```

### Update Deployment
```bash
cd /var/www/teaching_panel
git pull origin main
source venv/bin/activate
cd teaching_panel
pip install -r requirements-production.txt
python manage.py migrate
python manage.py collectstatic --noinput
cd ../frontend
npm install
npm run build
sudo systemctl restart teaching_panel celery celery-beat
```

---

## 📊 Post-Deployment Monitoring

### Daily
- [ ] Check error logs
- [ ] Monitor disk space
- [ ] Verify backups running

### Weekly
- [ ] Review application performance
- [ ] Check for security updates
- [ ] Review user feedback

### Monthly
- [ ] Update dependencies
- [ ] Review and rotate logs
- [ ] Performance optimization
- [ ] Security audit

---

## 🚨 Emergency Procedures

### Application Down
1. Check service status: `sudo systemctl status teaching_panel`
2. Check logs: `sudo journalctl -u teaching_panel -n 100`
3. Restart service: `sudo systemctl restart teaching_panel`
4. If persistent, check .env file and database connection

### Database Issues
1. Check PostgreSQL: `sudo systemctl status postgresql`
2. Verify connection: `psql -U teaching_panel_user -d teaching_panel -h localhost`
3. Restore backup if needed: see `manage_database.sh`

### High Load
1. Check processes: `htop`
2. Check Nginx connections: `sudo netstat -anp | grep :80`
3. Scale workers if needed (modify systemd service file)
4. Consider caching layer (Redis cache)

### Rollback
```bash
cd /var/www/teaching_panel
git log --oneline -n 10  # Find commit to rollback to
git reset --hard <commit-hash>
source venv/bin/activate
cd teaching_panel
python manage.py migrate
python manage.py collectstatic --noinput
cd ../frontend
npm run build
sudo systemctl restart teaching_panel celery celery-beat
```

---

## 📞 Support Contacts

- Documentation: `/DEPLOYMENT_GUIDE.md`
- Security Audit: `deployment/security_audit.py`
- Database Management: `deployment/manage_database.sh`
- Logs: `/var/log/teaching_panel/`
