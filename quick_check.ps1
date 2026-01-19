# Quick check of active lessons on production

$output = ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python -c 'from schedule.models import Lesson; al = Lesson.objects.filter(is_active=True); print(\"Active:\", al.count()); [print(l.id, l.group.name if l.group else \"NoGroup\", l.is_quick_lesson) for l in al]'"

Write-Host "Result:"
Write-Host $output
