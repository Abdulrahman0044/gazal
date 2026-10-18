import environment
"""Postgres/Supabase backend; SQLite remains available for local development."""
import os,re,sqlite3
from pathlib import Path
from contextlib import contextmanager
class Row(dict):
    def __getitem__(self,key):return list(self.values())[key] if isinstance(key,int) else super().__getitem__(key)
class Result:
    def __init__(self,cursor):self.cursor=cursor
    def fetchone(self):
        r=self.cursor.fetchone();return Row(r) if r is not None else None
    def fetchall(self):return [Row(r) for r in self.cursor.fetchall()]
    def __iter__(self):return iter(self.fetchall())
def postgres_sql(sql):
    # Legacy queries use double quotes only for literal values; Postgres requires single quotes.
    return re.sub(r'"([^"\n]*)"',lambda m:"'"+m[1].replace("'","''")+"'",sql).replace('?','%s')
class Postgres:
    def __init__(self,c):self.c=c
    def execute(self,sql,params=()):return Result(self.c.execute(postgres_sql(sql),params))
    def executescript(self,script):
        for statement in script.split(';'):
            if statement.strip():self.execute(statement)
@contextmanager
def connection(sqlite_path):
    url=os.getenv('SUPABASE_DB_URL')
    if url:
        import psycopg
        from psycopg.rows import dict_row
        opts={'sslmode':'verify-full' if os.getenv('SUPABASE_SSLROOTCERT') else 'require'}
        if os.getenv('SUPABASE_SSLROOTCERT'):opts['sslrootcert']=os.environ['SUPABASE_SSLROOTCERT']
        with psycopg.connect(url,row_factory=dict_row,connect_timeout=10,prepare_threshold=None,**opts) as c:
            c.execute('SET search_path TO promptto')
            yield Postgres(c)
    else:
        Path(sqlite_path).parent.mkdir(parents=True,exist_ok=True)
        c=sqlite3.connect(sqlite_path);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA busy_timeout=5000')
        try:yield c;c.commit()
        except Exception:c.rollback();raise
        finally:c.close()

def initialize_schema(c):
    """Local dev initializes the same schema; cloud requires reviewed migrations first."""
    sql=(Path(__file__).parent/'schema_core.sql').read_text()
    if os.getenv('SUPABASE_DB_URL'):
        expected=set(re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)',sql))
        actual={r['table_name'] for r in c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='promptto'")}
        if expected-actual:raise RuntimeError('Gazal database schema is incomplete. Run python migrate.py --apply before starting the backend.')
    else:c.executescript(sql)
