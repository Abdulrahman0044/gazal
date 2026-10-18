from datetime import datetime,timezone,timedelta
from test_app import client,auth
from app import conn

def ctx():
 h=auth('manager@promptto.local');eh=auth('employee@promptto.local');a=client.get('/api/accounts',headers=h).json()[0]['id'];employee=client.get('/api/me',headers=eh).json()['id'];return h,eh,a,employee

def test_remote_work_sessions_isolation_and_presence():
 h,eh,a,e=ctx();b=f'/api/accounts/{a}';tasks=client.get(b+'/tasks',headers=eh).json();task=next(t for t in tasks if t['status'] not in ['approved','cancelled'])
 r=client.post(b+'/work-sessions',headers=eh,json={'task_id':task['id']});assert r.status_code==201,r.text;s=r.json()['session']['id']
 r2=client.post(b+'/work-sessions',headers=eh,json={'task_id':task['id']});assert r2.json()['already_active'] and r2.json()['session']['id']==s
 assert client.post(b+f'/work-sessions/{s}/status',headers=h,json={'status':'break'}).status_code==404
 assert client.post(b+f'/work-sessions/{s}/status',headers=eh,json={'status':'invalid'}).status_code==422
 assert client.post(b+f'/work-sessions/{s}/status',headers=eh,json={'status':'break','task_id':task['id']}).status_code==200
 assert client.get(b+'/workday',headers=eh).json()['active_session']['status']=='break'
 assert client.get(b+'/remote-team',headers=eh).status_code==403
 assert client.post(b+'/presence',headers=eh,json={}).status_code==200
 team=client.get(b+'/remote-team',headers=h).json()['employees'];member=next(m for m in team if m['id']==e);assert member['connection']=='connected' and member['availability']=='break'
 before=client.get(b+'/scores',headers=h).json()
 with conn() as c:c.execute('UPDATE employee_presence SET last_seen=? WHERE account_id=? AND user_id=?',((datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat(),a,e))
 team=client.get(b+'/remote-team',headers=h).json()['employees'];member=next(m for m in team if m['id']==e);assert member['connection']=='offline' and member['session']['id']==s
 assert client.get(b+'/scores',headers=h).json()==before
 other=next(x for x in client.get('/api/accounts',headers=eh).json() if x['id']!=a)['id']
 assert client.post(f'/api/accounts/{other}/work-sessions/{s}/end',headers=eh,json={}).status_code==404
 assert client.post(b+f'/work-sessions/{s}/end',headers=eh,json={}).status_code==200
 assert client.post(b+f'/work-sessions/{s}/end',headers=eh,json={}).status_code==200
 assert client.get(b+'/workday',headers=eh).json()['active_session'] is None
 assert client.get(b+'/workday',headers=h).json()['sessions']==[]

def test_daily_updates_and_blocker_alerts():
 h,eh,a,e=ctx();b=f'/api/accounts/{a}';payload={'priorities':'Deliver task work','achievements':'Prepared testing evidence','blockers':'Waiting for API access'}
 for _ in range(2):assert client.post(b+'/daily-updates',headers=eh,json=payload).status_code==200
 d=client.get(b+'/workday',headers=eh).json();assert d['daily_update']['blockers']==payload['blockers']
 notes=client.get(b+'/notifications',headers=h).json();assert sum(n['title']=='Remote-work blocker' and 'Waiting for API access' in n['message'] for n in notes)==1
 with conn() as c:assert c.execute('SELECT count(*) FROM daily_update_events WHERE account_id=? AND user_id=?',(a,e)).fetchone()[0]>=2

def test_correction_keeps_original_and_requires_other_admin():
 h,eh,a,e=ctx();b=f'/api/accounts/{a}';s=client.post(b+'/work-sessions',headers=eh,json={}).json()['session']['id'];client.post(b+f'/work-sessions/{s}/end',headers=eh,json={})
 now=datetime.now(timezone.utc);start=(now-timedelta(hours=3)).isoformat();end=(now-timedelta(hours=2)).isoformat()
 body={'session_id':s,'requested_start':start,'requested_end':end,'reason':'Correct the recorded work session times'}
 assert client.post(b+'/time-corrections',headers=eh,json={**body,'requested_end':(now+timedelta(hours=1)).isoformat()}).status_code==422
 r=client.post(b+'/time-corrections',headers=eh,json=body);assert r.status_code==201,r.text;i=r.json()['id']
 assert client.post(b+'/time-corrections',headers=eh,json=body).status_code==409
 assert client.post(b+f'/time-corrections/{i}/decision',headers=eh,json={'decision':'approved','notes':'Correction is verified'}).status_code==403
 with conn() as c:original=dict(c.execute('SELECT * FROM work_sessions WHERE id=?',(s,)).fetchone())
 assert client.post(b+f'/time-corrections/{i}/decision',headers=h,json={'decision':'approved','notes':'Correction is verified'}).status_code==200
 assert client.post(b+f'/time-corrections/{i}/decision',headers=h,json={'decision':'approved','notes':'Correction is verified'}).status_code==409
 with conn() as c:assert dict(c.execute('SELECT * FROM work_sessions WHERE id=?',(s,)).fetchone())==original
 hist=client.get(b+f'/remote-team/{e}/sessions',headers=h).json();assert next(x for x in hist if x['id']==s)['approved_duration_seconds']==3600


def test_overnight_session_duration_and_no_task_stealing():
 h,eh,a,e=ctx();b=f'/api/accounts/{a}';s=client.post(b+'/work-sessions',headers=eh,json={}).json()['session']['id'];old=(datetime.now(timezone.utc)-timedelta(hours=10)).isoformat()
 with conn() as c:
  c.execute('UPDATE work_sessions SET started_at=? WHERE id=?',(old,s));c.execute('UPDATE work_session_events SET created_at=? WHERE session_id=?',(old,s))
 d=client.get(b+'/workday',headers=eh).json();assert d['active_session']['duration_seconds']>=36000
 assert client.post(b+'/work-sessions',headers=h,json={'task_id':client.get(b+'/tasks',headers=eh).json()[0]['id']}).status_code==422
 client.post(b+f'/work-sessions/{s}/end',headers=eh,json={})

def test_daily_report_splits_midnight_and_checks_access():
 from zoneinfo import ZoneInfo
 from app import uid,now
 h,eh,a,e=ctx();manager=client.get('/api/me',headers=h).json()['id'];day=(datetime.now(ZoneInfo('Africa/Lagos'))-timedelta(days=2)).date();boundary=datetime.combine(day,datetime.min.time(),ZoneInfo('Africa/Lagos')).astimezone(timezone.utc);start=(boundary-timedelta(minutes=30)).isoformat();end=(boundary+timedelta(minutes=30)).isoformat();sid=uid()
 with conn() as c:
  c.execute('INSERT INTO work_sessions VALUES(?,?,?,?,?,?,?,?)',(sid,a,manager,None,'working',start,end,end));c.execute('INSERT INTO work_session_events VALUES(?,?,?,?,?,?,?,?)',(uid(),a,sid,manager,'working',None,'Historical test session',start))
 b=f'/api/accounts/{a}/work-report?day={day}&employee={manager}'
 assert client.get(b,headers=eh).status_code==403
 r=client.get(b,headers=h);assert r.status_code==200;assert r.json()['recorded_seconds']==1800 and r.json()['status_seconds']['working']==1800

def test_parallel_starts_share_one_active_session():
 from concurrent.futures import ThreadPoolExecutor
 h,eh,a,e=ctx();b=f'/api/accounts/{a}'
 with ThreadPoolExecutor(max_workers=4) as pool:responses=list(pool.map(lambda _:client.post(b+'/work-sessions',headers=eh,json={}),range(4)))
 assert all(r.status_code==201 for r in responses),[r.text for r in responses]
 assert len({r.json()['session']['id'] for r in responses})==1
 sid=responses[0].json()['session']['id'];client.post(b+f'/work-sessions/{sid}/end',headers=eh,json={})
