import secrets
from test_app import client,auth

def ctx():
 h=auth('manager@promptto.local');a=client.get('/api/accounts',headers=h).json()[0]['id'];p=client.get(f'/api/accounts/{a}/projects',headers=h).json()[0]['id'];return h,a,p

def test_invitation_signup_and_login():
 h,a,p=ctx();email='invite-'+secrets.token_hex(4)+'@example.com';body={'name':'Invited Employee','email':email,'project_id':p}
 eh=auth('employee@promptto.local');assert client.post(f'/api/accounts/{a}/invitations',headers=eh,json=body).status_code==403
 r=client.post(f'/api/accounts/{a}/invitations',headers=h,json=body);assert r.status_code==201,r.text;tok=r.json()['invite_link'].split('token=')[1]
 assert client.post('/api/invitations/inspect',json={'token':tok}).json()['existing_user']==False
 assert client.post('/api/invitations/accept',json={'token':tok,'password':'short'}).status_code==422
 assert client.post('/api/invitations/accept',json={'token':tok,'password':'SecureJoinPass2026!'}).status_code==200
 assert client.post('/api/invitations/accept',json={'token':tok,'password':'SecureJoinPass2026!'}).status_code==410
 r=client.post('/api/login',json={'email':email,'password':'SecureJoinPass2026!','portal':'employee'});assert r.status_code==200;joined={'Authorization':'Bearer '+r.json()['token']}
 assert client.post('/api/login',json={'email':email,'password':'SecureJoinPass2026!','portal':'admin'}).status_code==200
 notes=client.get(f'/api/accounts/{a}/notifications',headers=joined).json();assert notes and notes[0]['title']=='Welcome to Gazal'
 nid=notes[0]['id'];assert client.post(f'/api/accounts/{a}/notifications/{nid}/read',headers=eh).status_code==404
 assert client.post(f'/api/accounts/{a}/notifications/{nid}/read',headers=joined).status_code==200
 assert 'token_hash' not in client.get(f'/api/accounts/{a}/invitations',headers=h).text
 from app import conn
 with conn() as c:assert c.execute('SELECT count(*) FROM project_members WHERE account_id=? AND project_id=?',(a,p)).fetchone()[0]>=1

def test_existing_user_cannot_be_reset_or_promoted():
 h,a,p=ctx();r=client.post(f'/api/accounts/{a}/invitations',headers=h,json={'name':'Existing','email':'employee@promptto.local','project_id':p,'role':'account_admin'});tok=r.json()['invite_link'].split('token=')[1]
 assert client.post('/api/invitations/accept',json={'token':tok,'password':'OverwritePassword123!'}).status_code==401
 assert client.post('/api/invitations/accept',headers=h,json={'token':tok}).status_code==403
 eh=auth('employee@promptto.local');assert client.post('/api/invitations/accept',headers=eh,json={'token':tok}).status_code==200
 accounts=client.get('/api/accounts',headers=eh).json();assert next(x for x in accounts if x['id']==a)['role']=='employee'

def test_task_notifications_and_due_reminders():
 h,a,p=ctx();eh=auth('employee@promptto.local');employee=next(e['id'] for e in client.get(f'/api/accounts/{a}/employees',headers=h).json() if e['email']=='employee@promptto.local')
 r=client.post(f'/api/accounts/{a}/tasks',headers=h,json={'title':'Notification test','project_id':p,'assignee_id':employee,'due_date':'2026-01-01'});assert r.status_code==201
 notes=client.get(f'/api/accounts/{a}/notifications',headers=eh).json();assert any(n['title']=='New task assigned' and 'Notification test' in n['message'] for n in notes)
 assert client.post(f'/api/accounts/{a}/task-reminders',headers=eh).status_code==403
 assert client.post(f'/api/accounts/{a}/task-reminders',headers=h).json()['created']>=1
 assert client.post(f'/api/accounts/{a}/task-reminders',headers=h).json()['created']==0
 assert client.get('/admin/login').status_code==200 and client.get('/employee/login').status_code==200
