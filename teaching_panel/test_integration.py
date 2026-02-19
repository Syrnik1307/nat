#!/usr/bin/env python
"""Quick integration test for tenant system."""
import urllib.request
import json

BASE = 'http://127.0.0.1:8000'

def api(method, path, data=None, headers=None):
    hdrs = headers or {}
    hdrs['Content-Type'] = 'application/json'
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f'{BASE}{path}', data=body, headers=hdrs, method=method)
    try:
        r = urllib.request.urlopen(req)
        raw = r.read()
        try:
            return r.status, json.loads(raw)
        except json.JSONDecodeError:
            return r.status, raw.decode()[:200]
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw.decode()[:200]

# 1. JWT Login
code, tokens = api('POST', '/api/jwt/token/', {'email': 'olga@olgaflowers.ru', 'password': 'Test12345!'})
print(f'1. JWT Login: {code}')
assert code == 200, f'Expected 200, got {code}: {tokens}'
access = tokens['access']
auth = {'Authorization': f'Bearer {access}'}

# 2. My tenants
code, tenants = api('GET', '/api/tenants/my/', headers=auth)
print(f'2. My tenants: {code}, count={len(tenants)}')
for t in tenants:
    name = t['tenant']['name']
    slug = t['tenant']['slug']
    role = t['role']
    print(f'   - {name} (slug={slug}) role={role}')

# 3. Olga public branding
code, brand = api('GET', '/api/tenants/public/olga/branding/')
print(f'3. Public branding: {code}, name={brand["name"]}, color={brand["metadata"]["theme"]["primary_color"]}')

def get_results(resp):
    """Handle both paginated and non-paginated responses."""
    if isinstance(resp, dict) and 'results' in resp:
        return resp['results']
    if isinstance(resp, list):
        return resp
    return []

# 4. Groups list (tenant-scoped, should be empty initially)
hdrs_olga = {**auth, 'X-Tenant-ID': 'olga'}
code, resp4 = api('GET', '/api/groups/', headers=hdrs_olga)
olga_groups_before = get_results(resp4)
print(f'4. Groups (olga): {code}, count={len(olga_groups_before)}')

# 5. Create a group in Olga tenant
code, group = api('POST', '/api/groups/', {'name': 'Фарфоровые розы', 'description': 'Курс по созданию роз'}, headers=hdrs_olga)
print(f'5. Create group: {code}, id={group.get("id", "?")}')
assert code == 201, f'Expected 201, got {code}: {group}'

# 6. Check group is visible in Olga scoped tenant
code, resp6a = api('GET', '/api/groups/', headers=hdrs_olga)
olga_groups = get_results(resp6a)
hdrs_default = {**auth, 'X-Tenant-ID': 'default'}
code2, resp6b = api('GET', '/api/groups/', headers=hdrs_default)
default_groups = get_results(resp6b)
print(f'6. Isolation: olga={len(olga_groups)} groups, default={len(default_groups)} groups')
assert len(olga_groups) >= 1, 'Olga should have at least 1 group'
assert len(default_groups) == 0, f'Default should have 0 groups, got {len(default_groups)}'

# 7. Lessons calendar (tenant-scoped)
code, cal = api('GET', '/api/lessons/calendar/', headers=hdrs_olga)
print(f'7. Calendar (olga): {code}')

print()
print('=== ALL TESTS PASSED ===')
