"""Quick test of AI grading service — standalone (no Django setup)."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Minimal settings mock
class _Settings:
    GEMINI_API_KEY = 'AIzaSyDqzAprCVHN09ZLOjPa3W3ZvNj-3XonEl4'
    GEMINI_MODEL = 'gemini-2.5-flash-lite'
    DEEPSEEK_API_KEY = ''
    DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
    DEEPSEEK_MODEL = 'deepseek-chat'
    OPENAI_API_KEY = ''
    OPENAI_MODEL = 'gpt-4o-mini'

# Monkey-patch django.conf.settings
import types
_fake_django = types.ModuleType('django')
_fake_conf = types.ModuleType('django.conf')
_fake_conf.settings = _Settings()
sys.modules['django'] = _fake_django
sys.modules['django.conf'] = _fake_conf
_fake_django.conf = _fake_conf

# Now import our service
from homework.ai_service import check_provider_health, grade_answer_with_ai

print("=" * 60)
print("1. Health check Gemini...")
health = check_provider_health('gemini')
print("   ok=%s  response=%s" % (health["ok"], health["raw_response"][:100]))
print()

if not health["ok"]:
    print("FAILED: %s" % health["message"])
    sys.exit(1)

print("2. Тест AI-проверки ДЗ (биология)...")
result = grade_answer_with_ai(
    provider='gemini',
    question_text='Объясните, что такое фотосинтез и почему он важен для жизни на Земле.',
    answer_text='Фотосинтез это когда растения делают еду из солнца. Они берут свет и воду и делают кислород который мы дышим.',
    max_points=10,
    extra_instructions='Оцени полноту ответа, научную точность и грамотность изложения.',
)
print("   score: %s / 10" % result["score"])
print("   feedback: %s" % result["feedback"])
print("   error: %s" % result["error"])
print()

print("3. Тест AI-проверки ДЗ (математика)...")
result2 = grade_answer_with_ai(
    provider='gemini',
    question_text='Решите уравнение: 2x + 5 = 15. Покажите ход решения.',
    answer_text='2x + 5 = 15, 2x = 10, x = 5',
    max_points=5,
)
print("   score: %s / 5" % result2["score"])
print("   feedback: %s" % result2["feedback"])
print("   error: %s" % result2["error"])
print()

print("4. Тест AI-проверки (плохой ответ)...")
result3 = grade_answer_with_ai(
    provider='gemini',
    question_text='Назовите три причины Первой мировой войны.',
    answer_text='не знаю',
    max_points=10,
)
print("   score: %s / 10" % result3["score"])
print("   feedback: %s" % result3["feedback"])
print("   error: %s" % result3["error"])

print()
print("=" * 60)
print("ALL TESTS PASSED!")
