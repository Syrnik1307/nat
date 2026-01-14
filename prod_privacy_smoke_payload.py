import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import timedelta
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import CustomUser
from schedule.models import Group, Lesson
from homework.models import Homework, Question, Choice

public_base = os.environ.get("TP_BASE_URL", "https://lectio.tw1.ru").rstrip("/")
internal_base = os.environ.get("TP_INTERNAL_BASE", "http://127.0.0.1:8000").rstrip("/")
parsed = urllib.parse.urlparse(public_base)
host = parsed.netloc or "lectio.tw1.ru"


def ensure_user(email, role, first, last):
    user, created = CustomUser.objects.get_or_create(
        email=email,
        defaults={"role": role, "is_active": True, "first_name": first, "last_name": last},
    )
    if created:
        user.set_password("Test1234!")
        user.save()
    return user


def build_headers(user):
    tok = str(RefreshToken.for_user(user).access_token)
    return {
        "Authorization": "Bearer " + tok,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Host": host,
        "X-Forwarded-Proto": "https",
    }


def http(method, url, headers, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, headers=headers, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", "ignore")
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore") if e.fp else ""
        return e.code, body


teacher_a = ensure_user("smoke_hw_teacher@test.local", "teacher", "Smoke", "TeacherA")
student_a = ensure_user("smoke_hw_student@test.local", "student", "Smoke", "StudentA")
teacher_b = ensure_user("smoke_hw_teacher_b@test.local", "teacher", "Smoke", "TeacherB")
student_b = ensure_user("smoke_hw_student_b@test.local", "student", "Smoke", "StudentB")

group_b, _ = Group.objects.get_or_create(
    name="SMOKE PRIVACY GROUP B",
    teacher=teacher_b,
    defaults={"description": "Privacy smoke group B"},
)
group_b.students.add(student_b)

start = timezone.now() + timedelta(hours=2)
end = start + timedelta(hours=1)
lesson_b, created = Lesson.objects.get_or_create(
    group=group_b,
    teacher=teacher_b,
    title="SMOKE PRIVACY LESSON B",
    defaults={"start_time": start, "end_time": end},
)
if not created:
    changed = False
    if not lesson_b.start_time:
        lesson_b.start_time = start
        changed = True
    if not lesson_b.end_time:
        lesson_b.end_time = end
        changed = True
    if changed:
        lesson_b.save(update_fields=["start_time", "end_time"])

hw_b, _ = Homework.objects.get_or_create(
    title="SMOKE PRIVACY HW B",
    teacher=teacher_b,
    defaults={"lesson": lesson_b, "status": "draft"},
)
hw_b.lesson = lesson_b
hw_b.status = "published"
hw_b.published_at = timezone.now()
hw_b.save(update_fields=["lesson", "status", "published_at"])

hw_b.questions.all().delete()
q1 = Question.objects.create(
    homework=hw_b,
    prompt="SC Q",
    question_type="SINGLE_CHOICE",
    points=1,
    order=1,
)
c1 = Choice.objects.create(question=q1, text="A", is_correct=True)
c2 = Choice.objects.create(question=q1, text="B", is_correct=False)
q1.config = {
    "options": [{"id": str(c1.id), "text": "A"}, {"id": str(c2.id), "text": "B"}],
    "correctOptionId": str(c1.id),
}
q1.save(update_fields=["config"])

# Cross-access checks
h_a = build_headers(teacher_a)
code_hw_a, body_hw_a = http("GET", f"{internal_base}/api/homework/{hw_b.id}/", h_a)
code_lesson_a, body_lesson_a = http("GET", f"{internal_base}/api/schedule/lessons/{lesson_b.id}/", h_a)
print("TEACHER_A_GET_HW_B_STATUS", code_hw_a)
print("TEACHER_A_GET_LESSON_B_STATUS", code_lesson_a)

h_sa = build_headers(student_a)
code_hw_sa, _ = http("GET", f"{internal_base}/api/homework/{hw_b.id}/", h_sa)
code_lesson_sa, _ = http("GET", f"{internal_base}/api/schedule/lessons/{lesson_b.id}/", h_sa)
print("STUDENT_A_GET_HW_B_STATUS", code_hw_sa)
print("STUDENT_A_GET_LESSON_B_STATUS", code_lesson_sa)

h_b = build_headers(teacher_b)
code_hw_b, _ = http("GET", f"{internal_base}/api/homework/{hw_b.id}/", h_b)
print("TEACHER_B_GET_HW_B_STATUS", code_hw_b)

h_sb = build_headers(student_b)
code_hw_sb, _ = http("GET", f"{internal_base}/api/homework/{hw_b.id}/", h_sb)
print("STUDENT_B_GET_HW_B_STATUS", code_hw_sb)

assert code_hw_a in (403, 404), f"Teacher A should be blocked, got {code_hw_a}: {body_hw_a[:200]}"
assert code_lesson_a in (403, 404), f"Teacher A lesson access should be blocked, got {code_lesson_a}: {body_lesson_a[:200]}"
assert code_hw_sa in (403, 404), f"Student A should be blocked from HW B, got {code_hw_sa}"
assert code_lesson_sa in (403, 404), f"Student A should be blocked from Lesson B, got {code_lesson_sa}"
assert code_hw_b == 200, f"Teacher B should see own HW, got {code_hw_b}"
assert code_hw_sb in (200, 404), f"Student B should be enrolled; got {code_hw_sb}"

print("PRIVACY_SMOKE_OK")
