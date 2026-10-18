import environment
"""Create the first real admin. Password is read invisibly; no demo cloud users."""
import os,getpass
if not os.getenv('SUPABASE_DB_URL'):raise SystemExit('Set SUPABASE_DB_URL in the backend environment first.')
from app import conn,uid,hash_pw
email=input('Admin email: ').strip().lower();name=input('Admin name: ').strip();password=getpass.getpass('New admin password (at least 14 characters): ')
if '@' not in email or not name or len(password)<14:raise SystemExit('Invalid email/name or password too short')
with conn() as c:
 if c.execute('SELECT count(*) FROM users').fetchone()[0]:raise SystemExit('Users already exist; bootstrap is only for an empty installation')
 c.execute('INSERT INTO users VALUES(?,?,?,?,1)',(uid(),name,email,hash_pw(password)))
print('Initial admin created. Sign in and create your business accounts.')
