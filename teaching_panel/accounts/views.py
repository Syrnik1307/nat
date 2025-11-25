from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse
from .models import CustomUser
from .forms import RegistrationForm, LoginForm
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
from .recaptcha_utils import verify_recaptcha, get_client_ip


@csrf_exempt
def register_user(request):
    """API-style регистрация пользователя согласно мастер-плану.

    POST JSON:
    {
        "email": "user@example.com",
        "password": "Password123",
        "first_name": "Иван",
        "last_name": "Иванов",
        "role": "student",  # или teacher
        "birth_date": "2000-01-01",  # optional
        "recaptcha_token": "..."  # reCAPTCHA v3 token
    }
    """
    if request.method != 'POST':
        return JsonResponse({'detail': 'Только POST'}, status=405)
    try:
        import json
        data = json.loads(request.body.decode('utf-8'))
        
        # Логирование для отладки
        print("🔍 DEBUG: Получены данные регистрации:")
        print(f"  - Email: {data.get('email')}")
        print(f"  - First name: {data.get('first_name')}")
        print(f"  - Last name: {data.get('last_name')}")
        print(f"  - Role: {data.get('role')}")
        print(f"  - reCAPTCHA token присутствует: {bool(data.get('recaptcha_token'))}")
        
    except Exception as e:
        print(f"❌ DEBUG: Ошибка парсинга JSON: {e}")
        return JsonResponse({'detail': 'Некорректный JSON'}, status=400)

    # reCAPTCHA отключена
    # recaptcha_token = data.get('recaptcha_token')
    # if recaptcha_token:
    #     client_ip = get_client_ip(request)
    #     recaptcha_result = verify_recaptcha(recaptcha_token, action='register', remote_ip=client_ip)
    #     if not recaptcha_result['success']:
    #         return JsonResponse({'detail': 'Защита от роботов'}, status=400)

    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'student')
    first_name = data.get('first_name', '')
    last_name = data.get('last_name', '')
    middle_name = data.get('middle_name', '')
    birth_date_raw = data.get('birth_date')

    if not email or not password:
        return JsonResponse({'detail': 'Email и пароль обязательны'}, status=400)
    if CustomUser.objects.filter(email__iexact=email).exists():
        return JsonResponse({'detail': 'Пользователь с таким email уже существует'}, status=400)

    # Парольная политика
    if len(password) < 6:
        return JsonResponse({'detail': 'Пароль должен содержать минимум 6 символов'}, status=400)
    if not any(c.isupper() for c in password):
        return JsonResponse({'detail': 'Пароль должен содержать хотя бы одну заглавную букву'}, status=400)
    if not any(c.islower() for c in password):
        return JsonResponse({'detail': 'Пароль должен содержать хотя бы одну строчную букву'}, status=400)
    if not any(c.isdigit() for c in password):
        return JsonResponse({'detail': 'Пароль должен содержать хотя бы одну цифру'}, status=400)

    try:
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            role=role,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name
        )
        if birth_date_raw:
            bd = parse_date(birth_date_raw)
            if bd:
                user.birth_date = bd
                user.save()
        
        print(f"✅ DEBUG: Пользователь успешно создан: {user.email} (ID: {user.id})")
        
        return JsonResponse({'detail': 'Регистрация успешна', 'user_id': user.id}, status=201)
    except Exception as e:
        print(f"❌ DEBUG: Ошибка создания пользователя: {e}")
        return JsonResponse({'detail': f'Ошибка создания пользователя: {e}'}, status=400)


def role_selection_view(request):
    """
    Первый шаг: выбор роли (Ученик или Преподаватель)
    Сохраняем выбор в сессии
    """
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ['student', 'teacher']:
            request.session['selected_role'] = role
            return redirect('accounts:login_register')
        else:
            messages.error(request, 'Пожалуйста, выберите роль')
    
    return render(request, 'accounts/role_selection.html')


def login_register_view(request):
    """
    Второй шаг: вход/регистрация
    Проверяем, существует ли пользователь:
    - Если да -> логиним
    - Если нет -> автоматически регистрируем и логиним
    """
    selected_role = request.session.get('selected_role')
    if not selected_role:
        messages.warning(request, 'Пожалуйста, сначала выберите роль')
        return redirect('accounts:role_selection')
    
    if request.method == 'POST':
        login_type = request.POST.get('login_type', 'email')  # email or phone
        password = request.POST.get('password')
        agreed_to_marketing = request.POST.get('agreed_to_marketing') == 'on'
        
        # Получаем идентификатор (email или телефон)
        if login_type == 'email':
            identifier = request.POST.get('email')
            lookup_field = 'email'
        else:
            identifier = request.POST.get('phone')
            lookup_field = 'phone_number'
        
        if not identifier or not password:
            messages.error(request, 'Заполните все обязательные поля')
            return render(request, 'accounts/login_register.html', {
                'selected_role': selected_role,
                'login_type': login_type
            })
        
        # Пытаемся найти пользователя (с нечувствительным к регистру поиском по email)
        try:
            if lookup_field == 'email':
                user = CustomUser.objects.get(email__iexact=identifier)
            else:
                user = CustomUser.objects.get(**{lookup_field: identifier})

            # Пользователь существует - проверяем пароль
            user = authenticate(request, username=user.email, password=password)
            if user:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.get_full_name() or user.email}!')
                
                # Очищаем сессию
                if 'selected_role' in request.session:
                    del request.session['selected_role']
                
                # Редирект в зависимости от роли
                if user.is_teacher():
                    return redirect('schedule:teacher_schedule')
                else:
                    return redirect('schedule:student_dashboard')
            else:
                messages.error(request, 'Неверный пароль')
        
        except CustomUser.DoesNotExist:
            # Пользователь не существует - регистрируем автоматически
            try:
                user_data = {
                    'password': password,
                    'role': selected_role,
                    'agreed_to_marketing': agreed_to_marketing,
                }
                
                if login_type == 'email':
                    user_data['email'] = identifier
                else:
                    user_data['phone_number'] = identifier
                    # Генерируем временный email
                    user_data['email'] = f"{identifier.replace('+', '').replace(' ', '')}@temp.phone"
                
                # Создаем пользователя
                user = CustomUser.objects.create_user(**user_data)
                
                # Автоматически логиним
                login(request, user)
                messages.success(request, f'Аккаунт создан! Добро пожаловать, {user.email}!')
            except Exception as e:
                messages.error(request, f'Ошибка при создании аккаунта: {str(e)}')
                return render(request, 'accounts/login_register.html', {
                    'selected_role': selected_role,
                    'login_type': login_type
                })
            
            # Очищаем сессию
            if 'selected_role' in request.session:
                del request.session['selected_role']
            
            # Редирект в зависимости от роли
            if user.is_teacher():
                return redirect('schedule:teacher_schedule')
            else:
                return redirect('schedule:student_dashboard')
    
    return render(request, 'accounts/login_register.html', {
        'selected_role': selected_role
    })


@login_required
def profile_view(request):
    """Просмотр и редактирование профиля"""
    user = request.user
    
    if request.method == 'POST':
        # Обновление профиля
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.middle_name = request.POST.get('middle_name', '')
        user.agreed_to_marketing = request.POST.get('agreed_to_marketing') == 'on'
        
        # Обновление телефона (если задан)
        phone = request.POST.get('phone_number')
        if phone:
            user.phone_number = phone

        avatar = request.POST.get('avatar')
        if avatar is not None:
            user.avatar = avatar
        
        user.save()
        messages.success(request, 'Профиль обновлен')
        return redirect('accounts:profile')
    
    return render(request, 'accounts/profile.html', {'user': user})


# API endpoints для OAuth/Social Auth (заглушки)
def oauth_vk_login(request):
    """Вход через VK (заглушка для будущей интеграции)"""
    messages.info(request, 'Вход через VK будет доступен в следующей версии')
    return redirect('accounts:login_register')


def oauth_yandex_login(request):
    """Вход через Yandex (заглушка)"""
    messages.info(request, 'Вход через Yandex будет доступен в следующей версии')
    return redirect('accounts:login_register')


def oauth_university_login(request):
    """Вход через 20.35 University (заглушка)"""
    messages.info(request, 'Вход через университет будет доступен в следующей версии')
    return redirect('accounts:login_register')
