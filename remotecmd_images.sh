#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
../venv/bin/python manage.py shell -c "
from homework.models import Homework, Question
# Найдём вопросы с картинками
qs = Question.objects.exclude(config__isnull=True).order_by('-id')[:10]
print('Questions with config:')
for q in qs:
    cfg = q.config
    if isinstance(cfg, dict) and cfg.get('imageUrl'):
        print(f'  Q#{q.id}: imageUrl={cfg.get(\"imageUrl\")}')
    elif isinstance(cfg, dict) and cfg.get('image_url'):
        print(f'  Q#{q.id}: image_url={cfg.get(\"image_url\")}')
    else:
        keys = list(cfg.keys()) if isinstance(cfg, dict) else type(cfg)
        print(f'  Q#{q.id}: config keys={keys}')
"
