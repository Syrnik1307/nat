from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status

from .serializers import UserProfileSerializer
from .models import CustomUser


class MeView(APIView):
    """Возвращает и обновляет профиль текущего пользователя"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def users_list(request):
    """Возвращает список всех пользователей для создания чатов"""
    users = CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name')
    serializer = UserProfileSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Смена пароля текущего пользователя"""
    user = request.user
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response(
            {'detail': 'Требуются оба поля: old_password и new_password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверяем старый пароль
    if not user.check_password(old_password):
        return Response(
            {'detail': 'Неверный текущий пароль'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Валидация нового пароля
    if len(new_password) < 8:
        return Response(
            {'detail': 'Пароль должен содержать минимум 8 символов'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not any(c.isupper() for c in new_password):
        return Response(
            {'detail': 'Пароль должен содержать хотя бы одну заглавную букву'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not any(c.islower() for c in new_password):
        return Response(
            {'detail': 'Пароль должен содержать хотя бы одну строчную букву'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not any(c.isdigit() for c in new_password):
        return Response(
            {'detail': 'Пароль должен содержать хотя бы одну цифру'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Устанавливаем новый пароль
    user.set_password(new_password)
    user.save()
    
    return Response(
        {'detail': 'Пароль успешно изменён'},
        status=status.HTTP_200_OK
    )
