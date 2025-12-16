# Extended production smoke (API-only)
# - additional endpoints: recurring lessons, attendance/rating, invite codes, individual students, recordings
# - safe: mostly GET requests; any 404 on optional modules is treated as WARN

$ErrorActionPreference = 'Stop'

$remote = @'
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

import json
import urllib.request, urllib.error, urllib.parse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

BASE = 'https://lectio.space'

User = get_user_model()

def pick(role):
    return User.objects.filter(role=role).order_by('id').first()

admin = pick('admin')
teacher = pick('teacher')
student = pick('student')
assert admin and teacher and student, 'Missing one of roles (admin/teacher/student)'

teacher_id = getattr(teacher, 'id', None)
student_id = getattr(student, 'id', None)

TOK = {
    'admin': str(RefreshToken.for_user(admin).access_token),
    'teacher': str(RefreshToken.for_user(teacher).access_token),
    'student': str(RefreshToken.for_user(student).access_token),
}

print('REV_SMOKE_EXT roles:', admin.email, teacher.email, student.email)


FAIL = 0


def fail(msg):
    global FAIL
    FAIL += 1
    print('FAIL', msg)


def parse_json(label, raw):
    if raw is None:
        fail(f'{label} EMPTY_BODY')
        return None
    try:
        return json.loads(raw) if raw else None
    except Exception:
        fail(f'{label} JSON_PARSE')
        return None


def expect_dict(label, obj):
    if not isinstance(obj, dict):
        fail(f'{label} EXPECT_DICT got={type(obj).__name__}')
        return False
    return True


def expect_keys(label, obj, keys):
    if not expect_dict(label, obj):
        return False
    okk = True
    for k in keys:
        if k not in obj:
            okk = False
            fail(f'{label} MISSING_KEY {k}')
    return okk


def expect_paginated(label, obj):
    if not expect_keys(label, obj, ['count', 'next', 'previous', 'results']):
        return False
    if not isinstance(obj.get('results'), list):
        fail(f'{label} EXPECT_LIST results got={type(obj.get("results")).__name__}')
        return False
    return True


def expect_list_or_paginated(label, obj):
    if isinstance(obj, list):
        return True
    if isinstance(obj, dict) and 'results' in obj:
        # Some endpoints return {'results': [...]} without full DRF pagination keys
        if all(k in obj for k in ['count', 'next', 'previous']):
            return expect_paginated(label, obj)
        if not isinstance(obj.get('results'), list):
            fail(f'{label} EXPECT_LIST results got={type(obj.get("results")).__name__}')
            return False
        return True
    if isinstance(obj, dict):
        return True
    fail(f'{label} EXPECT_LIST_OR_DICT got={type(obj).__name__}')
    return False


def call(role, method, path, body=None, accept_404=False):
    url = BASE + path
    headers = {
        'Authorization': 'Bearer ' + TOK[role],
        'Content-Type': 'application/json',
    }
    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        if isinstance(body, str):
            data = body.encode('utf-8')
        else:
            data = body
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode('utf-8', 'ignore')
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'ignore')
        if accept_404 and e.code == 404:
            return e.code, raw
        return e.code, raw


def ok(label, status, allow=(200,)):
    good = status in allow
    print(f'{label} STATUS={status} OK={1 if good else 0}')
    return good

# Basic role check
for role in ['student','teacher','admin']:
    s, raw = call(role, 'GET', '/api/me/')
    if ok(f'{role}.me', s):
        me = parse_json(f'{role}.me', raw)
        if expect_dict(f'{role}.me', me):
            expect_keys(f'{role}.me', me, ['email', 'role'])

# Get one group id for group-scoped endpoints (needed for calendar_feed too)
group_id = None
s, raw = call('teacher', 'GET', '/api/groups/?page_size=5')
if ok('teacher.groups', s):
    data = parse_json('teacher.groups', raw)
    if isinstance(data, dict) and 'results' in data:
        expect_paginated('teacher.groups', data)
        results = data.get('results', [])
    elif isinstance(data, list):
        results = data
    else:
        results = []
    if results:
        if isinstance(results[0], dict):
            expect_keys('teacher.groups.item0', results[0], ['id'])
            group_id = results[0].get('id')

# Recurring lessons (teacher)
qs = urllib.parse.urlencode({'page_size': 3})
s, raw = call('teacher', 'GET', '/api/recurring-lessons/?' + qs)
if ok('teacher.recurring_lessons', s):
    data = parse_json('teacher.recurring_lessons', raw)
    expect_paginated('teacher.recurring_lessons', data)

# Schedule lessons list (teacher + student)
import datetime
now = datetime.datetime.now(datetime.timezone.utc)
start = (now - datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
end = (now + datetime.timedelta(days=7)).replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
qs = urllib.parse.urlencode({'start': start, 'end': end, 'include_recurring': 'true', 'page_size': 5})

s, raw = call('teacher', 'GET', '/api/schedule/lessons/?' + qs)
if ok('teacher.lessons', s):
    data = parse_json('teacher.lessons', raw)
    expect_list_or_paginated('teacher.lessons', data)

s, raw = call('student', 'GET', '/api/schedule/lessons/?' + qs)
if ok('student.lessons', s, allow=(200,403)) and s == 200:
    data = parse_json('student.lessons', raw)
    expect_list_or_paginated('student.lessons', data)

# Calendar feed (teacher) — shape may be list/dict
qs_feed = {'start': start, 'end': end}
if isinstance(teacher_id, int):
    qs_feed['teacher'] = teacher_id
if isinstance(group_id, int):
    qs_feed['group'] = group_id
qs = urllib.parse.urlencode(qs_feed)
s, raw = call('teacher', 'GET', '/api/schedule/lessons/calendar_feed/?' + qs)
if ok('teacher.calendar_feed', s):
    data = parse_json('teacher.calendar_feed', raw)
    expect_list_or_paginated('teacher.calendar_feed', data)

# Attendance record endpoints (teacher/student)
qs = urllib.parse.urlencode({'page_size': 3})
s, raw = call('teacher', 'GET', '/api/attendance-records/?' + qs)
if ok('teacher.attendance_records', s):
    data = parse_json('teacher.attendance_records', raw)
    expect_paginated('teacher.attendance_records', data)

s, raw = call('student', 'GET', '/api/attendance-records/?' + qs)
if ok('student.attendance_records', s, allow=(200,403)) and s == 200:
    data = parse_json('student.attendance_records', raw)
    expect_paginated('student.attendance_records', data)

# Ratings endpoints
qs = urllib.parse.urlencode({'page_size': 3})
s, raw = call('teacher', 'GET', '/api/ratings/?' + qs)
if ok('teacher.ratings', s):
    data = parse_json('teacher.ratings', raw)
    expect_paginated('teacher.ratings', data)

s, raw = call('student', 'GET', '/api/ratings/?' + qs)
if ok('student.ratings', s, allow=(200,403)) and s == 200:
    data = parse_json('student.ratings', raw)
    expect_paginated('student.ratings', data)

if isinstance(group_id, int):
    s, raw = call('teacher', 'GET', f'/api/groups/{group_id}/attendance-log/?page_size=3')
    if ok('teacher.group_attendance_log', s):
        data = parse_json('teacher.group_attendance_log', raw)
        expect_list_or_paginated('teacher.group_attendance_log', data)

    s, raw = call('teacher', 'GET', f'/api/groups/{group_id}/rating/?page_size=3')
    if ok('teacher.group_rating', s):
        data = parse_json('teacher.group_rating', raw)
        # shape may vary; at least ensure it's valid JSON
        if data is None:
            fail('teacher.group_rating EMPTY_JSON')

    # gradebook for group
    s, raw = call('teacher', 'GET', '/api/gradebook/?' + urllib.parse.urlencode({'group': group_id}))
    if ok('teacher.gradebook', s):
        data = parse_json('teacher.gradebook', raw)
        # shape may vary; ensure valid JSON
        if data is None:
            fail('teacher.gradebook EMPTY_JSON')

    # group report (optional)
    s, raw = call('teacher', 'GET', f'/api/groups/{group_id}/report/?page_size=3', accept_404=True)
    if ok('teacher.group_report', s, allow=(200,404,403)) and s == 200:
        data = parse_json('teacher.group_report', raw)
        expect_list_or_paginated('teacher.group_report', data)
else:
    print('WARN no group id found, skip group-scoped checks')

# Student card (teacher) — optional
if isinstance(student_id, int):
    s, raw = call('teacher', 'GET', f'/api/students/{student_id}/card/', accept_404=True)
    if ok('teacher.student_card', s, allow=(200,404,403)) and s == 200:
        data = parse_json('teacher.student_card', raw)
        expect_dict('teacher.student_card', data)
else:
    print('WARN no student id found, skip student card checks')

# Invite codes & individual students
qs = urllib.parse.urlencode({'page_size': 3})
s, raw = call('teacher', 'GET', '/api/individual-invite-codes/?' + qs)
if ok('teacher.individual_invite_codes', s):
    data = parse_json('teacher.individual_invite_codes', raw)
    expect_paginated('teacher.individual_invite_codes', data)

s, raw = call('teacher', 'GET', '/api/individual-students/?' + qs)
if ok('teacher.individual_students', s):
    data = parse_json('teacher.individual_students', raw)
    expect_paginated('teacher.individual_students', data)

# Homework + submissions (teacher + student)
qs = urllib.parse.urlencode({'page_size': 3})

s, raw = call('teacher', 'GET', '/api/homework/?' + qs)
if ok('teacher.homework', s, allow=(200,403)) and s == 200:
    data = parse_json('teacher.homework', raw)
    expect_paginated('teacher.homework', data)

s, raw = call('student', 'GET', '/api/homework/?' + qs)
if ok('student.homework', s, allow=(200,403)) and s == 200:
    data = parse_json('student.homework', raw)
    expect_paginated('student.homework', data)

s, raw = call('teacher', 'GET', '/api/submissions/?' + qs)
if ok('teacher.submissions', s, allow=(200,403)) and s == 200:
    data = parse_json('teacher.submissions', raw)
    expect_paginated('teacher.submissions', data)

s, raw = call('student', 'GET', '/api/submissions/?' + qs)
if ok('student.submissions', s, allow=(200,403)) and s == 200:
    data = parse_json('student.submissions', raw)
    expect_paginated('student.submissions', data)

# Recordings (schedule namespace)
# Teacher recordings list
qs = urllib.parse.urlencode({'page_size': 3})
s, raw = call('teacher', 'GET', '/schedule/api/recordings/teacher/?' + qs)
if ok('teacher.recordings', s, allow=(200,404)) and s == 200:
    data = parse_json('teacher.recordings', raw)
    expect_paginated('teacher.recordings', data)

# Student recordings list
s, raw = call('student', 'GET', '/schedule/api/recordings/?' + qs)
if ok('student.recordings', s, allow=(200,404,403)) and s == 200:
    data = parse_json('student.recordings', raw)
    expect_paginated('student.recordings', data)

# Zoom pool stats (admin)
s, raw = call('admin', 'GET', '/api/zoom-pool/zoom-accounts/stats/')
if ok('admin.zoom_pool_stats', s, allow=(200,404,403)) and s == 200:
    data = parse_json('admin.zoom_pool_stats', raw)
    expect_dict('admin.zoom_pool_stats', data)

# Zoom pool list (admin) — safe GET
qs = urllib.parse.urlencode({'page_size': 3})
s, raw = call('admin', 'GET', '/api/zoom-pool/zoom-accounts/?' + qs, accept_404=True)
if ok('admin.zoom_pool_list', s, allow=(200,404,403)) and s == 200:
    data = parse_json('admin.zoom_pool_list', raw)
    expect_list_or_paginated('admin.zoom_pool_list', data)

# Schedule zoom accounts (admin) — safe GET (sometimes guarded)
s, raw = call('admin', 'GET', '/schedule/api/zoom-accounts/?' + qs, accept_404=True)
if s >= 500:
    print('ERR admin.schedule_zoom_accounts BODY=', (raw or '')[:1200])
if ok('admin.schedule_zoom_accounts', s, allow=(200,404,403)) and s == 200:
    data = parse_json('admin.schedule_zoom_accounts', raw)
    expect_list_or_paginated('admin.schedule_zoom_accounts', data)

s, raw = call('admin', 'GET', '/schedule/api/zoom-accounts/status_summary/', accept_404=True)
if s >= 500:
    print('ERR admin.schedule_zoom_accounts_status BODY=', (raw or '')[:1200])
if ok('admin.schedule_zoom_accounts_status', s, allow=(200,404,403)) and s == 200:
    data = parse_json('admin.schedule_zoom_accounts_status', raw)
    expect_list_or_paginated('admin.schedule_zoom_accounts_status', data)

# Storage statistics (admin) — safe GET
s, raw = call('admin', 'GET', '/schedule/api/storage/statistics/', accept_404=True)
if ok('admin.storage_statistics', s, allow=(200,404,403)) and s == 200:
    data = parse_json('admin.storage_statistics', raw)
    expect_dict('admin.storage_statistics', data)

# Subscriptions (teacher/admin)
s, raw = call('teacher', 'GET', '/api/subscription/', accept_404=True)
if ok('teacher.subscription_me', s, allow=(200,404,403)) and s == 200:
    data = parse_json('teacher.subscription_me', raw)
    expect_dict('teacher.subscription_me', data)

s, raw = call('admin', 'GET', '/api/admin/subscriptions/?page_size=3', accept_404=True)
if ok('admin.subscriptions_list', s, allow=(200,404,403)) and s == 200:
    data = parse_json('admin.subscriptions_list', raw)
    expect_list_or_paginated('admin.subscriptions_list', data)

# Support module (optional)
s, raw = call('student', 'GET', '/api/support/tickets/?page_size=1', accept_404=True)
if ok('student.support.tickets', s, allow=(200,404,403)) and s == 200:
    data = parse_json('student.support.tickets', raw)
    # expected to be paginated in our API
    expect_paginated('student.support.tickets', data)


if FAIL:
    raise SystemExit(2)

print('OK: extended smoke finished')
'@

# execute remote python reliably via python -c exec("""...""")
$remoteEsc = $remote -replace '\\', '\\\\' -replace '"', '\\"' -replace "`r", "" -replace "`n", "\\n"
# execute remote python via stdin (avoids quoting issues)
$cmd = @"
cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python - <<'PY'
$remote
PY
"@

# IMPORTANT: strip CR to make heredoc terminator match on Linux
$cmd = $cmd -replace "`r", ""

ssh tp $cmd
