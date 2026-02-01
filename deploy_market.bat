@echo off
echo === Removing untracked market files ===
ssh tp "cd /var/www/teaching_panel/teaching_panel && rm -rf teaching_panel/market/"
echo === Git pull ===
ssh tp "cd /var/www/teaching_panel/teaching_panel && git pull"
echo === Migrate market ===
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py migrate market --noinput"
echo === Restart service ===
ssh tp "sudo systemctl restart teaching_panel"
echo === Test endpoint ===
ssh tp "sleep 2 && curl -s http://127.0.0.1:8000/api/market/products/"
