# 🔧 Примеры интеграции - Code Examples

## Обзор

Этот документ содержит готовые примеры кода для интеграции новых компонентов в существующий проект.

---

## 📄 1. Обновление App.js

### Полный пример App.js с новыми компонентами:

```javascript
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth';

// Новые компоненты
import AuthPage from './components/AuthPage';
import TeacherHomePage from './components/TeacherHomePage';
import NavBar from './components/NavBarNew';

// Существующие компоненты
import StudentDashboard from './components/StudentDashboard';
import AdminDashboard from './components/AdminDashboard';
import GroupsManage from './components/GroupsManage';
import HomeworkManage from './components/HomeworkManage';
import RecurringLessonsManage from './components/RecurringLessonsManage';
import HomeworkList from './components/HomeworkList';
import HomeworkSubmission from './components/HomeworkSubmission';
import LessonAttendance from './components/LessonAttendance';

import './App.css';

// Защищенный маршрут
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { accessTokenValid, role } = useAuth();
  
  if (!accessTokenValid) {
    return <Navigate to="/login" replace />;
  }
  
  if (allowedRoles && !allowedRoles.includes(role)) {
    return <Navigate to="/" replace />;
  }
  
  return children;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <NavBar />
          <Routes>
            {/* Публичные маршруты */}
            <Route path="/login" element={<AuthPage />} />
            <Route path="/register" element={<AuthPage />} />
            
            {/* Главная страница */}
            <Route 
              path="/" 
              element={
                <ProtectedRoute>
                  <TeacherHomePage />
                </ProtectedRoute>
              } 
            />
            
            {/* Маршруты для преподавателя */}
            <Route 
              path="/teacher" 
              element={
                <ProtectedRoute allowedRoles={['teacher', 'admin']}>
                  <TeacherHomePage />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/groups/manage" 
              element={
                <ProtectedRoute allowedRoles={['teacher', 'admin']}>
                  <GroupsManage />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/homework/manage" 
              element={
                <ProtectedRoute allowedRoles={['teacher', 'admin']}>
                  <HomeworkManage />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/recurring-lessons/manage" 
              element={
                <ProtectedRoute allowedRoles={['teacher', 'admin']}>
                  <RecurringLessonsManage />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/lessons/:id/attendance" 
              element={
                <ProtectedRoute allowedRoles={['teacher', 'admin']}>
                  <LessonAttendance />
                </ProtectedRoute>
              } 
            />
            
            {/* Маршруты для ученика */}
            <Route 
              path="/student" 
              element={
                <ProtectedRoute allowedRoles={['student']}>
                  <StudentDashboard />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/homework" 
              element={
                <ProtectedRoute allowedRoles={['student']}>
                  <HomeworkList />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/homework/:id/submit" 
              element={
                <ProtectedRoute allowedRoles={['student']}>
                  <HomeworkSubmission />
                </ProtectedRoute>
              } 
            />
            
            {/* Маршруты для админа */}
            <Route 
              path="/admin" 
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <AdminDashboard />
                </ProtectedRoute>
              } 
            />
            
            {/* 404 */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
```

---

## 🔐 2. Обновление auth.js для SMS

### Добавьте поддержку SMS аутентификации:

```javascript
// frontend/src/auth.js

import React, { createContext, useContext, useState, useEffect } from 'react';
import { jwtDecode } from 'jwt-decode';
import apiService from './apiService';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [accessToken, setAccessToken] = useState(localStorage.getItem('accessToken'));
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem('refreshToken'));
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);

  // ... существующий код ...

  // Новая функция: отправка SMS кода
  const sendSMSCode = async (phone) => {
    try {
      const response = await apiService.post('/auth/sms/send', { phone });
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  // Новая функция: проверка SMS кода
  const verifySMSCode = async (phone, code) => {
    try {
      const response = await apiService.post('/auth/sms/verify', { phone, code });
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  // Обновленная функция login с поддержкой SMS
  const login = async ({ email, password, roleSelection, smsCode }) => {
    try {
      const response = await apiService.post('/auth/login', {
        email,
        password,
        role: roleSelection,
        sms_code: smsCode, // Опционально
      });

      const { access, refresh, user: userData } = response.data;
      
      setAccessToken(access);
      setRefreshToken(refresh);
      localStorage.setItem('accessToken', access);
      localStorage.setItem('refreshToken', refresh);
      
      const decoded = jwtDecode(access);
      setUser(userData);
      setRole(decoded.role || roleSelection);
      
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  // Новая функция: регистрация с SMS
  const register = async ({ email, password, firstName, lastName, phone, role }) => {
    try {
      const response = await apiService.post('/auth/register', {
        email,
        password,
        first_name: firstName,
        last_name: lastName,
        phone,
        role,
      });
      
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  // ... остальной код ...

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        refreshToken,
        user,
        role,
        accessTokenValid: !!accessToken,
        login,
        register,
        sendSMSCode,
        verifySMSCode,
        logout,
        refreshAccessToken,
      }}
    >
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
```

---

## 🛠️ 3. Backend API эндпоинты (Django)

### a) SMS сервис

```python
# teaching_panel/accounts/sms_service.py

import random
import string
from django.core.cache import cache
from twilio.rest import Client  # или другой провайдер
from django.conf import settings

class SMSService:
    @staticmethod
    def generate_code(length=6):
        """Генерация 6-значного кода"""
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def send_code(phone_number):
        """Отправка SMS кода"""
        # Генерируем код
        code = SMSService.generate_code()
        
        # Сохраняем в кэш на 5 минут
        cache_key = f'sms_code_{phone_number}'
        cache.set(cache_key, code, timeout=300)
        
        # Отправляем через Twilio (или другой сервис)
        try:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                body=f'Ваш код подтверждения: {code}',
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            return True
        except Exception as e:
            print(f'Ошибка отправки SMS: {e}')
            return False
    
    @staticmethod
    def verify_code(phone_number, code):
        """Проверка SMS кода"""
        cache_key = f'sms_code_{phone_number}'
        stored_code = cache.get(cache_key)
        
        if stored_code and stored_code == code:
            cache.delete(cache_key)
            return True
        return False
```

### b) Views для SMS

```python
# teaching_panel/accounts/views.py

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .sms_service import SMSService
from .models import User

@api_view(['POST'])
@permission_classes([AllowAny])
def send_sms_code(request):
    """Отправить SMS код на телефон"""
    phone = request.data.get('phone')
    
    if not phone:
        return Response(
            {'error': 'Телефон обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверяем rate limiting
    rate_limit_key = f'sms_rate_limit_{phone}'
    attempts = cache.get(rate_limit_key, 0)
    
    if attempts >= 3:
        return Response(
            {'error': 'Превышено количество попыток. Попробуйте через 5 минут.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Отправляем код
    if SMSService.send_code(phone):
        # Увеличиваем счетчик попыток
        cache.set(rate_limit_key, attempts + 1, timeout=300)
        
        return Response({
            'success': True,
            'message': 'Код отправлен'
        })
    else:
        return Response(
            {'error': 'Ошибка отправки SMS'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_sms_code(request):
    """Проверить SMS код"""
    phone = request.data.get('phone')
    code = request.data.get('code')
    
    if not phone or not code:
        return Response(
            {'error': 'Телефон и код обязательны'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if SMSService.verify_code(phone, code):
        return Response({
            'success': True,
            'message': 'Код подтвержден'
        })
    else:
        return Response(
            {'error': 'Неверный код'},
            status=status.HTTP_400_BAD_REQUEST
        )
```

### c) URLs

```python
# teaching_panel/accounts/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ... существующие маршруты ...
    
    path('auth/sms/send', views.send_sms_code, name='send_sms_code'),
    path('auth/sms/verify', views.verify_sms_code, name='verify_sms_code'),
]
```

### d) Обновление модели User

```python
# teaching_panel/accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Существующие поля...
    
    # Новые поля для SMS
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Телефон'
    )
    phone_verified = models.BooleanField(
        default=False,
        verbose_name='Телефон подтвержден'
    )
    
    # Поля для защиты от атак
    failed_login_attempts = models.IntegerField(
        default=0,
        verbose_name='Неудачные попытки входа'
    )
    blocked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Заблокирован до'
    )
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP последнего входа'
    )
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
```

### e) Миграции

```bash
# Создать миграции
python manage.py makemigrations

# Применить миграции
python manage.py migrate
```

---

## 🔒 4. Rate Limiting Middleware

```python
# teaching_panel/accounts/middleware.py

from django.core.cache import cache
from django.http import JsonResponse
from datetime import datetime, timedelta

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Проверяем только для входа
        if request.path == '/api/auth/login' and request.method == 'POST':
            ip_address = self.get_client_ip(request)
            rate_limit_key = f'login_rate_limit_{ip_address}'
            
            # Получаем количество попыток
            attempts = cache.get(rate_limit_key, 0)
            
            # Максимум 5 попыток в минуту
            if attempts >= 5:
                return JsonResponse({
                    'error': 'Превышено количество попыток входа. Попробуйте через минуту.'
                }, status=429)
            
            # Увеличиваем счетчик
            cache.set(rate_limit_key, attempts + 1, timeout=60)
        
        response = self.get_response(request)
        return response
    
    @staticmethod
    def get_client_ip(request):
        """Получить IP адрес клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

### Добавить в settings.py:

```python
# teaching_panel/teaching_panel/settings.py

MIDDLEWARE = [
    # ... другие middleware ...
    'accounts.middleware.RateLimitMiddleware',
]

# Twilio настройки (для SMS)
TWILIO_ACCOUNT_SID = 'your_account_sid'
TWILIO_AUTH_TOKEN = 'your_auth_token'
TWILIO_PHONE_NUMBER = '+1234567890'
```

---

## 📱 5. Frontend - Использование AuthPage

### Пример с SMS подтверждением:

```javascript
import React, { useState } from 'react';
import { useAuth } from '../auth';
import { useNavigate } from 'react-router-dom';

function LoginExample() {
  const { login, sendSMSCode, verifySMSCode } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1=login, 2=sms
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    phone: '',
  });
  const [smsCode, setSmsCode] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    
    try {
      // Отправляем SMS код
      await sendSMSCode(formData.phone);
      setStep(2); // Переход к вводу кода
    } catch (err) {
      setError('Ошибка отправки SMS');
    }
  };

  const handleVerifySMS = async (e) => {
    e.preventDefault();
    
    try {
      // Проверяем SMS код
      await verifySMSCode(formData.phone, smsCode);
      
      // Выполняем вход
      await login({
        email: formData.email,
        password: formData.password,
        roleSelection: 'teacher',
        smsCode,
      });
      
      navigate('/');
    } catch (err) {
      setError('Неверный код');
    }
  };

  if (step === 2) {
    return (
      <form onSubmit={handleVerifySMS}>
        <input
          type="text"
          value={smsCode}
          onChange={(e) => setSmsCode(e.target.value)}
          placeholder="Введите код"
          maxLength={6}
        />
        <button type="submit">Подтвердить</button>
        {error && <p>{error}</p>}
      </form>
    );
  }

  return (
    <form onSubmit={handleLogin}>
      <input
        type="email"
        value={formData.email}
        onChange={(e) => setFormData({...formData, email: e.target.value})}
        placeholder="Email"
      />
      <input
        type="password"
        value={formData.password}
        onChange={(e) => setFormData({...formData, password: e.target.value})}
        placeholder="Пароль"
      />
      <input
        type="tel"
        value={formData.phone}
        onChange={(e) => setFormData({...formData, phone: e.target.value})}
        placeholder="Телефон"
      />
      <button type="submit">Войти</button>
      {error && <p>{error}</p>}
    </form>
  );
}
```

---

## 🎨 6. Кастомизация стилей

### Изменить основной цвет:

```css
/* frontend/src/App.css */

:root {
  /* Замените синий на свой цвет */
  --primary-500: #your-color;
  --primary-600: #your-darker-color;
  --primary-700: #your-darkest-color;
}
```

### Изменить радиусы:

```css
:root {
  --radius-sm: 12px;  /* вместо 8px */
  --radius-md: 16px;  /* вместо 12px */
  --radius-lg: 20px;  /* вместо 16px */
}
```

---

## ✅ Готово!

Используйте эти примеры для быстрой интеграции новых компонентов в ваш проект.
