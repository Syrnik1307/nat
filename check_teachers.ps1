# Copy migration to correct location and run
ssh tp "cp /var/www/teaching_panel/teaching_panel/teaching_panel/schedule/migrations/0029_alter_lessonrecording_download_url_and_more.py /var/www/teaching_panel/teaching_panel/schedule/migrations/ && cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py migrate schedule" 2>&1 | Out-File -FilePath sync_result.txt -Encoding utf8
Get-Content sync_result.txt
