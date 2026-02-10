"""
Загрузка начальных данных кодификаторов ФИПИ для ЕГЭ и ОГЭ.

Использование:
    python manage.py seed_fipi_data
    python manage.py seed_fipi_data --exam ege
    python manage.py seed_fipi_data --exam oge
    python manage.py seed_fipi_data --clear  # очистить и перезаписать
"""

from django.core.management.base import BaseCommand
from knowledge_map.models import ExamType, Subject, Section, Topic


# ============================================================
# КОДИФИКАТОРЫ ФИПИ (структура тем)
# Основаны на кодификаторах ФИПИ 2025-2026
# ============================================================

FIPI_DATA = {
    'ege': {
        'name': 'ЕГЭ',
        'description': 'Единый государственный экзамен (11 класс)',
        'subjects': [
            {
                'code': 'math_prof',
                'name': 'Математика (профильный уровень)',
                'icon': 'calculator',
                'color': '#6366f1',
                'max_primary_score': 32,
                'total_tasks': 18,
                'sections': [
                    {
                        'code': 'algebra',
                        'name': 'Алгебра',
                        'topics': [
                            {'code': '1', 'name': 'Целые числа, дроби, рациональные числа', 'task_number': 1, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.1'},
                            {'code': '2', 'name': 'Степени и корни', 'task_number': 4, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.2'},
                            {'code': '3', 'name': 'Логарифмы', 'task_number': 4, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.3'},
                            {'code': '4', 'name': 'Преобразование выражений', 'task_number': 8, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.4'},
                            {'code': '5', 'name': 'Линейные уравнения и неравенства', 'task_number': 1, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.1'},
                            {'code': '6', 'name': 'Квадратные уравнения', 'task_number': 1, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.2'},
                            {'code': '7', 'name': 'Рациональные уравнения и неравенства', 'task_number': 1, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.3'},
                            {'code': '8', 'name': 'Иррациональные уравнения', 'task_number': 12, 'max_score': 2, 'difficulty': 'medium', 'fipi_code': '2.4'},
                            {'code': '9', 'name': 'Показательные уравнения и неравенства', 'task_number': 12, 'max_score': 2, 'difficulty': 'medium', 'fipi_code': '2.5'},
                            {'code': '10', 'name': 'Логарифмические уравнения и неравенства', 'task_number': 14, 'max_score': 2, 'difficulty': 'medium', 'fipi_code': '2.6'},
                            {'code': '11', 'name': 'Системы уравнений', 'task_number': 17, 'max_score': 4, 'difficulty': 'high', 'fipi_code': '2.7'},
                        ],
                    },
                    {
                        'code': 'functions',
                        'name': 'Функции',
                        'topics': [
                            {'code': '12', 'name': 'Линейная, квадратичная, дробно-рациональная функции', 'task_number': 9, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.1'},
                            {'code': '13', 'name': 'Показательная и логарифмическая функции', 'task_number': 9, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.2'},
                            {'code': '14', 'name': 'Тригонометрические функции', 'task_number': 9, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.3'},
                            {'code': '15', 'name': 'Производная функции', 'task_number': 6, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.1'},
                            {'code': '16', 'name': 'Исследование функции с помощью производной', 'task_number': 11, 'max_score': 2, 'difficulty': 'medium', 'fipi_code': '4.2'},
                            {'code': '17', 'name': 'Первообразная и интеграл', 'task_number': 6, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.3'},
                        ],
                    },
                    {
                        'code': 'geometry',
                        'name': 'Геометрия',
                        'topics': [
                            {'code': '18', 'name': 'Планиметрия: треугольники', 'task_number': 3, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '5.1'},
                            {'code': '19', 'name': 'Планиметрия: четырёхугольники', 'task_number': 3, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '5.2'},
                            {'code': '20', 'name': 'Планиметрия: окружность', 'task_number': 3, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '5.3'},
                            {'code': '21', 'name': 'Площади фигур', 'task_number': 3, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '5.4'},
                            {'code': '22', 'name': 'Координаты и векторы на плоскости', 'task_number': 3, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '5.5'},
                            {'code': '23', 'name': 'Стереометрия: призмы, пирамиды', 'task_number': 2, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '6.1'},
                            {'code': '24', 'name': 'Стереометрия: тела вращения', 'task_number': 2, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '6.2'},
                            {'code': '25', 'name': 'Объёмы и площади поверхностей', 'task_number': 2, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '6.3'},
                            {'code': '26', 'name': 'Стереометрическая задача (развёрнутый ответ)', 'task_number': 13, 'max_score': 3, 'difficulty': 'medium', 'fipi_code': '6.4'},
                            {'code': '27', 'name': 'Планиметрическая задача (развёрнутый ответ)', 'task_number': 16, 'max_score': 3, 'difficulty': 'high', 'fipi_code': '5.6'},
                        ],
                    },
                    {
                        'code': 'probability',
                        'name': 'Теория вероятностей и статистика',
                        'topics': [
                            {'code': '28', 'name': 'Классическая вероятность', 'task_number': 5, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '7.1'},
                            {'code': '29', 'name': 'Теоремы о вероятностях событий', 'task_number': 5, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '7.2'},
                            {'code': '30', 'name': 'Случайные величины и распределения', 'task_number': 10, 'max_score': 1, 'difficulty': 'medium', 'fipi_code': '7.3'},
                        ],
                    },
                    {
                        'code': 'word_problems',
                        'name': 'Текстовые задачи и параметры',
                        'topics': [
                            {'code': '31', 'name': 'Текстовые задачи (движение, работа, проценты)', 'task_number': 7, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '8.1'},
                            {'code': '32', 'name': 'Экономические задачи (кредиты, вклады)', 'task_number': 15, 'max_score': 2, 'difficulty': 'medium', 'fipi_code': '8.2'},
                            {'code': '33', 'name': 'Задача с параметром', 'task_number': 17, 'max_score': 4, 'difficulty': 'high', 'fipi_code': '8.3'},
                            {'code': '34', 'name': 'Числа и их свойства (олимпиадная)', 'task_number': 18, 'max_score': 4, 'difficulty': 'high', 'fipi_code': '8.4'},
                        ],
                    },
                ],
            },
            {
                'code': 'russian',
                'name': 'Русский язык',
                'icon': 'book-open',
                'color': '#ec4899',
                'max_primary_score': 50,
                'total_tasks': 27,
                'sections': [
                    {
                        'code': 'text_analysis',
                        'name': 'Работа с текстом',
                        'topics': [
                            {'code': '1', 'name': 'Информационная обработка текстов', 'task_number': 1, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.1'},
                            {'code': '2', 'name': 'Средства связи предложений в тексте', 'task_number': 2, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.2'},
                            {'code': '3', 'name': 'Лексическое значение слова', 'task_number': 3, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.3'},
                        ],
                    },
                    {
                        'code': 'orthography',
                        'name': 'Орфография',
                        'topics': [
                            {'code': '4', 'name': 'Орфоэпические нормы (ударения)', 'task_number': 4, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.1'},
                            {'code': '5', 'name': 'Лексические нормы (паронимы)', 'task_number': 5, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.2'},
                            {'code': '6', 'name': 'Лексические нормы (исправление ошибок)', 'task_number': 6, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.3'},
                            {'code': '7', 'name': 'Морфологические нормы (формы слов)', 'task_number': 7, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.4'},
                            {'code': '8', 'name': 'Синтаксические нормы', 'task_number': 8, 'max_score': 3, 'difficulty': 'medium', 'fipi_code': '2.5'},
                            {'code': '9', 'name': 'Правописание корней', 'task_number': 9, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.1'},
                            {'code': '10', 'name': 'Правописание приставок', 'task_number': 10, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.2'},
                            {'code': '11', 'name': 'Правописание суффиксов', 'task_number': 11, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.3'},
                            {'code': '12', 'name': 'Правописание личных окончаний глаголов', 'task_number': 12, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.4'},
                            {'code': '13', 'name': 'Слитное и раздельное написание НЕ', 'task_number': 13, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.5'},
                            {'code': '14', 'name': 'Слитное, дефисное, раздельное написание', 'task_number': 14, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.6'},
                            {'code': '15', 'name': 'Правописание -Н- и -НН-', 'task_number': 15, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.7'},
                        ],
                    },
                    {
                        'code': 'punctuation',
                        'name': 'Пунктуация',
                        'topics': [
                            {'code': '16', 'name': 'Знаки препинания в простом предложении', 'task_number': 16, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '4.1'},
                            {'code': '17', 'name': 'Знаки препинания при обособлении', 'task_number': 17, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.2'},
                            {'code': '18', 'name': 'Знаки препинания при вводных конструкциях', 'task_number': 18, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.3'},
                            {'code': '19', 'name': 'Знаки препинания в сложноподчинённом предложении', 'task_number': 19, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.4'},
                            {'code': '20', 'name': 'Знаки препинания в сложном предложении с разными видами связи', 'task_number': 20, 'max_score': 1, 'difficulty': 'medium', 'fipi_code': '4.5'},
                            {'code': '21', 'name': 'Пунктуационный анализ', 'task_number': 21, 'max_score': 1, 'difficulty': 'medium', 'fipi_code': '4.6'},
                        ],
                    },
                    {
                        'code': 'speech_analysis',
                        'name': 'Речь. Языковые средства выразительности',
                        'topics': [
                            {'code': '22', 'name': 'Текст как речевое произведение', 'task_number': 22, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '5.1'},
                            {'code': '23', 'name': 'Функционально-смысловые типы речи', 'task_number': 23, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '5.2'},
                            {'code': '24', 'name': 'Лексическое значение слова (синонимы, антонимы)', 'task_number': 24, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '5.3'},
                            {'code': '25', 'name': 'Средства связи предложений в тексте', 'task_number': 25, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '5.4'},
                            {'code': '26', 'name': 'Языковые средства выразительности', 'task_number': 26, 'max_score': 4, 'difficulty': 'medium', 'fipi_code': '5.5'},
                        ],
                    },
                    {
                        'code': 'essay',
                        'name': 'Сочинение',
                        'topics': [
                            {'code': '27', 'name': 'Сочинение-рассуждение (задание 27)', 'task_number': 27, 'max_score': 21, 'difficulty': 'high', 'fipi_code': '6.1'},
                        ],
                    },
                ],
            },
            {
                'code': 'physics',
                'name': 'Физика',
                'icon': 'atom',
                'color': '#f59e0b',
                'max_primary_score': 54,
                'total_tasks': 26,
                'sections': [
                    {
                        'code': 'mechanics',
                        'name': 'Механика',
                        'topics': [
                            {'code': '1', 'name': 'Кинематика', 'task_number': 1, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '1.1'},
                            {'code': '2', 'name': 'Динамика (законы Ньютона)', 'task_number': 2, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '1.2'},
                            {'code': '3', 'name': 'Статика и гидростатика', 'task_number': 3, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.3'},
                            {'code': '4', 'name': 'Законы сохранения в механике', 'task_number': 4, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '1.4'},
                            {'code': '5', 'name': 'Механические колебания и волны', 'task_number': 5, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '1.5'},
                        ],
                    },
                    {
                        'code': 'thermodynamics',
                        'name': 'Молекулярная физика. Термодинамика',
                        'topics': [
                            {'code': '6', 'name': 'МКТ и газовые законы', 'task_number': 8, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '2.1'},
                            {'code': '7', 'name': 'Термодинамика (первый закон)', 'task_number': 9, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '2.2'},
                            {'code': '8', 'name': 'Агрегатные состояния, фазовые переходы', 'task_number': 10, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.3'},
                        ],
                    },
                    {
                        'code': 'electrodynamics',
                        'name': 'Электродинамика',
                        'topics': [
                            {'code': '9', 'name': 'Электростатика', 'task_number': 12, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '3.1'},
                            {'code': '10', 'name': 'Законы постоянного тока', 'task_number': 13, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '3.2'},
                            {'code': '11', 'name': 'Магнитное поле. Электромагнитная индукция', 'task_number': 14, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '3.3'},
                            {'code': '12', 'name': 'Электромагнитные колебания и волны', 'task_number': 15, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '3.4'},
                            {'code': '13', 'name': 'Оптика (геометрическая и волновая)', 'task_number': 16, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '3.5'},
                        ],
                    },
                    {
                        'code': 'quantum',
                        'name': 'Квантовая физика',
                        'topics': [
                            {'code': '14', 'name': 'Фотоэффект, фотоны', 'task_number': 19, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '4.1'},
                            {'code': '15', 'name': 'Атом, ядерная физика', 'task_number': 20, 'max_score': 2, 'difficulty': 'base', 'fipi_code': '4.2'},
                        ],
                    },
                ],
            },
            {
                'code': 'informatics',
                'name': 'Информатика',
                'icon': 'code',
                'color': '#10b981',
                'max_primary_score': 29,
                'total_tasks': 27,
                'sections': [
                    {
                        'code': 'information',
                        'name': 'Информация и её кодирование',
                        'topics': [
                            {'code': '1', 'name': 'Системы счисления', 'task_number': 4, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.1'},
                            {'code': '2', 'name': 'Кодирование и декодирование', 'task_number': 5, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.2'},
                            {'code': '3', 'name': 'Измерение информации', 'task_number': 7, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.3'},
                        ],
                    },
                    {
                        'code': 'logic',
                        'name': 'Логика',
                        'topics': [
                            {'code': '4', 'name': 'Логические выражения и таблицы истинности', 'task_number': 2, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.1'},
                            {'code': '5', 'name': 'Логические уравнения', 'task_number': 15, 'max_score': 1, 'difficulty': 'medium', 'fipi_code': '2.2'},
                        ],
                    },
                    {
                        'code': 'algorithms',
                        'name': 'Алгоритмизация и программирование',
                        'topics': [
                            {'code': '6', 'name': 'Исполнители и алгоритмы', 'task_number': 6, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.1'},
                            {'code': '7', 'name': 'Рекурсивные алгоритмы', 'task_number': 11, 'max_score': 1, 'difficulty': 'medium', 'fipi_code': '3.2'},
                            {'code': '8', 'name': 'Обработка числовых последовательностей', 'task_number': 17, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.3'},
                            {'code': '9', 'name': 'Сортировка и поиск', 'task_number': 25, 'max_score': 2, 'difficulty': 'high', 'fipi_code': '3.4'},
                            {'code': '10', 'name': 'Программирование (анализ программ)', 'task_number': 22, 'max_score': 1, 'difficulty': 'medium', 'fipi_code': '3.5'},
                            {'code': '11', 'name': 'Динамическое программирование', 'task_number': 26, 'max_score': 2, 'difficulty': 'high', 'fipi_code': '3.6'},
                            {'code': '12', 'name': 'Теория игр', 'task_number': 19, 'max_score': 1, 'difficulty': 'medium', 'fipi_code': '3.7'},
                            {'code': '13', 'name': 'Программирование (написание программ)', 'task_number': 27, 'max_score': 2, 'difficulty': 'high', 'fipi_code': '3.8'},
                        ],
                    },
                    {
                        'code': 'data',
                        'name': 'Информационные технологии',
                        'topics': [
                            {'code': '14', 'name': 'Электронные таблицы', 'task_number': 9, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.1'},
                            {'code': '15', 'name': 'Базы данных', 'task_number': 10, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.2'},
                            {'code': '16', 'name': 'Файловые системы', 'task_number': 3, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.3'},
                            {'code': '17', 'name': 'Сети и интернет (IP-адресация)', 'task_number': 12, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.4'},
                            {'code': '18', 'name': 'Графы', 'task_number': 1, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.5'},
                            {'code': '19', 'name': 'Комбинаторика', 'task_number': 8, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.6'},
                        ],
                    },
                ],
            },
            {
                'code': 'english',
                'name': 'Английский язык',
                'icon': 'languages',
                'color': '#3b82f6',
                'max_primary_score': 86,
                'total_tasks': 38,
                'sections': [
                    {
                        'code': 'listening',
                        'name': 'Аудирование',
                        'topics': [
                            {'code': '1', 'name': 'Понимание основного содержания (задание 1)', 'task_number': 1, 'max_score': 3, 'difficulty': 'base', 'fipi_code': '1.1'},
                            {'code': '2', 'name': 'Понимание запрашиваемой информации (задание 2)', 'task_number': 2, 'max_score': 4, 'difficulty': 'base', 'fipi_code': '1.2'},
                            {'code': '3', 'name': 'Полное понимание (задания 3-9)', 'task_number': 3, 'max_score': 7, 'difficulty': 'medium', 'fipi_code': '1.3'},
                        ],
                    },
                    {
                        'code': 'reading',
                        'name': 'Чтение',
                        'topics': [
                            {'code': '4', 'name': 'Понимание основного содержания текста (задание 10)', 'task_number': 10, 'max_score': 4, 'difficulty': 'base', 'fipi_code': '2.1'},
                            {'code': '5', 'name': 'Понимание структурно-смысловых связей (задание 11)', 'task_number': 11, 'max_score': 6, 'difficulty': 'base', 'fipi_code': '2.2'},
                            {'code': '6', 'name': 'Полное понимание информации (задания 12-18)', 'task_number': 12, 'max_score': 7, 'difficulty': 'medium', 'fipi_code': '2.3'},
                        ],
                    },
                    {
                        'code': 'grammar_vocabulary',
                        'name': 'Грамматика и лексика',
                        'topics': [
                            {'code': '7', 'name': 'Грамматические формы (задания 19-25)', 'task_number': 19, 'max_score': 7, 'difficulty': 'base', 'fipi_code': '3.1'},
                            {'code': '8', 'name': 'Словообразование (задания 26-31)', 'task_number': 26, 'max_score': 6, 'difficulty': 'base', 'fipi_code': '3.2'},
                            {'code': '9', 'name': 'Лексическая сочетаемость (задания 32-38)', 'task_number': 32, 'max_score': 7, 'difficulty': 'medium', 'fipi_code': '3.3'},
                        ],
                    },
                    {
                        'code': 'writing',
                        'name': 'Письменная речь',
                        'topics': [
                            {'code': '10', 'name': 'Электронное письмо (задание 37)', 'task_number': 37, 'max_score': 6, 'difficulty': 'base', 'fipi_code': '4.1'},
                            {'code': '11', 'name': 'Развёрнутое письменное высказывание (задание 38)', 'task_number': 38, 'max_score': 14, 'difficulty': 'high', 'fipi_code': '4.2'},
                        ],
                    },
                    {
                        'code': 'speaking',
                        'name': 'Устная часть',
                        'topics': [
                            {'code': '12', 'name': 'Чтение вслух', 'task_number': None, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '5.1'},
                            {'code': '13', 'name': 'Условный диалог-расспрос', 'task_number': None, 'max_score': 4, 'difficulty': 'base', 'fipi_code': '5.2'},
                            {'code': '14', 'name': 'Тематическое монологическое высказывание с опорой', 'task_number': None, 'max_score': 10, 'difficulty': 'medium', 'fipi_code': '5.3'},
                        ],
                    },
                ],
            },
        ],
    },
    'oge': {
        'name': 'ОГЭ',
        'description': 'Основной государственный экзамен (9 класс)',
        'subjects': [
            {
                'code': 'math',
                'name': 'Математика',
                'icon': 'calculator',
                'color': '#6366f1',
                'max_primary_score': 31,
                'total_tasks': 25,
                'sections': [
                    {
                        'code': 'algebra_oge',
                        'name': 'Алгебра',
                        'topics': [
                            {'code': '1', 'name': 'Числа и вычисления', 'task_number': 1, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.1'},
                            {'code': '2', 'name': 'Числовые неравенства и координатная прямая', 'task_number': 2, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '1.2'},
                            {'code': '3', 'name': 'Алгебраические выражения', 'task_number': 4, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.1'},
                            {'code': '4', 'name': 'Уравнения и системы уравнений', 'task_number': 5, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.2'},
                            {'code': '5', 'name': 'Неравенства', 'task_number': 6, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.3'},
                            {'code': '6', 'name': 'Функции и графики', 'task_number': 7, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.1'},
                            {'code': '7', 'name': 'Арифметические и геометрические прогрессии', 'task_number': 8, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.2'},
                            {'code': '8', 'name': 'Статистика и теория вероятностей', 'task_number': 9, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.1'},
                            {'code': '9', 'name': 'Практические задачи (таблицы, графики)', 'task_number': 3, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '4.2'},
                            {'code': '10', 'name': 'Текстовая задача (система уравнений)', 'task_number': 21, 'max_score': 2, 'difficulty': 'medium', 'fipi_code': '5.1'},
                            {'code': '11', 'name': 'Уравнения и неравенства повышенной сложности', 'task_number': 22, 'max_score': 2, 'difficulty': 'medium', 'fipi_code': '5.2'},
                            {'code': '12', 'name': 'Построение графиков функций', 'task_number': 23, 'max_score': 2, 'difficulty': 'high', 'fipi_code': '5.3'},
                        ],
                    },
                    {
                        'code': 'geometry_oge',
                        'name': 'Геометрия',
                        'topics': [
                            {'code': '13', 'name': 'Треугольники и их свойства', 'task_number': 15, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '6.1'},
                            {'code': '14', 'name': 'Четырёхугольники', 'task_number': 16, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '6.2'},
                            {'code': '15', 'name': 'Окружность, вписанные и описанные фигуры', 'task_number': 17, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '6.3'},
                            {'code': '16', 'name': 'Площади фигур', 'task_number': 18, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '6.4'},
                            {'code': '17', 'name': 'Координаты и векторы', 'task_number': 19, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '6.5'},
                            {'code': '18', 'name': 'Геометрическая задача на вычисление', 'task_number': 24, 'max_score': 2, 'difficulty': 'medium', 'fipi_code': '7.1'},
                            {'code': '19', 'name': 'Геометрическая задача на доказательство', 'task_number': 25, 'max_score': 2, 'difficulty': 'high', 'fipi_code': '7.2'},
                        ],
                    },
                    {
                        'code': 'practical_oge',
                        'name': 'Практико-ориентированные задачи',
                        'topics': [
                            {'code': '20', 'name': 'Задачи на участки, планы, схемы', 'task_number': 10, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '8.1'},
                            {'code': '21', 'name': 'Задачи на тарифы и расчёты', 'task_number': 11, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '8.2'},
                            {'code': '22', 'name': 'Задачи на листы/шины/плитку', 'task_number': 12, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '8.3'},
                            {'code': '23', 'name': 'Задачи на формулы и процессы', 'task_number': 13, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '8.4'},
                            {'code': '24', 'name': 'Комплексная практическая задача', 'task_number': 14, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '8.5'},
                        ],
                    },
                ],
            },
            {
                'code': 'russian_oge',
                'name': 'Русский язык',
                'icon': 'book-open',
                'color': '#ec4899',
                'max_primary_score': 33,
                'total_tasks': 9,
                'sections': [
                    {
                        'code': 'izlozhenie',
                        'name': 'Изложение',
                        'topics': [
                            {'code': '1', 'name': 'Сжатое изложение', 'task_number': 1, 'max_score': 7, 'difficulty': 'medium', 'fipi_code': '1.1'},
                        ],
                    },
                    {
                        'code': 'test_part',
                        'name': 'Тестовая часть',
                        'topics': [
                            {'code': '2', 'name': 'Синтаксический анализ (грамматическая основа)', 'task_number': 2, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.1'},
                            {'code': '3', 'name': 'Пунктуационный анализ', 'task_number': 3, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.2'},
                            {'code': '4', 'name': 'Синтаксический анализ (словосочетание)', 'task_number': 4, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.3'},
                            {'code': '5', 'name': 'Орфографический анализ', 'task_number': 5, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '2.4'},
                            {'code': '6', 'name': 'Анализ содержания текста', 'task_number': 6, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.1'},
                            {'code': '7', 'name': 'Анализ средств выразительности', 'task_number': 7, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.2'},
                            {'code': '8', 'name': 'Лексический анализ', 'task_number': 8, 'max_score': 1, 'difficulty': 'base', 'fipi_code': '3.3'},
                        ],
                    },
                    {
                        'code': 'sochinenie_oge',
                        'name': 'Сочинение',
                        'topics': [
                            {'code': '9', 'name': 'Сочинение-рассуждение (9.1 / 9.2 / 9.3)', 'task_number': 9, 'max_score': 9, 'difficulty': 'high', 'fipi_code': '4.1'},
                        ],
                    },
                ],
            },
        ],
    },
}


class Command(BaseCommand):
    help = 'Загрузить начальные данные кодификаторов ФИПИ (ЕГЭ/ОГЭ)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exam', type=str, default='all',
            help='ege, oge или all (по умолчанию all)'
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='Удалить все данные перед загрузкой'
        )

    def handle(self, *args, **options):
        exam_filter = options['exam']
        clear = options['clear']

        if clear:
            self.stdout.write(self.style.WARNING('Удаляю старые данные...'))
            Topic.objects.all().delete()
            Section.objects.all().delete()
            Subject.objects.all().delete()
            ExamType.objects.all().delete()

        exams_to_load = []
        if exam_filter in ('all', 'ege'):
            exams_to_load.append('ege')
        if exam_filter in ('all', 'oge'):
            exams_to_load.append('oge')

        for exam_code in exams_to_load:
            data = FIPI_DATA[exam_code]
            exam_type, created = ExamType.objects.get_or_create(
                code=exam_code,
                defaults={
                    'name': data['name'],
                    'description': data['description'],
                }
            )
            verb = 'Создан' if created else 'Существует'
            self.stdout.write(f'  {verb}: {exam_type}')

            for s_order, s_data in enumerate(data['subjects'], 1):
                subject, created = Subject.objects.update_or_create(
                    exam_type=exam_type,
                    code=s_data['code'],
                    defaults={
                        'name': s_data['name'],
                        'icon': s_data.get('icon', ''),
                        'color': s_data.get('color', '#6366f1'),
                        'max_primary_score': s_data.get('max_primary_score', 0),
                        'total_tasks': s_data.get('total_tasks', 0),
                        'order': s_order,
                    }
                )
                self.stdout.write(f'    {"+" if created else "~"} Предмет: {subject.name}')

                for sec_order, sec_data in enumerate(s_data['sections'], 1):
                    section, created = Section.objects.update_or_create(
                        subject=subject,
                        code=sec_data['code'],
                        defaults={
                            'name': sec_data['name'],
                            'description': sec_data.get('description', ''),
                            'order': sec_order,
                        }
                    )

                    for t_order, t_data in enumerate(sec_data['topics'], 1):
                        Topic.objects.update_or_create(
                            section=section,
                            code=t_data['code'],
                            defaults={
                                'name': t_data['name'],
                                'task_number': t_data.get('task_number'),
                                'max_score': t_data.get('max_score', 1),
                                'difficulty': t_data.get('difficulty', 'base'),
                                'fipi_code': t_data.get('fipi_code', ''),
                                'order': t_order,
                            }
                        )

                    topic_count = len(sec_data['topics'])
                    self.stdout.write(f'      {"+" if created else "~"} {section.name} ({topic_count} тем)')

        total_topics = Topic.objects.count()
        total_subjects = Subject.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\nГотово! Загружено: {total_subjects} предметов, {total_topics} тем.'
        ))
