"""
Miro OAuth Integration.

Позволяет преподавателям авторизоваться в Miro через OAuth 2.0
и получать доступ к своим доскам.
"""

import os
import logging
import requests
from urllib.parse import urlencode

from django.conf import settings as django_settings
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MiroUserToken, LessonMaterial, Group

logger = logging.getLogger(__name__)


def get_miro_config():
    """Получить конфигурацию Miro OAuth из настроек."""
    return {
        'client_id': getattr(django_settings, 'MIRO_CLIENT_ID', None) or os.environ.get('MIRO_CLIENT_ID'),
        'client_secret': getattr(django_settings, 'MIRO_CLIENT_SECRET', None) or os.environ.get('MIRO_CLIENT_SECRET'),
        'redirect_uri': getattr(django_settings, 'MIRO_REDIRECT_URI', None) or os.environ.get('MIRO_REDIRECT_URI'),
    }


def is_miro_oauth_configured():
    """Проверить, настроен ли Miro OAuth."""
    config = get_miro_config()
    return bool(config['client_id'] and config['client_secret'])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def miro_auth_status(request):
    """
    Проверить статус интеграции Miro для текущего пользователя.
    
    Returns:
        - oauth_configured: настроен ли OAuth на сервере
        - user_connected: подключил ли пользователь свой Miro
        - user_info: информация о пользователе Miro (если подключен)
        - auth_url: URL для авторизации (если не подключен)
    """
    if request.user.role != 'teacher':
        return Response(
            {'error': 'Только для учителей'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    config = get_miro_config()
    oauth_configured = is_miro_oauth_configured()
    
    # Проверяем, есть ли у пользователя токен
    try:
        token = MiroUserToken.objects.get(user=request.user)
        user_connected = True
        is_expired = token.is_expired
        
        user_info = {
            'miro_user_id': token.miro_user_id,
            'miro_team_id': token.miro_team_id,
            'connected_at': token.created_at.isoformat(),
            'is_expired': is_expired,
            'needs_refresh': token.needs_refresh(),
        }
    except MiroUserToken.DoesNotExist:
        user_connected = False
        user_info = None
        is_expired = False
    
    # Формируем URL для авторизации
    auth_url = None
    if oauth_configured and not user_connected:
        auth_url = build_oauth_url(request)
    
    return Response({
        'oauth_configured': oauth_configured,
        'user_connected': user_connected,
        'is_expired': is_expired,
        'user_info': user_info,
        'auth_url': auth_url,
        'instructions': {
            'to_connect': 'Перейдите по auth_url для подключения Miro',
            'after_connect': 'После авторизации вы сможете создавать и управлять досками Miro',
        }
    })


def build_oauth_url(request):
    """Построить URL для OAuth авторизации Miro."""
    config = get_miro_config()
    
    if not config['client_id']:
        return None
    
    # Определяем redirect_uri
    redirect_uri = config['redirect_uri']
    if not redirect_uri:
        # Автоматически формируем из текущего запроса
        scheme = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        redirect_uri = f"{scheme}://{host}/schedule/api/miro/oauth/callback/"
    
    params = {
        'response_type': 'code',
        'client_id': config['client_id'],
        'redirect_uri': redirect_uri,
        'state': str(request.user.id),  # Передаём user_id для callback
    }
    
    return f"https://miro.com/oauth/authorize?{urlencode(params)}"


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def miro_oauth_start(request):
    """
    Начать OAuth авторизацию с Miro.
    Перенаправляет пользователя на страницу авторизации Miro.
    """
    if request.user.role != 'teacher':
        return Response(
            {'error': 'Только для учителей'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not is_miro_oauth_configured():
        return Response({
            'error': 'Miro OAuth не настроен на сервере',
            'setup_instructions': {
                'step1': 'Создайте приложение на https://miro.com/app/settings/user-profile/apps',
                'step2': 'Настройте Redirect URI: https://your-domain.com/schedule/api/miro/oauth/callback/',
                'step3': 'Добавьте MIRO_CLIENT_ID и MIRO_CLIENT_SECRET в переменные окружения',
            }
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
    
    auth_url = build_oauth_url(request)
    
    # Для API возвращаем URL, клиент сам перенаправит
    return Response({
        'auth_url': auth_url,
        'message': 'Перейдите по ссылке для авторизации в Miro'
    })


@api_view(['GET'])
def miro_oauth_callback(request):
    """
    Callback для Miro OAuth.
    Получает код авторизации и обменивает на токен.
    """
    code = request.GET.get('code')
    state = request.GET.get('state')  # user_id
    error = request.GET.get('error')
    
    # Определяем frontend URL для редиректа
    frontend_url = getattr(django_settings, 'FRONTEND_URL', None) or os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    
    if error:
        logger.error(f"Miro OAuth error: {error}")
        return redirect(f"{frontend_url}/teacher/materials?miro_error={error}")
    
    if not code:
        return redirect(f"{frontend_url}/teacher/materials?miro_error=no_code")
    
    if not state:
        return redirect(f"{frontend_url}/teacher/materials?miro_error=no_state")
    
    config = get_miro_config()
    
    # Определяем redirect_uri (должен совпадать с тем, что был при авторизации)
    redirect_uri = config['redirect_uri']
    if not redirect_uri:
        scheme = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        redirect_uri = f"{scheme}://{host}/schedule/api/miro/oauth/callback/"
    
    # Обмениваем код на токен
    try:
        token_response = requests.post(
            'https://api.miro.com/v1/oauth/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'code': code,
                'redirect_uri': redirect_uri,
            },
            timeout=30
        )
        
        if token_response.status_code != 200:
            logger.error(f"Miro token exchange failed: {token_response.text}")
            return redirect(f"{frontend_url}/teacher/materials?miro_error=token_exchange_failed")
        
        token_data = token_response.json()
        
    except requests.RequestException as e:
        logger.exception(f"Miro token request failed: {e}")
        return redirect(f"{frontend_url}/teacher/materials?miro_error=network_error")
    
    # Получаем информацию о пользователе
    access_token = token_data.get('access_token')
    
    try:
        user_response = requests.get(
            'https://api.miro.com/v1/users/me',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=15
        )
        
        if user_response.status_code == 200:
            miro_user = user_response.json()
            miro_user_id = miro_user.get('id', '')
            miro_team_id = miro_user.get('team', {}).get('id', '')
        else:
            miro_user_id = ''
            miro_team_id = ''
            
    except requests.RequestException:
        miro_user_id = ''
        miro_team_id = ''
    
    # Сохраняем токен для пользователя
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        user = User.objects.get(id=int(state))
    except (User.DoesNotExist, ValueError):
        return redirect(f"{frontend_url}/teacher/materials?miro_error=invalid_user")
    
    # Вычисляем время истечения
    expires_in = token_data.get('expires_in')  # секунды
    expires_at = None
    if expires_in:
        expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
    
    # Создаём или обновляем токен
    MiroUserToken.objects.update_or_create(
        user=user,
        defaults={
            'access_token': access_token,
            'refresh_token': token_data.get('refresh_token', ''),
            'token_type': token_data.get('token_type', 'Bearer'),
            'expires_at': expires_at,
            'miro_user_id': miro_user_id,
            'miro_team_id': miro_team_id,
            'scopes': token_data.get('scope', ''),
        }
    )
    
    logger.info(f"Miro OAuth successful for user {user.email}")
    
    return redirect(f"{frontend_url}/teacher/materials?miro_connected=true")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def miro_disconnect(request):
    """
    Отключить интеграцию с Miro для текущего пользователя.
    """
    if request.user.role != 'teacher':
        return Response(
            {'error': 'Только для учителей'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        token = MiroUserToken.objects.get(user=request.user)
        token.delete()
        logger.info(f"Miro disconnected for user {request.user.email}")
        return Response({'message': 'Miro отключен успешно'})
    except MiroUserToken.DoesNotExist:
        return Response({'message': 'Miro уже отключен'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def miro_refresh_token(request):
    """
    Обновить access token используя refresh token.
    """
    if request.user.role != 'teacher':
        return Response(
            {'error': 'Только для учителей'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        token = MiroUserToken.objects.get(user=request.user)
    except MiroUserToken.DoesNotExist:
        return Response(
            {'error': 'Miro не подключен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not token.refresh_token:
        return Response(
            {'error': 'Refresh token отсутствует, требуется повторная авторизация'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    config = get_miro_config()
    
    try:
        response = requests.post(
            'https://api.miro.com/v1/oauth/token',
            data={
                'grant_type': 'refresh_token',
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'refresh_token': token.refresh_token,
            },
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Miro refresh failed: {response.text}")
            return Response(
                {'error': 'Не удалось обновить токен'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        
        token_data = response.json()
        
        # Обновляем токен
        expires_in = token_data.get('expires_in')
        expires_at = None
        if expires_in:
            expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
        
        token.access_token = token_data.get('access_token', token.access_token)
        token.refresh_token = token_data.get('refresh_token', token.refresh_token)
        token.expires_at = expires_at
        token.save()
        
        return Response({'message': 'Токен обновлён успешно'})
        
    except requests.RequestException as e:
        logger.exception(f"Miro refresh request failed: {e}")
        return Response(
            {'error': 'Ошибка сети'},
            status=status.HTTP_502_BAD_GATEWAY
        )


def get_user_miro_token(user):
    """
    Получить действующий Miro токен для пользователя.
    Автоматически обновляет если нужно.
    
    Returns:
        str: access_token или None
    """
    try:
        token = MiroUserToken.objects.get(user=user)
    except MiroUserToken.DoesNotExist:
        return None
    
    # Если токен скоро истечёт и есть refresh_token - обновляем
    if token.needs_refresh() and token.refresh_token:
        config = get_miro_config()
        
        try:
            response = requests.post(
                'https://api.miro.com/v1/oauth/token',
                data={
                    'grant_type': 'refresh_token',
                    'client_id': config['client_id'],
                    'client_secret': config['client_secret'],
                    'refresh_token': token.refresh_token,
                },
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                expires_in = token_data.get('expires_in')
                expires_at = None
                if expires_in:
                    expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
                
                token.access_token = token_data.get('access_token', token.access_token)
                token.refresh_token = token_data.get('refresh_token', token.refresh_token)
                token.expires_at = expires_at
                token.save()
                
        except requests.RequestException:
            pass  # Вернём существующий токен
    
    # Если токен полностью истёк и refresh не помог
    if token.is_expired:
        return None
    
    return token.access_token


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def miro_list_boards(request):
    """
    Получить список досок Miro пользователя.
    Требует подключенной интеграции.
    """
    if request.user.role != 'teacher':
        return Response(
            {'error': 'Только для учителей'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    access_token = get_user_miro_token(request.user)
    
    if not access_token:
        return Response({
            'error': 'Miro не подключен или токен истёк',
            'needs_auth': True
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        response = requests.get(
            'https://api.miro.com/v2/boards',
            headers={'Authorization': f'Bearer {access_token}'},
            params={
                'limit': 50,
                'sort': 'last_modified',
            },
            timeout=15
        )
        
        if response.status_code == 401:
            return Response({
                'error': 'Токен Miro недействителен',
                'needs_auth': True
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if response.status_code != 200:
            return Response({
                'error': 'Ошибка получения списка досок',
                'details': response.text
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        boards_data = response.json()
        
        # Форматируем ответ
        boards = []
        for board in boards_data.get('data', []):
            boards.append({
                'id': board.get('id'),
                'name': board.get('name'),
                'description': board.get('description', ''),
                'view_link': board.get('viewLink'),
                'modified_at': board.get('modifiedAt'),
                'created_at': board.get('createdAt'),
                'picture': board.get('picture', {}).get('imageURL'),
            })
        
        return Response({
            'boards': boards,
            'total': len(boards),
        })
        
    except requests.RequestException as e:
        logger.exception(f"Miro boards request failed: {e}")
        return Response(
            {'error': 'Ошибка сети'},
            status=status.HTTP_502_BAD_GATEWAY
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def miro_create_board_oauth(request):
    """
    Создать новую доску Miro через OAuth.
    Использует личный токен пользователя.
    """
    if request.user.role != 'teacher':
        return Response(
            {'error': 'Только для учителей'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    access_token = get_user_miro_token(request.user)
    
    if not access_token:
        return Response({
            'error': 'Miro не подключен или токен истёк',
            'needs_auth': True
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    board_name = request.data.get('name', '').strip() or 'Новая доска'
    description = request.data.get('description', '').strip()
    lesson_id = request.data.get('lesson_id')
    visibility = request.data.get('visibility', 'lesson_group')
    
    try:
        # Создаём доску в Miro
        response = requests.post(
            'https://api.miro.com/v2/boards',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            json={
                'name': board_name,
                'description': description,
                'sharingPolicy': {
                    'access': 'view',
                    'inviteToAccountAndBoardLinkAccess': 'viewer'
                }
            },
            timeout=15
        )
        
        if response.status_code == 401:
            return Response({
                'error': 'Токен Miro недействителен',
                'needs_auth': True
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if response.status_code not in (200, 201):
            return Response({
                'error': 'Ошибка создания доски в Miro',
                'details': response.json() if response.text else response.status_code
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        board_data = response.json()
        board_id = board_data.get('id')
        board_url = board_data.get('viewLink')
        embed_url = f"https://miro.com/app/live-embed/{board_id}/?autoplay=yep"
        
    except requests.RequestException as e:
        logger.exception(f"Miro create board failed: {e}")
        return Response(
            {'error': 'Ошибка сети'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    
    # Создаём материал в БД
    from .models import Lesson
    
    lesson = None
    if lesson_id:
        try:
            lesson = Lesson.objects.get(id=lesson_id, teacher=request.user)
        except Lesson.DoesNotExist:
            pass
    
    material = LessonMaterial.objects.create(
        uploaded_by=request.user,
        lesson=lesson,
        material_type=LessonMaterial.MaterialType.MIRO_BOARD,
        title=board_name,
        description=description,
        miro_board_id=board_id,
        miro_board_url=board_url,
        miro_embed_url=embed_url,
        miro_thumbnail_url=board_data.get('picture', {}).get('imageURL', ''),
        visibility=visibility
    )
    
    # Добавляем группы если custom
    if visibility == 'custom_groups':
        group_ids = request.data.get('allowed_groups', [])
        if group_ids:
            groups = Group.objects.filter(id__in=group_ids, teacher=request.user)
            material.allowed_groups.set(groups)
    
    from .serializers import LessonMaterialSerializer
    serializer = LessonMaterialSerializer(material)
    
    return Response({
        'material': serializer.data,
        'miro_board': {
            'id': board_id,
            'name': board_name,
            'view_link': board_url,
            'embed_url': embed_url,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def miro_import_board(request):
    """
    Импортировать существующую доску Miro в материалы.
    Использует OAuth для получения информации о доске.
    """
    if request.user.role != 'teacher':
        return Response(
            {'error': 'Только для учителей'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    board_id = request.data.get('board_id', '').strip()
    lesson_id = request.data.get('lesson_id')
    visibility = request.data.get('visibility', 'lesson_group')
    
    if not board_id:
        return Response(
            {'error': 'ID доски обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    access_token = get_user_miro_token(request.user)
    
    # Если есть токен - получаем информацию о доске
    board_name = request.data.get('title', '').strip()
    description = request.data.get('description', '').strip()
    board_url = f"https://miro.com/app/board/{board_id}/"
    thumbnail_url = ''
    
    if access_token:
        try:
            response = requests.get(
                f'https://api.miro.com/v2/boards/{board_id}',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=15
            )
            
            if response.status_code == 200:
                board_data = response.json()
                board_name = board_name or board_data.get('name', 'Доска Miro')
                description = description or board_data.get('description', '')
                board_url = board_data.get('viewLink', board_url)
                thumbnail_url = board_data.get('picture', {}).get('imageURL', '')
                
        except requests.RequestException:
            pass
    
    if not board_name:
        board_name = 'Доска Miro'
    
    embed_url = f"https://miro.com/app/live-embed/{board_id}/?autoplay=yep"
    
    # Создаём материал
    from .models import Lesson
    
    lesson = None
    if lesson_id:
        try:
            lesson = Lesson.objects.get(id=lesson_id, teacher=request.user)
        except Lesson.DoesNotExist:
            pass
    
    material = LessonMaterial.objects.create(
        uploaded_by=request.user,
        lesson=lesson,
        material_type=LessonMaterial.MaterialType.MIRO_BOARD,
        title=board_name,
        description=description,
        miro_board_id=board_id,
        miro_board_url=board_url,
        miro_embed_url=embed_url,
        miro_thumbnail_url=thumbnail_url,
        visibility=visibility
    )
    
    if visibility == 'custom_groups':
        group_ids = request.data.get('allowed_groups', [])
        if group_ids:
            groups = Group.objects.filter(id__in=group_ids, teacher=request.user)
            material.allowed_groups.set(groups)
    
    from .serializers import LessonMaterialSerializer
    serializer = LessonMaterialSerializer(material)
    
    return Response(serializer.data, status=status.HTTP_201_CREATED)
