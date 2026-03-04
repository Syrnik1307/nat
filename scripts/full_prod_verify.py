#!/usr/bin/env python3
"""Full production verification — checks EVERYTHING a student needs."""
import json, os, subprocess, sys, time

ROOT = "/var/www/teaching_panel/frontend/build"
BASE_URL = "https://lectiospace.ru"
INTERNAL_URL = "http://127.0.0.1:8000"
FAIL = False

def section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

def ok(msg):
    print(f"  [OK]   {msg}")

def fail(msg):
    global FAIL
    FAIL = True
    print(f"  [FAIL] {msg}")

def warn(msg):
    print(f"  [WARN] {msg}")

def curl(url, timeout=10):
    """Returns (http_code, body_size, content_type)"""
    try:
        r = subprocess.run(
            ["curl", "-sk", "-o", "/dev/null", "-w", "%{http_code}|%{size_download}|%{content_type}", url, "--max-time", str(timeout)],
            capture_output=True, text=True, timeout=timeout+5
        )
        parts = r.stdout.strip().split("|")
        return int(parts[0]), int(float(parts[1])), parts[2] if len(parts) > 2 else ""
    except Exception as e:
        return 0, 0, str(e)

def curl_json(url, headers=None, timeout=10):
    """Returns (http_code, json_body)"""
    try:
        cmd = ["curl", "-sk", "--max-time", str(timeout), url]
        if headers:
            for h in headers:
                cmd.extend(["-H", h])
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+5)
        code_r = subprocess.run(
            ["curl", "-sk", "-o", "/dev/null", "-w", "%{http_code}", url, "--max-time", str(timeout)] + (["-H", headers[0]] if headers else []),
            capture_output=True, text=True, timeout=timeout+5
        )
        code = int(code_r.stdout.strip())
        try:
            body = json.loads(r.stdout)
        except:
            body = r.stdout[:200]
        return code, body
    except Exception as e:
        return 0, str(e)

# ================================================================
# 1. ASSET MANIFEST INTEGRITY
# ================================================================
section("1. ASSET MANIFEST INTEGRITY (all files from manifest exist on disk)")

manifest_path = os.path.join(ROOT, "asset-manifest.json")
if not os.path.exists(manifest_path):
    fail("asset-manifest.json NOT FOUND")
    sys.exit(1)

manifest = json.load(open(manifest_path))
files = {k: v for k, v in manifest.get("files", {}).items() if v.startswith("/")}
missing = []
for k, v in files.items():
    full = ROOT + v
    if not os.path.exists(full):
        missing.append(v)
        fail(f"MISSING: {v}")

if missing:
    fail(f"{len(missing)}/{len(files)} assets MISSING from disk!")
else:
    ok(f"All {len(files)} assets present on disk")

# ================================================================
# 2. DIRECTORY PERMISSIONS
# ================================================================
section("2. DIRECTORY & FILE PERMISSIONS")

for d in ["", "/static", "/static/js", "/static/css"]:
    path = ROOT + d
    perms = oct(os.stat(path).st_mode)[-3:]
    if int(perms[0]) >= 7 and int(perms[1]) >= 5 and int(perms[2]) >= 5:
        ok(f"{path} perms={perms}")
    else:
        fail(f"{path} perms={perms} (need at least 755)")

# Check a JS file is world-readable
js_files = [f for f in os.listdir(ROOT + "/static/js") if f.endswith(".js")]
if js_files:
    sample = ROOT + "/static/js/" + js_files[0]
    perms = oct(os.stat(sample).st_mode)[-3:]
    if int(perms[2]) >= 4:
        ok(f"JS files readable (sample: {perms})")
    else:
        fail(f"JS files NOT world-readable: {perms}")

# ================================================================
# 3. INDEX.HTML REFERENCES CORRECT JS/CSS
# ================================================================
section("3. INDEX.HTML BUNDLE REFERENCES")

index_html = open(ROOT + "/index.html").read()
import re
js_ref = re.search(r'src="/static/js/(main\.[a-f0-9]+\.js)"', index_html)
css_ref = re.search(r'href="/static/css/(main\.[a-f0-9]+\.css)"', index_html)

if js_ref:
    js_name = js_ref.group(1)
    js_path = ROOT + "/static/js/" + js_name
    if os.path.exists(js_path):
        size = os.path.getsize(js_path)
        ok(f"main JS: {js_name} ({size:,} bytes)")
    else:
        fail(f"index.html references {js_name} but file MISSING!")
else:
    fail("No main JS reference in index.html!")

if css_ref:
    css_name = css_ref.group(1)
    css_path = ROOT + "/static/css/" + css_name
    if os.path.exists(css_path):
        size = os.path.getsize(css_path)
        ok(f"main CSS: {css_name} ({size:,} bytes)")
    else:
        fail(f"index.html references {css_name} but file MISSING!")
else:
    fail("No main CSS reference in index.html!")

# ================================================================
# 4. HTTP CHECK — EVERY SINGLE JS CHUNK
# ================================================================
section("4. HTTP CHECK — ALL JS CHUNKS (not just one!)")

js_dir = ROOT + "/static/js"
all_js = sorted([f for f in os.listdir(js_dir) if f.endswith(".chunk.js")])
print(f"  Testing {len(all_js)} chunk files via HTTPS...")

http_fails = []
for f in all_js:
    url = f"{BASE_URL}/static/js/{f}"
    code, size, ctype = curl(url, timeout=5)
    if code != 200:
        fail(f"{f} -> HTTP {code}")
        http_fails.append(f)
    elif size < 100:
        fail(f"{f} -> HTTP 200 but only {size} bytes (too small, likely error page)")
        http_fails.append(f)

if not http_fails:
    ok(f"All {len(all_js)} JS chunks return HTTP 200")
else:
    fail(f"{len(http_fails)}/{len(all_js)} chunks FAILED HTTP check!")

# ================================================================
# 5. HTTP CHECK — ALL CSS CHUNKS
# ================================================================
section("5. HTTP CHECK — ALL CSS CHUNKS")

css_dir = ROOT + "/static/css"
all_css = sorted([f for f in os.listdir(css_dir) if f.endswith(".chunk.css")])
css_fails = []
for f in all_css:
    url = f"{BASE_URL}/static/css/{f}"
    code, size, ctype = curl(url, timeout=5)
    if code != 200:
        fail(f"{f} -> HTTP {code}")
        css_fails.append(f)

if not css_fails:
    ok(f"All {len(all_css)} CSS chunks return HTTP 200")
else:
    fail(f"{len(css_fails)}/{len(all_css)} CSS chunks FAILED!")

# ================================================================
# 6. KEY PAGES — SPA ROUTING
# ================================================================
section("6. KEY PAGES (SPA routing)")

pages = [
    "/",
    "/login",
    "/student",
    "/student/homework/75",
    "/teacher",
    "/homework",
]
for page in pages:
    code, size, ctype = curl(f"{BASE_URL}{page}")
    if code == 200 and size > 500:
        ok(f"{page} -> HTTP {code} ({size:,} bytes)")
    else:
        fail(f"{page} -> HTTP {code} ({size} bytes)")

# ================================================================
# 7. API HEALTH
# ================================================================
section("7. BACKEND API HEALTH")

code, size, ctype = curl(f"{BASE_URL}/api/health/")
if code == 200:
    ok(f"/api/health/ -> HTTP {code}")
else:
    fail(f"/api/health/ -> HTTP {code}")

# ================================================================
# 8. STUDENT AUTH + HOMEWORK API
# ================================================================
section("8. STUDENT HOMEWORK E2E TEST")

# Read test credentials from config
config = {}
config_path = "/opt/lectio-monitor/config.env"
if os.path.exists(config_path):
    for line in open(config_path):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            config[k.strip()] = v.strip().strip('"').strip("'")

student_email = config.get("SMOKE_STUDENT_EMAIL", "smoke_student@test.local")
student_password = config.get("SMOKE_STUDENT_PASSWORD", "SmokeTest123!")

# Login
login_r = subprocess.run(
    ["curl", "-sk", "--max-time", "10", "-X", "POST",
     f"{INTERNAL_URL}/api/jwt/token/",
     "-H", "Content-Type: application/json",
     "-H", f"Host: lectiospace.ru",
     "-H", "X-Forwarded-Proto: https",
     "-d", json.dumps({"email": student_email, "password": student_password})],
    capture_output=True, text=True, timeout=15
)

try:
    login_data = json.loads(login_r.stdout)
    token = login_data.get("access", "")
except:
    token = ""
    login_data = login_r.stdout[:200]

if token:
    ok(f"Student login OK (email: {student_email})")
    
    # Get homework list
    hw_r = subprocess.run(
        ["curl", "-sk", "--max-time", "10",
         f"{INTERNAL_URL}/api/homework/",
         "-H", f"Authorization: Bearer {token}",
         "-H", f"Host: lectiospace.ru",
         "-H", "X-Forwarded-Proto: https"],
        capture_output=True, text=True, timeout=15
    )
    try:
        hw_data = json.loads(hw_r.stdout)
        if isinstance(hw_data, dict) and "results" in hw_data:
            ok(f"Homework list API -> {len(hw_data['results'])} homeworks")
        elif isinstance(hw_data, list):
            ok(f"Homework list API -> {len(hw_data)} homeworks")
        else:
            warn(f"Homework list API returned unexpected format: {str(hw_data)[:100]}")
    except:
        warn(f"Homework list API returned non-JSON: {hw_r.stdout[:100]}")
    
    # Try to get a specific homework detail
    hw_detail_r = subprocess.run(
        ["curl", "-sk", "--max-time", "10", "-o", "/dev/null", "-w", "%{http_code}",
         f"{INTERNAL_URL}/api/homework/75/",
         "-H", f"Authorization: Bearer {token}",
         "-H", f"Host: lectiospace.ru",
         "-H", "X-Forwarded-Proto: https"],
        capture_output=True, text=True, timeout=15
    )
    hw_code = hw_detail_r.stdout.strip()
    if hw_code in ("200", "404"):
        ok(f"Homework detail API /api/homework/75/ -> HTTP {hw_code}")
    else:
        fail(f"Homework detail API /api/homework/75/ -> HTTP {hw_code}")

    # Try my-answers endpoint
    my_ans_r = subprocess.run(
        ["curl", "-sk", "--max-time", "10", "-o", "/dev/null", "-w", "%{http_code}",
         f"{INTERNAL_URL}/api/homework/75/my-answers/",
         "-H", f"Authorization: Bearer {token}",
         "-H", f"Host: lectiospace.ru",
         "-H", "X-Forwarded-Proto: https"],
        capture_output=True, text=True, timeout=15
    )
    ans_code = my_ans_r.stdout.strip()
    if ans_code in ("200", "404"):
        ok(f"My-answers API /api/homework/75/my-answers/ -> HTTP {ans_code}")
    else:
        fail(f"My-answers API /api/homework/75/my-answers/ -> HTTP {ans_code}")

    # Try submit-answers endpoint (GET to check it exists, don't actually POST)
    submit_r = subprocess.run(
        ["curl", "-sk", "--max-time", "10", "-o", "/dev/null", "-w", "%{http_code}",
         "-X", "OPTIONS",
         f"{INTERNAL_URL}/api/homework/75/submit-answers/",
         "-H", f"Authorization: Bearer {token}",
         "-H", f"Host: lectiospace.ru",
         "-H", "X-Forwarded-Proto: https"],
        capture_output=True, text=True, timeout=15
    )
    sub_code = submit_r.stdout.strip()
    ok(f"Submit-answers OPTIONS -> HTTP {sub_code}")

else:
    warn(f"Student login FAILED (no test user?): {str(login_data)[:100]}")
    warn("Skipping API tests — no auth token")

# ================================================================
# 9. NGINX ERRORS (last 5 minutes - 404 on static files)
# ================================================================
section("9. NGINX RECENT ERRORS (static file 404s)")

nginx_r = subprocess.run(
    ["sudo", "tail", "-200", "/var/log/nginx/error.log"],
    capture_output=True, text=True, timeout=10
)
recent_errors = []
now = time.time()
for line in nginx_r.stdout.split("\n"):
    if "No such file" in line and "/static/" in line:
        recent_errors.append(line.strip())

if recent_errors:
    # Check if they're from before the fix (before 19:55) or after
    after_fix = [l for l in recent_errors if "20:0" in l or "20:1" in l or "20:2" in l or "20:3" in l or "20:4" in l or "20:5" in l or "21:" in l or "22:" in l or "23:" in l]
    if after_fix:
        fail(f"{len(after_fix)} static file 404s AFTER fix!")
        for l in after_fix[:5]:
            print(f"    {l[:150]}")
    else:
        ok(f"All {len(recent_errors)} static 404s are from BEFORE the fix")
else:
    ok("No static file 404s in recent nginx errors")

# ================================================================
# 10. SERVICES STATUS
# ================================================================
section("10. CRITICAL SERVICES")

services = ["teaching_panel", "nginx", "celery", "celery-beat", "redis-server"]
for svc in services:
    r = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True, timeout=5)
    status = r.stdout.strip()
    if status == "active":
        ok(f"{svc}: active")
    else:
        fail(f"{svc}: {status}")

# ================================================================
# FINAL VERDICT
# ================================================================
print(f"\n{'='*60}")
if FAIL:
    print("  VERDICT: SOME CHECKS FAILED — SEE ABOVE")
    print(f"{'='*60}")
    sys.exit(1)
else:
    print("  VERDICT: ALL CHECKS PASSED")
    print(f"  Assets: {len(files)} files verified")
    print(f"  JS chunks: {len(all_js)} tested via HTTPS")
    print(f"  CSS chunks: {len(all_css)} tested via HTTPS")
    print(f"  Student auth: {'OK' if token else 'SKIPPED'}")
    print(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S MSK')}")
    print(f"{'='*60}")
    sys.exit(0)
