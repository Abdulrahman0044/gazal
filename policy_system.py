"""Versioned admin policy, lexical NLP suggestions and verified quality assessment."""
import json,re
from fastapi import Depends,HTTPException
from pydantic import BaseModel,Field,model_validator
DEFAULT={'version':'1.0','weights':{'quality':40,'on_time':35,'completion':25},'nlp_weight':0.25,'minimum_approved':5,'minimum_due':5,'window_days':90,'status':'Pilot policy','definitions':{'quality':'40% correctness, 30% acceptance, 20% validation, 10% documentation; NLP assists acceptance and documentation only','on_time':'Complexity-weighted timely final submissions','completion':'Complexity-weighted approved share of eligible due work','forecast':'Disabled until historical validation'}}
def active_policy(c,a):
 r=c.execute('SELECT v.* FROM account_policy p JOIN policy_versions v ON v.id=p.policy_id AND v.account_id=p.account_id WHERE p.account_id=?',(a,)).fetchone()
 return {**json.loads(r['config_json']),'id':r['id'],'version':str(r['version']), 'published_at':r['created_at']} if r else DEFAULT

def tokens(text):return set(re.findall(r'[a-z0-9]+',text.lower()))-{'the','a','an','to','of','and','in','for','is','be','with','must','should'}
def suggestions(items,evidence):
 out=[]
 for item in items:
  required=tokens(item['text']);matches=[]
  for e in evidence:
   words=tokens(e['text']);overlap=len(required&words)/max(len(required),1)
   if overlap:matches.append({'evidence_id':e['id'],'overlap':round(overlap,3),'excerpt':e['text'][:300]})
  out.append({'criterion_id':item['id'],'criterion':item['text'],'matches':sorted(matches,key=lambda m:m['overlap'],reverse=True)[:3]})
 return out

def task_quality(b,rubric,config,evidence_ids):
 def coverage(items,ratings):
  if set(ratings)!=set(i['id'] for i in items):raise HTTPException(422,'Rate every checklist item exactly once')
  for rating in ratings.values():
   if rating['status'] not in [0,0.5,1]:raise HTTPException(422,'Checklist status must be 0, 0.5 or 1')
   if rating.get('evidence_id') and rating['evidence_id'] not in evidence_ids:raise HTTPException(422,'Evidence does not belong to this task')
   if evidence_ids and rating['status']>0 and not rating.get('evidence_id'):raise HTTPException(422,'Confirmed or partial evidence requires an evidence reference')
  return sum(i['weight']*ratings[i['id']]['status'] for i in items)/sum(i['weight'] for i in items)
 an=coverage(rubric['requirements'],b['requirements']);dn=coverage(rubric['documentation'],b['documentation']);lam=config['nlp_weight'] if evidence_ids else 0
 q=100*(.4*b['correctness']+.3*((1-lam)*b['acceptance_human']+lam*an)+.2*b['validation']+.1*((1-lam)*b['documentation_human']+lam*dn))
 return {'quality':round(q,4),'acceptance_nlp':an,'documentation_nlp':dn,'lambda_used':lam,'nlp_available':bool(evidence_ids),'method':'Reviewer-confirmed checklist coverage; lexical NLP suggests matches, never verifies correctness'}
def install(app,conn,current,enforce,uid,now,event):
 class Weights(BaseModel):
  quality:float=Field(default=40,ge=0,le=100);on_time:float=Field(default=35,ge=0,le=100);completion:float=Field(default=25,ge=0,le=100)
  @model_validator(mode='after')
  def total(self):
   if abs(self.quality+self.on_time+self.completion-100)>1e-8:raise ValueError('Weights must sum to 100')
   return self
 class Publish(BaseModel):
  name:str=Field(min_length=3,max_length=100);weights:Weights=Field(default_factory=Weights);nlp_weight:float=Field(default=.25,ge=0,le=.25);minimum_approved:int=Field(default=5,ge=5,le=100);minimum_due:int=Field(default=5,ge=5,le=100);reason:str=Field(min_length=10,max_length=1000)
 class Item(BaseModel):
  id:str=Field(min_length=1,max_length=40,pattern=r'^[a-zA-Z0-9_-]+$');text:str=Field(min_length=5,max_length=1000);weight:float=Field(default=1,gt=0,le=100)
 class Rubric(BaseModel):
  requirements:list[Item]=Field(min_length=1,max_length=30);documentation:list[Item]=Field(min_length=1,max_length=30)
 class Evidence(BaseModel):text:str=Field(min_length=10,max_length=10000)
 class Rating(BaseModel):status:float; evidence_id:str|None=None
 class Assessment(BaseModel):
  correctness:float=Field(ge=0,le=1);acceptance_human:float=Field(ge=0,le=1);validation:float=Field(ge=0,le=1);documentation_human:float=Field(ge=0,le=1);requirements:dict[str,Rating];documentation:dict[str,Rating];notes:str=Field(min_length=10,max_length=2000)
 def task(c,a,t):
  r=c.execute('SELECT * FROM tasks WHERE account_id=? AND id=?',(a,t)).fetchone()
  if not r:raise HTTPException(404,'Task not found')
  return r
 @app.get('/api/accounts/{a}/policies')
 def policies(a:str,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a,{'account_admin'});active=active_policy(c,a);versions=[{**dict(r),'config':json.loads(r['config_json'])} for r in c.execute('SELECT * FROM policy_versions WHERE account_id=? ORDER BY version DESC',(a,))]
   return {'active':active,'versions':versions}
 @app.get('/api/accounts/{a}/policy-settings')
 def settings(a:str,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a,{'account_admin'});active=active_policy(c,a);versions=[dict(r) for r in c.execute('SELECT id,version,name,reason,created_at FROM policy_versions WHERE account_id=? ORDER BY version DESC',(a,))]
   name=next((r['name'] for r in versions if r['id']==active.get('id')),'Standard scoring policy')
   return {'active':{'id':active.get('id'),'version':active['version'],'name':name},'versions':versions}
 @app.post('/api/accounts/{a}/policies',status_code=201)
 def publish(a:str,b:Publish,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a,{'account_admin'});ident=uid();v=c.execute('SELECT COALESCE(MAX(version),0)+1 FROM policy_versions WHERE account_id=?',(a,)).fetchone()[0];config={**active_policy(c,a),**b.model_dump(exclude={'reason','name'},exclude_unset=True),'version':str(v)};config.pop('id',None);config.pop('published_at',None)
   c.execute('INSERT INTO policy_versions VALUES(?,?,?,?,?,?,?,?)',(ident,a,v,b.name,json.dumps(config),b.reason,u['id'],now()))
   c.execute('INSERT INTO account_policy VALUES(?,?) ON CONFLICT(account_id) DO UPDATE SET policy_id=excluded.policy_id',(a,ident));return {'id':ident,'version':v}
 @app.post('/api/accounts/{a}/tasks/{t}/rubric')
 def rubric(a:str,t:str,b:Rubric,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a,{'account_admin'});r=task(c,a,t)
   if r['status'] not in {'backlog','assigned'}:raise HTTPException(409,'Define criteria before work starts')
   if c.execute('SELECT 1 FROM task_rubrics WHERE account_id=? AND task_id=?',(a,t)).fetchone():raise HTTPException(409,'Criteria are already frozen')
   config=active_policy(c,a)
   if not config.get('id'):raise HTTPException(409,'Publish an account policy first')
   for items in [b.requirements,b.documentation]:
    if len({i.id for i in items})!=len(items):raise HTTPException(422,'Checklist IDs must be unique')
   c.execute('INSERT INTO task_rubrics VALUES(?,?,?,?,?,?,?)',(a,t,config['id'],json.dumps(b.model_dump()),r['complexity'],u['id'],now()));return {'ok':True,'policy_version':config['version']}
 @app.get('/api/accounts/{a}/tasks/{t}/rubric')
 def get_rubric(a:str,t:str,u=Depends(current)):
  with conn() as c:
   role=enforce(c,u,a);r=task(c,a,t)
   if role=='employee' and r['assignee_id']!=u['id']:raise HTTPException(403,'Not your task')
   rr=c.execute('SELECT rubric_json FROM task_rubrics WHERE account_id=? AND task_id=?',(a,t)).fetchone();return json.loads(rr['rubric_json']) if rr else None
 @app.post('/api/accounts/{a}/tasks/{t}/evidence',status_code=201)
 def evidence(a:str,t:str,b:Evidence,u=Depends(current)):
  with conn() as c:
   role=enforce(c,u,a,{'employee','account_admin','project_manager','team_lead'});r=task(c,a,t)
   if role=='employee' and r['assignee_id']!=u['id']:raise HTTPException(403,'Not your task')
   if r['status'] in {'approved','cancelled'}:raise HTTPException(409,'Task is closed')
   ident=uid();c.execute('INSERT INTO task_evidence VALUES(?,?,?,?,?,?)',(ident,a,t,b.text,u['id'],now()));return {'id':ident}
 @app.get('/api/accounts/{a}/tasks/{t}/evidence')
 def get_evidence(a:str,t:str,u=Depends(current)):
  with conn() as c:
   role=enforce(c,u,a);r=task(c,a,t)
   if role=='employee' and r['assignee_id']!=u['id']:raise HTTPException(403,'Not your task')
   return [dict(r) for r in c.execute('SELECT * FROM task_evidence WHERE account_id=? AND task_id=? ORDER BY created_at',(a,t))]
 @app.get('/api/accounts/{a}/tasks/{t}/nlp-suggestions')
 def suggest(a:str,t:str,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a,{'account_admin'});task(c,a,t);r=c.execute('SELECT rubric_json FROM task_rubrics WHERE account_id=? AND task_id=?',(a,t)).fetchone()
   if not r:raise HTTPException(409,'No task rubric')
   rr=json.loads(r['rubric_json']);ev=[dict(r) for r in c.execute('SELECT * FROM task_evidence WHERE account_id=? AND task_id=?',(a,t))]
   return {'requirements':suggestions(rr['requirements'],ev),'documentation':suggestions(rr['documentation'],ev),'evidence':ev,'method':'Lexical token overlap — evidence suggestion only, not semantic verification'}
 @app.post('/api/accounts/{a}/tasks/{t}/policy-assessment')
 def assess(a:str,t:str,b:Assessment,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a,{'account_admin'});r=task(c,a,t)
   if r['status']!='submitted':raise HTTPException(409,'Task must be submitted')
   rr=c.execute('SELECT * FROM task_rubrics WHERE account_id=? AND task_id=?',(a,t)).fetchone()
   if not rr:raise HTTPException(409,'No rubric')
   policy=c.execute('SELECT config_json FROM policy_versions WHERE id=? AND account_id=?',(rr['policy_id'],a)).fetchone();config=json.loads(policy['config_json']);ids={r['id'] for r in c.execute('SELECT id FROM task_evidence WHERE account_id=? AND task_id=?',(a,t))};result=task_quality(b.model_dump(),json.loads(rr['rubric_json']),config,ids)
   c.execute('INSERT INTO policy_assessments VALUES(?,?,?,?,?,?,?,?)',(uid(),a,t,rr['policy_id'],json.dumps({'input':b.model_dump(),'result':result}),result['quality'],u['id'],now()))
   c.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?,?)',(uid(),a,t,u['id'],'approved',result['quality'],b.notes,now()));c.execute("UPDATE tasks SET status='approved',approved_at=?,updated_at=? WHERE account_id=? AND id=?",(now(),now(),a,t));event(c,a,t,u['id'],'review','submitted','approved',b.notes);return result
 @app.get('/api/accounts/{a}/tasks/{t}/policy-assessment')
 def assessment(a:str,t:str,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a,{'account_admin'});task(c,a,t);r=c.execute('SELECT * FROM policy_assessments WHERE account_id=? AND task_id=? ORDER BY created_at DESC LIMIT 1',(a,t)).fetchone();return {**dict(r),'assessment':json.loads(r['assessment_json'])} if r else None
 @app.post('/api/accounts/{a}/score-snapshots',status_code=201)
 def snapshot(a:str,u=Depends(current)):
  from scoring import score_account
  with conn() as c:
   enforce(c,u,a,{'account_admin'});data=score_account(c,a);ident=uid();c.execute('INSERT INTO score_snapshots VALUES(?,?,?,?,?)',(ident,a,json.dumps(data),u['id'],now()));return {'id':ident,'scores':data}
 @app.get('/api/accounts/{a}/score-snapshots')
 def snapshots(a:str,u=Depends(current)):
  with conn() as c:
   enforce(c,u,a,{'account_admin'});return [{**dict(r),'scores':json.loads(r['scores_json'])} for r in c.execute('SELECT * FROM score_snapshots WHERE account_id=? ORDER BY created_at DESC LIMIT 50',(a,))]
