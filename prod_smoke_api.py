#!/usr/bin/env python
import json
import urllib.request
import urllib.parse
import urllib.error
import datetime
import ssl
import django
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

django.setup()

ssl._create_default_https_context = ssl._create_unverified_context

user = get_user_model().objects.get(email='syrnik1307@gmail.com')
tok = str(RefreshToken.for_user(user).access_token)
import os

base = os.environ.get('TP_BASE_URL', 'https://lectio.tw1.ru').rstrip('/')
headers = {'Authorization': 'Bearer ' + tok}


def call(method, url, data=None):
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode('utf-8', 'ignore')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'ignore')


code, body = call('GET', base + '/api/me/')
print('ME', code)
print(body[:200])

now = datetime.datetime.now()
day = now.strftime('%Y-%m-%d')
qs = urllib.parse.urlencode({'start': day+'T00:00:00', 'end': day+'T23:59:59', 'include_recurring': 'true'})
code, body = call('GET', base + '/api/schedule/lessons/?' + qs)
print('LESSONS', code)
try:
    data = json.loads(body) if body else {}
    items = data.get('results', data if isinstance(data, list) else [])
except Exception:
    items = []
real = []
for it in items:
    lid = it.get('id'); dt = it.get('start_time')
    if isinstance(lid, int) and dt:
        real.append((dt, lid))
real = sorted(real)
print('LESSONS_COUNT', len(real))
found = False
for dt, lid in real[:5]:
    url = base + '/api/schedule/lessons/{}/join/'.format(lid)
    c, b = call('POST', url, data=b'{}')
    print('JOIN_TRY', lid, c)
    if c == 200:
        try:
            jd = json.loads(b)
            print('JOIN_OK', lid, 'has_url', bool(jd.get('zoom_join_url')))
        except Exception as e:
            print('JOIN_PARSE_ERR', e)
        found = True
        break
print('JOIN_RESULT', found)
