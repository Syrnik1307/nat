"""
Шкалы перевода баллов ФИПИ и предзаполненные шаблоны экзаменов.

Используется для:
1. Предзаполнения ExamBlueprint при создании
2. Management command для загрузки шаблонов
"""

# =============================================================================
# Шкалы перевода первичных → тестовые баллы ЕГЭ 2025/2026
# Источник: ФИПИ / Рособрнадзор
# Формат: {первичный: тестовый}
# =============================================================================

SCORE_SCALES = {
    'ege_informatics_2026': {
        '0': 0, '1': 7, '2': 14, '3': 20, '4': 27, '5': 34,
        '6': 40, '7': 42, '8': 44, '9': 46, '10': 48,
        '11': 50, '12': 52, '13': 54, '14': 56, '15': 58,
        '16': 60, '17': 62, '18': 64, '19': 66, '20': 68,
        '21': 70, '22': 72, '23': 74, '24': 76, '25': 78,
        '26': 82, '27': 86, '28': 94, '29': 100,
    },
    'ege_math_prof_2026': {
        '0': 0, '1': 6, '2': 11, '3': 17, '4': 22, '5': 27,
        '6': 34, '7': 40, '8': 46, '9': 52, '10': 58,
        '11': 62, '12': 64, '13': 66, '14': 68, '15': 70,
        '16': 72, '17': 74, '18': 76, '19': 78, '20': 80,
        '21': 82, '22': 84, '23': 86, '24': 88, '25': 90,
        '26': 92, '27': 94, '28': 96, '29': 98, '30': 100,
        '31': 100, '32': 100,
    },
    'ege_russian_2026': {
        '0': 0, '1': 3, '2': 5, '3': 8, '4': 10, '5': 12,
        '6': 15, '7': 17, '8': 20, '9': 22, '10': 24,
        '11': 26, '12': 28, '13': 30, '14': 32, '15': 34,
        '16': 36, '17': 38, '18': 39, '19': 40, '20': 41,
        '21': 42, '22': 43, '23': 44, '24': 45, '25': 46,
        '26': 47, '27': 48, '28': 49, '29': 50, '30': 51,
        '31': 52, '32': 53, '33': 54, '34': 55, '35': 56,
        '36': 57, '37': 58, '38': 59, '39': 60, '40': 61,
        '41': 62, '42': 63, '43': 64, '44': 65, '45': 66,
        '46': 67, '47': 68, '48': 69, '49': 70, '50': 71,
        '51': 73, '52': 75, '53': 77, '54': 79, '55': 81,
        '56': 83, '57': 85, '58': 88, '59': 91, '60': 94,
        '61': 97, '62': 100,
    },
    'ege_physics_2026': {
        '0': 0, '1': 4, '2': 7, '3': 10, '4': 14, '5': 17,
        '6': 20, '7': 23, '8': 27, '9': 30, '10': 33,
        '11': 36, '12': 38, '13': 39, '14': 40, '15': 41,
        '16': 42, '17': 44, '18': 45, '19': 46, '20': 47,
        '21': 48, '22': 49, '23': 51, '24': 52, '25': 53,
        '26': 54, '27': 55, '28': 57, '29': 58, '30': 59,
        '31': 60, '32': 61, '33': 62, '34': 64, '35': 66,
        '36': 68, '37': 70, '38': 72, '39': 74, '40': 76,
        '41': 78, '42': 80, '43': 82, '44': 84, '45': 87,
        '46': 89, '47': 92, '48': 94, '49': 97, '50': 100,
    },
    'ege_english_2026': {
        '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
        '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
        '11': 11, '12': 12, '13': 13, '14': 14, '15': 15,
        '16': 16, '17': 17, '18': 18, '19': 19, '20': 20,
        '21': 21, '22': 22, '23': 23, '24': 24, '25': 25,
        '26': 26, '27': 27, '28': 28, '29': 29, '30': 30,
        '31': 31, '32': 32, '33': 33, '34': 34, '35': 35,
        '36': 36, '37': 37, '38': 38, '39': 39, '40': 40,
        '41': 41, '42': 42, '43': 43, '44': 44, '45': 45,
        '46': 46, '47': 47, '48': 48, '49': 49, '50': 50,
        '51': 51, '52': 52, '53': 53, '54': 54, '55': 55,
        '56': 56, '57': 57, '58': 58, '59': 59, '60': 60,
        '61': 61, '62': 62, '63': 63, '64': 64, '65': 65,
        '66': 66, '67': 67, '68': 68, '69': 69, '70': 70,
        '71': 71, '72': 72, '73': 73, '74': 74, '75': 75,
        '76': 76, '77': 77, '78': 78, '79': 79, '80': 80,
        '81': 81, '82': 82, '83': 83, '84': 84, '85': 85,
        '86': 90, '87': 93, '88': 95, '89': 97, '90': 99,
        '91': 100, '92': 100, '93': 100, '94': 100, '95': 100,
        '96': 100, '97': 100, '98': 100, '99': 100, '100': 100,
    },
}

# =============================================================================
# Пороги оценок (минимальный тестовый балл для оценки)
# =============================================================================

GRADE_THRESHOLDS = {
    'ege_informatics': {'2': 0, '3': 40, '4': 57, '5': 72},
    'ege_math_prof': {'2': 0, '3': 27, '4': 50, '5': 68},
    'ege_russian': {'2': 0, '3': 36, '4': 57, '5': 72},
    'ege_physics': {'2': 0, '3': 36, '4': 53, '5': 68},
    'ege_english': {'2': 0, '3': 22, '4': 58, '5': 84},
    'oge_default': {'2': 0, '3': 0, '4': 0, '5': 0},  # ОГЭ использует другие пороги
}


# =============================================================================
# Шаблоны структуры экзаменов (слоты заданий)
# =============================================================================

EXAM_STRUCTURES = {
    'ege_informatics_2026': {
        'title': 'ЕГЭ Информатика 2026',
        'exam_type': 'ege',
        'subject_code': 'informatics',
        'duration_minutes': 235,
        'total_primary_score': 29,
        'tasks': [
            {'task_number': 1, 'title': 'Анализ информационных моделей', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 2, 'title': 'Построение таблиц истинности', 'answer_type': 'short_text', 'max_points': 1},
            {'task_number': 3, 'title': 'Базы данных. SQL-запросы', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 4, 'title': 'Кодирование и декодирование', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 5, 'title': 'Анализ алгоритмов', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 6, 'title': 'Определение результата программы', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 7, 'title': 'Кодирование графики и звука', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 8, 'title': 'Комбинаторика', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 9, 'title': 'Обработка данных в электронных таблицах', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 10, 'title': 'Поиск информации в текстовом файле', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 11, 'title': 'Рекурсивные алгоритмы', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 12, 'title': 'Организация компьютерных сетей. IP-адреса', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 13, 'title': 'Вычисление количества информации', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 14, 'title': 'Системы счисления', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 15, 'title': 'Преобразование логических выражений', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 16, 'title': 'Рекурсивные алгоритмы (повышенный)', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 17, 'title': 'Обработка числовых последовательностей', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 18, 'title': 'Робот-сборщик монет', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 19, 'title': 'Игра. Выигрышная стратегия (дерево)', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 20, 'title': 'Игра. Выигрышная стратегия (анализ)', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 21, 'title': 'Игра. Выигрышная стратегия (программа)', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 22, 'title': 'Анализ параллельных процессов', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 23, 'title': 'Оптимальный путь в графе', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 24, 'title': 'Обработка строк', 'answer_type': 'code_solution', 'max_points': 1},
            {'task_number': 25, 'title': 'Делимость. Обработка чисел', 'answer_type': 'code_solution', 'max_points': 1},
            {'task_number': 26, 'title': 'Обработка массива (сортировка)', 'answer_type': 'code_solution', 'max_points': 2},
            {'task_number': 27, 'title': 'Программирование (высокий)', 'answer_type': 'code_solution', 'max_points': 2},
        ],
    },
    'ege_math_prof_2026': {
        'title': 'ЕГЭ Математика (профиль) 2026',
        'exam_type': 'ege',
        'subject_code': 'math_prof',
        'duration_minutes': 235,
        'total_primary_score': 32,
        'tasks': [
            {'task_number': 1, 'title': 'Планиметрия (базовая)', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 2, 'title': 'Векторы и координаты', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 3, 'title': 'Стереометрия (базовая)', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 4, 'title': 'Теория вероятностей', 'answer_type': 'decimal_number', 'max_points': 1},
            {'task_number': 5, 'title': 'Теория вероятностей (повышенный)', 'answer_type': 'decimal_number', 'max_points': 1},
            {'task_number': 6, 'title': 'Уравнения', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 7, 'title': 'Функции и их свойства', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 8, 'title': 'Производная и интеграл', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 9, 'title': 'Текстовые задачи', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 10, 'title': 'Функции и графики', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 11, 'title': 'Последовательности и прогрессии', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 12, 'title': 'Тригонометрическое уравнение', 'answer_type': 'extended_text', 'max_points': 2},
            {'task_number': 13, 'title': 'Стереометрия', 'answer_type': 'extended_text', 'max_points': 3},
            {'task_number': 14, 'title': 'Неравенство', 'answer_type': 'extended_text', 'max_points': 2},
            {'task_number': 15, 'title': 'Экономическая задача', 'answer_type': 'extended_text', 'max_points': 2},
            {'task_number': 16, 'title': 'Планиметрия', 'answer_type': 'extended_text', 'max_points': 3},
            {'task_number': 17, 'title': 'Параметр', 'answer_type': 'extended_text', 'max_points': 4},
            {'task_number': 18, 'title': 'Теория чисел', 'answer_type': 'extended_text', 'max_points': 4},
        ],
    },
    'ege_russian_2026': {
        'title': 'ЕГЭ Русский язык 2026',
        'exam_type': 'ege',
        'subject_code': 'russian',
        'duration_minutes': 210,
        'total_primary_score': 50,
        'tasks': [
            {'task_number': 1, 'title': 'Средства связи предложений в тексте', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 2, 'title': 'Лексическое значение слова', 'answer_type': 'short_number', 'max_points': 1},
            {'task_number': 3, 'title': 'Стилистический анализ текста', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 4, 'title': 'Орфоэпические нормы', 'answer_type': 'short_text', 'max_points': 1},
            {'task_number': 5, 'title': 'Паронимы', 'answer_type': 'short_text', 'max_points': 1},
            {'task_number': 6, 'title': 'Лексические нормы', 'answer_type': 'short_text', 'max_points': 1},
            {'task_number': 7, 'title': 'Морфологические нормы', 'answer_type': 'short_text', 'max_points': 1},
            {'task_number': 8, 'title': 'Синтаксические нормы (грамматические ошибки)', 'answer_type': 'digit_sequence', 'max_points': 3},
            {'task_number': 9, 'title': 'Правописание корней', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 10, 'title': 'Правописание приставок', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 11, 'title': 'Правописание суффиксов', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 12, 'title': 'Правописание НЕ и НИ', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 13, 'title': 'Слитное/раздельное/дефисное написание', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 14, 'title': 'Правописание -Н- и -НН-', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 15, 'title': 'Пунктуационный анализ (запятые)', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 16, 'title': 'Пунктуационный анализ (обособленные)', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 17, 'title': 'Пунктуационный анализ (вводные)', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 18, 'title': 'Пунктуационный анализ (СПП)', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 19, 'title': 'Пунктуационный анализ (сложное)', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 20, 'title': 'Смысловая и композиционная целостность текста', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 21, 'title': 'Функционально-смысловые типы речи', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 22, 'title': 'Лексика и фразеология', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 23, 'title': 'Средства связи предложений (повышенный)', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 24, 'title': 'Языковые средства выразительности', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 25, 'title': 'Средства связи предложений', 'answer_type': 'digit_sequence', 'max_points': 1},
            {'task_number': 26, 'title': 'Средства выразительности', 'answer_type': 'digit_sequence', 'max_points': 4},
            {'task_number': 27, 'title': 'Сочинение', 'answer_type': 'essay', 'max_points': 21},
        ],
    },
}


def get_score_scale(exam_key: str) -> dict:
    """Получить шкалу перевода по ключу."""
    return SCORE_SCALES.get(exam_key, {})


def get_grade_thresholds(exam_key: str) -> dict:
    """Получить пороги оценок по ключу."""
    return GRADE_THRESHOLDS.get(exam_key, {})


def get_exam_structure(exam_key: str) -> dict | None:
    """Получить структуру экзамена по ключу."""
    return EXAM_STRUCTURES.get(exam_key)


def list_available_exams() -> list[str]:
    """Список доступных ключей экзаменов."""
    return list(EXAM_STRUCTURES.keys())
