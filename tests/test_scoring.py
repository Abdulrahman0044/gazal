from scoring import calculate
from test_app import client,auth

def sample(status='approved',quality=80,submitted='2026-10-10T12:00:00Z',complexity=3):
 return dict(status=status,quality=quality,submitted_at=submitted,complexity=complexity,due_date='2026-10-11',excluded=0,adjusted_due=None)
def test_score_math_and_evidence():
 r=calculate([sample() for _ in range(5)],'2026-07-15','2026-10-12');assert r['score']==92
 assert r['components']=={'quality':80,'on_time':100,'completion':100}
 assert calculate([sample() for _ in range(4)],'2026-07-15','2026-10-12')['score'] is None
 assert calculate([sample(quality=None) for _ in range(5)],'2026-07-15','2026-10-12')['score'] is None
 assert calculate([sample(submitted=None) for _ in range(5)],'2026-07-15','2026-10-12')['score'] is None
 rows=[sample() for _ in range(5)]+[sample(status='assigned',complexity=5)]
 assert calculate(rows,'2026-07-15','2026-10-12')['components']['completion']==75
 rows[-1]['excluded']=1;assert calculate(rows,'2026-07-15','2026-10-12')['score']==92
 rows=[sample(submitted='2026-10-12T10:00:00Z') for _ in range(5)]
 assert calculate(rows,'2026-07-15','2026-10-12')['score']==57
 for row in rows:row['adjusted_due']='2026-10-12'
 assert calculate(rows,'2026-07-15','2026-10-12')['score']==92

def test_scoring_permissions_and_audit():
 h=auth('manager@promptto.local');eh=auth('employee@promptto.local');a=client.get('/api/accounts',headers=h).json()[0]['id'];t=client.get(f'/api/accounts/{a}/tasks',headers=h).json()[0]['id'];b=f'/api/accounts/{a}'
 assert client.get(b+'/scoring-policy',headers=eh).status_code==403
 assert sum(client.get(b+'/scoring-policy',headers=h).json()['weights'].values())==100
 own=client.get(b+'/scores',headers=eh);assert own.status_code==403
 body={'adjusted_due':'2026-10-15','excluded':False,'reason':'Dependency blocked by external vendor'}
 assert client.post(b+f'/tasks/{t}/score-exception',headers=eh,json=body).status_code==403
 assert client.post(b+f'/tasks/{t}/score-exception',headers=h,json=body).status_code==200
 from app import conn
 with conn() as c:assert c.execute('SELECT count(*) FROM score_exception_events WHERE task_id=?',(t,)).fetchone()[0]>=1
 assert client.get('/api/system/database',headers=h).status_code==403
 ah=auth('admin@promptto.local');assert client.get('/api/system/database',headers=ah).json()['backend']=='sqlite'

def test_postgres_adapter_sql_and_rows():
 from database import postgres_sql,Row
 assert postgres_sql('SELECT * FROM tasks WHERE status="approved" AND id=?')=="SELECT * FROM tasks WHERE status='approved' AND id=%s"
 assert Row({'count':4})[0]==4
