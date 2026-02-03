"""
Email сервис для отправки писем верификации
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Пул потоков для асинхронной отправки email (fire-and-forget)
_email_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix='email_sender')


class EmailService:
    """Сервис для отправки email"""
    
    def __init__(self):
        """Инициализация email сервиса"""
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@teachingpanel.com')
        self.enabled = getattr(settings, 'EMAIL_BACKEND', '') != 'django.core.mail.backends.dummy.EmailBackend'
        
        if not self.enabled:
            logger.warning('Email backend not configured. Email sending will be disabled.')
    
    def send_verification_email(self, email, code, token, async_send=True):
        """
        Отправка email с кодом верификации
        
        Args:
            email (str): Email адрес получателя
            code (str): 6-значный код верификации
            token (str): UUID токен для ссылки верификации
            async_send (bool): Отправлять асинхронно (по умолчанию True)
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        if not self.enabled:
            logger.error('Email service not configured. Cannot send email.')
            return {
                'success': False,
                'message': 'Email service not configured'
            }
        
        # Асинхронная отправка - сразу возвращаем success, отправляем в фоне
        if async_send:
            try:
                _email_executor.submit(self._send_verification_email_sync, email, code, token)
                logger.info(f'Verification email queued for async sending to {email}')
                return {
                    'success': True,
                    'message': 'Email queued for sending'
                }
            except Exception as e:
                logger.error(f'Failed to queue verification email to {email}: {str(e)}')
                # Fallback на синхронную отправку
                return self._send_verification_email_sync(email, code, token)
        
        return self._send_verification_email_sync(email, code, token)
    
    def _send_verification_email_sync(self, email, code, token):
        """
        Синхронная отправка email (внутренний метод)
        """
        
        try:
            # Формируем ссылку для верификации
            verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}"
            
            # Тема письма
            subject = 'Подтверждение регистрации на Teaching Panel'
            
            # HTML версия письма
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                        border-radius: 10px 10px 0 0;
                    }}
                    .content {{
                        background: #f9fafb;
                        padding: 30px;
                        border-radius: 0 0 10px 10px;
                    }}
                    .code-box {{
                        background: white;
                        border: 2px solid #2563eb;
                        border-radius: 10px;
                        padding: 20px;
                        text-align: center;
                        margin: 20px 0;
                    }}
                    .code {{
                        font-size: 32px;
                        font-weight: bold;
                        color: #2563eb;
                        letter-spacing: 8px;
                        font-family: monospace;
                    }}
                    .button {{
                        display: inline-block;
                        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
                        color: white;
                        padding: 15px 40px;
                        text-decoration: none;
                        border-radius: 8px;
                        margin: 20px 0;
                        font-weight: bold;
                    }}
                    .footer {{
                        text-align: center;
                        color: #6b7280;
                        font-size: 12px;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📚 Teaching Panel</h1>
                    <p>Подтверждение регистрации</p>
                </div>
                <div class="content">
                    <p>Здравствуйте!</p>
                    <p>Спасибо за регистрацию на платформе <strong>Teaching Panel</strong>.</p>
                    <p>Для завершения регистрации используйте один из способов:</p>
                    
                    <h3>Способ 1: Введите код</h3>
                    <div class="code-box">
                        <p>Ваш код верификации:</p>
                        <div class="code">{code}</div>
                        <p style="color: #6b7280; font-size: 14px;">Код действителен 10 минут</p>
                    </div>
                    
                    <h3>Способ 2: Нажмите кнопку</h3>
                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">Подтвердить Email</a>
                    </div>
                    
                    <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                        Если вы не регистрировались на Teaching Panel, просто проигнорируйте это письмо.
                    </p>
                </div>
                <div class="footer">
                    <p>© 2025 Teaching Panel. Все права защищены.</p>
                    <p>Это автоматическое письмо, не отвечайте на него.</p>
                </div>
            </body>
            </html>
            """
            
            # Текстовая версия (fallback)
            text_content = f"""
            Здравствуйте!
            
            Спасибо за регистрацию на платформе Teaching Panel.
            
            Ваш код верификации: {code}
            
            Или перейдите по ссылке: {verification_url}
            
            Код действителен 10 минут.
            
            Если вы не регистрировались на Teaching Panel, просто проигнорируйте это письмо.
            
            © 2025 Teaching Panel
            """
            
            # Создаем email с HTML и текстом
            email_message = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=[email]
            )
            email_message.attach_alternative(html_content, "text/html")
            
            # Отправляем
            email_message.send()
            
            logger.info(f'Verification email sent successfully to {email}')
            
            return {
                'success': True,
                'message': 'Email sent successfully'
            }
            
        except Exception as e:
            logger.error(f'Failed to send verification email to {email}: {str(e)}')
            return {
                'success': False,
                'message': f'Failed to send email: {str(e)}'
            }
    
    def send_welcome_email(self, email, user_name, async_send=True):
        """
        Отправка приветственного письма после успешной верификации
        
        Args:
            email (str): Email адрес
            user_name (str): Имя пользователя
            async_send (bool): Отправлять асинхронно (по умолчанию True)
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        if not self.enabled:
            return {'success': False, 'message': 'Email service not configured'}
        
        # Асинхронная отправка
        if async_send:
            try:
                _email_executor.submit(self._send_welcome_email_sync, email, user_name)
                logger.info(f'Welcome email queued for async sending to {email}')
                return {
                    'success': True,
                    'message': 'Welcome email queued for sending'
                }
            except Exception as e:
                logger.error(f'Failed to queue welcome email to {email}: {str(e)}')
                return self._send_welcome_email_sync(email, user_name)
        
        return self._send_welcome_email_sync(email, user_name)
    
    def _send_welcome_email_sync(self, email, user_name):
        """
        Синхронная отправка welcome email (внутренний метод)
        """
        try:
            subject = f'Добро пожаловать в Teaching Panel, {user_name}!'
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                        border-radius: 10px;
                    }}
                    .content {{
                        padding: 30px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🎓 Добро пожаловать!</h1>
                </div>
                <div class="content">
                    <p>Здравствуйте, {user_name}!</p>
                    <p>Ваша регистрация на платформе <strong>Teaching Panel</strong> успешно завершена.</p>
                    <p>Теперь вы можете войти в систему и начать обучение!</p>
                    <p>С уважением,<br>Команда Teaching Panel</p>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Здравствуйте, {user_name}!
            
            Ваша регистрация на платформе Teaching Panel успешно завершена.
            Теперь вы можете войти в систему и начать обучение!
            
            С уважением,
            Команда Teaching Panel
            """
            
            email_message = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=[email]
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send()
            
            logger.info(f'Welcome email sent to {email}')
            
            return {
                'success': True,
                'message': 'Welcome email sent successfully'
            }
            
        except Exception as e:
            logger.error(f'Failed to send welcome email to {email}: {str(e)}')
            return {
                'success': False,
                'message': f'Failed to send email: {str(e)}'
            }


# Singleton instance
email_service = EmailService()
