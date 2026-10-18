"""Visible remote-work sessions. Connection presence never determines productivity."""
import os,json
from datetime import datetime,timezone,timedelta,date
from zoneinfo import ZoneInfo
from fastapi import Depends,HTTPException
from pydantic import BaseModel,Field
STATUSES={'working','meeting','break','away'}
def dt(s):return datetime.fromisoformat(s)
def elapsed(start,end):return max(0,int((dt(end)-dt(start)).total_seconds()))
def session_summary(c,r,stamp):
 if not r:return None
 r=dict(r);end=r['ended_at'] or stamp;events=[dict(e) for e in c.execute('SELECT * FROM work_session_events WHERE session_id=? AND account_id=? ORDER BY created_at,id',(r['id'],r['account_id']))]
 totals={s:0 for s in STATUSES};task_time={};cursor=r['started_at'];status='working';task=None
 for e in events:
  if e['created_at']>end:break
  duration=elapsed(cursor,e['created_at']);totals[status]+=duration
  if task and status=='working':task_time[task]=task_time.get(task,0)+duration
  cursor=e['created_at'];status=e['status'];task=e['task_id']
 duration=elapsed(cursor,end);totals[status]+=duration
 if task and status=='working':task_time[task]=task_time.get(task,0)+duration
 r.update(duration_seconds=elapsed(r['started_at'],end),status_seconds=totals,task_seconds=task_time,server_now=stamp)
 correction=c.execute("SELECT requested_start,requested_end,id FROM time_corrections WHERE session_id=? AND account_id=? AND decision='approved' ORDER BY decided_at DESC LIMIT 1",(r['id'],r['account_id'])).fetchone()
 r['approved_duration_seconds']=elapsed(correction['requested_start'],correction['requested_end']) if correction else None
 r['correction_id']=correction['id'] if correction else None
 return r

def daily_report(c,a,user,day,stamp):
 start=datetime.combine(day,datetime.min.time(),ZoneInfo('Africa/Lagos')).astimezone(timezone.utc);finish=start+timedelta(days=1);cutoff=min(finish,dt(stamp));totals={s:0 for s in STATUSES};task_seconds={};recorded=0;adjusted=0
 def clipped(x,y):return max(0,int((min(dt(y),cutoff)-max(dt(x),start)).total_seconds()))
 rows=c.execute("""SELECT * FROM work_sessions WHERE account_id=? AND user_id=? AND (started_at<? AND (ended_at IS NULL OR ended_at>?) OR id IN (SELECT session_id FROM time_corrections WHERE account_id=? AND user_id=? AND decision='approved' AND requested_start<? AND requested_end>?))""",(a,user,finish.isoformat(),start.isoformat(),a,user,finish.isoformat(),start.isoformat())).fetchall()
 for r in rows:
  end=r['ended_at'] or stamp;recorded+=clipped(r['started_at'],end);cursor=r['started_at'];status='working';task=None
  for e in c.execute('SELECT * FROM work_session_events WHERE account_id=? AND session_id=? ORDER BY created_at,id',(a,r['id'])):
   if e['created_at']>end:break
   seconds=clipped(cursor,e['created_at']);totals[status]+=seconds
   if task and status=='working':task_seconds[task]=task_seconds.get(task,0)+seconds
   cursor=e['created_at'];status=e['status'];task=e['task_id']
  seconds=clipped(cursor,end);totals[status]+=seconds
  if task and status=='working':task_seconds[task]=task_seconds.get(task,0)+seconds
  correction=c.execute("SELECT requested_start,requested_end FROM time_corrections WHERE account_id=? AND session_id=? AND decision='approved' ORDER BY decided_at DESC LIMIT 1",(a,r['id'])).fetchone()
  adjusted+=clipped(correction['requested_start'],correction['requested_end']) if correction else clipped(r['started_at'],end)
 return {'day':day.isoformat(),'recorded_seconds':recorded,'approved_adjusted_seconds':adjusted,'status_seconds':totals,'task_seconds':task_seconds,'timezone':'Africa/Lagos'}

def install(app,conn,current,enforce,uid,now):
 class Start(BaseModel):task_id:str|None=None
 class Change(BaseModel):status:str;task_id:str|None=None;note:str=Field(default='',max_length=1000)
 class Daily(BaseModel):priorities:str=Field(default='',max_length=4000);achievements:str=Field(default='',max_length=4000);blockers:str=Field(default='',max_length=4000)
 class Correction(BaseModel):session_id:str;requested_start:datetime;requested_end:datetime;reason:str=Field(min_length=10,max_length=1000)
 class Decision(BaseModel):decision:str;notes:str=Field(min_length=10,max_length=1000)
 def own(c,a,s,u):
  r=c.execute('SELECT * FROM work_sessions WHERE account_id=? AND id=? AND user_id=?',(a,s,u['id'])).fetchone()
  if not r:raise HTTPException(404,'Work session not found')
  return r
 def task(c,a,t,u):
  if t and not c.execute("SELECT 1 FROM tasks WHERE account_id=? AND id=? AND assignee_id=? AND status NOT IN ('approved','cancelled')",(a,t,u['id'])).fetchone():raise HTTPException(422,'Choose your own open task in this account')
 def log(c,a,s,u,status,t,note):c.execute('INSERT INTO work_session_events VALUES(?,?,?,?,?,?,?,?)',(uid(),a,s,u['id'],status,t,note,now()))
 @app.post('/api/accounts/{a}/presence')
 def heartbeat(a:str,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a);stamp=now();c.execute('INSERT INTO employee_presence VALUES(?,?,?) ON CONFLICT(account_id,user_id) DO UPDATE SET last_seen=excluded.last_seen',(a,u['id'],stamp))
  return {'last_seen':stamp,'heartbeat_seconds':30}
 @app.get('/api/accounts/{a}/workday')
 def workday(a:str,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a);stamp=now();active=c.execute('SELECT * FROM work_sessions WHERE account_id=? AND user_id=? AND ended_at IS NULL',(a,u['id'])).fetchone()
   sessions=[session_summary(c,r,stamp) for r in c.execute('SELECT * FROM work_sessions WHERE account_id=? AND user_id=? ORDER BY started_at DESC LIMIT 30',(a,u['id']))]
   day=datetime.now(ZoneInfo('Africa/Lagos')).date().isoformat();update=c.execute('SELECT * FROM daily_updates WHERE account_id=? AND user_id=? AND day=?',(a,u['id'],day)).fetchone();corrections=[dict(r) for r in c.execute('SELECT * FROM time_corrections WHERE account_id=? AND user_id=? ORDER BY created_at DESC LIMIT 30',(a,u['id']))]
   return {'active_session':session_summary(c,active,stamp),'sessions':sessions,'daily_update':dict(update) if update else None,'corrections':corrections,'server_now':stamp,'day':day,'report_today':daily_report(c,a,u['id'],date.fromisoformat(day),stamp)}
 @app.post('/api/accounts/{a}/work-sessions',status_code=201)
 def start(a:str,b:Start,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a);task(c,a,b.task_id,u);ident=uid();stamp=now()
   inserted=c.execute("INSERT INTO work_sessions VALUES(?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING RETURNING id",(ident,a,u['id'],b.task_id,'working',stamp,None,stamp)).fetchone()
   if inserted:log(c,a,ident,u,'working',b.task_id,'Session started')
   r=c.execute('SELECT * FROM work_sessions WHERE account_id=? AND user_id=? AND ended_at IS NULL',(a,u['id'])).fetchone()
   return {'session':session_summary(c,r,now()),'already_active':not bool(inserted)}
 @app.post('/api/accounts/{a}/work-sessions/{s}/status')
 def change(a:str,s:str,b:Change,u=Depends(current)):
  if b.status not in STATUSES:raise HTTPException(422,'Invalid availability status')
  with conn() as c:
   enforce(c,u,a);r=own(c,a,s,u)
   if r['ended_at']:raise HTTPException(409,'Session already ended')
   task(c,a,b.task_id,u)
   if b.status==r['status'] and b.task_id==r['task_id']:return session_summary(c,r,now())
   updated=c.execute('UPDATE work_sessions SET status=?,task_id=?,updated_at=? WHERE id=? AND account_id=? AND user_id=? AND ended_at IS NULL AND updated_at=? RETURNING id',(b.status,b.task_id,now(),s,a,u['id'],r['updated_at'])).fetchone()
   if not updated:raise HTTPException(409,'Session changed in another tab; refresh and retry')
   log(c,a,s,u,b.status,b.task_id,b.note);return session_summary(c,own(c,a,s,u),now())
 @app.post('/api/accounts/{a}/work-sessions/{s}/end')
 def end(a:str,s:str,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a);r=own(c,a,s,u)
   stamp=now();changed=c.execute('UPDATE work_sessions SET ended_at=?,updated_at=? WHERE id=? AND account_id=? AND user_id=? AND ended_at IS NULL RETURNING id',(stamp,stamp,s,a,u['id'])).fetchone()
   if changed:log(c,a,s,u,r['status'],r['task_id'],'Session ended')
   return session_summary(c,own(c,a,s,u),now())
 @app.post('/api/accounts/{a}/daily-updates')
 def update(a:str,b:Daily,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a);day=datetime.now(ZoneInfo('Africa/Lagos')).date().isoformat();old=c.execute('SELECT blockers FROM daily_updates WHERE account_id=? AND user_id=? AND day=?',(a,u['id'],day)).fetchone();payload=b.model_dump()
   c.execute('INSERT INTO daily_updates VALUES(?,?,?,?,?,?,?) ON CONFLICT(account_id,user_id,day) DO UPDATE SET priorities=excluded.priorities,achievements=excluded.achievements,blockers=excluded.blockers,updated_at=excluded.updated_at',(a,u['id'],day,b.priorities,b.achievements,b.blockers,now()))
   c.execute('INSERT INTO daily_update_events VALUES(?,?,?,?,?,?)',(uid(),a,u['id'],day,json.dumps(payload),now()))
   if b.blockers.strip() and (not old or old['blockers']!=b.blockers):
    from collaboration import notify
    for manager in c.execute("SELECT user_id FROM memberships WHERE account_id=? AND active=1 AND role='account_admin'",(a,)):
     notify(c,a,manager['user_id'],'Remote-work blocker',u['name']+' reported: '+b.blockers[:500],uid,now)
  return {'ok':True}
 @app.post('/api/accounts/{a}/time-corrections',status_code=201)
 def correction(a:str,b:Correction,u=Depends(current)):
  if b.requested_start.tzinfo is None or b.requested_end.tzinfo is None:raise HTTPException(422,'Use timezone-aware timestamps')
  start=b.requested_start.astimezone(timezone.utc);end=b.requested_end.astimezone(timezone.utc)
  if end<=start or end>datetime.now(timezone.utc)+timedelta(seconds=5) or end-start>timedelta(hours=48):raise HTTPException(422,'Correction must cover 0–48 hours and cannot end in the future')
  with conn() as c:
   enforce(c,u,a);r=own(c,a,b.session_id,u)
   if not r['ended_at']:raise HTTPException(409,'End the session before requesting a correction')
   if c.execute("SELECT 1 FROM time_corrections WHERE account_id=? AND session_id=? AND decision='pending'",(a,b.session_id)).fetchone():raise HTTPException(409,'A correction is already pending')
   ident=uid();inserted=c.execute('INSERT INTO time_corrections VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING RETURNING id',(ident,a,b.session_id,u['id'],start.isoformat(),end.isoformat(),b.reason,'pending',None,None,None,now())).fetchone()
   if not inserted:raise HTTPException(409,'A correction is already pending')
   return {'id':ident}
 @app.get('/api/accounts/{a}/time-corrections')
 def corrections(a:str,u=Depends(current)):
  with conn() as c:
   role=enforce(c,u,a);sql='SELECT tc.*,u.name FROM time_corrections tc JOIN users u ON u.id=tc.user_id WHERE tc.account_id=?';params=[a]
   if role not in {'account_admin','super_admin'}:sql+=' AND tc.user_id=?';params.append(u['id'])
   return [dict(r) for r in c.execute(sql+' ORDER BY tc.created_at DESC LIMIT 100',params)]
 @app.post('/api/accounts/{a}/time-corrections/{i}/decision')
 def decide(a:str,i:str,b:Decision,u=Depends(current)):
  if b.decision not in {'approved','rejected'}:raise HTTPException(422,'Invalid decision')
  with conn() as c:
   if not os.getenv('SUPABASE_DB_URL'):c.execute('BEGIN IMMEDIATE')
   enforce(c,u,a,{'account_admin'});r=c.execute('SELECT * FROM time_corrections WHERE account_id=? AND id=?',(a,i)).fetchone()
   if not r:raise HTTPException(404,'Correction not found')
   if os.getenv('SUPABASE_DB_URL'):c.execute('SELECT id FROM users WHERE id=? FOR UPDATE',(r['user_id'],)).fetchone()
   if r['decision']!='pending':raise HTTPException(409,'Correction already decided')
   if r['user_id']==u['id']:raise HTTPException(403,'A different admin must review your correction')
   if b.decision=='approved':
    for other in c.execute('SELECT * FROM work_sessions WHERE account_id=? AND user_id=? AND id<>?',(a,r['user_id'],r['session_id'])):
     prior=c.execute("SELECT requested_start,requested_end FROM time_corrections WHERE account_id=? AND session_id=? AND decision='approved' ORDER BY decided_at DESC LIMIT 1",(a,other['id'])).fetchone();ostart=prior['requested_start'] if prior else other['started_at'];oend=prior['requested_end'] if prior else other['ended_at'] or now()
     if r['requested_start']<oend and r['requested_end']>ostart:raise HTTPException(409,'Corrected interval overlaps another recorded session')
   changed=c.execute("UPDATE time_corrections SET decision=?,decided_by=?,decision_notes=?,decided_at=? WHERE account_id=? AND id=? AND decision='pending' RETURNING id",(b.decision,u['id'],b.notes,now(),a,i)).fetchone()
   if not changed:raise HTTPException(409,'Correction already decided')
   from collaboration import notify
   notify(c,a,r['user_id'],'Time correction '+b.decision,b.notes,uid,now)
  return {'ok':True}
 @app.get('/api/accounts/{a}/remote-team')
 def team(a:str,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a,{'account_admin'});stamp=now();day=datetime.now(ZoneInfo('Africa/Lagos')).date().isoformat();out=[]
   for member in c.execute('SELECT u.id,u.name,u.email,m.role FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.account_id=? AND m.active=1 ORDER BY u.name',(a,)):
    r=c.execute('SELECT s.*,t.title task_title FROM work_sessions s LEFT JOIN tasks t ON t.id=s.task_id AND t.account_id=s.account_id WHERE s.account_id=? AND s.user_id=? AND s.ended_at IS NULL',(a,member['id'])).fetchone();presence=c.execute('SELECT last_seen FROM employee_presence WHERE account_id=? AND user_id=?',(a,member['id'])).fetchone();age=elapsed(presence['last_seen'],stamp) if presence else None;connection='connected' if age is not None and age<=90 else 'recently_disconnected' if age is not None and age<=300 else 'offline' if presence else 'unknown';daily=c.execute('SELECT * FROM daily_updates WHERE account_id=? AND user_id=? AND day=?',(a,member['id'],day)).fetchone()
    out.append({**dict(member),'session':session_summary(c,r,stamp),'last_connected':presence['last_seen'] if presence else None,'connection':connection,'availability':r['status'] if r else 'not_checked_in','daily_update':dict(daily) if daily else None})
   return {'employees':out,'server_now':stamp,'day':day,'presence_note':'Connection status is not a productivity measure'}
 @app.get('/api/accounts/{a}/remote-team/{employee}/sessions')
 def history(a:str,employee:str,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a,{'account_admin'})
   if not c.execute('SELECT 1 FROM memberships WHERE account_id=? AND user_id=?',(a,employee)).fetchone():raise HTTPException(404,'Employee not found')
   return [session_summary(c,r,now()) for r in c.execute('SELECT * FROM work_sessions WHERE account_id=? AND user_id=? ORDER BY started_at DESC LIMIT 100',(a,employee))]

 @app.get('/api/accounts/{a}/work-report')
 def report(a:str,day:date|None=None,employee:str|None=None,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a)
   if employee and employee!=u['id']:
    enforce(c,u,a,{'account_admin'})
    if not c.execute('SELECT 1 FROM memberships WHERE account_id=? AND user_id=?',(a,employee)).fetchone():raise HTTPException(404,'Employee not found')
   return daily_report(c,a,employee or u['id'],day or datetime.now(ZoneInfo('Africa/Lagos')).date(),now())
