from django.test import TestCase
from django.contrib.auth.models import User
from .models import Course, Lesson, Assignment, Submission

# Create your tests here.

class CourseModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher', password='test123')
        self.student = User.objects.create_user(username='student', password='test123')
    
    def test_create_course(self):
        course = Course.objects.create(
            title='Test Course',
            teacher=self.teacher
        )
        self.assertEqual(str(course), 'Test Course')
        self.assertEqual(course.teacher, self.teacher)
