import requests
BASE='http://127.0.0.1:8000'
TEACHER_EMAIL='hw-teacher@demo.local'
STUDENT_EMAIL='hw-student@demo.local'
PASSWORD='Test123!hw'
GROUP_ID=16

s=requests.Session()

def login(email,pw):
    r=s.post(f"{BASE}/api/jwt/token/", json={'email':email,'password':pw})
    r.raise_for_status(); return r.json()['access']

at=login(TEACHER_EMAIL,PASSWORD)
as_ = login(STUDENT_EMAIL,PASSWORD)
ht={'Authorization': f'Bearer {at}'}

# teacher filtered list
r=s.get(f"{BASE}/api/submissions/", params={'status':'submitted','group_id':GROUP_ID}, headers=ht)
r.raise_for_status(); data=r.json()
print('Filtered submitted count', len(data.get('results', data)))

# get all for teacher
r=s.get(f"{BASE}/api/submissions/", headers=ht)
r.raise_for_status(); all_data=r.json();
print('All submissions count', len(all_data.get('results', all_data)))

# show statuses
items=all_data.get('results', all_data)
for it in items:
    print(it['id'], it['homework'], it['status'], it.get('total_score'))
