$ErrorActionPreference = 'Stop'

$ssh = "C:\Program Files\OpenSSH\ssh.exe"
if (-not (Test-Path $ssh)) {
  throw "ssh.exe not found at: $ssh"
}

$py = @'
import os
import urllib.request, urllib.parse, json
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
admin = User.objects.filter(role="admin").order_by("id").first()
print("ADMIN_ID", getattr(admin, "id", None))
assert admin, "NO_ADMIN_USER_FOUND"

tok = str(RefreshToken.for_user(admin).access_token)
headers = {
    "Authorization": "Bearer " + tok,
    "Content-Type": "application/json",
}

# We prefer hitting the app via localhost to avoid server DNS issues.
# Host header is set to the public hostname so Django/DRF routing stays consistent.
public_base = os.environ.get("TP_BASE_URL", "https://lectio.tw1.ru").rstrip("/")
internal_base = os.environ.get("TP_INTERNAL_BASE", "http://127.0.0.1:8000").rstrip("/")

parsed = urllib.parse.urlparse(public_base)
host = parsed.netloc or "lectio.tw1.ru"
headers["Host"] = host
headers["X-Forwarded-Proto"] = "https"

def get(url):
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.status, resp.read().decode("utf-8", "ignore")

code, body = get(internal_base + "/accounts/api/admin/teachers/?" + urllib.parse.urlencode({"page": 1, "page_size": 5, "sort": "name", "order": "asc"}))
print("TEACHERS_STATUS", code)
tdata = json.loads(body) if body else {}
tlist = tdata.get("results", []) if isinstance(tdata, dict) else []
print("TEACHERS_NUM", len(tlist))
first_tid = tlist[0].get("id") if tlist else None
print("TEACHER0_ID", first_tid)

code, body = get(internal_base + "/accounts/api/admin/students/?" + urllib.parse.urlencode({"page": 1, "page_size": 5, "status": "active", "sort": "last_login", "order": "desc"}))
print("STUDENTS_STATUS", code)
sdata = json.loads(body) if body else {}
slist = sdata.get("results", []) if isinstance(sdata, dict) else []
print("STUDENTS_TOTAL", sdata.get("total"), "RESULTS", len(slist))
if slist:
    s0 = slist[0]
    want = ["id","email","first_name","last_name","created_at","last_login","is_active","groups","teachers"]
    print("STUDENT0_HAS_FIELDS", all(k in s0 for k in want))

if first_tid:
    code, body = get(internal_base + "/accounts/api/admin/students/?" + urllib.parse.urlencode({"page": 1, "page_size": 5, "status": "all", "teacher_id": first_tid}))
    print("STUDENTS_BY_TEACHER_STATUS", code)
    jj = json.loads(body) if body else {}
    rr = jj.get("results", []) if isinstance(jj, dict) else []
    print("STUDENTS_BY_TEACHER_RESULTS", len(rr))

# archived filter
code, body = get(internal_base + "/accounts/api/admin/students/?" + urllib.parse.urlencode({"page": 1, "page_size": 5, "status": "archived"}))
print("ARCHIVED_STATUS", code)
adata = json.loads(body) if body else {}
alist = adata.get("results", []) if isinstance(adata, dict) else []
print("ARCHIVED_TOTAL", adata.get("total"), "RESULTS", len(alist))
if alist:
    print("ARCHIVED0_IS_ACTIVE", alist[0].get("is_active"))

# sort by name asc
code, body = get(internal_base + "/accounts/api/admin/students/?" + urllib.parse.urlencode({"page": 1, "page_size": 5, "status": "active", "sort": "name", "order": "asc"}))
print("SORT_NAME_ASC_STATUS", code)
ndata = json.loads(body) if body else {}
nlist = ndata.get("results", []) if isinstance(ndata, dict) else []
names = [s.get("last_name", "") for s in nlist]
print("SORT_NAME_ASC_OK", names == sorted(names))

# sort by created_at desc
code, body = get(internal_base + "/accounts/api/admin/students/?" + urllib.parse.urlencode({"page": 1, "page_size": 5, "status": "active", "sort": "created_at", "order": "desc"}))
print("SORT_CREATED_DESC_STATUS", code)
cdata = json.loads(body) if body else {}
clist = cdata.get("results", []) if isinstance(cdata, dict) else []
dates = [s.get("created_at", "") for s in clist]
print("SORT_CREATED_DESC_OK", dates == sorted(dates, reverse=True))
'@

$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))

# NOTE: manage.py shell already configures Django settings.
$remote = "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py shell -c ""import base64; exec(base64.b64decode('$b64'))"""

& $ssh tp $remote
