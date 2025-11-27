# -*- coding: utf-8 -*-
"""
API endpoints для управления учебными материалами
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Q, F
import json

from .models import Lesson, LessonMaterial, MaterialView
from accounts.models import CustomUser


@csrf_exempt
@require_http_methods(["POST"])
def upload_material(request, lesson_id):
    """
    Загрузка учебного материала к уроку (теория или конспект)
    
    POST /schedule/api/lessons/<lesson_id>/materials/upload/
    Body: {
        "material_type": "theory" or "notes",
        "title": "Название материала",
        "description": "Описание (optional)",
        "file_url": "https://drive.google.com/...",
        "file_name": "document.pdf",
        "file_size_bytes": 1024000
    }
    """
    # Проверка авторизации
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)
    
    # Только преподаватель может загружать материалы
    if request.user.role != 'teacher':
        return JsonResponse({'error': 'Только преподаватели могут загружать материалы'}, status=403)
    
    try:
        # Получить урок
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return JsonResponse({'error': 'Урок не найден'}, status=404)
        
        # Проверить, что учитель владеет уроком
        if lesson.teacher_id != request.user.id:
            return JsonResponse({'error': 'Вы не можете загружать материалы к чужим урокам'}, status=403)
        
        # Парсинг данных
        data = json.loads(request.body)
        
        # Валидация обязательных полей
        required_fields = ['material_type', 'title', 'file_url']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'Отсутствует обязательное поле: {field}'}, status=400)
        
        # Валидация типа материала
        if data['material_type'] not in ['theory', 'notes']:
            return JsonResponse({'error': 'Тип материала должен быть theory или notes'}, status=400)
        
        # Создать материал
        material = LessonMaterial.objects.create(
            lesson=lesson,
            material_type=data['material_type'],
            title=data['title'],
            description=data.get('description', ''),
            file_url=data['file_url'],
            file_name=data.get('file_name', ''),
            file_size_bytes=data.get('file_size_bytes', 0),
            uploaded_by=request.user
        )
        
        # Сериализация ответа
        response_data = {
            'id': material.id,
            'lesson_id': material.lesson_id,
            'material_type': material.material_type,
            'title': material.title,
            'description': material.description,
            'file_url': material.file_url,
            'file_name': material.file_name,
            'file_size_bytes': material.file_size_bytes,
            'file_size_mb': round(material.file_size_mb, 2),
            'uploaded_by': {
                'id': material.uploaded_by.id,
                'name': material.uploaded_by.get_full_name(),
                'email': material.uploaded_by.email
            },
            'uploaded_at': material.uploaded_at.isoformat(),
            'views_count': material.views_count
        }
        
        return JsonResponse(response_data, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def list_materials(request, lesson_id):
    """
    Получить список всех материалов урока
    
    GET /schedule/api/lessons/<lesson_id>/materials/
    Query params:
        - material_type (optional): "theory" or "notes"
    """
    # Проверка авторизации
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)
    
    try:
        # Получить урок
        try:
            lesson = Lesson.objects.select_related('teacher').get(id=lesson_id)
        except Lesson.DoesNotExist:
            return JsonResponse({'error': 'Урок не найден'}, status=404)
        
        # Базовый запрос
        materials = LessonMaterial.objects.filter(lesson=lesson).select_related('uploaded_by')
        
        # Фильтрация по типу
        material_type = request.GET.get('material_type')
        if material_type and material_type in ['theory', 'notes']:
            materials = materials.filter(material_type=material_type)
        
        # Сортировка
        materials = materials.order_by('material_type', '-uploaded_at')
        
        # Для ученика - проверить просмотры
        is_student = request.user.role == 'student'
        viewed_material_ids = set()
        
        if is_student:
            viewed_material_ids = set(
                MaterialView.objects.filter(
                    student=request.user,
                    material__lesson=lesson
                ).values_list('material_id', flat=True)
            )
        
        # Сериализация
        materials_data = []
        for material in materials:
            material_dict = {
                'id': material.id,
                'lesson_id': material.lesson_id,
                'material_type': material.material_type,
                'material_type_display': material.get_material_type_display(),
                'title': material.title,
                'description': material.description,
                'file_url': material.file_url,
                'file_name': material.file_name,
                'file_size_bytes': material.file_size_bytes,
                'file_size_mb': round(material.file_size_mb, 2),
                'uploaded_by': {
                    'id': material.uploaded_by.id if material.uploaded_by else None,
                    'name': material.uploaded_by.get_full_name() if material.uploaded_by else 'Неизвестен',
                    'email': material.uploaded_by.email if material.uploaded_by else ''
                },
                'uploaded_at': material.uploaded_at.isoformat(),
                'views_count': material.views_count
            }
            
            # Для ученика добавить информацию о просмотре
            if is_student:
                material_dict['is_viewed'] = material.id in viewed_material_ids
            
            materials_data.append(material_dict)
        
        return JsonResponse({
            'lesson': {
                'id': lesson.id,
                'title': lesson.title,
                'teacher': {
                    'id': lesson.teacher.id,
                    'name': lesson.teacher.get_full_name()
                }
            },
            'materials': materials_data,
            'count': len(materials_data)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_material_detail(request, material_id):
    """
    Получить детальную информацию о материале
    
    GET /schedule/api/materials/<material_id>/
    """
    # Проверка авторизации
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)
    
    try:
        # Получить материал
        try:
            material = LessonMaterial.objects.select_related(
                'lesson', 'lesson__teacher', 'uploaded_by'
            ).get(id=material_id)
        except LessonMaterial.DoesNotExist:
            return JsonResponse({'error': 'Материал не найден'}, status=404)
        
        # Базовые данные
        material_dict = {
            'id': material.id,
            'lesson': {
                'id': material.lesson.id,
                'title': material.lesson.title,
                'start_time': material.lesson.start_time.isoformat(),
                'teacher': {
                    'id': material.lesson.teacher.id,
                    'name': material.lesson.teacher.get_full_name()
                }
            },
            'material_type': material.material_type,
            'material_type_display': material.get_material_type_display(),
            'title': material.title,
            'description': material.description,
            'file_url': material.file_url,
            'file_name': material.file_name,
            'file_size_bytes': material.file_size_bytes,
            'file_size_mb': round(material.file_size_mb, 2),
            'uploaded_by': {
                'id': material.uploaded_by.id if material.uploaded_by else None,
                'name': material.uploaded_by.get_full_name() if material.uploaded_by else 'Неизвестен'
            },
            'uploaded_at': material.uploaded_at.isoformat(),
            'views_count': material.views_count
        }
        
        # Для ученика - добавить информацию о просмотре
        if request.user.role == 'student':
            try:
                view = MaterialView.objects.get(material=material, student=request.user)
                material_dict['view_info'] = {
                    'viewed_at': view.viewed_at.isoformat(),
                    'duration_seconds': view.duration_seconds,
                    'completed': view.completed
                }
            except MaterialView.DoesNotExist:
                material_dict['view_info'] = None
        
        return JsonResponse(material_dict)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def track_material_view(request, material_id):
    """
    Отследить просмотр материала учеником
    
    POST /schedule/api/materials/<material_id>/view/
    Body: {
        "duration_seconds": 120 (optional),
        "completed": true (optional)
    }
    """
    # Проверка авторизации
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)
    
    # Только ученик может отмечать просмотры
    if request.user.role != 'student':
        return JsonResponse({'error': 'Только ученики могут отмечать просмотры'}, status=403)
    
    try:
        # Получить материал
        try:
            material = LessonMaterial.objects.get(id=material_id)
        except LessonMaterial.DoesNotExist:
            return JsonResponse({'error': 'Материал не найден'}, status=404)
        
        # Парсинг данных
        data = json.loads(request.body) if request.body else {}
        
        # Получить или создать запись о просмотре
        with transaction.atomic():
            view, created = MaterialView.objects.get_or_create(
                material=material,
                student=request.user,
                defaults={
                    'duration_seconds': data.get('duration_seconds', 0),
                    'completed': data.get('completed', False)
                }
            )
            
            # Если запись уже существует, обновить метрики
            if not created:
                if 'duration_seconds' in data:
                    view.duration_seconds = data['duration_seconds']
                if 'completed' in data:
                    view.completed = data['completed']
                view.save()
            
            # Увеличить счетчик просмотров материала (только при первом просмотре)
            if created:
                material.views_count = F('views_count') + 1
                material.save()
                material.refresh_from_db()
        
        return JsonResponse({
            'material_id': material.id,
            'student_id': request.user.id,
            'viewed_at': view.viewed_at.isoformat(),
            'duration_seconds': view.duration_seconds,
            'completed': view.completed,
            'is_first_view': created
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_material_views(request, material_id):
    """
    Получить статистику просмотров материала (для учителя)
    
    GET /schedule/api/materials/<material_id>/views/
    """
    # Проверка авторизации
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)
    
    # Только преподаватель может видеть статистику
    if request.user.role != 'teacher':
        return JsonResponse({'error': 'Только преподаватели могут видеть статистику просмотров'}, status=403)
    
    try:
        # Получить материал
        try:
            material = LessonMaterial.objects.select_related('lesson', 'lesson__teacher').get(id=material_id)
        except LessonMaterial.DoesNotExist:
            return JsonResponse({'error': 'Материал не найден'}, status=404)
        
        # Проверить, что учитель владеет уроком
        if material.lesson.teacher_id != request.user.id:
            return JsonResponse({'error': 'Вы не можете просматривать статистику чужих материалов'}, status=403)
        
        # Получить всех учеников урока (из группы или индивидуальные)
        lesson = material.lesson
        if lesson.group:
            students = lesson.group.students.all()
        elif lesson.student:
            students = [lesson.student]
        else:
            students = []
        
        # Получить просмотры
        views = MaterialView.objects.filter(material=material).select_related('student')
        views_dict = {view.student_id: view for view in views}
        
        # Сформировать список студентов с информацией о просмотрах
        students_data = []
        for student in students:
            view = views_dict.get(student.id)
            students_data.append({
                'student_id': student.id,
                'student_name': student.get_full_name(),
                'student_email': student.email,
                'has_viewed': view is not None,
                'viewed_at': view.viewed_at.isoformat() if view else None,
                'duration_seconds': view.duration_seconds if view else 0,
                'completed': view.completed if view else False
            })
        
        # Статистика
        total_students = len(students)
        viewed_count = len(views_dict)
        completion_count = sum(1 for view in views_dict.values() if view.completed)
        
        return JsonResponse({
            'material': {
                'id': material.id,
                'title': material.title,
                'material_type': material.material_type,
                'views_count': material.views_count
            },
            'statistics': {
                'total_students': total_students,
                'viewed_count': viewed_count,
                'not_viewed_count': total_students - viewed_count,
                'completion_count': completion_count,
                'view_rate': round((viewed_count / total_students * 100) if total_students > 0 else 0, 1),
                'completion_rate': round((completion_count / total_students * 100) if total_students > 0 else 0, 1)
            },
            'students': students_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_material(request, material_id):
    """
    Удалить материал (только владелец)
    
    DELETE /schedule/api/materials/<material_id>/
    """
    # Проверка авторизации
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)
    
    # Только преподаватель может удалять материалы
    if request.user.role != 'teacher':
        return JsonResponse({'error': 'Только преподаватели могут удалять материалы'}, status=403)
    
    try:
        # Получить материал
        try:
            material = LessonMaterial.objects.select_related('lesson').get(id=material_id)
        except LessonMaterial.DoesNotExist:
            return JsonResponse({'error': 'Материал не найден'}, status=404)
        
        # Проверить, что учитель владеет уроком
        if material.lesson.teacher_id != request.user.id:
            return JsonResponse({'error': 'Вы не можете удалять материалы к чужим урокам'}, status=403)
        
        # Удалить материал (автоматически удалятся и просмотры через CASCADE)
        material_title = material.title
        material.delete()
        
        return JsonResponse({
            'message': f'Материал "{material_title}" успешно удален',
            'deleted_id': material_id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_lesson_materials_statistics(request, lesson_id):
    """
    Получить общую статистику по всем материалам урока (для учителя)
    
    GET /schedule/api/lessons/<lesson_id>/materials/statistics/
    """
    # Проверка авторизации
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)
    
    # Только преподаватель может видеть статистику
    if request.user.role != 'teacher':
        return JsonResponse({'error': 'Только преподаватели могут видеть статистику'}, status=403)
    
    try:
        # Получить урок
        try:
            lesson = Lesson.objects.select_related('teacher', 'group').get(id=lesson_id)
        except Lesson.DoesNotExist:
            return JsonResponse({'error': 'Урок не найден'}, status=404)
        
        # Проверить, что учитель владеет уроком
        if lesson.teacher_id != request.user.id:
            return JsonResponse({'error': 'Вы не можете просматривать статистику чужих уроков'}, status=403)
        
        # Получить всех учеников урока
        if lesson.group:
            students = list(lesson.group.students.all())
        elif lesson.student:
            students = [lesson.student]
        else:
            students = []
        
        # Получить все материалы урока
        materials = LessonMaterial.objects.filter(lesson=lesson).prefetch_related('views')
        
        # Статистика по типам материалов
        theory_materials = materials.filter(material_type='theory')
        notes_materials = materials.filter(material_type='notes')
        
        # Получить все просмотры для этого урока
        all_views = MaterialView.objects.filter(
            material__lesson=lesson
        ).select_related('student', 'material')
        
        # Сформировать матрицу просмотров: студент × материал
        students_data = []
        for student in students:
            student_views = [v for v in all_views if v.student_id == student.id]
            
            theory_views = [v for v in student_views if v.material.material_type == 'theory']
            notes_views = [v for v in student_views if v.material.material_type == 'notes']
            
            students_data.append({
                'student_id': student.id,
                'student_name': student.get_full_name(),
                'student_email': student.email,
                'theory_viewed': len(theory_views),
                'theory_total': theory_materials.count(),
                'theory_completed': sum(1 for v in theory_views if v.completed),
                'notes_viewed': len(notes_views),
                'notes_total': notes_materials.count(),
                'notes_completed': sum(1 for v in notes_views if v.completed),
                'total_views': len(student_views)
            })
        
        # Общая статистика
        total_students = len(students)
        total_materials = materials.count()
        total_views = all_views.count()
        
        return JsonResponse({
            'lesson': {
                'id': lesson.id,
                'title': lesson.title,
                'start_time': lesson.start_time.isoformat() if lesson.start_time else None
            },
            'summary': {
                'total_students': total_students,
                'total_materials': total_materials,
                'theory_materials_count': theory_materials.count(),
                'notes_materials_count': notes_materials.count(),
                'total_views': total_views,
                'avg_views_per_material': round(total_views / total_materials, 1) if total_materials > 0 else 0
            },
            'students': students_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
