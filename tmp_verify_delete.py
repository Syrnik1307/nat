from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIRequestFactory, force_authenticate
from schedule.models import Lesson
from schedule.views import LessonViewSet

User = get_user_model()
teacher = User.objects.filter(role='teacher').first()
if not teacher:
    raise SystemExit('Teacher not found')

group = teacher.teaching_groups.first()
if not group:
    raise SystemExit('Teacher has no group')

start = timezone.now() + timedelta(hours=1)
created = []
try:
    single = Lesson.objects.create(
        title='UI Auto Single',
        group=group,
        teacher=teacher,
        start_time=start,
        end_time=start + timedelta(hours=1),
    )
    created.append(single.pk)

    for offset in (1, 2):
        lesson = Lesson.objects.create(
            title='UI Auto Series',
            group=group,
            teacher=teacher,
            start_time=start + timedelta(days=offset),
            end_time=start + timedelta(days=offset, hours=1),
        )
        created.append(lesson.pk)

    factory = APIRequestFactory()

    destroy_request = factory.delete(f'/api/schedule/lessons/{single.pk}/')
    force_authenticate(destroy_request, user=teacher)
    destroy_response = LessonViewSet.as_view({'delete': 'destroy'})(destroy_request, pk=single.pk)

    action_request = factory.post(
        '/api/schedule/lessons/delete_recurring/',
        {'title': 'UI Auto Series', 'group_id': group.pk},
        format='json',
    )
    force_authenticate(action_request, user=teacher)
    action_response = LessonViewSet.as_view({'post': 'delete_recurring'})(action_request)

    print('single_status', destroy_response.status_code)
    print('series_status', action_response.status_code, action_response.data)
finally:
    # Clean up any leftovers if the API call failed
    Lesson.objects.filter(pk__in=created).delete()
