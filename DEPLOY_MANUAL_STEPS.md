# 🚀 ДЕПЛОЙ ИСПРАВЛЕНИЙ - Пошаговая инструкция

## Проблема на сервере
На сервере `/var/www/teaching_panel` не является git-репозиторием, поэтому `git pull` не работает.

## ✅ Решение: Копируем файлы вручную

### Вариант 1: Через WinSCP (рекомендуется для Windows)

1. **Скачайте и установите WinSCP:** https://winscp.net/eng/download.php

2. **Подключитесь к серверу:**
   - Host: `72.56.81.163`
   - Username: `root`
   - Password: ваш пароль

3. **Скопируйте файлы:**
   
   Локальные файлы (слева) → Удалённая директория (справа)
   
   ```
   C:\Users\User\Desktop\nat\frontend\src\components\NavBarNew.js
   → /var/www/teaching_panel/frontend/src/components/NavBarNew.js
   
   C:\Users\User\Desktop\nat\frontend\src\components\TeacherHomePage.js
   → /var/www/teaching_panel/frontend/src/components/TeacherHomePage.js
   
   C:\Users\User\Desktop\nat\frontend\package.json
   → /var/www/teaching_panel/frontend/package.json
   ```

4. **Откройте терминал WinSCP** (Ctrl+T) и выполните:
   ```bash
   cd /var/www/teaching_panel/frontend
   npm run build
   sudo systemctl restart nginx
   ```

---

### Вариант 2: Через PuTTY + текстовый редактор

1. **Подключитесь через PuTTY:**
   - Host: `72.56.81.163`
   - Username: `root`

2. **Отредактируйте файлы напрямую:**

#### Файл 1: NavBarNew.js

```bash
nano /var/www/teaching_panel/frontend/src/components/NavBarNew.js
```

Найдите функцию `loadMessages` (строка ~51) и замените на:

```javascript
  const loadMessages = async () => {
    try {
      const token = localStorage.getItem('tp_access_token');
      const response = await fetch('/accounts/api/status-messages/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      // Проверяем статус ответа
      if (!response.ok) {
        console.warn('Статус-сообщения недоступны:', response.status);
        return;
      }
      
      // Проверяем, что ответ действительно JSON
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        console.warn('Получен не-JSON ответ от /accounts/api/status-messages/');
        return;
      }
      
      const data = await response.json();
      const activeMessages = Array.isArray(data) ? data.filter(msg => msg.is_active) : [];
      setMessages(activeMessages);
    } catch (error) {
      console.error('Ошибка загрузки сообщений:', error);
      setMessages([]); // Устанавливаем пустой массив при ошибке
    }
  };
```

Сохраните: `Ctrl+O`, Enter, `Ctrl+X`

#### Файл 2: TeacherHomePage.js

```bash
nano /var/www/teaching_panel/frontend/src/components/TeacherHomePage.js
```

Найдите секцию "Сводная статистика" (~403 строка) и замените проверки:

Было:
```javascript
{breakdown.groups.length === 0 && (
```

Стало:
```javascript
{(!breakdown?.groups || breakdown.groups.length === 0) && (
```

И строку:
```javascript
{breakdown.groups.map(g => (
```

Заменить на:
```javascript
{breakdown?.groups && breakdown.groups.map(g => (
```

То же самое для `breakdown.students` - добавить `?.` и проверку.

Сохраните: `Ctrl+O`, Enter, `Ctrl+X`

#### Файл 3: package.json (опционально)

```bash
nano /var/www/teaching_panel/frontend/package.json
```

В секции `"scripts"` измените:
```json
"build": "react-scripts --max_old_space_size=4096 build",
```

---

### Вариант 3: Скопировать содержимое через буфер обмена

Если у вас есть SSH-доступ через любой клиент:

1. **Откройте локальный файл** `NavBarNew.js` в VSCode
2. **Скопируйте весь код** (Ctrl+A, Ctrl+C)
3. **На сервере создайте временный файл:**
   ```bash
   nano /tmp/NavBarNew.js
   ```
4. **Вставьте код** (правая кнопка мыши в PuTTY)
5. **Сохраните и скопируйте:**
   ```bash
   cp /tmp/NavBarNew.js /var/www/teaching_panel/frontend/src/components/NavBarNew.js
   ```

Повторите для остальных файлов.

---

## После копирования файлов

Выполните на сервере:

```bash
cd /var/www/teaching_panel/frontend
npm run build
sudo systemctl restart nginx
```

Проверьте сборку:
```bash
# Если сборка успешна, увидите:
# "Compiled successfully"
# "The build folder is ready to be deployed"
```

Проверьте сайт: **http://72.56.81.163**

---

## Проверка работы

1. Откройте сайт в браузере
2. Откройте DevTools (F12)
3. Перейдите на страницу учителя
4. В консоли не должно быть ошибок:
   - ❌ `SyntaxError: Unexpected token '<'`
   - ❌ `Cannot read properties of undefined (reading 'length')`

---

## Если нужно настроить Git на сервере

Чтобы в будущем использовать `git pull`:

```bash
cd /var/www/teaching_panel

# Инициализировать git
git init

# Добавить remote
git remote add origin https://github.com/Syrnik1307/nat.git

# Получить изменения
git fetch origin main

# Сбросить на последний коммит (ОСТОРОЖНО: удалит локальные изменения!)
git reset --hard origin/main
```

После этого `git pull origin main` будет работать.

---

## Альтернатива: Клонировать репозиторий заново

Если на сервере нет важных локальных изменений:

```bash
# Сделать бэкап текущей директории
cd /var/www
sudo mv teaching_panel teaching_panel_backup

# Клонировать репозиторий
git clone https://github.com/Syrnik1307/nat.git teaching_panel

# Восстановить виртуальное окружение
cd teaching_panel
python3 -m venv venv
source venv/bin/activate
pip install -r teaching_panel/requirements-production.txt

# Скопировать .env файл из бэкапа
cp ../teaching_panel_backup/teaching_panel/.env teaching_panel/.env

# Применить миграции и собрать статику
python teaching_panel/manage.py migrate
python teaching_panel/manage.py collectstatic --noinput

# Собрать фронтенд
cd frontend
npm install
npm run build

# Перезапустить сервисы
sudo systemctl restart teaching_panel celery celery-beat nginx
```

---

## Нужна помощь?

Если возникли проблемы, отправьте вывод команды:
```bash
sudo journalctl -u teaching_panel -n 50
```
