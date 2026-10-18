import secrets
from test_app import client,auth

def test_auth_pages_are_dedicated_and_no_role_self_registration():
 for path in ['/signin','/signup','/employee/login','/employee/signup','/admin/login','/admin/signup','/join']:
  r=client.get(path);assert r.status_code==200
  assert 'id="signinForm"' in r.text and 'id="signupForm"' in r.text
  assert '/static/auth.js' in r.text and 'name="role"' not in r.text
 assert client.get('/static/auth.css').status_code==200 and client.get('/static/auth.js').status_code==200

def test_signup_then_signin_and_portal_access():
 h=auth('manager@promptto.local');a=client.get('/api/accounts',headers=h).json()[0]['id'];email='signup-'+secrets.token_hex(3)+'@example.com'
 r=client.post(f'/api/accounts/{a}/invitations',headers=h,json={'email':email,'name':'Signup Test','role':'employee'});token=r.json()['invite_link'].split('token=')[1]
 info=client.post('/api/invitations/inspect',json={'token':token}).json();assert info['role']=='employee' and info['email']==email
 assert client.post('/api/invitations/accept',json={'token':token,'password':'SignupPassword2026!'}).status_code==200
 r=client.post('/api/login',json={'email':email,'password':'SignupPassword2026!','portal':'employee'});assert r.status_code==200
 joined={'Authorization':'Bearer '+r.json()['token']};assert any(x['id']==a for x in client.get('/api/accounts',headers=joined).json())
 assert client.post('/api/login',json={'email':email,'password':'SignupPassword2026!','portal':'admin'}).status_code==200
 assert client.post('/api/login',json={'email':email,'password':'WrongPassword123!','portal':'employee'}).status_code==401

def test_create_account_redirects_to_signup():
 r=client.get('/create-account',follow_redirects=False);assert r.status_code==307 and r.headers['location']=='/signup'
 assert 'id="signupForm"' in client.get(r.headers['location']).text

def test_unified_signup_and_landing_routes():
 email='public-'+secrets.token_hex(4)+'@example.com';payload={'name':'New Gazal User','email':email,'password':'UnifiedSignup2026!','is_super':True,'role':'account_admin'}
 r=client.post('/api/signup',json=payload);assert r.status_code==201,r.text
 assert client.post('/api/signup',json=payload).status_code==409
 assert client.post('/api/signup',json={**payload,'email':'invalid'}).status_code==422
 r=client.post('/api/login',json={'email':email,'password':payload['password']});assert r.status_code==200
 h={'Authorization':'Bearer '+r.json()['token']};assert not r.json()['user']['is_super'];assert client.get('/api/accounts',headers=h).json()==[]
 assert client.post('/api/accounts',headers=h,json={'name':'Unauthorized'}).status_code==403
 html=client.get('/').text;assert 'Your business growth.' in html and html.count('href="/signin"')>=3
 assert 'id="app"' in client.get('/app').text
 for path in ['/admin/login','/employee/login']:
  r=client.get(path,follow_redirects=False);assert r.status_code==307 and r.headers['location']=='/signin'
 assert 'employeePortal' not in client.get('/signup').text
