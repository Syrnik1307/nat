# Deploy Teacher Heatmap files to production
$ErrorActionPreference = "Stop"

$prodPath = "/var/www/teaching_panel/teaching_panel/teaching_panel"

# Copy files using scp
Write-Host "Copying files to production..."

# Copy analytics files
scp c:\Users\User\Desktop\nat\teaching_panel\analytics\apps.py tp:$prodPath/analytics/
scp c:\Users\User\Desktop\nat\teaching_panel\analytics\signals.py tp:$prodPath/analytics/
scp c:\Users\User\Desktop\nat\teaching_panel\analytics\teacher_signals.py tp:$prodPath/analytics/
scp c:\Users\User\Desktop\nat\teaching_panel\analytics\views.py tp:$prodPath/analytics/
scp c:\Users\User\Desktop\nat\teaching_panel\analytics\urls.py tp:$prodPath/analytics/

# Copy accounts files
scp c:\Users\User\Desktop\nat\teaching_panel\accounts\models.py tp:$prodPath/accounts/

# Copy migrations
scp c:\Users\User\Desktop\nat\teaching_panel\accounts\migrations\0036_add_payment_admin_notified_at.py tp:$prodPath/accounts/migrations/
scp c:\Users\User\Desktop\nat\teaching_panel\accounts\migrations\0037_teacher_activity_heatmap.py tp:$prodPath/accounts/migrations/

Write-Host "Files copied. Running migrations..."

# Run migrations - using temp key since .env has special chars
ssh tp "cd $prodPath && SECRET_KEY=temp123 DEBUG=False ALLOWED_HOSTS=* /var/www/teaching_panel/venv/bin/python manage.py migrate accounts --noinput"

Write-Host "Restarting service..."
ssh tp "sudo systemctl restart teaching_panel.service"

Write-Host "Done! Checking status..."
ssh tp "sudo systemctl status teaching_panel.service | head -5"
