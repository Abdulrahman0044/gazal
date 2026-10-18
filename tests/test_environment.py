from environment import production_errors
from test_app import client

def test_production_requires_real_secrets(monkeypatch):
 monkeypatch.setenv('GAZAL_ENV','production');monkeypatch.setenv('SUPABASE_DB_URL','');monkeypatch.setenv('SUPABASE_SSLROOTCERT','');monkeypatch.setenv('GAZAL_PUBLIC_URL','http://localhost');monkeypatch.setenv('GAZAL_ALLOWED_HOSTS','*')
 assert len(production_errors())==4

def test_brand_and_health_pages():
 assert client.get('/healthz').json()['status']=='ok'
 assert client.get('/readyz').json()['status']=='ready'
 for path in ['/','/signin','/app']:
  r=client.get(path);assert 'gazal-logo' in r.text and r.headers['x-content-type-options']=='nosniff'
 assert client.get('/static/brand/gazal-logo.svg').status_code==200
 assert client.get('/api/me').headers['cache-control']=='no-store'


def test_money_precision_and_decimal_validation():
 from test_traction import context
 h,a,p,b=context();p=client.post(f'/api/accounts/{a}/projects',headers=h,json={'name':'Precision test project'}).json()['id'];b=f'/api/accounts/{a}/projects/{p}';raw='date,metric,value\n2026-10-12,collected,123456789.25\n'
 r=client.post(b+'/imports/preview',headers=h,files={'file':('money.csv',raw)});assert r.status_code==200
 assert client.post(b+'/imports/'+r.json()['id']+'/commit',headers=h).status_code==200
 value=next(m['value'] for m in client.get(b+'/traction',headers=h).json()['metrics'] if m['key']=='collected');assert value==123456789.25
 for value in ['0.001','1000000000001']:
  r=client.post(b+'/imports/preview',headers=h,files={'file':('invalid.csv','date,metric,value\n2026-10-12,billed,'+value+'\n')});assert r.status_code==422
