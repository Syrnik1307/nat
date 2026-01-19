from django.utils import timezone
from schedule.models import Lesson

now = timezone.now()
start_dt = now
end_dt = now + timezone.timedelta(days=30)

# Симулируем логику пересечения окна (как в API после фикса)
qs = Lesson.objects.filter(
    start_time__lte=end_dt,
    end_time__gte=start_dt,
    group__students__isnull=False,
).distinct()

print('Now:', now.isoformat())
print('Window end:', end_dt.isoformat())
print('Count overlap lessons:', qs.count())

# Покажем быстрые уроки со ссылкой
quick = qs.filter(is_quick_lesson=True).exclude(zoom_join_url__isnull=True).exclude(zoom_join_url='')
print('Quick overlap with zoom:', quick.count())
for l in quick.order_by('-start_time')[:10]:
    print('ID=%s group=%s start=%s end=%s' % (l.id, l.group.name, l.start_time, l.end_time))
