#!/usr/bin/env python3
"""
Скрипт для массовой замены старых цветов на новые Premium Minimalist переменные
"""
import os
import re
from pathlib import Path

# Карта замен: старый цвет -> новая переменная
COLOR_REPLACEMENTS = {
    # Старые синие на Indigo
    '#1e3a8a': 'var(--color-primary)',
    '#0c1e3a': 'var(--color-primary-dark)',
    '#1e40af': 'var(--color-primary)',
    '#0369a1': 'var(--color-primary-dark)',
    
    # Фоны
    '#f9fafb': 'var(--bg-app)',
    '#f8fafc': 'var(--bg-app)',
    '#f3f4f6': 'var(--bg-surface)',
    '#f1f5f9': 'var(--bg-surface)',
    '#e5e7eb': 'var(--border-light)',
    '#d1d5db': 'var(--border-medium)',
    '#ffffff': 'var(--bg-paper)',
    
    # Текст
    '#111827': 'var(--text-main)',
    '#374151': 'var(--text-main)',
    '#1e293b': 'var(--text-main)',
    '#0f172a': 'var(--text-main)',
    '#6b7280': 'var(--text-muted)',
    '#64748b': 'var(--text-muted)',
    '#94a3b8': 'var(--text-light)',
    '#9ca3af': 'var(--text-light)',
    '#334155': 'var(--text-main)',
    '#475569': 'var(--text-muted)',
    
    # Ошибки
    '#ef4444': 'var(--color-error)',
    '#dc2626': 'var(--color-error)',
    '#991b1b': 'var(--color-error)',
    '#b91c1c': 'var(--color-error)',
    '#c62828': 'var(--color-error)',
    '#fee2e2': 'var(--color-error-light)',
    '#fef2f2': 'var(--color-error-light)',
    '#fecaca': 'var(--color-error-light)',
    
    # Успех
    '#10b981': 'var(--color-success)',
    '#059669': 'var(--color-success)',
    '#065f46': 'var(--color-success)',
    '#16a34a': 'var(--color-success)',
    '#2e7d32': 'var(--color-success)',
    '#15803d': 'var(--color-success)',
    '#d1fae5': 'var(--color-success-light)',
    '#e8f5e9': 'var(--color-success-light)',
    '#f0fdf4': 'var(--color-success-light)',
    
    # Предупреждения
    '#f59e0b': 'var(--color-warning)',
    '#d97706': 'var(--color-warning)',
    '#92400e': 'var(--color-warning)',
    '#e65100': 'var(--color-warning)',
    '#fef3c7': 'var(--color-warning-light)',
    '#fff3e0': 'var(--color-warning-light)',
    
    # Indigo палитра
    '#4f46e5': 'var(--color-primary)',
    '#4338ca': 'var(--color-primary-dark)',
    '#6366f1': 'var(--color-primary-light)',
    '#818cf8': 'var(--color-primary-light)',
    '#e0e7ff': 'var(--color-primary-subtle)',
    '#eef2ff': 'var(--color-primary-subtle)',
    '#c7d2fe': 'var(--color-primary-subtle)',
    '#3730a3': 'var(--color-primary-dark)',
    
    # Другие
    '#cbd5e1': 'var(--border-light)',
    '#e2e8f0': 'var(--border-light)',
    '#bae6fd': 'var(--color-primary-subtle)',
    '#dbeafe': 'var(--color-info-light)',
    '#eff6ff': 'var(--color-primary-subtle)',
    '#3b82f6': 'var(--color-info)',
    '#2563eb': 'var(--color-info)',
    '#1d4ed8': 'var(--color-primary)',
}

def replace_colors_in_file(file_path):
    """Заменяет цвета в файле"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = False
        
        # Замена цветов (case-insensitive)
        for old_color, new_var in COLOR_REPLACEMENTS.items():
            # Ищем цвет в разных форматах: #abc, #ABC, с пробелами и без
            pattern = re.compile(re.escape(old_color), re.IGNORECASE)
            if pattern.search(content):
                content = pattern.sub(new_var, content)
                changes_made = True
        
        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Updated: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False

def main():
    frontend_path = Path(__file__).parent / 'frontend' / 'src'
    
    # Исключаем design-system.css (там определения переменных)
    exclude_files = {'design-system.css'}
    
    updated_count = 0
    total_count = 0
    
    # Обходим все CSS файлы
    for css_file in frontend_path.rglob('*.css'):
        if css_file.name not in exclude_files:
            total_count += 1
            if replace_colors_in_file(css_file):
                updated_count += 1
    
    print(f"\n{'='*60}")
    print(f"Обработано файлов: {total_count}")
    print(f"Обновлено файлов: {updated_count}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
