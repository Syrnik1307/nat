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
from django.db.models import Count
from rest_framework_simplejwt.tokens import RefreshToken

from schedule.models import Lesson

User = get_user_model()

best = Lesson.objects.values("teacher_id").annotate(c=Count("id")).order_by("-c").first() or {}
best_teacher_id = best.get("teacher_id")
best_lessons_count = best.get("c", 0)

user = None
if best_teacher_id:
    user = User.objects.filter(id=best_teacher_id, is_active=True).first()

if not user:
    user = User.objects.filter(role="admin", is_active=True).order_by("id").first()

print("SELECTED_USER_ID", getattr(user, "id", None))
print("SELECTED_USER_EMAIL", getattr(user, "email", None))
print("SELECTED_USER_ROLE", getattr(user, "role", None))
print("BEST_TEACHER_LESSONS_COUNT", best_lessons_count)
assert user, "NO_TEACHER_OR_ADMIN_USER_FOUND"

tok = str(RefreshToken.for_user(user).access_token)
headers = {
    "Authorization": "Bearer " + tok,
    "Content-Type": "application/json",
}

public_base = os.environ.get("TP_BASE_URL", "https://lectio.tw1.ru").rstrip("/")
internal_base = os.environ.get("TP_INTERNAL_BASE", "http://127.0.0.1:8000").rstrip("/")

parsed = urllib.parse.urlparse(public_base)
host = parsed.netloc or "lectio.tw1.ru"
headers["Host"] = host
headers["X-Forwarded-Proto"] = "https"

def get(url):
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")

checks = [
    ("WEEKLY", "/api/teacher-stats/weekly_dynamics/", {"weeks": 8}, "weeks", "window_weeks"),
    ("MONTHLY", "/api/teacher-stats/monthly_dynamics/", {"months": 3}, "months", "window_months"),
]

for label, path, qs, items_key, window_key in checks:
    url = internal_base + path + "?" + urllib.parse.urlencode(qs)
    code, body = get(url)
    print(label, "STATUS", code)
    if code != 200:
        print(label, "BODY_HEAD", (body or "")[:500])
        continue

    data = json.loads(body) if body else {}
    items = data.get(items_key, [])
    print(label, "LEN", len(items), "WINDOW", data.get(window_key))

    if items:
        first = items[0]
        last = items[-1]
        if label == "WEEKLY":
            print("WEEK0", first.get("week_start"), first.get("week_end"), "lessons", first.get("lessons_count"), "att", first.get("attendance_percent"), "avg", first.get("avg_score_percent"))
            print("WEEK_LAST", last.get("week_start"), last.get("week_end"), "lessons", last.get("lessons_count"), "att", last.get("attendance_percent"), "avg", last.get("avg_score_percent"))
        else:
            print("MONTH0", first.get("month"), "lessons", first.get("lessons_count"), "att", first.get("attendance_percent"), "avg", first.get("avg_score_percent"))
            print("MONTH_LAST", last.get("month"), "lessons", last.get("lessons_count"), "att", last.get("attendance_percent"), "avg", last.get("avg_score_percent"))
'@

$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))

# NOTE: manage.py shell already configures Django settings.
$remote = "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py shell -c ""import base64; exec(base64.b64decode('$b64'))"""

& $ssh tp $remote
