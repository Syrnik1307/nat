from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Course


class CourseModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            first_name='Test',
            last_name='Teacher',
            role='teacher',
        )

    def test_create_course(self):
        course = Course.objects.create(title='Test Course', teacher=self.teacher)
        self.assertEqual(str(course), 'Test Course')
        self.assertEqual(course.teacher, self.teacher)
