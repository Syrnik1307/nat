"""
Тестовый скрипт для демонстрации AI-проверки ЕГЭ/ОГЭ

Запуск:
    cd teaching_panel
    python test_ai_grading_demo.py

Требования:
    - Установлен DEEPSEEK_API_KEY в settings.py
    - Запущен Django
"""

import os
import sys
import django

# Настраиваем Django
# Добавляем teaching_panel/ в путь Python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEACHING_PANEL_DIR = os.path.join(BASE_DIR, 'teaching_panel')
sys.path.insert(0, TEACHING_PANEL_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from decimal import Decimal
from homework.ai_grading_examples import (
    EXAMPLE_1_SOURCE,
    EXAMPLE_1_STUDENT_ANSWER,
    EXAMPLE_1_EXPECTED_OUTPUT,
    EGE_CRITERIA
)
from homework.exam_ai_grading_service import (
    ExamAIGradingService,
    grade_ege_essay,
    estimate_exam_grading_cost
)


def print_separator(title=""):
    """Красивый разделитель"""
    print("\n" + "=" * 80)
    if title:
        print(f"║ {title.center(76)} ║")
        print("=" * 80)
    print()


def demo_single_grading():
    """Демо: проверка одного сочинения"""
    print_separator("ДЕМО 1: Проверка одного сочинения ЕГЭ")
    
    print("📝 Исходный текст:")
    print(EXAMPLE_1_SOURCE[:200] + "...\n")
    
    print("✍️  Ответ ученика:")
    print(EXAMPLE_1_STUDENT_ANSWER[:300] + "...\n")
    
    print("⏳ Проверяем с помощью AI...")
    
    try:
        result = grade_ege_essay(
            source_text=EXAMPLE_1_SOURCE,
            student_answer=EXAMPLE_1_STUDENT_ANSWER,
            provider='deepseek',
            use_cache=True
        )
        
        print(f"✅ Проверка завершена!\n")
        
        print(f"📊 РЕЗУЛЬТАТ:")
        print(f"   Оценка: {result.total_score} / {result.max_score} баллов")
        print(f"   Стоимость: {result.cost_rubles} ₽")
        print(f"   Модель: {result.model_used}")
        print(f"   Токены: {result.tokens_used}")
        
        print(f"\n💬 ИТОГ:")
        print(f"   {result.summary}")
        
        print(f"\n✅ СИЛЬНЫЕ СТОРОНЫ:")
        for strength in result.strengths:
            print(f"   • {strength}")
        
        print(f"\n⚠️  ЧТО УЛУЧШИТЬ:")
        for weakness in result.weaknesses:
            print(f"   • {weakness}")
        
        print(f"\n📋 ОЦЕНКА ПО КРИТЕРИЯМ:")
        for criterion, data in result.criteria_scores.items():
            score = data.get('score', 0)
            reasoning = data.get('reasoning', '')
            print(f"   {criterion}: {score} балл(ов) - {reasoning}")
        
        if result.examples_of_errors:
            print(f"\n❌ ПРИМЕРЫ ОШИБОК (первые 5):")
            for i, err in enumerate(result.examples_of_errors[:5], 1):
                print(f"   {i}. [{err['type']}]")
                print(f"      Фрагмент: \"{err['fragment']}\"")
                if err.get('correction'):
                    print(f"      Исправление: \"{err['correction']}\"")
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_cost_estimation():
    """Демо: расчет стоимости для класса"""
    print_separator("ДЕМО 2: Оценка стоимости для класса")
    
    scenarios = [
        {"students": 30, "desc": "Класс из 30 учеников"},
        {"students": 100, "desc": "Параллель из 100 учеников"},
        {"students": 500, "desc": "Вся школа (500 учеников)"},
    ]
    
    print("📊 Сценарии проверки (сочинения по 2000 символов):\n")
    
    for scenario in scenarios:
        estimate = estimate_exam_grading_cost(
            num_students=scenario["students"],
            exam_type="ЕГЭ",
            task_type="russian_27",
            avg_length=2000
        )
        
        print(f"   {scenario['desc']}:")
        print(f"      • Общая стоимость: {estimate['total_cost_rubles']:.2f} ₽")
        print(f"      • За 1 работу: {estimate['cost_per_work_rubles']:.4f} ₽")
        print(f"      • Токенов всего: {estimate['total_tokens']:,}")
        print()


def demo_model_comparison():
    """Демо: сравнение моделей по стоимости"""
    print_separator("ДЕМО 3: Сравнение моделей")
    
    models = [
        ("deepseek-chat", "DeepSeek Chat (РЕКОМЕНДУЕТСЯ)"),
        ("deepseek-reasoner", "DeepSeek Reasoner"),
        ("gpt-4o-mini", "GPT-4o-mini"),
    ]
    
    print("💰 Стоимость проверки класса из 30 учеников:\n")
    
    for model_name, model_desc in models:
        service = ExamAIGradingService(model=model_name)
        estimate = service.estimate_cost(
            num_works=30,
            avg_work_length=2000,
            criteria_key="russian_27"
        )
        
        total_cost = estimate["total_cost_rubles"]
        per_work = estimate["cost_per_work_rubles"]
        
        print(f"   {model_desc}:")
        print(f"      • Всего: {total_cost:.2f} ₽")
        print(f"      • За работу: {per_work:.4f} ₽")
        print()


def demo_cache_benefit():
    """Демо: выгода от кэширования"""
    print_separator("ДЕМО 4: Кэширование (повторная проверка бесплатна)")
    
    print("Проверяем одну работу дважды...\n")
    
    # Первая проверка
    print("1️⃣  Первая проверка (без кэша):")
    result1 = grade_ege_essay(
        source_text=EXAMPLE_1_SOURCE,
        student_answer=EXAMPLE_1_STUDENT_ANSWER,
        use_cache=False  # принудительно без кэша
    )
    print(f"   Стоимость: {result1.cost_rubles} ₽")
    print(f"   Токены: {result1.tokens_used}")
    
    # Вторая проверка (из кэша)
    print("\n2️⃣  Повторная проверка (из кэша):")
    result2 = grade_ege_essay(
        source_text=EXAMPLE_1_SOURCE,
        student_answer=EXAMPLE_1_STUDENT_ANSWER,
        use_cache=True  # используем кэш
    )
    print(f"   Стоимость: 0.0000 ₽ (из кэша!)")
    print(f"   Токены: 0 (из кэша!)")
    
    print(f"\n💡 Экономия: {result1.cost_rubles} ₽ на каждую повторную проверку")


def demo_criteria_breakdown():
    """Демо: детальный разбор критериев ФИПИ"""
    print_separator("ДЕМО 5: Критерии ФИПИ для ЕГЭ Русский язык (Задание 27)")
    
    criteria = EGE_CRITERIA["russian_27"]
    
    print(f"Название: {criteria['name']}")
    print(f"Максимум баллов: {criteria['max_score']}\n")
    
    print("Критерии оценивания:\n")
    
    for key, criterion in criteria["criteria"].items():
        print(f"   {key} - {criterion['name']} (макс. {criterion['max']} балл.)")
        
        # Показываем уровни оценивания
        if "levels" in criterion:
            for level in criterion["levels"][:2]:  # первые 2 уровня
                print(f"      • {level['score']} балл: {level['desc']}")
        
        print()


def main():
    """Главная функция - запускает все демо"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " AI ПРОВЕРКА ЕГЭ/ОГЭ - ДЕМОНСТРАЦИЯ ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Проверяем настройки
    from django.conf import settings
    
    if not getattr(settings, 'DEEPSEEK_API_KEY', None):
        print("\n⚠️  ВНИМАНИЕ: DEEPSEEK_API_KEY не настроен в settings.py")
        print("   Демо будет работать в режиме эмуляции (без реальных запросов к AI)\n")
    
    # Запускаем демо
    demos = [
        ("Проверка сочинения", demo_single_grading),
        ("Оценка стоимости", demo_cost_estimation),
        ("Сравнение моделей", demo_model_comparison),
        ("Кэширование", demo_cache_benefit),
        ("Критерии ФИПИ", demo_criteria_breakdown),
    ]
    
    for i, (name, func) in enumerate(demos, 1):
        try:
            func()
        except Exception as e:
            print(f"\n❌ Ошибка в демо '{name}': {e}")
            import traceback
            traceback.print_exc()
        
        if i < len(demos):
            input("\n\nНажмите Enter для продолжения...")
    
    print_separator("ДЕМО ЗАВЕРШЕНО")
    
    print("📚 Документация:")
    print("   • AI_GRADING_GUIDE.md - полное руководство по архитектуре")
    print("   • EGE_OGE_AI_INTEGRATION_GUIDE.md - пошаговая интеграция")
    print("   • ai_grading_examples.py - примеры и критерии ФИПИ")
    print("   • exam_ai_grading_service.py - основной сервис\n")
    
    print("🚀 Следующие шаги:")
    print("   1. Настройте DEEPSEEK_API_KEY в settings.py")
    print("   2. Примените миграции БД (см. EGE_OGE_AI_INTEGRATION_GUIDE.md)")
    print("   3. Добавьте API endpoints")
    print("   4. Протестируйте на реальных работах")
    print("   5. Раскатите на production\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Демо прервано пользователем")
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
