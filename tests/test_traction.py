from test_app import client,auth
import json,time,hmac,hashlib,io
from openpyxl import Workbook

def context():
    h=auth('manager@promptto.local');a=client.get('/api/accounts',headers=h).json()[0]['id'];p=next(p['id'] for p in client.get(f'/api/accounts/{a}/projects',headers=h).json() if p['name']=='Website Relaunch');return h,a,p,f'/api/accounts/{a}/projects/{p}'
def test_import_validation_and_isolation():
    h,a,p,b=context();eh=auth('employee@promptto.local')
    assert client.get(b+'/traction',headers=eh).status_code==403
    assert client.get(b.replace(p,'missing')+'/traction',headers=h).status_code==404
    assert client.get(b+'/traction?start=2026-10-20&end=2026-10-10',headers=h).status_code==422
    for value in ['-1','nan','1.5']:
        assert client.post(b+'/imports/preview',headers=h,files={'file':('x.csv',f'date,metric,value\n2026-10-12,total_users,{value}\n')}).status_code==422
    raw='date,metric,value\n2026-10-12,total_users,100\n2026-10-12,collected,15000\n'
    r=client.post(b+'/imports/preview',headers=h,files={'file':('x.csv',raw)});assert r.status_code==200,r.text
    assert all(m['value'] is None for m in client.get(b+'/traction',headers=h).json()['metrics'])
    i=r.json()['id'];assert client.post(b+f'/imports/{i}/commit',headers=eh).status_code==403
    for _ in range(2):assert client.post(b+f'/imports/{i}/commit',headers=h).status_code==200
    d=client.get(b+'/traction',headers=h).json();assert next(m['value'] for m in d['metrics'] if m['key']=='total_users')==100
    assert len(d['history'])==2
    wb=Workbook();wb.active.append(['date','metric','value']);wb.active.append(['2026-10-11','active_users',20]);f=io.BytesIO();wb.save(f)
    r=client.post(b+'/imports/preview',headers=h,files={'file':('x.xlsx',f.getvalue())});assert r.status_code==200,r.text

def test_signed_webhook_and_source_conflicts():
    h,a,p,b=context();r=client.post(b+'/sources',headers=h,json={'metric':'mrr','mode':'webhook'});assert r.status_code==200
    s=r.json();stamp=str(int(time.time()));raw=json.dumps({'event_id':'test-event-1','date':'2026-10-12','metric':'mrr','value':5000}).encode();sig=hmac.new(s['secret'].encode(),stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest();headers={'X-PromptTo-Timestamp':stamp,'X-PromptTo-Signature':sig}
    assert client.post(s['endpoint'],content=raw,headers={**headers,'X-PromptTo-Signature':'bad'}).status_code==401
    assert client.post(s['endpoint'],content=raw,headers=headers).status_code==200
    assert client.post(s['endpoint'],content=raw,headers=headers).json()['duplicate']
    assert client.post(s['endpoint'],content=raw,headers={**headers,'X-PromptTo-Timestamp':'1'}).status_code==401
    assert client.post(b+'/imports/preview',headers=h,files={'file':('x.csv','date,metric,value\n2026-10-12,mrr,1\n')}).status_code==409
    assert 'secret' not in client.get(b+'/sources',headers=h).text
    assert next(m['value'] for m in client.get(b+'/traction',headers=h).json()['metrics'] if m['key']=='mrr')==5000
