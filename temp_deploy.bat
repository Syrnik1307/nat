@echo off
cd /d c:\Users\User\Desktop\nat\frontend
call npm run build
if errorlevel 1 (
    echo BUILD_FAILED
    exit /b 1
)
echo LOCAL_BUILD_OK
ssh tp "cd /var/www/teaching_panel && sudo git fetch origin main && sudo git reset --hard origin/main && echo GIT_SYNC_OK"
ssh tp "cd /var/www/teaching_panel/frontend && npm run build && echo SERVER_BUILD_OK"
ssh tp "sudo systemctl restart teaching_panel && echo RESTART_OK"
