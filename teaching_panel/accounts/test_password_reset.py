from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core import mail

User = get_user_model()


class PasswordResetAPITests(TestCase):
    """Тесты для API сброса пароля"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='oldpassword123',
            first_name='Test',
            role='student'
        )
    
    def test_password_reset_request_success(self):
        """Тест успешного запроса на сброс пароля"""
        url = reverse('accounts:password_reset_request')
        data = {'email': 'test@example.com'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Новый пароль', mail.outbox[0].body)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('oldpassword123'))
    
    def test_password_reset_request_nonexistent_email(self):
        """Тест запроса с несуществующим email (безопасность)"""
        url = reverse('accounts:password_reset_request')
        data = {'email': 'nonexistent@example.com'}
        
        response = self.client.post(url, data, format='json')
        
        # Должен возвращать успех для безопасности
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)
        self.assertEqual(len(mail.outbox), 0)
    
    def test_password_reset_request_missing_email(self):
        """Тест запроса без email"""
        url = reverse('accounts:password_reset_request')
        data = {}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)
    
    def test_password_reset_confirm_success(self):
        """Тест успешного сброса пароля"""
        # Генерируем валидный токен
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        url = reverse('accounts:password_reset_confirm')
        data = {
            'uid': uid,
            'token': token,
            'password': 'newpassword123'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)
        
        # Проверяем, что пароль изменился
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))
    
    def test_password_reset_confirm_invalid_token(self):
        """Тест с недействительным токеном"""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        url = reverse('accounts:password_reset_confirm')
        data = {
            'uid': uid,
            'token': 'invalid-token',
            'password': 'newpassword123'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)
    
    def test_password_reset_confirm_short_password(self):
        """Тест с коротким паролем"""
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        url = reverse('accounts:password_reset_confirm')
        data = {
            'uid': uid,
            'token': token,
            'password': '12345'  # Слишком короткий
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)
    
    def test_password_reset_validate_token_valid(self):
        """Тест проверки валидного токена"""
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        url = reverse('accounts:password_reset_validate', kwargs={'uid': uid, 'token': token})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['valid'])
        self.assertEqual(response.data['email'], self.user.email)
    
    def test_password_reset_validate_token_invalid(self):
        """Тест проверки невалидного токена"""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        url = reverse('accounts:password_reset_validate', kwargs={'uid': uid, 'token': 'invalid'})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['valid'])
        self.assertIn('error', response.data)
