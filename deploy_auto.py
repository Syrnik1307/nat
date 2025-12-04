#!/usr/bin/env python3
"""
Automated Deployment Script for Teaching Panel
Использует paramiko для SSH соединения
"""

import paramiko
import sys
import time
from pathlib import Path

# Конфигурация сервера
HOST_ALIAS = "tp"
DEFAULT_HOST = "72.56.81.163"
DEFAULT_USER = "root"  # Переопределите, если в ssh-конфиге не указан User
REMOTE_PATH = "/var/www/teaching_panel"


def load_host_config(alias: str) -> dict:
    """Читает ~/.ssh/config и возвращает настройки для указанного алиаса."""
    config_path = Path.home() / ".ssh" / "config"
    if not config_path.exists():
        return {}

    ssh_config = paramiko.SSHConfig()
    with config_path.open() as cfg:
        ssh_config.parse(cfg)

    return ssh_config.lookup(alias)

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
        host_config = load_host_config(HOST_ALIAS)
        hostname = host_config.get('hostname', DEFAULT_HOST)
        port = int(host_config.get('port', 22))
        username = host_config.get('user', DEFAULT_USER)
        identity_files = host_config.get('identityfile', [])
        key_file = identity_files[0] if identity_files else None
        if not key_file:
            default_key = Path.home() / '.ssh' / 'id_ed25519'
            if default_key.exists():
                key_file = str(default_key)

        if not username:
            raise RuntimeError(
                "Не удалось определить пользователя SSH. Добавьте 'User' в ~/.ssh/config "
                f"для алиаса '{HOST_ALIAS}' или задайте DEFAULT_USER в deploy_auto.py."
            )

        # Подключение к серверу
        print(f"📡 Connecting to {username}@{hostname} (alias: {HOST_ALIAS})...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs = {
            'hostname': hostname,
            'username': username,
            'timeout': 10,
            'look_for_keys': True,
            'port': port,
        }
        if key_file:
            connect_kwargs['key_filename'] = key_file
        ssh.connect(**connect_kwargs)
        print("✅ Connected successfully!")
        
        # Цепочка команд для deployment
        project_path = f"{REMOTE_PATH}/teaching_panel"
        commands = [
            # 1. Переход в директорию проекта
            (f"cd {REMOTE_PATH} && pwd", 10),
            
            # 2. Получение последних изменений
            (f"cd {REMOTE_PATH} && sudo -u www-data git pull origin main", 30),
            
            # 3. Активация виртуального окружения и установка зависимостей
            (f"cd {project_path} && source ../venv/bin/activate && pip install -r requirements.txt --quiet", 120),
            
            # 4. Миграции базы данных
            (f"cd {project_path} && source ../venv/bin/activate && python manage.py migrate", 60),
            
            # 5. Сбор статических файлов
            (f"cd {project_path} && source ../venv/bin/activate && python manage.py collectstatic --noinput", 60),
            
            # 6. Перезапуск Django
            ("sudo systemctl restart teaching_panel", 10),
            
            # 7. Перезапуск Nginx
            ("sudo systemctl restart nginx", 10),
            
            # 8. Проверка статуса
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
        print("🌐 Website should be available at: http://72.56.81.163/")
        print()
        
        # Закрываем соединение
        ssh.close()
        return True
        
    except paramiko.AuthenticationException:
        print("❌ Authentication failed. Check SSH keys/username.")
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
