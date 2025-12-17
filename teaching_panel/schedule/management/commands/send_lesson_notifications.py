"""
Management command для отправки Telegram-уведомлений о начале уроков.

Запуск:
    python manage.py send_lesson_notifications

Для cron (каждую минуту):
    * * * * * cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py send_lesson_notifications >> /var/log/lesson_notifications.log 2>&1
"""

import os
import logging
from datetime import datetime, timedelta, date, time as dt_time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

import requests

from schedule.models import RecurringLesson, LessonNotificationLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Отправить Telegram-уведомления о начале уроков'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет отправлено, но не отправлять',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Подробный вывод',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        if not bot_token and not dry_run:
            self.stderr.write('TELEGRAM_BOT_TOKEN не установлен')
            return

        now = timezone.localtime()
        today = now.date()
        current_weekday = today.weekday()  # 0 = Monday

        if verbose:
            self.stdout.write(f"Текущее время: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            self.stdout.write(f"День недели: {current_weekday}")

        # 1. Напоминания о начале урока
        self._process_reminders(bot_token, now, today, current_weekday, dry_run, verbose)
        
        # 2. Анонсы (утром в день урока)
        self._process_announces(bot_token, now, today, current_weekday, dry_run, verbose)

    def _process_reminders(self, bot_token, now, today, current_weekday, dry_run, verbose):
        """Обработка напоминаний за N минут до начала урока"""
        
        # Находим уроки с включёнными уведомлениями на сегодня
        lessons = RecurringLesson.objects.filter(
            telegram_notify_enabled=True,
            day_of_week=current_weekday,
            start_date__lte=today,
            end_date__gte=today,
        ).select_related('teacher', 'group')

        for rl in lessons:
            # Проверяем тип недели (ALL / UPPER / LOWER)
            if not self._matches_week_type(rl.week_type, today, rl.start_date):
                continue

            # Вычисляем время напоминания
            lesson_start = timezone.make_aware(
                datetime.combine(today, rl.start_time),
                timezone.get_current_timezone()
            )
            notify_at = lesson_start - timedelta(minutes=rl.telegram_notify_minutes)
            
            # Проверяем, попадает ли текущее время в окно отправки (±1 минута)
            time_diff = (now - notify_at).total_seconds()
            if not (-30 <= time_diff <= 90):
                # Не пора ещё или уже прошло
                continue

            # Проверяем, не отправляли ли уже
            already_sent = LessonNotificationLog.objects.filter(
                recurring_lesson=rl,
                notification_type='reminder',
                lesson_date=today
            ).exists()

            if already_sent:
                if verbose:
                    self.stdout.write(f"  [SKIP] {rl.title} - уже отправлено")
                continue

            # Формируем сообщение
            message = self._build_reminder_message(rl, today)
            
            if verbose or dry_run:
                self.stdout.write(f"\n{'[DRY-RUN] ' if dry_run else ''}Отправка напоминания:")
                self.stdout.write(f"  Урок: {rl.title}")
                self.stdout.write(f"  Группа: {rl.group.name}")
                self.stdout.write(f"  Время: {rl.start_time}")
                self.stdout.write(f"  За минут: {rl.telegram_notify_minutes}")

            if dry_run:
                continue

            # Отправляем
            recipients_count = 0
            error_message = ''
            
            try:
                recipients_count = self._send_notification(
                    bot_token, rl, message, verbose
                )
            except Exception as e:
                error_message = str(e)
                logger.exception(f"Ошибка отправки уведомления для {rl.title}")

            # Записываем в лог
            with transaction.atomic():
                LessonNotificationLog.objects.create(
                    recurring_lesson=rl,
                    notification_type='reminder',
                    lesson_date=today,
                    recipients_count=recipients_count,
                    error_message=error_message
                )

            if verbose:
                status = '✓' if not error_message else f'✗ {error_message}'
                self.stdout.write(f"  Результат: {status} (получателей: {recipients_count})")

    def _process_announces(self, bot_token, now, today, current_weekday, dry_run, verbose):
        """Обработка анонсов (утром в день урока)"""
        
        lessons = RecurringLesson.objects.filter(
            telegram_notify_enabled=True,
            telegram_announce_enabled=True,
            telegram_announce_time__isnull=False,
            day_of_week=current_weekday,
            start_date__lte=today,
            end_date__gte=today,
        ).select_related('teacher', 'group')

        for rl in lessons:
            if not self._matches_week_type(rl.week_type, today, rl.start_date):
                continue

            # Время анонса
            announce_at = timezone.make_aware(
                datetime.combine(today, rl.telegram_announce_time),
                timezone.get_current_timezone()
            )
            
            time_diff = (now - announce_at).total_seconds()
            if not (-30 <= time_diff <= 90):
                continue

            already_sent = LessonNotificationLog.objects.filter(
                recurring_lesson=rl,
                notification_type='announce',
                lesson_date=today
            ).exists()

            if already_sent:
                continue

            message = self._build_announce_message(rl, today)
            
            if verbose or dry_run:
                self.stdout.write(f"\n{'[DRY-RUN] ' if dry_run else ''}Отправка анонса:")
                self.stdout.write(f"  Урок: {rl.title}")

            if dry_run:
                continue

            recipients_count = 0
            error_message = ''
            
            try:
                recipients_count = self._send_notification(
                    bot_token, rl, message, verbose
                )
            except Exception as e:
                error_message = str(e)

            with transaction.atomic():
                LessonNotificationLog.objects.create(
                    recurring_lesson=rl,
                    notification_type='announce',
                    lesson_date=today,
                    recipients_count=recipients_count,
                    error_message=error_message
                )

    def _matches_week_type(self, week_type, current_date, start_date):
        """Проверить, подходит ли текущая неделя под тип (ALL/UPPER/LOWER)"""
        if week_type == 'ALL':
            return True
        
        # Считаем номер недели от start_date
        days_diff = (current_date - start_date).days
        week_number = (days_diff // 7) % 2  # 0 = UPPER, 1 = LOWER
        
        if week_type == 'UPPER':
            return week_number == 0
        elif week_type == 'LOWER':
            return week_number == 1
        
        return True

    def _build_reminder_message(self, rl, lesson_date):
        """Построить текст напоминания"""
        teacher_name = rl.teacher.get_full_name() if rl.teacher else 'Преподаватель'
        pmi_link = getattr(rl.teacher, 'zoom_pmi_link', '') if rl.teacher else ''
        
        start_str = rl.start_time.strftime('%H:%M')
        end_str = rl.end_time.strftime('%H:%M')
        
        lines = [
            f"🔔 *Урок начнётся через {rl.telegram_notify_minutes} минут!*",
            "",
            f"📚 {rl.title} — {rl.group.name}",
            f"⏰ {start_str} – {end_str}",
            f"👨‍🏫 {teacher_name}",
        ]
        
        if pmi_link:
            lines.append("")
            lines.append(f"🔗 [Подключиться к Zoom]({pmi_link})")
        
        return "\n".join(lines)

    def _build_announce_message(self, rl, lesson_date):
        """Построить текст анонса"""
        teacher_name = rl.teacher.get_full_name() if rl.teacher else 'Преподаватель'
        pmi_link = getattr(rl.teacher, 'zoom_pmi_link', '') if rl.teacher else ''
        
        start_str = rl.start_time.strftime('%H:%M')
        end_str = rl.end_time.strftime('%H:%M')
        
        lines = [
            f"📣 *Сегодня урок!*",
            "",
            f"📚 {rl.title} — {rl.group.name}",
            f"⏰ {start_str} – {end_str}",
            f"👨‍🏫 {teacher_name}",
        ]
        
        if pmi_link:
            lines.append("")
            lines.append(f"🔗 Ссылка: {pmi_link}")
        
        return "\n".join(lines)

    def _send_notification(self, bot_token, rl, message, verbose=False):
        """Отправить уведомление в Telegram"""
        recipients_count = 0
        
        # 1. Отправка в группу
        if rl.telegram_notify_to_group and rl.telegram_group_chat_id:
            chat_id = rl.telegram_group_chat_id.strip()
            if chat_id:
                success = self._send_telegram_message(bot_token, chat_id, message)
                if success:
                    recipients_count += 1
                    if verbose:
                        self.stdout.write(f"    → Группа {chat_id}: ✓")
                else:
                    if verbose:
                        self.stdout.write(f"    → Группа {chat_id}: ✗")

        # 2. Отправка ученикам в личку
        if rl.telegram_notify_to_students:
            students = rl.group.students.filter(
                telegram_id__isnull=False,
                telegram_verified=True
            ).exclude(telegram_id='')
            
            for student in students:
                chat_id = student.telegram_id.strip()
                if chat_id:
                    success = self._send_telegram_message(bot_token, chat_id, message)
                    if success:
                        recipients_count += 1
                        if verbose:
                            self.stdout.write(f"    → {student.email}: ✓")
                    else:
                        if verbose:
                            self.stdout.write(f"    → {student.email}: ✗")

        return recipients_count

    def _send_telegram_message(self, bot_token, chat_id, text):
        """Отправить сообщение через Telegram Bot API"""
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False,
            }
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ошибка отправки в {chat_id}: {e}")
            return False
