@echo off
echo ============================================================
echo    Teaching Panel Production Deployment Commands
echo ============================================================
echo.
echo STEP 1: Connect to server
echo    ssh nat@89.169.42.70
echo    Password: Syrnik13
echo.
echo STEP 2: Copy and paste this command:
echo.
echo cd /home/nat/teaching_panel ^&^& git pull origin main ^&^& source venv/bin/activate ^&^& pip install -r requirements.txt --quiet ^&^& python manage.py migrate ^&^& python manage.py collectstatic --noinput ^&^& sudo systemctl restart teaching_panel ^&^& sudo systemctl restart celery ^&^& sudo systemctl restart nginx ^&^& echo "✅ Deployment completed!" ^&^& sudo systemctl status teaching_panel --no-pager ^| head -10
echo.
echo ============================================================
echo.
pause
