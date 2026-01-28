"""
Клавиатуры для бота - общие элементы
"""
from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def back_button(callback_data: str = 'menu:root', text: str = '⬅️ Назад') -> InlineKeyboardButton:
    """Кнопка "Назад\""""
    return InlineKeyboardButton(text, callback_data=callback_data)


def cancel_button(callback_data: str = 'cancel', text: str = '❌ Отмена') -> InlineKeyboardButton:
    """Кнопка "Отмена\""""
    return InlineKeyboardButton(text, callback_data=callback_data)


def confirm_button(callback_data: str = 'confirm', text: str = '✅ Подтвердить') -> InlineKeyboardButton:
    """Кнопка "Подтвердить\""""
    return InlineKeyboardButton(text, callback_data=callback_data)


def main_menu_keyboard(is_teacher: bool = False) -> InlineKeyboardMarkup:
    """Главное меню"""
    if is_teacher:
        rows = [
            [
                InlineKeyboardButton('📅 Уроки', callback_data='menu:lessons'),
                InlineKeyboardButton('📝 Домашки', callback_data='menu:homework'),
            ],
            [
                InlineKeyboardButton('📣 Рассылка', callback_data='menu:broadcast'),
                InlineKeyboardButton('⏰ Запланированные', callback_data='menu:scheduled'),
            ],
            [
                InlineKeyboardButton('🔔 Уведомления', callback_data='menu:notifications'),
                InlineKeyboardButton('👤 Профиль', callback_data='menu:profile'),
            ],
            [InlineKeyboardButton('❓ Помощь', callback_data='menu:help')],
        ]
    else:
        rows = [
            [
                InlineKeyboardButton('📅 Мои уроки', callback_data='menu:my_lessons'),
                InlineKeyboardButton('📝 Мои ДЗ', callback_data='menu:my_homework'),
            ],
            [
                InlineKeyboardButton('📊 Мой прогресс', callback_data='menu:progress'),
            ],
            [
                InlineKeyboardButton('🔔 Уведомления', callback_data='menu:notifications'),
                InlineKeyboardButton('👤 Профиль', callback_data='menu:profile'),
            ],
            [InlineKeyboardButton('❓ Помощь', callback_data='menu:help')],
        ]
    
    return InlineKeyboardMarkup(rows)


def section_keyboard(
    section: str,
    include_refresh: bool = True,
    back_to: str = 'menu:root'
) -> InlineKeyboardMarkup:
    """Клавиатура раздела с кнопками Обновить и Назад"""
    rows = []
    if include_refresh:
        rows.append([InlineKeyboardButton('🔄 Обновить', callback_data=f'menu:{section}')])
    rows.append([back_button(back_to)])
    return InlineKeyboardMarkup(rows)


def confirmation_keyboard(
    confirm_callback: str,
    cancel_callback: str = 'cancel',
    confirm_text: str = '✅ Да',
    cancel_text: str = '❌ Нет',
) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(confirm_text, callback_data=confirm_callback),
            InlineKeyboardButton(cancel_text, callback_data=cancel_callback),
        ]
    ])


def pagination_keyboard(
    items: List,
    current_page: int,
    items_per_page: int,
    callback_prefix: str,
    back_callback: str = 'menu:root',
) -> InlineKeyboardMarkup:
    """Клавиатура с пагинацией"""
    total_pages = (len(items) + items_per_page - 1) // items_per_page
    
    rows = []
    
    # Навигация
    nav_row = []
    if current_page > 0:
        nav_row.append(InlineKeyboardButton('◀️', callback_data=f'{callback_prefix}:page:{current_page - 1}'))
    
    nav_row.append(InlineKeyboardButton(f'{current_page + 1}/{total_pages}', callback_data='noop'))
    
    if current_page < total_pages - 1:
        nav_row.append(InlineKeyboardButton('▶️', callback_data=f'{callback_prefix}:page:{current_page + 1}'))
    
    if nav_row:
        rows.append(nav_row)
    
    rows.append([back_button(back_callback)])
    
    return InlineKeyboardMarkup(rows)


def time_selector_keyboard(callback_prefix: str, back_callback: str = 'cancel') -> InlineKeyboardMarkup:
    """Клавиатура выбора времени отправки"""
    rows = [
        [InlineKeyboardButton('🚀 Сейчас', callback_data=f'{callback_prefix}:now')],
        [
            InlineKeyboardButton('15 мин', callback_data=f'{callback_prefix}:15min'),
            InlineKeyboardButton('30 мин', callback_data=f'{callback_prefix}:30min'),
            InlineKeyboardButton('1 час', callback_data=f'{callback_prefix}:1hour'),
        ],
        [
            InlineKeyboardButton('2 часа', callback_data=f'{callback_prefix}:2hours'),
            InlineKeyboardButton('3 часа', callback_data=f'{callback_prefix}:3hours'),
        ],
        [
            InlineKeyboardButton('Завтра 9:00', callback_data=f'{callback_prefix}:tomorrow_9'),
            InlineKeyboardButton('Завтра 18:00', callback_data=f'{callback_prefix}:tomorrow_18'),
        ],
        [cancel_button(back_callback)],
    ]
    return InlineKeyboardMarkup(rows)
