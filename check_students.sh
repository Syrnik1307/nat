ssh root@72.56.81.163 'cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python -c "
import os
import django
os.environ.setdefault(\"DJANGO_SETTINGS_MODULE\", \"teaching_panel.settings\")
django.setup()
from accounts.models import User
students = User.objects.filter(role=\"student\")[:5]
for s in students:
    print(f\"Student: {s.email}\")
"'
