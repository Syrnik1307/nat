#!/usr/bin/env python3
"""
Automated Deployment Script for Teaching Panel
Использует paramiko для SSH соединения
"""

import paramiko
import sys
import time

# Конфигурация сервера
SERVER = "89.169.42.70"
USER = "nat"
PASSWORD = "Syrnik13"
REMOTE_PATH = "/home/nat/teaching_panel"

def run_command(ssh, command, timeout=60):
    """Выполняет команду на сервере и возвращает результат"""
    print(f"\n🔧 Executing: {command[:80]}...")
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    
    # Читаем вывод в реальном времени
    for line in stdout:
        print(f"   {line.strip()}")
    
    # Проверяем ошибки
    errors = stderr.read().decode()
    if errors:
        print(f"⚠️  Stderr: {errors}")
    
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        print(f"❌ Command failed with exit code {exit_code}")
        return False
    
    return True

def deploy():
    """Главная функция deployment"""
    print("=" * 60)
    print("🚀 Teaching Panel Automated Deployment")
    print("=" * 60)
    print()
    
    try:
        # Подключение к серверу
        print(f"📡 Connecting to {USER}@{SERVER}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER, username=USER, password=PASSWORD, timeout=10)
        print("✅ Connected successfully!")
        
        # Цепочка команд для deployment
        commands = [
            # 1. Переход в директорию проекта
            (f"cd {REMOTE_PATH} && pwd", 10),
            
            # 2. Получение последних изменений
            (f"cd {REMOTE_PATH} && git pull origin main", 30),
            
            # 3. Активация виртуального окружения и установка зависимостей
            (f"cd {REMOTE_PATH} && source venv/bin/activate && pip install -r requirements.txt --quiet", 120),
            
            # 4. Миграции базы данных
            (f"cd {REMOTE_PATH} && source venv/bin/activate && python manage.py migrate", 60),
            
            # 5. Сбор статических файлов
            (f"cd {REMOTE_PATH} && source venv/bin/activate && python manage.py collectstatic --noinput", 60),
            
            # 6. Перезапуск Django
            ("sudo systemctl restart teaching_panel", 10),
            
            # 7. Перезапуск Celery
            ("sudo systemctl restart celery", 10),
            
            # 8. Перезапуск Nginx
            ("sudo systemctl restart nginx", 10),
            
            # 9. Проверка статуса
            ("sudo systemctl status teaching_panel --no-pager | head -10", 10),
        ]
        
        print("\n📦 Starting deployment process...\n")
        
        for i, (command, timeout) in enumerate(commands, 1):
            print(f"\n[{i}/{len(commands)}] Step:")
            if not run_command(ssh, command, timeout):
                print(f"\n❌ Deployment failed at step {i}")
                ssh.close()
                return False
            time.sleep(1)
        
        print("\n" + "=" * 60)
        print("✅ Deployment completed successfully!")
        print("=" * 60)
        print()
        print("🌐 Website should be available at: http://89.169.42.70/")
        print()
        
        # Закрываем соединение
        ssh.close()
        return True
        
    except paramiko.AuthenticationException:
        print("❌ Authentication failed. Check username/password.")
        return False
    except paramiko.SSHException as e:
        print(f"❌ SSH error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
