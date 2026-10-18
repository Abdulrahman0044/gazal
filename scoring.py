from datetime import datetime,timezone,timedelta,date
from zoneinfo import ZoneInfo
from fastapi import Depends,HTTPException
from pydantic import BaseModel,Field
POLICY={'version':'1.0','window_days':90,'weights':{'quality':40,'on_time':35,'completion':25},'minimum_approved':5,'minimum_due':5,'forecast_minimum_weeks':12,'status':'Pilot policy — requires organizational review','definitions':{'quality':'Complexity-weighted manager-reviewed quality of approved tasks','on_time':'Complexity-weighted share of approved due tasks submitted by the adjusted deadline; manager review delay is excluded','completion':'Complexity-weighted approved share of tasks due within the window','exclusions':'Cancelled and on-hold tasks, plus manager-approved exceptions with recorded reasons','forecast':'No trained predictive model is enabled. Historical score is not an AI prediction.'}}
def calculate(rows,start,end,policy=None):
    policy=policy or POLICY
    eligible=[]
    for r in rows:
        due=r.get('adjusted_due') or r.get('due_date')
        if r['status'] in {'cancelled','on_hold'} or r.get('excluded') or not due or not start<=due<=end:continue
        eligible.append({**r,'effective_due':due})
    approved=[r for r in eligible if r['status']=='approved']
    coverage=sum(r.get('quality') is not None and bool(r.get('submitted_at')) for r in approved)
    base={'due_tasks':len(eligible),'approved_tasks':len(approved),'coverage':coverage,'policy_version':policy['version'],'score':None,'components':None,'status':'Insufficient evidence','prediction':{'status':'Not enabled','reason':'Requires at least 12 weekly observations and validated out-of-time accuracy'}}
    if len(eligible)<policy['minimum_due'] or len(approved)<policy['minimum_approved'] or coverage!=len(approved):return base
    weight=lambda rs:sum(r['complexity'] for r in rs)
    quality=sum(r['quality']*r['complexity'] for r in approved)/weight(approved)
    ontime=100*sum(r['complexity'] for r in approved if datetime.fromisoformat(r['submitted_at']).astimezone(ZoneInfo('Africa/Lagos')).date().isoformat()<=r['effective_due'])/weight(approved)
    completion=100*weight(approved)/weight(eligible)
    return {**base,'score':round((policy['weights']['quality']*quality+policy['weights']['on_time']*ontime+policy['weights']['completion']*completion)/100,1),'components':{'quality':round(quality,1),'on_time':round(ontime,1),'completion':round(completion,1)},'status':'Pilot score — human review required'}
def install(app,conn,current,enforce,uid,now):
    # Schema is initialized centrally before route registration.
    class ExceptionIn(BaseModel):
        adjusted_due:date|None=None;excluded:bool=False;reason:str=Field(min_length=10,max_length=1000)
    @app.get('/api/accounts/{a}/scoring-policy')
    def policy(a:str,u=Depends(current)):
        with conn() as c:
            enforce(c,u,a,{'account_admin'})
            from policy_system import active_policy
            return active_policy(c,a)
    @app.post('/api/accounts/{a}/tasks/{t}/score-exception')
    def exception(a:str,t:str,b:ExceptionIn,u=Depends(current)):
        import json
        with conn() as c:
            enforce(c,u,a,{'account_admin'})
            if not c.execute('SELECT 1 FROM tasks WHERE id=? AND account_id=?',(t,a)).fetchone():raise HTTPException(404,'Task not found')
            c.execute('INSERT INTO score_exceptions VALUES(?,?,?,?,?,?,?) ON CONFLICT(account_id,task_id) DO UPDATE SET adjusted_due=excluded.adjusted_due,excluded=excluded.excluded,reason=excluded.reason,actor_id=excluded.actor_id,updated_at=excluded.updated_at',(a,t,str(b.adjusted_due) if b.adjusted_due else None,int(b.excluded),b.reason,u['id'],now()))
            c.execute('INSERT INTO score_exception_events VALUES(?,?,?,?,?,?)',(uid(),a,t,u['id'],json.dumps(b.model_dump(mode='json')),now()))
        return {'ok':True}
    @app.get('/api/accounts/{a}/scores')
    def scores(a:str,as_of:date|None=None,u=Depends(current)):
        if as_of and as_of!=datetime.now(ZoneInfo("Africa/Lagos")).date():raise HTTPException(422,'Use saved snapshots for historical scores')
        with conn() as c:
            enforce(c,u,a,{'account_admin'})
            return score_account(c,a)


def score_account(c,a):
    from policy_system import active_policy
    policy=active_policy(c,a);end=datetime.now(ZoneInfo("Africa/Lagos")).date();start=end-timedelta(days=policy['window_days']-1)
    members=c.execute('SELECT u.id,u.name FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.account_id=? AND m.active=1',(a,)).fetchall();out=[]
    for m in members:
        rows=c.execute("""SELECT t.*,e.adjusted_due,e.excluded,tr.policy_id bound_policy,
        CASE WHEN tr.policy_id IS NOT NULL THEN (SELECT pa.quality FROM policy_assessments pa WHERE pa.task_id=t.id AND pa.account_id=t.account_id ORDER BY pa.created_at DESC LIMIT 1)
        ELSE (SELECT r.quality FROM reviews r WHERE r.task_id=t.id AND r.account_id=t.account_id AND r.decision='approved' ORDER BY r.created_at DESC LIMIT 1) END quality
        FROM tasks t LEFT JOIN score_exceptions e ON e.task_id=t.id AND e.account_id=t.account_id LEFT JOIN task_rubrics tr ON tr.task_id=t.id AND tr.account_id=t.account_id WHERE t.account_id=? AND t.assignee_id=?""",(a,m['id'])).fetchall()
        out.append({'user_id':m['id'],'name':m['name'],'start':str(start),'end':str(end),'policy_id':policy.get('id'),'task_policy_ids':sorted({r['bound_policy'] for r in rows if r['bound_policy']}),**calculate([dict(r) for r in rows],str(start),str(end),policy)})
    return out
