ssh root@31.129.33.233 @"
echo '=== GUNICORN STATUS ==='
systemctl status gunicorn --no-pager
echo ''
echo '=== NGINX STATUS ==='
systemctl status nginx --no-pager
echo ''
echo '=== LAST 30 GUNICORN LOGS ==='
journalctl -u gunicorn -n 30 --no-pager
echo ''
echo '=== DISK USAGE ==='
df -h
echo ''
echo '=== MEMORY ==='
free -h
echo ''
echo '=== CPU LOAD ==='
uptime
"@
