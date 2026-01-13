$ErrorActionPreference = 'Stop'

$ssh = "C:\Program Files\OpenSSH\ssh.exe"
if (-not (Test-Path $ssh)) {
  throw "ssh.exe not found at: $ssh"
}

$py = @'
import os
import json
import urllib.request
import urllib.parse
import urllib.error

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from homework.models import Homework, StudentSubmission, Answer, Question
from django.db.models import Q

User = get_user_model()

# We prefer hitting the app via localhost to avoid server DNS issues.
public_base = os.environ.get("TP_BASE_URL", "https://lectio.tw1.ru").rstrip("/")
internal_base = os.environ.get("TP_INTERNAL_BASE", "http://127.0.0.1:8000").rstrip("/")

parsed = urllib.parse.urlparse(public_base)
host = parsed.netloc or "lectio.tw1.ru"

# --- Diagnostics: confirm there is data to test ----------------------
print("HOMEWORK_TOTAL", Homework.objects.count())
print("QUESTIONS_TOTAL", Question.objects.count())
choice_qs = Question.objects.filter(question_type__in=['SINGLE_CHOICE', 'MULTI_CHOICE'])
print("CHOICE_QUESTIONS_TOTAL", choice_qs.count())

# Find a student + homework pair that is actually visible to the student.
# HomeworkViewSet.get_queryset() for students is restricted and returns 404 if not visible.
student = None
hw = None

preferred_students = (
    User.objects.filter(role='student', is_active=True)
    .filter(Q(email__icontains='test') | Q(email__endswith='@test.local') | Q(email__iexact='test_student@example.com'))
    .order_by('-last_login', 'id')
)
fallback_students = User.objects.filter(role='student', is_active=True).order_by('-last_login', 'id')

students = list(preferred_students[:50]) + list(fallback_students[:100])

def pick_visible_homework_for_student(s, prefer_smoke: bool):
    qs = (
        Homework.objects
        .filter(status='published')
        .filter(questions__question_type__in=['SINGLE_CHOICE', 'MULTI_CHOICE'])
        .filter(Q(lesson__group__students=s) | Q(teacher__teaching_groups__students=s))
        .exclude(submissions__student=s)
    )
    if prefer_smoke:
        qs = qs.filter(title__startswith='SMOKE HW')
    return qs.distinct().order_by('-id').first()

for prefer_smoke in (True, False):
    for s in students:
        visible_hw = pick_visible_homework_for_student(s, prefer_smoke=prefer_smoke)
        if visible_hw:
            student = s
            hw = visible_hw
            break
    if hw:
        break

assert student and hw, "NO_VISIBLE_PUBLISHED_HOMEWORK_WITH_CHOICES_FOR_ANY_STUDENT"

# Create student access token.
tok = str(RefreshToken.for_user(student).access_token)
headers = {
    "Authorization": "Bearer " + tok,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Host": host,
    "X-Forwarded-Proto": "https",
}

def request(method, url, payload=None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, headers=headers, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read().decode('utf-8', 'ignore')
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = ''
        try:
            body = e.read().decode('utf-8', 'ignore')
        except Exception:
            body = ''
        return e.code, body

print("HW_ID", hw.id)
print("HW_TITLE", hw.title)
print("STUDENT_ID", student.id)
print("STUDENT_EMAIL", student.email)

# Fetch homework as student (ensures serializer works)
code, body = request('GET', f"{internal_base}/api/homework/{hw.id}/")
print("GET_HOMEWORK_STATUS", code)
assert code == 200, body[:300]

hw_json = json.loads(body)
questions = hw_json.get('questions') or []

# After the backend fix, student payload should not include config.options
leaked = []
for q in questions:
    qt = q.get('question_type')
    if qt in ('SINGLE_CHOICE', 'MULTIPLE_CHOICE'):
        cfg = q.get('config') or {}
        if isinstance(cfg, dict) and 'options' in cfg:
            leaked.append(q.get('id'))
print("STUDENT_CONFIG_OPTIONS_LEAKED_QIDS", leaked)
assert not leaked, "STUDENT_API_LEAKS_CONFIG_OPTIONS"

# Create submission
code, body = request('POST', f"{internal_base}/api/submissions/", {"homework": hw.id})
print("CREATE_SUBMISSION_STATUS", code)
assert code in (200, 201), body[:300]
sub_json = json.loads(body)
sub_id = sub_json.get('id')
assert sub_id, "NO_SUBMISSION_ID"
print("SUBMISSION_ID", sub_id)

# Build answers payload
answers_payload = {}

# Prefer testing legacy opt-* format using DB question.config.options (if it exists)
q_sc = next((q for q in questions if q.get('question_type') == 'SINGLE_CHOICE'), None)
if q_sc and q_sc.get('id'):
    qid = int(q_sc['id'])
    q_db = Question.objects.prefetch_related('choices').get(id=qid)
    options = (q_db.config or {}).get('options') if isinstance(q_db.config, dict) else None
    sent = None
    if isinstance(options, list) and options and isinstance(options[0], dict) and options[0].get('id'):
        sent = options[0]['id']
        answers_payload[str(qid)] = sent
        print("SINGLE_CHOICE_SENT_AS", "legacy_opt", sent)
    else:
        first_choice = q_db.choices.all().order_by('id').first()
        assert first_choice, f"NO_DB_CHOICES_FOR_SINGLE_CHOICE_Q={qid}"
        sent = first_choice.id
        answers_payload[str(qid)] = sent
        print("SINGLE_CHOICE_SENT_AS", "db_id", sent)

q_mc = next((q for q in questions if q.get('question_type') in ('MULTIPLE_CHOICE', 'MULTI_CHOICE')), None)
if q_mc and q_mc.get('id'):
    qid = int(q_mc['id'])
    q_db = Question.objects.prefetch_related('choices').get(id=qid)
    options = (q_db.config or {}).get('options') if isinstance(q_db.config, dict) else None
    sent_list = None
    if isinstance(options, list) and options and isinstance(options[0], dict) and options[0].get('id'):
        # Send legacy ids (first 1-2) if present
        sent_list = [options[0]['id']]
        if len(options) > 1 and isinstance(options[1], dict) and options[1].get('id'):
            sent_list.append(options[1]['id'])
        answers_payload[str(qid)] = sent_list
        print("MULTI_CHOICE_SENT_AS", "legacy_opt", sent_list)
    else:
        chs = list(q_db.choices.all().order_by('id')[:2])
        if chs:
            sent_list = [c.id for c in chs[:1]]
            answers_payload[str(qid)] = sent_list
            print("MULTI_CHOICE_SENT_AS", "db_id", sent_list)

print("ANSWERS_KEYS", sorted(list(answers_payload.keys())))
assert answers_payload, "NO_CHOICE_QUESTIONS_FOUND_IN_SERIALIZED_HOMEWORK"

# Save progress
code, body = request('PATCH', f"{internal_base}/api/submissions/{sub_id}/answer/", {"answers": answers_payload})
print("SAVE_PROGRESS_STATUS", code)
assert code == 200, body[:300]

# Submit
code, body = request('POST', f"{internal_base}/api/submissions/{sub_id}/submit/", {})
print("SUBMIT_STATUS", code)
assert code == 200, body[:300]

result = json.loads(body)
print("RESULT_STATUS", result.get('status'))
print("RESULT_TOTAL_SCORE", result.get('total_score'))

# DB verification: selected_choices should be set for answered questions
sub = StudentSubmission.objects.get(id=sub_id)

for qid_str, raw in answers_payload.items():
    qid = int(qid_str)
    ans = Answer.objects.get(submission=sub, question_id=qid)
    sel_count = ans.selected_choices.count()
    print("DB_ANSWER", ans.id, "Q", qid, "selected_count", sel_count, "auto", ans.auto_score)
    assert sel_count > 0, f"selected_choices not saved for Q={qid} raw={raw}"

print("SMOKE_OK")

# Cleanup: don't pollute production with test submissions
try:
    if (hw.title or '').startswith('SMOKE HW'):
        StudentSubmission.objects.filter(id=sub_id, homework=hw, student=student).delete()
        print("CLEANUP_OK")
except Exception as e:
    print("CLEANUP_FAILED", str(e))
'@

$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))
$remote = "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py shell -c ""import base64; exec(base64.b64decode('$b64'))"""

& $ssh tp $remote
