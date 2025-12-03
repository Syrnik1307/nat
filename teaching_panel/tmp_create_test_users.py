from accounts.models import CustomUser

password = 'StrongPass123!'

def ensure(email, role, first_name, last_name):
    user, _ = CustomUser.objects.get_or_create(email=email)
    user.role = role
    user.first_name = first_name
    user.last_name = last_name
    user.is_active = True
    user.set_password(password)
    user.save()
    return user

teacher = ensure('deploy_teacher@test.local', 'teacher', 'Deploy', 'Teacher')
student = ensure('deploy_student@test.local', 'student', 'Deploy', 'Student')

print('teacher_id', teacher.id, 'student_id', student.id)
