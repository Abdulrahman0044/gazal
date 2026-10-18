import secrets
from test_app import client,auth

def test_all_performance_apis_admin_only():
 admin=auth('manager@promptto.local');a=client.get('/api/accounts',headers=admin).json()[0]['id'];superadmin=auth('admin@promptto.local')
 for role in ['employee','project_manager','team_lead','hr_manager']:
  email=role+secrets.token_hex(3)+'@test.example';password='RoleTestPassword2026!'
  r=client.post(f'/api/accounts/{a}/employees',headers=admin,json={'name':'Role Test','email':email,'password':password,'role':role});assert r.status_code==201
  r=client.post('/api/login',json={'email':email,'password':password});h={'Authorization':'Bearer '+r.json()['token']}
  for endpoint in ['scores','performance','scoring-policy']:assert client.get(f'/api/accounts/{a}/{endpoint}',headers=h).status_code==403
  assert client.get(f'/api/accounts/{a}/notifications',headers=h).status_code==200
 for h in [admin,superadmin]:
  for endpoint in ['scores','performance','scoring-policy']:assert client.get(f'/api/accounts/{a}/{endpoint}',headers=h).status_code==200

def test_project_membership_and_invite_revocation():
 h=auth('manager@promptto.local');eh=auth('employee@promptto.local');a=client.get('/api/accounts',headers=h).json()[0]['id'];p=client.get(f'/api/accounts/{a}/projects',headers=h).json()[0]['id'];e=client.get('/api/me',headers=eh).json()['id'];base=f'/api/accounts/{a}'
 assert client.post(base+f'/projects/{p}/members',headers=eh,json={'user_id':e}).status_code==403
 assert client.post(base+f'/projects/{p}/members',headers=h,json={'user_id':'unknown'}).status_code==422
 assert client.post(base+f'/projects/{p}/members',headers=h,json={'user_id':e}).status_code==201
 assert all(m['user_id']==e for m in client.get(base+f'/projects/{p}/members',headers=eh).json())
 r=client.post(base+'/invitations',headers=h,json={'email':'revoked'+secrets.token_hex(3)+'@example.com','name':'Revoked Person'});ident=r.json()['id'];token=r.json()['invite_link'].split('token=')[1]
 assert client.post(base+f'/invitations/{ident}/revoke',headers=eh).status_code==403
 assert client.post(base+f'/invitations/{ident}/revoke',headers=h).status_code==200
 assert client.post('/api/invitations/inspect',json={'token':token}).status_code==410
