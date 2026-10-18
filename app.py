import environment
environment.validate_runtime()
"""Gazal: self-contained multi-account MVP. Run: uvicorn app:app --reload"""
import os, sqlite3, secrets, hashlib, hmac, json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import FileResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT=Path(__file__).parent
DB=Path(os.getenv('GAZAL_DB') or os.getenv('PROMPTTO_DB') or str(ROOT/'promptto.sqlite3'))
app=FastAPI(title='GAZAL.',version='0.10.1',docs_url='/docs' if os.getenv('GAZAL_ENV')!='production' else None,redoc_url=None,openapi_url='/openapi.json' if os.getenv('GAZAL_ENV')!='production' else None)
from starlette.middleware.trustedhost import TrustedHostMiddleware
app.add_middleware(TrustedHostMiddleware,allowed_hosts=[h.strip() for h in os.getenv('GAZAL_ALLOWED_HOSTS','localhost,127.0.0.1,testserver').split(',') if h.strip()])

@app.middleware('http')
async def response_security(request,call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='same-origin'
    if request.url.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
    if os.getenv('GAZAL_ENV')=='production':response.headers['Strict-Transport-Security']='max-age=31536000'
    return response

app.mount('/static',StaticFiles(directory=str(ROOT/'static')),name='static')
ROLES={'super_admin','account_admin','project_manager','team_lead','employee','hr_manager'}
STATUSES=['backlog','assigned','in_progress','submitted','revision','approved','on_hold','cancelled']
TRANSITIONS={'backlog':{'assigned','cancelled'},'assigned':{'in_progress','on_hold','cancelled'},'in_progress':{'submitted','on_hold'},'submitted':{'approved','revision'},'revision':{'in_progress','submitted'},'on_hold':{'in_progress','cancelled'},'approved':set(),'cancelled':set()}

from database import connection,initialize_schema
def conn():return connection(DB)

def now():return datetime.now(timezone.utc).isoformat()
def uid():return secrets.token_hex(12)
def hash_pw(p,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+'$'+hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),240000).hex()
def check_pw(p,stored):
    try:
        salt,val=stored.split('$');return hmac.compare_digest(hash_pw(p,salt),stored)
    except Exception:return False

def setup():
    with conn() as c:
        initialize_schema(c)
        if not os.getenv('SUPABASE_DB_URL') and c.execute('SELECT count(*) FROM users').fetchone()[0]==0:
            admin=uid();manager=uid();employee=uid();a=uid();b=uid()
            demo_pass=os.environ.get('PROMPTTO_DEMO_PASSWORD','DemoPass123!')
            for i,n,e,s in [(admin,'Gazal Admin','admin@promptto.local',1),(manager,'Novetiv Manager','manager@promptto.local',0),(employee,'Demo Employee','employee@promptto.local',0)]:
                c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(i,n,e,hash_pw(demo_pass),s))
            for i,n,slug in [(a,'Novetiv','novetiv'),(b,'Business B','business-b')]:c.execute('INSERT INTO accounts VALUES(?,?,?,?)',(i,n,slug,now()))
            for acc,user,role in [(a,manager,'account_admin'),(a,employee,'employee'),(b,employee,'project_manager')]:c.execute('INSERT INTO memberships VALUES(?,?,?,?,1)',(uid(),acc,user,role))
            p=uid();c.execute('INSERT INTO projects VALUES(?,?,?,?,?,?,?)',(p,a,'Website Relaunch','Novetiv site modernization','active',None,now()))
            for title,status,days,priority in [('Build login interface','in_progress',2,'high'),('Document API endpoints','assigned',4,'medium'),('Review accessibility','submitted',-1,'high')]:
                t=uid();c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(t,a,p,employee,title,'Demo task',priority,3,status,(datetime.now(timezone.utc)+timedelta(days=days)).date().isoformat(),now(),now(),None,None))
setup()

class Login(BaseModel): email:str;password:str
class Signup(BaseModel):name:str=Field(min_length=2,max_length=120);email:str=Field(max_length=254);password:str=Field(min_length=14,max_length=200)
class AccountIn(BaseModel):name:str=Field(min_length=2,max_length=100)
class ProjectIn(BaseModel):name:str=Field(min_length=2,max_length=160);description:str='';due_date:str|None=None
class EmployeeIn(BaseModel):name:str=Field(min_length=2,max_length=120);email:str;password:str=Field(min_length=10);role:str='employee'
class TaskIn(BaseModel):project_id:str;title:str=Field(min_length=2,max_length=200);description:str='';assignee_id:str|None=None;priority:str='medium';complexity:int=Field(default=3,ge=1,le=5);due_date:str|None=None
class TaskUpdate(BaseModel):status:str;notes:str=''
class ReviewIn(BaseModel):decision:str;quality:int|None=Field(default=None,ge=0,le=100);notes:str=''

def public_user(c,user):
    return {'id':user['id'],'name':user['name'],'email':user['email'],'is_super':bool(user['is_super'])}

def current(authorization:str|None=Header(None)):
    if not authorization or not authorization.startswith('Bearer '):raise HTTPException(401,'Login required')
    tok=hashlib.sha256(authorization[7:].encode()).hexdigest()
    with conn() as c:
        row=c.execute('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?',(tok,now())).fetchone()
        if not row:raise HTTPException(401,'Invalid or expired session')
        return dict(row)

def role_in(c,user,account):
    if user['is_super']:return 'super_admin'
    row=c.execute('SELECT role FROM memberships WHERE user_id=? AND account_id=? AND active=1',(user['id'],account)).fetchone()
    if not row:raise HTTPException(403,'Account access denied')
    return row['role']

def enforce(c,user,account,roles=None):
    role=role_in(c,user,account)
    if roles and role not in roles and role!='super_admin':raise HTTPException(403,'Insufficient permission')
    return role

def taskrow(c,a,t):
    row=c.execute('SELECT * FROM tasks WHERE account_id=? AND id=?',(a,t)).fetchone()
    if not row:raise HTTPException(404,'Task not found')
    return row

def event(c,a,t,user,kind,old=None,new=None,notes=''):
    c.execute('INSERT INTO task_events VALUES(?,?,?,?,?,?,?,?,?)',(uid(),a,t,user,kind,old,new,notes,now()))
    from collaboration import notify
    task=c.execute('SELECT title,assignee_id,due_date FROM tasks WHERE id=? AND account_id=?',(t,a)).fetchone()
    if task['assignee_id'] and kind in {'created','review'}:
        notify(c,a,task['assignee_id'],'New task assigned' if kind=='created' else 'Task review update',f'{task["title"]}: {new}. Deadline: {task["due_date"] or "Not set"}.',uid,now)
    if new=='submitted':
        for m in c.execute("SELECT user_id FROM memberships WHERE account_id=? AND active=1 AND role IN ('account_admin','project_manager','team_lead')",(a,)):
            notify(c,a,m['user_id'],'Work ready for review',task['title']+' has been submitted.',uid,now)

@app.get('/')
def index():return FileResponse(ROOT/'static'/'landing.html')
@app.get('/app')
def workspace():return FileResponse(ROOT/'static'/'index.html')

@app.post('/api/login')
def login(body:Login):
    with conn() as c:
        u=c.execute('SELECT * FROM users WHERE email=?',(body.email.lower().strip(),)).fetchone()
        if not u or not check_pw(body.password,u['pw_hash']):raise HTTPException(401,'Invalid credentials')
        token=secrets.token_urlsafe(42)
        c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),u['id'],(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()))
        return {'token':token,'user':public_user(c,u)}
@app.post('/api/logout')
def logout(authorization:str|None=Header(None),u=Depends(current)):
    with conn() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(authorization[7:].encode()).hexdigest(),))
    return {'ok':True}
@app.get('/api/me')
def me(u=Depends(current)):return public_user(None,u)
@app.get('/api/accounts')
def accounts(u=Depends(current)):
    with conn() as c:
        if u['is_super']:rows=c.execute('SELECT * FROM accounts ORDER BY name').fetchall()
        else:rows=c.execute('SELECT a.* FROM accounts a JOIN memberships m ON m.account_id=a.id WHERE m.user_id=? AND m.active=1 ORDER BY a.name',(u['id'],)).fetchall()
        return [{**dict(r),'role':role_in(c,u,r['id'])} for r in rows]
@app.post('/api/accounts',status_code=201)
def create_account(body:AccountIn,u=Depends(current)):
    if not u['is_super']:raise HTTPException(403,'Super Admin only')
    with conn() as c:
        i=uid();slug='account-'+i[:8];c.execute('INSERT INTO accounts VALUES(?,?,?,?)',(i,body.name,slug,now()))
        return {'id':i,'name':body.name,'slug':slug}
@app.get('/api/accounts/{a}/employees')
def employees(a:str,u=Depends(current)):
    with conn() as c:
        enforce(c,u,a)
        return [dict(r) for r in c.execute('SELECT u.id,u.name,u.email,m.role,m.active FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.account_id=? ORDER BY u.name',(a,)).fetchall()]
@app.post('/api/accounts/{a}/employees',status_code=201)
def add_employee(a:str,body:EmployeeIn,u=Depends(current)):
    if body.role not in ROLES-{'super_admin'}:raise HTTPException(400,'Invalid role')
    with conn() as c:
        enforce(c,u,a,{'account_admin'})
        email=body.email.lower().strip();user=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        if user:
            if c.execute('SELECT 1 FROM memberships WHERE account_id=? AND user_id=?',(a,user['id'])).fetchone():raise HTTPException(409,'Already a member')
            if not check_pw(body.password,user['pw_hash']):raise HTTPException(409,'Existing user: invite workflow required. Do not supply their password.')
            ident=user['id']
        else:
            ident=uid();c.execute('INSERT INTO users VALUES(?,?,?,?,0)',(ident,body.name,email,hash_pw(body.password)))
        c.execute('INSERT INTO memberships VALUES(?,?,?,?,1)',(uid(),a,ident,body.role))
        return {'id':ident,'name':body.name,'email':email,'role':body.role}
@app.get('/api/accounts/{a}/projects')
def projects(a:str,u=Depends(current)):
    with conn() as c:
        enforce(c,u,a);return [dict(r) for r in c.execute('SELECT * FROM projects WHERE account_id=? ORDER BY created_at DESC',(a,)).fetchall()]
@app.post('/api/accounts/{a}/projects',status_code=201)
def add_project(a:str,body:ProjectIn,u=Depends(current)):
    with conn() as c:
        enforce(c,u,a,{'account_admin','project_manager'})
        i=uid();c.execute('INSERT INTO projects VALUES(?,?,?,?,?,?,?)',(i,a,body.name,body.description,'active',body.due_date,now()));return {'id':i,'name':body.name}
@app.get('/api/accounts/{a}/tasks')
def tasks(a:str,u=Depends(current)):
    with conn() as c:
        role=enforce(c,u,a)
        sql='''SELECT t.*,p.name project_name, us.name assignee_name FROM tasks t JOIN projects p ON p.id=t.project_id LEFT JOIN users us ON us.id=t.assignee_id WHERE t.account_id=?'''
        params=[a]
        if role=='employee':sql+=' AND t.assignee_id=?';params.append(u['id'])
        sql+=' ORDER BY t.created_at DESC'
        return [dict(r) for r in c.execute(sql,params).fetchall()]
@app.post('/api/accounts/{a}/tasks',status_code=201)
def add_task(a:str,body:TaskIn,u=Depends(current)):
    if body.priority not in {'low','medium','high','urgent'}:raise HTTPException(400,'Invalid priority')
    with conn() as c:
        enforce(c,u,a,{'account_admin','project_manager','team_lead'})
        if not c.execute('SELECT 1 FROM projects WHERE id=? AND account_id=?',(body.project_id,a)).fetchone():raise HTTPException(400,'Project not in account')
        if body.assignee_id and not c.execute('SELECT 1 FROM memberships WHERE user_id=? AND account_id=? AND active=1',(body.assignee_id,a)).fetchone():raise HTTPException(400,'Assignee not in account')
        i=uid();status='assigned' if body.assignee_id else 'backlog';stamp=now()
        c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,a,body.project_id,body.assignee_id,body.title,body.description,body.priority,body.complexity,status,body.due_date,stamp,stamp,None,None))
        event(c,a,i,u['id'],'created',None,status)
        return {'id':i,'status':status}
@app.post('/api/accounts/{a}/tasks/{t}/transition')
def transition(a:str,t:str,body:TaskUpdate,u=Depends(current)):
    with conn() as c:
        role=enforce(c,u,a);task=taskrow(c,a,t);old=task['status']
        if body.status not in TRANSITIONS.get(old,set()):raise HTTPException(400,'Invalid status transition')
        if role=='employee' and (task['assignee_id']!=u['id'] or body.status not in {'in_progress','submitted'}):raise HTTPException(403,'Not permitted')
        if body.status in {'approved','revision'}:raise HTTPException(400,'Use review endpoint')
        if body.status in {'cancelled','on_hold','assigned'} and role not in {'super_admin','account_admin','project_manager','team_lead'}:raise HTTPException(403,'Not permitted')
        c.execute('UPDATE tasks SET status=?,updated_at=?,submitted_at=CASE WHEN ?="submitted" THEN ? ELSE submitted_at END WHERE id=? AND account_id=?',(body.status,now(),body.status,now(),t,a))
        event(c,a,t,u['id'],'transition',old,body.status,body.notes)
        return {'id':t,'status':body.status}
@app.post('/api/accounts/{a}/tasks/{t}/review')
def review(a:str,t:str,body:ReviewIn,u=Depends(current)):
    if body.decision not in {'approved','revision'}:raise HTTPException(400,'Invalid decision')
    if body.decision=='approved' and body.quality is None:raise HTTPException(400,'Quality score required')
    with conn() as c:
        enforce(c,u,a,{'account_admin','project_manager','team_lead'});task=taskrow(c,a,t)
        if task['status']!='submitted':raise HTTPException(400,'Task must be submitted first')
        if body.decision=='approved' and c.execute('SELECT 1 FROM task_rubrics WHERE account_id=? AND task_id=?',(a,t)).fetchone():raise HTTPException(409,'Use the policy-assessment endpoint for rubric-bound tasks')
        c.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?,?)',(uid(),a,t,u['id'],body.decision,body.quality,body.notes,now()))
        c.execute('UPDATE tasks SET status=?,updated_at=?,approved_at=? WHERE id=? AND account_id=?',(body.decision,now(),now() if body.decision=='approved' else None,t,a))
        event(c,a,t,u['id'],'review','submitted',body.decision,body.notes)
        return {'id':t,'status':body.decision}
@app.get('/api/accounts/{a}/tasks/{t}/events')
def task_events(a:str,t:str,u=Depends(current)):
    with conn() as c:
        role=enforce(c,u,a);task=taskrow(c,a,t)
        if role=='employee' and task['assignee_id']!=u['id']:raise HTTPException(403,'Not your task')
        return [dict(r) for r in c.execute('SELECT * FROM task_events WHERE account_id=? AND task_id=? ORDER BY created_at',(a,t))]
@app.get('/api/accounts/{a}/dashboard')
def dashboard(a:str,u=Depends(current)):
    with conn() as c:
        role=enforce(c,u,a);condition='account_id=?';params=[a]
        if role=='employee':condition+=' AND assignee_id=?';params.append(u['id'])
        rows=c.execute('SELECT status,due_date,complexity FROM tasks WHERE '+condition,params).fetchall()
        today=datetime.now(timezone.utc).date().isoformat()
        counts={s:sum(r['status']==s for r in rows) for s in STATUSES}
        return {'total':len(rows),'approved':counts['approved'],'overdue':sum(bool(r['due_date'] and r['due_date']<today and r['status'] not in {'approved','cancelled'}) for r in rows),'status_counts':counts,'active_projects':c.execute('SELECT count(*) FROM projects WHERE account_id=? AND status="active"',(a,)).fetchone()[0] if role!='employee' else None,'employee_count':c.execute('SELECT count(*) FROM memberships WHERE account_id=? AND active=1',(a,)).fetchone()[0] if role!='employee' else None}
@app.get('/api/accounts/{a}/performance')
def performance(a:str,u=Depends(current)):
    with conn() as c:
        role=enforce(c,u,a,{'account_admin'})
        members=c.execute('SELECT u.id,u.name FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.account_id=? AND m.active=1',(a,)).fetchall()
        out=[]
        for m in members:
            if role=='employee' and m['id']!=u['id']:continue
            rows=c.execute('SELECT t.id,t.status,t.due_date,t.approved_at,t.complexity,r.quality FROM tasks t LEFT JOIN reviews r ON r.task_id=t.id AND r.decision="approved" WHERE t.account_id=? AND t.assignee_id=?',(a,m['id'])).fetchall()
            completed=[r for r in rows if r['status']=='approved'];quality=[r['quality'] for r in completed if r['quality'] is not None]
            ontime=[r for r in completed if r['due_date'] and r['approved_at']]
            out.append({'user_id':m['id'],'name':m['name'],'assigned':len(rows),'approved':len(completed),'quality_avg':round(sum(quality)/len(quality),1) if quality else None,'on_time_rate':round(100*sum(r['approved_at'][:10]<=r['due_date'] for r in ontime)/len(ontime),1) if ontime else None,'score_status':'Insufficient data — scoring policy not yet calibrated'})
        return out

from traction import install
install(app,conn,current,enforce,uid,now)
from scoring import install as install_scoring
install_scoring(app,conn,current,enforce,uid,now)

@app.get('/api/system/database')
def database_status(u=Depends(current)):
    if not u['is_super']:raise HTTPException(403,'Super Admin only')
    with conn() as c:c.execute('SELECT 1').fetchone()
    from config import SUPABASE_URL
    return {'backend':'supabase_postgres' if os.getenv('SUPABASE_DB_URL') else 'sqlite','connected':True,'supabase_project_url':SUPABASE_URL,'supabase_connected':bool(os.getenv('SUPABASE_DB_URL'))}

from collaboration import install as install_collaboration
install_collaboration(app,conn,current,enforce,uid,now,hash_pw)
from management import install as install_management
install_management(app,conn,current,enforce,uid,now)

from policy_system import install as install_policy_system
install_policy_system(app,conn,current,enforce,uid,now,event)

from remote_work import install as install_remote_work
install_remote_work(app,conn,current,enforce,uid,now)

@app.get('/signin')
@app.get('/signup')
@app.get('/join')
def auth_pages():return FileResponse(ROOT/'static'/'auth.html')
@app.get('/employee/login')
@app.get('/admin/login')
def legacy_login():return RedirectResponse('/signin',status_code=307)
@app.get('/employee/signup')
@app.get('/admin/signup')
@app.get('/create-account')
def legacy_signup():return RedirectResponse('/signup',status_code=307)

@app.post('/api/signup',status_code=201)
def signup(body:Signup):
    import re
    email=body.email.strip().lower();name=body.name.strip()
    if len(name)<2 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):raise HTTPException(422,'Enter a valid name and email address')
    with conn() as c:
        inserted=c.execute('INSERT INTO users VALUES(?,?,?,?,0) ON CONFLICT(email) DO NOTHING RETURNING id',(uid(),name,email,hash_pw(body.password))).fetchone()
        if not inserted:raise HTTPException(409,'This email already has an account. Sign in instead.')
    return {'ok':True,'email':email,'message':'Account created. Sign in to join your workspace.'}

@app.get('/healthz')
def health():return {'status':'ok'}
@app.get('/readyz')
def readiness():
    try:
        with conn() as c:c.execute('SELECT 1').fetchone()
    except Exception:raise HTTPException(503,'Database unavailable')
    return {'status':'ready'}
