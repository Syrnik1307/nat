import json
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from schedule.models import Group, Lesson


def _auth_client(email, password):
    client = APIClient()
    response = client.post('/api/jwt/token/', {
        'email': email,
        'password': password,
    }, format='json')
    if response.status_code != 200:
        raise RuntimeError(f'Login failed for {email}: {response.status_code} {response.content}')
    data = json.loads(response.content.decode())
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
    return client


def run():
    User = get_user_model()
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    teacher_email = f'autotest_teacher_{timestamp}@example.com'
    student_email = f'autotest_student_{timestamp}@example.com'
    student2_email = f'autotest_student_b_{timestamp}@example.com'
    password = 'StrongPass123'

    User.objects.filter(email__in=[teacher_email, student_email, student2_email]).delete()

    teacher = User.objects.create_user(
        email=teacher_email,
        password=password,
        role='teacher',
        first_name='Auto',
        last_name='Teacher'
    )
    student = User.objects.create_user(
        email=student_email,
        password=password,
        role='student',
        first_name='Auto',
        last_name='Student'
    )
    student2 = User.objects.create_user(
        email=student2_email,
        password=password,
        role='student',
        first_name='Auto',
        last_name='StudentB'
    )

    teacher_client = _auth_client(teacher_email, password)
    student_client = _auth_client(student_email, password)
    student2_client = _auth_client(student2_email, password)

    results = []

    def record(name, ok, detail=''):
        status = 'PASS' if ok else 'FAIL'
        results.append({'test': name, 'status': status, 'detail': detail})

    # 1.1 Создание группы
    resp = teacher_client.post('/api/groups/', {
        'name': 'English A1',
        'description': 'Evening group',
        'teacher_id': teacher.id,
    }, format='json')
    data = json.loads(resp.content.decode()) if resp.content else {}
    group_id = data.get('id')
    invite_code = data.get('invite_code')
    record('1.1 Create group', resp.status_code == 201 and bool(invite_code), f'status={resp.status_code}, invite_code={invite_code}')

    # 1.2 Редактирование группы
    resp = teacher_client.put(f'/api/groups/{group_id}/', {
        'name': 'English A1 - Evening',
        'description': 'Tue/Thu 18:00',
        'teacher_id': teacher.id,
    }, format='json')
    ok = resp.status_code == 200 and json.loads(resp.content.decode()).get('name') == 'English A1 - Evening'
    record('1.2 Update group', ok, f'status={resp.status_code}')

    # 1.3 Удаление группы
    resp_new = teacher_client.post('/api/groups/', {
        'name': 'Temp Deletion Group',
        'description': 'To delete',
        'teacher_id': teacher.id,
    }, format='json')
    delete_id = json.loads(resp_new.content.decode()).get('id')
    delete_resp = teacher_client.delete(f'/api/groups/{delete_id}/')
    record('1.3 Delete group', delete_resp.status_code == 204, f'status={delete_resp.status_code}')

    # 1.4 Пустое название
    resp = teacher_client.post('/api/groups/', {
        'name': '',
        'description': '',
        'teacher_id': teacher.id,
    }, format='json')
    record('1.4 Empty name validation', resp.status_code == 400, f'status={resp.status_code}')

    # 1.5 Дубликат названия
    resp_first = teacher_client.post('/api/groups/', {
        'name': 'Math 9A',
        'description': 'Morning',
        'teacher_id': teacher.id,
    }, format='json')
    resp_second = teacher_client.post('/api/groups/', {
        'name': 'Math 9A',
        'description': 'Evening',
        'teacher_id': teacher.id,
    }, format='json')
    record('1.5 Duplicate name allowed', resp_second.status_code == 201, f'status={resp_second.status_code}')

    # 2.5 Регенерация кода и проверка
    resp = teacher_client.post(f'/api/groups/{group_id}/regenerate_code/')
    regen_data = json.loads(resp.content.decode())
    new_code = regen_data.get('invite_code')
    old_code = invite_code
    record('2.5 Regenerate code', resp.status_code == 200 and new_code and new_code != old_code, f'old={old_code}, new={new_code}')

    invalid_join = student_client.post('/api/groups/join_by_code/', {'invite_code': old_code}, format='json')
    record('2.5 Old code invalidated', invalid_join.status_code == 404, f'status={invalid_join.status_code}')

    # 3.1 Успешное присоединение
    join_resp = student_client.post('/api/groups/join_by_code/', {'invite_code': new_code}, format='json')
    record('3.1 Join group success', join_resp.status_code == 200, f'status={join_resp.status_code}')

    # 3.2 Неверный код
    bad_code = student_client.post('/api/groups/join_by_code/', {'invite_code': 'WRONGCOD'}, format='json')
    record('3.2 Join invalid code', bad_code.status_code == 404, f'status={bad_code.status_code}')

    # 3.3 Пустой код
    empty_code = student_client.post('/api/groups/join_by_code/', {'invite_code': ''}, format='json')
    record('3.3 Join empty code', empty_code.status_code == 400, f'status={empty_code.status_code}')

    # 3.4 Повторное присоединение
    repeat_join = student_client.post('/api/groups/join_by_code/', {'invite_code': new_code}, format='json')
    repeat_data = json.loads(repeat_join.content.decode()) if repeat_join.content else {}
    repeat_message = repeat_data.get('message')
    repeat_ok = repeat_join.status_code == 200 and repeat_message == 'Вы уже состоите в этой группе'
    record('3.4 Join same group again', repeat_ok, f"status={repeat_join.status_code}, message={repeat_message}")

    # 3.6 Учитель пытается присоединиться
    teacher_join = teacher_client.post('/api/groups/join_by_code/', {'invite_code': new_code}, format='json')
    record('3.6 Teacher join forbidden', teacher_join.status_code == 403, f'status={teacher_join.status_code}')

    # 4.5 Добавление учеников по ID (устаревший метод)
    add_resp = teacher_client.post(f'/api/groups/{group_id}/add_students/', {
        'student_ids': [student.id, student2.id],
    }, format='json')
    add_data = json.loads(add_resp.content.decode()) if add_resp.content else {}
    record('4.5 Add students by id', add_resp.status_code == 200 and add_data.get('student_count') == 2, f'status={add_resp.status_code}')

    # 4.2/4.3 Удаление одного и нескольких учеников
    remove_resp = teacher_client.post(f'/api/groups/{group_id}/remove_students/', {
        'student_ids': [student.id],
    }, format='json')
    record('4.2 Remove single student', remove_resp.status_code == 200, f'status={remove_resp.status_code}')

    remove_multi = teacher_client.post(f'/api/groups/{group_id}/remove_students/', {
        'student_ids': [student.id, student2.id],
    }, format='json')
    record('4.3 Remove multiple students', remove_multi.status_code == 200, f'status={remove_multi.status_code}')

    # 4.4 Удаление несуществующего ID
    remove_fake = teacher_client.post(f'/api/groups/{group_id}/remove_students/', {
        'student_ids': [999999],
    }, format='json')
    record('4.4 Remove non-existent ID', remove_fake.status_code == 200, f'status={remove_fake.status_code}')

    # 5.1 Создание ученика через register endpoint
    new_student_resp = teacher_client.post('/api/jwt/register/', {
        'email': f'new_student_{timestamp}@example.com',
        'password': 'NewStudent123',
        'first_name': 'New',
        'last_name': 'Student',
        'role': 'student'
    }, format='json')
    record('5.1 Teacher creates student', new_student_resp.status_code == 201, f'status={new_student_resp.status_code}')

    # 6.1 Удаление группы с учениками
    group_with_students = teacher_client.post('/api/groups/', {
        'name': 'Cascade Group',
        'description': 'For cascade delete',
        'teacher_id': teacher.id,
    }, format='json')
    cascade_id = json.loads(group_with_students.content.decode()).get('id')
    group_obj = Group.objects.get(id=cascade_id)
    group_obj.students.add(student)
    teacher_client.delete(f'/api/groups/{cascade_id}/')
    still_exists = Group.objects.filter(id=cascade_id).exists()
    record('6.1 Delete group cascades students relation', not still_exists, f'group_exists_after_delete={still_exists}')

    # 6.2 Удаление группы с уроками (подтверждаем что урок удаляется без предупреждения)
    lesson_group_resp = teacher_client.post('/api/groups/', {
        'name': 'Lesson Group',
        'description': 'Has lesson',
        'teacher_id': teacher.id,
    }, format='json')
    lesson_group_id = json.loads(lesson_group_resp.content.decode()).get('id')
    lesson_group = Group.objects.get(id=lesson_group_id)
    lesson = Lesson.objects.create(
        title='Temp lesson',
        group=lesson_group,
        teacher=teacher,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=1)
    )
    teacher_client.delete(f'/api/groups/{lesson_group_id}/')
    lesson_exists = Lesson.objects.filter(id=lesson.id).exists()
    record('6.2 Delete group deletes lessons silently', not lesson_exists, f'lesson_exists_after_delete={lesson_exists}')

    print(json.dumps(results, indent=2, ensure_ascii=False))

    # Очистка
    Group.objects.filter(teacher=teacher).delete()
    Lesson.objects.filter(teacher=teacher).delete()
    teacher.delete()
    student.delete()
    student2.delete()


if __name__ == '__main__':
    run()
