"""
Отправка кодов восстановления пароля через Telegram или WhatsApp
"""
import os
import random
import requests
from django.utils import timezone
from django.utils.crypto import get_random_string
from .models import CustomUser
from datetime import timedelta


class PasswordResetCode:
    """Генерация и отправка кодов восстановления пароля"""
    
    @staticmethod
    def generate_code(length=6):
        """Генерирует 6-значный код"""
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])
    
    @staticmethod
    def send_to_telegram(phone, code):
        """
        Отправка кода через Telegram по номеру телефона
        Использует Telegram Bot API
        """
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            raise ValueError('TELEGRAM_BOT_TOKEN не настроен')
        
        # Форматируем номер для поиска (убираем все кроме цифр)
        phone_digits = ''.join(filter(str.isdigit, phone))
        
        message = (
            f"🔐 Код для восстановления пароля: {code}\n\n"
            f"Код действителен 15 минут.\n"
            f"Если вы не запрашивали восстановление пароля, игнорируйте это сообщение."
        )
        
        try:
            # Пытаемся найти пользователя по номеру телефона в Telegram
            # Примечание: Telegram Bot API не позволяет напрямую отправлять по номеру
            # Нужно чтобы пользователь сначала написал боту /start
            # Здесь мы используем базу сохранённых chat_id
            
            user = CustomUser.objects.filter(phone=phone).first()
            if not user or not user.telegram_chat_id:
                return {
                    'success': False,
                    'error': 'Пользователь не связал аккаунт с Telegram ботом. Отправьте /start боту @YourBotName'
                }
            
            url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
            response = requests.post(url, json={
                'chat_id': user.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            })
            
            if response.status_code == 200:
                return {'success': True, 'method': 'telegram'}
            else:
                return {'success': False, 'error': f'Telegram API error: {response.text}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def send_to_whatsapp(phone, code):
        """
        Отправка кода через WhatsApp
        Использует WhatsApp Business API или сервис вроде Twilio
        """
        # Вариант 1: Twilio (платный, но надёжный)
        twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
        twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
        twilio_whatsapp = os.getenv('TWILIO_WHATSAPP_NUMBER')  # например: whatsapp:+14155238886
        
        if not all([twilio_sid, twilio_token, twilio_whatsapp]):
            return {
                'success': False,
                'error': 'WhatsApp (Twilio) не настроен. Добавьте TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER'
            }
        
        message = (
            f"🔐 Код для восстановления пароля: {code}\n\n"
            f"Код действителен 15 минут.\n"
            f"Если вы не запрашивали восстановление пароля, игнорируйте это сообщение."
        )
        
        try:
            from twilio.rest import Client
            
            client = Client(twilio_sid, twilio_token)
            
            # Форматируем номер для WhatsApp
            formatted_phone = phone if phone.startswith('+') else f'+{phone}'
            
            message_obj = client.messages.create(
                from_=twilio_whatsapp,
                body=message,
                to=f'whatsapp:{formatted_phone}'
            )
            
            return {'success': True, 'method': 'whatsapp', 'sid': message_obj.sid}
            
        except ImportError:
            return {
                'success': False,
                'error': 'Библиотека Twilio не установлена. Установите: pip install twilio'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}


def send_password_reset_code(email, phone, method='telegram'):
    """
    Главная функция для отправки кода восстановления пароля
    
    Args:
        email: Email пользователя
        phone: Номер телефона пользователя
        method: 'telegram' или 'whatsapp'
    
    Returns:
        dict: {'success': bool, 'code': str, 'method': str, 'error': str}
    """
    import random
    from django.core.cache import cache
    
    try:
        # Проверяем существование пользователя
        user = CustomUser.objects.filter(email=email).first()
        if not user:
            return {'success': False, 'error': 'Пользователь не найден'}
        
        # Проверяем совпадение телефона
        if user.phone != phone:
            return {'success': False, 'error': 'Номер телефона не совпадает с указанным при регистрации'}
        
        # Генерируем 6-значный код
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Сохраняем код в кэш на 15 минут
        cache_key = f'password_reset_{email}'
        cache.set(cache_key, code, 15 * 60)  # 15 минут
        
        # Отправляем код через выбранный метод
        if method == 'telegram':
            result = PasswordResetCode.send_to_telegram(phone, code)
        elif method == 'whatsapp':
            result = PasswordResetCode.send_to_whatsapp(phone, code)
        else:
            return {'success': False, 'error': 'Неизвестный метод отправки'}
        
        if result['success']:
            result['code'] = code  # Для тестирования (в продакшене убрать!)
            return result
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'error': str(e)}


def verify_reset_code(email, code):
    """
    Проверка кода восстановления пароля
    
    Args:
        email: Email пользователя
        code: Введённый код
    
    Returns:
        dict: {'success': bool, 'error': str}
    """
    from django.core.cache import cache
    
    cache_key = f'password_reset_{email}'
    stored_code = cache.get(cache_key)
    
    if not stored_code:
        return {'success': False, 'error': 'Код истёк или не был запрошен'}
    
    if stored_code != code:
        return {'success': False, 'error': 'Неверный код'}
    
    # Код верный, удаляем его из кэша
    cache.delete(cache_key)
    
    # Генерируем временный токен для смены пароля (действует 30 минут)
    from .models import PasswordResetToken
    user = CustomUser.objects.get(email=email)
    token = PasswordResetToken.generate_token(user, expires_in_minutes=30)
    
    return {
        'success': True,
        'token': token.token,
        'message': 'Код подтверждён. Можете сменить пароль.'
    }
