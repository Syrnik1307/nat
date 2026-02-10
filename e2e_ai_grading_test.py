#!/usr/bin/env python3
"""E2E тест AI Grading Microservice — запустить на сервере."""
import os, sys, django, time

sys.path.insert(0, "/var/www/teaching_panel/teaching_panel")
os.environ["DJANGO_SETTINGS_MODULE"] = "teaching_panel.settings"
django.setup()

from django.conf import settings
print(f"AI_GRADING_ASYNC = {settings.AI_GRADING_ASYNC}")
print(f"AI_CALLBACK_URL = {settings.AI_CALLBACK_URL}")
has_key = bool(settings.DEEPSEEK_API_KEY)
print(f"DEEPSEEK_API_KEY = {'SET' if has_key else 'NOT SET (mock mode)'}")

from homework.models import Homework, Question, StudentSubmission, Answer
from django.contrib.auth import get_user_model
User = get_user_model()

teacher = User.objects.filter(role="teacher").first()
student = User.objects.filter(role="student").first()
print(f"\nTeacher: {teacher} (id={teacher.id})")
print(f"Student: {student} (id={student.id})")

# Homework с AI
hw = Homework.objects.filter(ai_grading_enabled=True).first()
if not hw:
    hw = Homework.objects.filter(teacher=teacher, status="published").first()
    if hw:
        hw.ai_grading_enabled = True
        hw.ai_provider = "deepseek"
        hw.save(update_fields=["ai_grading_enabled", "ai_provider"])
        print(f"Enabled AI on homework: {hw.id} - {hw.title}")

if not hw:
    # Создаём тестовое homework
    hw = Homework.objects.create(
        teacher=teacher,
        title="[AI Test] Рекурсия и базовые алгоритмы",
        status="published",
        ai_grading_enabled=True,
        ai_provider="deepseek",
    )
    print(f"Created test homework: {hw.id}")

print(f"\nHomework: id={hw.id}, title={hw.title}")

# TEXT question
text_q = hw.questions.filter(question_type="TEXT").first()
if not text_q:
    text_q = Question.objects.create(
        homework=hw,
        question_type="TEXT",
        prompt="Explain recursion with factorial example. What is the base case?",
        points=10,
        order=99,
    )
    print(f"Created TEXT question: id={text_q.id}")
else:
    print(f"Found TEXT question: id={text_q.id}")

# Submission
sub, created = StudentSubmission.objects.get_or_create(
    homework=hw, student=student,
    defaults={"status": "submitted"}
)
if not created:
    sub.status = "submitted"
    sub.save(update_fields=["status"])
print(f"Submission: id={sub.id} ({'new' if created else 'existing'})")

# Answer — reset
answer, a_created = Answer.objects.get_or_create(
    submission=sub, question=text_q,
    defaults={"text_answer": "Recursion is when a function calls itself. factorial(n) = n * factorial(n-1), base case factorial(1) = 1."}
)
if not a_created:
    answer.text_answer = "Recursion is when a function calls itself. factorial(5)=5*4*3*2*1. Base case is factorial(1)=1."
    answer.auto_score = None
    answer.teacher_score = None
    answer.ai_grading_status = None
    answer.grading_job_id = None
    answer.needs_manual_review = False
    answer.teacher_feedback = ""
    answer.ai_confidence = None
    answer.ai_provider_used = None
    answer.ai_cost_rubles = None
    answer.ai_latency_ms = None
    answer.ai_tokens_used = None
    answer.ai_checked_at = None
    answer.save()

print(f"Answer: id={answer.id}")
print(f"Before: status={answer.ai_grading_status}, score={answer.auto_score}")

# === CALL GATEWAY ===
print("\n--- Calling AIGradingGateway ---")
from homework.ai_gateway import AIGradingGateway
gateway = AIGradingGateway()
job_id = gateway.submit_for_grading(answer, hw)

answer.refresh_from_db()
print(f"job_id = {job_id}")
print(f"ai_grading_status = {answer.ai_grading_status}")

# === POLL ===
print("\n--- Waiting for worker ---")
for i in range(25):
    time.sleep(1)
    answer.refresh_from_db()
    st = answer.ai_grading_status
    sc = answer.auto_score
    fb = (answer.teacher_feedback or "")[:50]
    print(f"  [{i+1:2d}s] status={st}, score={sc}, feedback={fb}")
    if st in ("completed", "failed"):
        break

# === RESULT ===
print("\n=== RESULT ===")
answer.refresh_from_db()
print(f"  status:       {answer.ai_grading_status}")
print(f"  score:        {answer.auto_score}/{text_q.points}")
print(f"  confidence:   {answer.ai_confidence}")
print(f"  provider:     {answer.ai_provider_used}")
print(f"  cost (RUB):   {answer.ai_cost_rubles}")
print(f"  latency (ms): {answer.ai_latency_ms}")
print(f"  tokens:       {answer.ai_tokens_used}")
print(f"  manual_rev:   {answer.needs_manual_review}")
print(f"  feedback:     {answer.teacher_feedback}")
print(f"  checked_at:   {answer.ai_checked_at}")

if answer.ai_grading_status == "completed":
    print("\nE2E TEST PASSED")
elif answer.ai_grading_status == "failed":
    print("\nAI failed (no API key) - fallback to manual review OK")
else:
    print(f"\nTIMEOUT - status still: {answer.ai_grading_status}")
