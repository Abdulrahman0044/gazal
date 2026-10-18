import os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
fd,path=tempfile.mkstemp(suffix='.sqlite3');os.close(fd);os.environ['PROMPTTO_DB']=path
from fastapi.testclient import TestClient
from app import app
client=TestClient(app)
def auth(email):
    r=client.post('/api/login',json={'email':email,'password':'DemoPass123!'})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}
def test_multi_tenant_and_task_workflow():
    ah=auth('admin@promptto.local'); mh=auth('manager@promptto.local');eh=auth('employee@promptto.local')
    all_accounts=client.get('/api/accounts',headers=ah).json()
    assert len(all_accounts)==2
    nov=next(x for x in all_accounts if x['name']=='Novetiv')['id'];other=next(x for x in all_accounts if x['name']=='Business B')['id']
    assert len(client.get('/api/accounts',headers=mh).json())==1
    assert client.get(f'/api/accounts/{other}/tasks',headers=mh).status_code==403
    p=client.get(f'/api/accounts/{nov}/projects',headers=mh).json()[0]['id']
    employee=next(x for x in client.get(f'/api/accounts/{nov}/employees',headers=mh).json() if x['role']=='employee')['id']
    assert client.post(f'/api/accounts/{nov}/tasks',headers=mh,json={'project_id':'wrong','title':'Nope'}).status_code==400
    assert client.post(f'/api/accounts/{nov}/tasks',headers=mh,json={'project_id':p,'assignee_id':ah['Authorization'],'title':'Nope'}).status_code==400
    r=client.post(f'/api/accounts/{nov}/tasks',headers=mh,json={'project_id':p,'assignee_id':employee,'title':'New test task','due_date':'2026-11-12'})
    assert r.status_code==201,r.text
    tid=r.json()['id']
    assert client.post(f'/api/accounts/{nov}/tasks/{tid}/transition',headers=eh,json={'status':'in_progress'}).status_code==200
    assert client.post(f'/api/accounts/{nov}/tasks/{tid}/transition',headers=eh,json={'status':'submitted'}).status_code==200
    assert client.post(f'/api/accounts/{nov}/tasks/{tid}/review',headers=eh,json={'decision':'approved','quality':90}).status_code==403
    assert client.post(f'/api/accounts/{nov}/tasks/{tid}/review',headers=mh,json={'decision':'approved','quality':90}).status_code==200
    assert len(client.get(f'/api/accounts/{nov}/tasks/{tid}/events',headers=mh).json())==4
    assert client.get(f'/api/accounts/{other}/tasks/{tid}/events',headers=eh).status_code==404
    assert client.get(f'/api/accounts/{nov}/dashboard',headers=mh).status_code==200
    assert client.get(f'/api/accounts/{nov}/performance',headers=mh).status_code==200
