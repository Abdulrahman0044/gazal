import secrets
from test_app import client,auth
from policy_system import task_quality,suggestions

def test_quality_formula_and_nlp_fallback():
 rubric={'requirements':[{'id':'r','text':'Implement secure login','weight':2}],'documentation':[{'id':'d','text':'Include setup instructions','weight':1}]}
 b={'correctness':.9,'acceptance_human':.8,'validation':1,'documentation_human':.7,'requirements':{'r':{'status':1,'evidence_id':'e'}},'documentation':{'d':{'status':.5,'evidence_id':'e'}}}
 r=task_quality(b,rubric,{'nlp_weight':.25},{'e'});assert r['quality']==88 and r['lambda_used']==.25
 b['requirements']['r']['evidence_id']=None;b['documentation']['d']['evidence_id']=None
 r=task_quality(b,rubric,{'nlp_weight':.25},set());assert r['quality']==87 and r['lambda_used']==0
 assert suggestions(rubric['requirements'],[{'id':'e','text':'Secure login was implemented and tested'}])[0]['matches'][0]['evidence_id']=='e'

def test_policy_lifecycle_and_guardrails():
 h=auth('manager@promptto.local');eh=auth('employee@promptto.local');a=client.get('/api/accounts',headers=h).json()[0]['id'];p=client.get(f'/api/accounts/{a}/projects',headers=h).json()[0]['id'];emp=client.get('/api/me',headers=eh).json()['id'];base=f'/api/accounts/{a}'
 body={'name':'Verified evidence policy','reason':'Publish documented quality criteria'}
 assert client.post(base+'/policies',headers=eh,json=body).status_code==403
 assert client.post(base+'/policies',headers=h,json={**body,'weights':{'quality':80,'on_time':35,'completion':25}}).status_code==422
 assert client.post(base+'/policies',headers=h,json={**body,'nlp_weight':.5}).status_code==422
 r=client.post(base+'/policies',headers=h,json=body);assert r.status_code==201,r.text;v1=r.json()['id']
 tid=client.post(base+'/tasks',headers=h,json={'project_id':p,'assignee_id':emp,'title':'Policy-driven task','due_date':'2026-12-01'}).json()['id'];t=base+'/tasks/'+tid
 rubric={'requirements':[{'id':'r','text':'Implement secure login','weight':2}],'documentation':[{'id':'d','text':'Include setup instructions','weight':1}]}
 assert client.post(t+'/rubric',headers=h,json=rubric).status_code==200
 assert client.post(t+'/rubric',headers=h,json=rubric).status_code==409
 client.post(base+'/policies',headers=h,json={**body,'nlp_weight':0,'name':'Second version'})
 assert client.post(t+'/rubric',headers=eh,json=rubric).status_code==403
 e=client.post(t+'/evidence',headers=eh,json={'text':'Secure login implemented; setup instructions included and tests verified.'}).json()['id']
 assert client.get(t+'/nlp-suggestions',headers=eh).status_code==403
 assert client.get(t+'/nlp-suggestions',headers=h).json()['requirements'][0]['matches']
 client.post(t+'/transition',headers=eh,json={'status':'in_progress'});client.post(t+'/transition',headers=eh,json={'status':'submitted'})
 assert client.post(t+'/review',headers=h,json={'decision':'approved','quality':100}).status_code==409
 assess={'correctness':1,'acceptance_human':1,'validation':1,'documentation_human':1,'requirements':{'r':{'status':1,'evidence_id':e}},'documentation':{'d':{'status':1,'evidence_id':e}},'notes':'Verified implementation and all acceptance criteria'}
 assert client.post(t+'/policy-assessment',headers=eh,json=assess).status_code==403
 assert client.post(t+'/policy-assessment',headers=h,json={**assess,'requirements':{'r':{'status':1,'evidence_id':'foreign'}}}).status_code==422
 r=client.post(t+'/policy-assessment',headers=h,json=assess);assert r.status_code==200,r.text;assert r.json()['quality']==100 and r.json()['lambda_used']==.25
 assert client.get(t+'/policy-assessment',headers=h).json()['policy_id']==v1
 assert client.post(t+'/policy-assessment',headers=h,json=assess).status_code==409
 assert client.post(t+'/evidence',headers=eh,json={'text':'Late evidence attempt'}).status_code==409
 assert client.post(base+'/score-snapshots',headers=h).status_code==201
 assert client.get(base+'/score-snapshots',headers=eh).status_code==403
 assert client.get(base+'/score-snapshots',headers=h).json()

def test_policy_summary_hides_formula_and_preserves_rules():
 h=auth('manager@promptto.local');eh=auth('employee@promptto.local');a=client.get('/api/accounts',headers=h).json()[0]['id'];base=f'/api/accounts/{a}'
 config={'name':'Custom account rules','reason':'Preserve reviewed configuration across versions','weights':{'quality':50,'on_time':30,'completion':20},'nlp_weight':.1}
 assert client.post(base+'/policies',headers=h,json=config).status_code==201
 assert client.post(base+'/policies',headers=h,json={'name':'Renamed account policy','reason':'New version retains previously approved rules'}).status_code==201
 active=client.get(base+'/policies',headers=h).json()['active'];assert active['weights']==config['weights'] and active['nlp_weight']==.1
 summary=client.get(base+'/policy-settings',headers=h).json();assert 'weights' not in summary['active'] and 'config_json' not in str(summary)
 assert client.get(base+'/policy-settings',headers=eh).status_code==403
 from app import ROOT
 html=(ROOT/'static/index.html').read_text();js=(ROOT/'static/app.js').read_text()
 assert 'data-view="policies"' not in html and 'Quality formula' not in js and 'q = 100' not in js
