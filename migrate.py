"""Review with python migrate.py; apply with python migrate.py --apply."""
import argparse,hashlib,os
from pathlib import Path
from database import connection
p=argparse.ArgumentParser(description='Gazal ordered Supabase migrations');p.add_argument('--apply',action='store_true');args=p.parse_args()
files=sorted((Path(__file__).parent/'supabase').glob('[0-9][0-9][0-9]_*.sql'))
if not args.apply:
    print('Migration plan (no database changes):')
    for f in files:print(f.name)
    print('Set SUPABASE_DB_URL securely, then run python migrate.py --apply.');raise SystemExit(0)
if not os.getenv('SUPABASE_DB_URL'):raise SystemExit('SUPABASE_DB_URL is required. No changes made.')
try:
    with connection(None) as c:
        c.execute('CREATE SCHEMA IF NOT EXISTS promptto')
        c.execute('CREATE TABLE IF NOT EXISTS schema_migrations(filename TEXT PRIMARY KEY,checksum TEXT NOT NULL,applied_at TEXT NOT NULL)')
        for f in files:
            sql=f.read_text();checksum=hashlib.sha256(sql.encode()).hexdigest();r=c.execute('SELECT checksum FROM schema_migrations WHERE filename=?',(f.name,)).fetchone()
            if r:
                if r['checksum']!=checksum:raise RuntimeError('Previously applied migration has changed')
                continue
            c.executescript(sql)
            c.execute("INSERT INTO schema_migrations VALUES(?,?,CAST(CURRENT_TIMESTAMP AS TEXT))",(f.name,checksum))
        c.execute('REVOKE ALL ON ALL TABLES IN SCHEMA promptto FROM PUBLIC, anon, authenticated')
    print('Gazal migrations applied successfully.')
except Exception as e:
    # Connection errors can contain private connection details: do not print them.
    raise SystemExit('Migration failed and was rolled back ('+type(e).__name__+'). Inspect server-side database diagnostics securely.')
