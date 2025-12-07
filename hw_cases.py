import requests
BASE='http://127.0.0.1:8000'
TEACHER_EMAIL='hw-teacher@demo.local'
STUDENT_EMAIL='hw-student@demo.local'
PASSWORD='Test123!hw'
LESSON_ID=16
GROUP_ID=16

session=requests.Session()

def login(email,pw):
    r=session.post(f"{BASE}/api/jwt/token/", json={'email':email,'password':pw})
    r.raise_for_status()
    return r.json()['access']

token_t=login(TEACHER_EMAIL,PASSWORD)
token_s=login(STUDENT_EMAIL,PASSWORD)
headers_t={'Authorization': f'Bearer {token_t}'}
headers_s={'Authorization': f'Bearer {token_s}'}

homeworks=[]

hw1={
    'title':'HW QA Mixed Types',
    'description':'Text + single + multi + drag-drop placeholder',
    'lesson':LESSON_ID,
    'questions':[
        {'prompt':'Short text answer','question_type':'TEXT','points':5,'order':1,'config':{'correctAnswer':'any'}},
        {'prompt':'Single choice correctness','question_type':'SINGLE_CHOICE','points':3,'order':2,'choices':[{'text':'Correct','is_correct':True},{'text':'Wrong','is_correct':False}], 'config':{}},
        {'prompt':'Select all valid states','question_type':'MULTI_CHOICE','points':4,'order':3,'choices':[{'text':'draft','is_correct':True},{'text':'published','is_correct':True},{'text':'archived','is_correct':True},{'text':'deleted','is_correct':False}], 'config':{}},
        {'prompt':'Drag-drop placeholder','question_type':'DRAG_DROP','points':2,'order':4,'config':{'correctOrder':['A','B','C']}}
    ]
}

hw2={
    'title':'HW QA Quick Check',
    'description':'Single-question check',
    'lesson':LESSON_ID,
    'questions':[{'prompt':'Platform name?','question_type':'SINGLE_CHOICE','points':2,'order':1,'choices':[{'text':'Teaching Panel','is_correct':True},{'text':'Other','is_correct':False}], 'config':{}}]
}

for payload in (hw1, hw2):
    r=session.post(f"{BASE}/api/homework/", json=payload, headers=headers_t)
    r.raise_for_status()
    hw=r.json()
    homeworks.append(hw)
    r=session.post(f"{BASE}/api/homework/{hw['id']}/publish/", headers=headers_t)
    r.raise_for_status()

print('Created+published', [h['id'] for h in homeworks])

submissions=[]
for hw in homeworks:
    r=session.post(f"{BASE}/api/submissions/", json={'homework': hw['id']}, headers=headers_s)
    r.raise_for_status()
    submissions.append(r.json())

# HW1 answers
hw_detail=session.get(f"{BASE}/api/homework/{homeworks[0]['id']}/", headers=headers_s).json()
q_map={q['order']:q for q in hw_detail['questions']}
q2_choices=[c['id'] for c in q_map[2]['choices']]
q3_choices=[c['id'] for c in q_map[3]['choices']]
answers1={str(q_map[1]['id']): 'Sample text', str(q_map[2]['id']): q2_choices[0], str(q_map[3]['id']): q3_choices[:3], str(q_map[4]['id']): ['A','B','C']}

r=session.patch(f"{BASE}/api/submissions/{submissions[0]['id']}/answer/", json={'answers': answers1}, headers=headers_s)
r.raise_for_status()
r=session.post(f"{BASE}/api/submissions/{submissions[0]['id']}/submit/", json={}, headers=headers_s)
r.raise_for_status()

# HW2 answers
hw2_detail=session.get(f"{BASE}/api/homework/{homeworks[1]['id']}/", headers=headers_s).json()
q2map={q['order']:q for q in hw2_detail['questions']}
choices_q1=[c['id'] for c in q2map[1]['choices']]
answers2={str(q2map[1]['id']): choices_q1[0]}

r=session.patch(f"{BASE}/api/submissions/{submissions[1]['id']}/answer/", json={'answers': answers2}, headers=headers_s)
r.raise_for_status()
r=session.post(f"{BASE}/api/submissions/{submissions[1]['id']}/submit/", json={}, headers=headers_s)
r.raise_for_status()

print('Submissions done', [s['id'] for s in submissions])
