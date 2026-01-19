from django.utils import timezone
from schedule.models import Lesson

now = timezone.now()
end = now + timezone.timedelta(days=30)

student_email = 'komlenok.vladimir@gmail.com'

qs = (
    Lesson.objects
    .filter(group__students__email=student_email)
    .filter(start_time__lte=end, end_time__gte=now)
    .order_by('start_time')
)

print('Student:', student_email)
print('Now:', now.isoformat())
print('End:', end.isoformat())
print('Lessons overlapping window:', qs.count())

for l in qs[:20]:
    print('ID=%s | group=%s | quick=%s | start=%s | end=%s | zoom=%s | meet=%s' % (
        l.id,
        l.group.name if l.group else 'NO_GROUP',
        l.is_quick_lesson,
        l.start_time,
        l.end_time,
        bool(l.zoom_join_url),
        bool(l.google_meet_link),
    ))
