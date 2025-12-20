import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser
t = CustomUser.objects.filter(role='teacher').first()
print('Teacher:', t.email)
print('zoom_pmi_link:', repr(t.zoom_pmi_link))
