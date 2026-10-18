import re
from pathlib import Path
from app import conn,ROOT
from database import initialize_schema

def test_schema_used_by_backend_matches_sql_export():
 core=(ROOT/'schema_core.sql').read_text();export=(ROOT/'supabase/schema.sql').read_text()
 assert core in export
 expected=set(re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)',core))
 with conn() as c:
  actual={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 assert expected<=actual and len(expected)==31

def test_cloud_startup_rejects_incomplete_schema(monkeypatch):
 monkeypatch.setenv('SUPABASE_DB_URL','not-a-real-url')
 class Stub:
  def execute(self,sql):return []
 try:initialize_schema(Stub())
 except RuntimeError as e:assert 'migrate.py --apply' in str(e)
 else:assert False,'Incomplete database must not start'

def test_cloud_startup_accepts_matching_schema(monkeypatch):
 monkeypatch.setenv('SUPABASE_DB_URL','not-a-real-url')
 expected=re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)',(ROOT/'schema_core.sql').read_text())
 class Stub:
  def execute(self,sql):return [{'table_name':n} for n in expected]
 initialize_schema(Stub())
