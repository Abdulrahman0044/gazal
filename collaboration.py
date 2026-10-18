"""Invite onboarding and account-scoped notification inbox."""
import hashlib,secrets,os,smtplib,json
from datetime import datetime,timezone,timedelta
from email.message import EmailMessage
from fastapi import Depends,HTTPException,Header,BackgroundTasks
from pydantic import BaseModel,Field

def notify(c,a,user,title,message,uid,now):
    c.execute('INSERT INTO notifications VALUES(?,?,?,?,?,?,0)',(uid(),a,user,title,message,now()))
def install(app,conn,current,enforce,uid,now,hash_pw):
    # Schema is initialized centrally before route registration.
    class Invite(BaseModel):
        email:str=Field(max_length=254);name:str=Field(min_length=2,max_length=120);role:str='employee';project_id:str|None=None
    class Accept(BaseModel):
        token:str=Field(min_length=20,max_length=200);password:str|None=Field(default=None,min_length=14,max_length=200)
    def tokenrow(c,token):
        r=c.execute('SELECT * FROM invitations WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if not r or r['accepted_at'] or r['expires_at']<=now() or c.execute('SELECT 1 FROM invitation_revocations WHERE invitation_id=?',(r['id'],)).fetchone():raise HTTPException(410,'Invitation expired or already used')
        return r
    def send_email(ident,email,name,link):
        status='failed'
        try:
            msg=EmailMessage();msg['Subject']='You are invited to Gazal';msg['From']=os.environ['SMTP_FROM'];msg['To']=email;msg.set_content(f'Hello {name},\n\nYou have been invited to Gazal. Open this link to join:\n{link}\n\nThis invitation expires in seven days. If you already have an account, sign in before accepting.')
            with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.getenv('SMTP_PORT','587')),timeout=15) as smtp:
                smtp.starttls()
                if os.getenv('SMTP_USER'):smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
                smtp.send_message(msg)
            status='sent'
        except Exception:pass
        with conn() as c:c.execute('UPDATE invitations SET email_status=? WHERE id=?',(status,ident))
    @app.post('/api/accounts/{a}/invitations',status_code=201)
    def invite(a:str,b:Invite,background:BackgroundTasks,u=Depends(current)):
        email=b.email.strip().lower()
        if '@' not in email or any(ch in email for ch in '\r\n') or b.role not in {'employee','team_lead','project_manager','hr_manager','account_admin'}:raise HTTPException(422,'Invalid email or role')
        with conn() as c:
            enforce(c,u,a,{'account_admin'})
            if b.project_id and not c.execute('SELECT 1 FROM projects WHERE account_id=? AND id=?',(a,b.project_id)).fetchone():raise HTTPException(404,'Project not found')
            token=secrets.token_urlsafe(32);ident=uid();status='pending' if os.getenv('SMTP_HOST') and os.getenv('SMTP_FROM') and os.getenv('GAZAL_PUBLIC_URL') else 'not_configured'
            c.execute('INSERT INTO invitations VALUES(?,?,?,?,?,?,?,?,NULL,?,?)',(ident,a,b.project_id,email,b.name,b.role,hashlib.sha256(token.encode()).hexdigest(),(datetime.now(timezone.utc)+timedelta(days=7)).isoformat(),u['id'],status))
            existing=c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
            if existing and c.execute('SELECT 1 FROM memberships WHERE account_id=? AND user_id=? AND active=1',(a,existing['id'])).fetchone():notify(c,a,existing['id'],'Project invitation',f'You have been invited to join a project. Ask your manager for the invitation link.',uid,now)
        link=os.getenv('GAZAL_PUBLIC_URL','').rstrip('/')+'/join#token='+token
        if status=='pending':background.add_task(send_email,ident,email,b.name,link)
        return {'id':ident,'invite_link':link,'email_status':status,'expires_in_days':7}
    @app.get('/api/accounts/{a}/invitations')
    def invites(a:str,u=Depends(current)):
        with conn() as c:
            enforce(c,u,a,{'account_admin'});return [dict(r) for r in c.execute('SELECT i.id,i.email,i.name,i.role,i.project_id,i.expires_at,i.accepted_at,i.email_status,r.revoked_at FROM invitations i LEFT JOIN invitation_revocations r ON r.invitation_id=i.id WHERE i.account_id=? ORDER BY i.expires_at DESC',(a,))]
    @app.post('/api/invitations/inspect')
    def inspect(b:Accept):
        with conn() as c:
            r=tokenrow(c,b.token);account=c.execute('SELECT name FROM accounts WHERE id=?',(r['account_id'],)).fetchone();project=c.execute('SELECT name FROM projects WHERE id=?',(r['project_id'],)).fetchone() if r['project_id'] else None
            return {'account':account['name'],'project':project['name'] if project else None,'email':r['email'],'name':r['name'],'role':r['role'],'existing_user':bool(c.execute('SELECT 1 FROM users WHERE email=?',(r['email'],)).fetchone())}
    @app.post('/api/invitations/accept')
    def accept(b:Accept,authorization:str|None=Header(None)):
        with conn() as c:
            r=tokenrow(c,b.token);existing=c.execute('SELECT * FROM users WHERE email=?',(r['email'],)).fetchone()
            if existing:
                u=current(authorization)
                if u['id']!=existing['id']:raise HTTPException(403,'Sign in as the invited email address')
                user=existing['id']
            else:
                if not b.password:raise HTTPException(422,'Create a password with at least 14 characters')
                user=uid();c.execute('INSERT INTO users VALUES(?,?,?,?,0)',(user,r['name'],r['email'],hash_pw(b.password)))
            # Atomic token claim prevents two simultaneous accepts from reusing an invitation.
            claimed=c.execute('UPDATE invitations SET accepted_at=? WHERE id=? AND accepted_at IS NULL AND expires_at>? RETURNING id',(now(),r['id'],now())).fetchone()
            if not claimed:raise HTTPException(410,'Invitation already used')
            member=c.execute('SELECT * FROM memberships WHERE account_id=? AND user_id=?',(r['account_id'],user)).fetchone()
            if member and not member['active']:raise HTTPException(403,'Membership is inactive; ask the administrator to reactivate it')
            if not member:c.execute('INSERT INTO memberships VALUES(?,?,?,?,1)',(uid(),r['account_id'],user,r['role']))
            # An existing membership's role never changes merely by accepting a project invite.
            if r['project_id']:c.execute('INSERT INTO project_members VALUES(?,?,?,?) ON CONFLICT(account_id,project_id,user_id) DO NOTHING',(r['account_id'],r['project_id'],user,now()))
            notify(c,r['account_id'],user,'Welcome to Gazal','Your invitation was accepted. Open Tasks to see your assignments.',uid,now)
        return {'ok':True,'email':r['email'],'login':'/employee/login'}
    @app.get('/api/accounts/{a}/notifications')
    def inbox(a:str,u=Depends(current)):
        with conn() as c:
            enforce(c,u,a);return [dict(r) for r in c.execute('SELECT * FROM notifications WHERE account_id=? AND user_id=? ORDER BY created_at DESC LIMIT 100',(a,u['id']))]
    @app.post('/api/accounts/{a}/notifications/{n}/read')
    def read(a:str,n:str,u=Depends(current)):
        with conn() as c:
            enforce(c,u,a)
            if not c.execute('SELECT 1 FROM notifications WHERE id=? AND account_id=? AND user_id=?',(n,a,u['id'])).fetchone():raise HTTPException(404,'Notification not found')
            c.execute('UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?',(n,u['id']))
        return {'ok':True}
    @app.post('/api/accounts/{a}/task-reminders')
    def reminders(a:str,u=Depends(current)):
        today=datetime.now(timezone.utc).date().isoformat();count=0
        with conn() as c:
            enforce(c,u,a,{'account_admin','project_manager','team_lead'})
            rows=c.execute("SELECT * FROM tasks WHERE account_id=? AND due_date<=? AND assignee_id IS NOT NULL AND status NOT IN ('approved','cancelled','on_hold','submitted')",(a,today)).fetchall()
            for t in rows:
                if c.execute('SELECT 1 FROM reminder_receipts WHERE account_id=? AND task_id=? AND day=?',(a,t['id'],today)).fetchone():continue
                c.execute('INSERT INTO reminder_receipts VALUES(?,?,?)',(a,t['id'],today));notify(c,a,t['assignee_id'],'Task due reminder',f'{t["title"]} is due {t["due_date"]}. Open Tasks to update or submit your work.',uid,now);count+=1
        return {'created':count}
