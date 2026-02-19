"""Patch schedule/views.py to add LessonMaterialViewSet"""
import re

views_path = '/var/www/teaching_panel/teaching_panel/schedule/views.py'

with open(views_path, 'r') as f:
    content = f.read()

# 1. Add LessonMaterial to models import
content = content.replace(
    'from .models import ZoomAccount, Group, Lesson, Attendance, RecurringLesson, LessonRecording, AuditLog',
    'from .models import ZoomAccount, Group, Lesson, Attendance, RecurringLesson, LessonRecording, AuditLog, LessonMaterial'
)

# 2. Add LessonMaterialSerializer to serializers import
content = content.replace(
    "    RecurringLessonSerializer\n)",
    "    RecurringLessonSerializer,\n    LessonMaterialSerializer\n)"
)

# 3. Add LessonMaterialViewSet class at the end of file
viewset_code = '''

class LessonMaterialViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """CRUD для учебных материалов к урокам."""
    serializer_class = LessonMaterialSerializer

    def get_queryset(self):
        qs = LessonMaterial.objects.all()
        lesson_id = self.request.query_params.get('lesson')
        material_type = self.request.query_params.get('type')
        if lesson_id:
            qs = qs.filter(lesson_id=lesson_id)
        if material_type:
            qs = qs.filter(material_type=material_type)
        return qs

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
'''

content = content.rstrip() + viewset_code

with open(views_path, 'w') as f:
    f.write(content)

print('OK: LessonMaterialViewSet added to schedule/views.py')
