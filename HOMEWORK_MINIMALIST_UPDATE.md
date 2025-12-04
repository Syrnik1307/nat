# Редизайн модуля ДЗ под минимализм - Декабрь 2025

**Дата:** 5 декабря 2025  
**Статус:** ✅ Залито на продакшн

## Что сделано

Полностью переработан дизайн конструктора домашних заданий и всех связанных компонентов под минималистичный стиль вкладки "Регулярные занятия".

## Изменённые файлы

### 1. HomeworkConstructor.css
- Цветовая палитра: #111827, #6b7280, #e5e7eb, white
- Border-radius: 8px (кнопки), 12px (карточки)
- Тени: 0 1px 2px rgba(0,0,0,0.05)
- Добавлены унифицированные классы кнопок и форм

### 2. HomeworkPage.css
- Табы в стиле RecurringLessons
- Активный таб: черный фон + белый текст
- Неактивный: светло-серый фон

### 3. SubmissionsList.css
- Минималистичная таблица
- Черные кнопки вместо синих
- Упрощенные бейджи

## Ключевые стили

```css
/* Цвета */
--text-primary: #111827
--text-secondary: #6b7280
--border: #e5e7eb
--background: white / #f9fafb

/* Кнопки */
.gm-btn-primary: черная
.gm-btn-surface: белая с границей
.gm-btn-danger: красная

/* Типографика */
Заголовки: 1.125-1.875rem, weight: 600
Текст: 0.875rem, weight: 400-500
```

## Деплой

```bash
git push origin main
ssh tp "cd /var/www/teaching_panel && sudo git pull origin main"
ssh tp "cd /var/www/teaching_panel/frontend && npm run build"
ssh tp "sudo systemctl restart teaching_panel nginx"
```

**Результат:** ✅ Все сервисы работают, дизайн обновлен на проде.
