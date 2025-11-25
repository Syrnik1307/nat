"""
SMS сервис для отправки кодов верификации через SMS.RU
"""
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class SMSService:
    """Сервис для отправки SMS через SMS.RU API"""
    
    def __init__(self):
        """Инициализация SMS.RU клиента"""
        self.api_id = getattr(settings, 'SMSRU_API_ID', None)
        self.from_name = getattr(settings, 'SMSRU_FROM_NAME', 'Teaching Panel')
        self.api_url = 'https://sms.ru/sms/send'
        
        if not self.api_id:
            logger.warning('SMS.RU API ID not configured. SMS sending will be disabled.')
            self.enabled = False
        else:
            self.enabled = True
    
    def send_verification_code(self, phone_number, code):
        """
        Отправка кода верификации на телефон
        
        Args:
            phone_number (str): Номер телефона в формате 79991234567 (без +)
            code (str): 6-значный код верификации
            
        Returns:
            dict: {'success': bool, 'message': str, 'sms_id': str|None}
        """
        if not self.enabled:
            logger.error('SMS.RU API not configured. Cannot send SMS.')
            return {
                'success': False,
                'message': 'SMS service not configured',
                'sms_id': None
            }
        
        try:
            # Убираем + из номера (SMS.RU требует без +)
            clean_phone = phone_number.replace('+', '')
            
            # Форматируем сообщение
            message_text = f'Ваш код верификации для Teaching Panel: {code}\n\nКод действителен 10 минут.'
            
            # Параметры запроса
            params = {
                'api_id': self.api_id,
                'to': clean_phone,
                'msg': message_text,
                'json': 1  # Ответ в JSON формате
            }
            
            # Отправляем SMS через SMS.RU API
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            # Проверяем результат
            # Коды ответов SMS.RU: 100 = успех, остальные = ошибки
            if result.get('status_code') == 100:
                sms_id = result.get('sms', {}).get(clean_phone, {}).get('sms_id')
                logger.info(f'SMS sent successfully to {phone_number}. SMS ID: {sms_id}')
                
                return {
                    'success': True,
                    'message': 'SMS sent successfully',
                    'sms_id': sms_id
                }
            else:
                error_msg = self._get_error_message(result.get('status_code'))
                logger.error(f'SMS.RU error for {phone_number}: {error_msg}')
                
                return {
                    'success': False,
                    'message': error_msg,
                    'sms_id': None
                }
            
        except requests.RequestException as e:
            logger.error(f'Network error sending SMS to {phone_number}: {str(e)}')
            return {
                'success': False,
                'message': f'Ошибка сети: {str(e)}',
                'sms_id': None
            }
        except Exception as e:
            logger.error(f'Failed to send SMS to {phone_number}: {str(e)}')
            return {
                'success': False,
                'message': f'Ошибка отправки SMS: {str(e)}',
                'sms_id': None
            }
    
    def _get_error_message(self, status_code):
        """Расшифровка кодов ошибок SMS.RU"""
        error_codes = {
            200: 'Неправильный api_id',
            201: 'Не хватает средств на лицевом счете',
            202: 'Неправильно указан получатель',
            203: 'Нет текста сообщения',
            204: 'Имя отправителя не согласовано с администрацией',
            205: 'Сообщение слишком длинное (более 8 SMS)',
            206: 'Будет превышен или уже превышен дневной лимит на отправку сообщений',
            207: 'На этот номер нельзя отправлять сообщения',
            208: 'Параметр time указан неправильно',
            209: 'Вы добавили этот номер в стоп-лист',
            210: 'Используется GET, где необходимо использовать POST',
            211: 'Метод не найден',
            220: 'Сервис временно недоступен, попробуйте чуть позже',
            300: 'Неправильный token',
            301: 'Неправильный пароль',
            302: 'Пользователь авторизован, но аккаунт не подтвержден'
        }
        return error_codes.get(status_code, f'Неизвестная ошибка (код {status_code})')
    
    def send_welcome_message(self, phone_number, user_name):
        """
        Отправка приветственного сообщения после регистрации
        
        Args:
            phone_number (str): Номер телефона
            user_name (str): Имя пользователя
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        if not self.enabled:
            return {'success': False, 'message': 'SMS service not configured'}
        
        try:
            clean_phone = phone_number.replace('+', '')
            message_text = f'Добро пожаловать в Teaching Panel, {user_name}! 🎓\n\nВаша регистрация успешно завершена.'
            
            params = {
                'api_id': self.api_id,
                'to': clean_phone,
                'msg': message_text,
                'json': 1
            }
            
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('status_code') == 100:
                logger.info(f'Welcome SMS sent to {phone_number}')
                return {
                    'success': True,
                    'message': 'Welcome SMS sent successfully'
                }
            else:
                error_msg = self._get_error_message(result.get('status_code'))
                logger.error(f'Failed to send welcome SMS: {error_msg}')
                return {
                    'success': False,
                    'message': error_msg
                }
            
        except Exception as e:
            logger.error(f'Failed to send welcome SMS to {phone_number}: {str(e)}')
            return {
                'success': False,
                'message': f'Failed to send welcome SMS: {str(e)}'
            }


# Singleton instance
sms_service = SMSService()
