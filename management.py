"""Account-scoped project membership and invitation lifecycle operations."""
from fastapi import Depends,HTTPException
from pydantic import BaseModel

def install(app,conn,current,enforce,uid,now):
    # Schema is initialized centrally before route registration.
    class Member(BaseModel):user_id:str
    def project(c,a,p):
        if not c.execute('SELECT 1 FROM projects WHERE account_id=? AND id=?',(a,p)).fetchone():raise HTTPException(404,'Project not found')
    @app.get('/api/accounts/{a}/projects/{p}/members')
    def members(a:str,p:str,u=Depends(current)):
        with conn() as c:
            role=enforce(c,u,a);project(c,a,p)
            sql='SELECT pm.user_id,u.name,u.email,pm.joined_at FROM project_members pm JOIN users u ON u.id=pm.user_id WHERE pm.account_id=? AND pm.project_id=?';params=[a,p]
            if role=='employee':sql+=' AND pm.user_id=?';params.append(u['id'])
            return [dict(r) for r in c.execute(sql,params)]
    @app.post('/api/accounts/{a}/projects/{p}/members',status_code=201)
    def add_member(a:str,p:str,b:Member,u=Depends(current)):
        with conn() as c:
            enforce(c,u,a,{'account_admin','project_manager','team_lead'});project(c,a,p)
            if not c.execute('SELECT 1 FROM memberships WHERE account_id=? AND user_id=? AND active=1',(a,b.user_id)).fetchone():raise HTTPException(422,'User must be an active member of this account')
            c.execute('INSERT INTO project_members VALUES(?,?,?,?) ON CONFLICT(account_id,project_id,user_id) DO NOTHING',(a,p,b.user_id,now()))
            from collaboration import notify
            notify(c,a,b.user_id,'Project membership','You were added to a project. Open Projects to view your workspace.',uid,now)
        return {'ok':True}
    @app.delete('/api/accounts/{a}/projects/{p}/members/{member}')
    def remove_member(a:str,p:str,member:str,u=Depends(current)):
        with conn() as c:
            enforce(c,u,a,{'account_admin','project_manager'});project(c,a,p)
            c.execute('DELETE FROM project_members WHERE account_id=? AND project_id=? AND user_id=?',(a,p,member))
        return {'ok':True,'note':'Existing task assignments are retained; reassign them separately if required'}
    @app.post('/api/accounts/{a}/invitations/{i}/revoke')
    def revoke(a:str,i:str,u=Depends(current)):
        with conn() as c:
            enforce(c,u,a,{'account_admin'});r=c.execute('SELECT accepted_at FROM invitations WHERE id=? AND account_id=?',(i,a)).fetchone()
            if not r:raise HTTPException(404,'Invitation not found')
            if r['accepted_at']:raise HTTPException(409,'Accepted invitations cannot be revoked; manage membership instead')
            c.execute('INSERT INTO invitation_revocations VALUES(?,?,?,?) ON CONFLICT(invitation_id) DO NOTHING',(i,a,u['id'],now()))
        return {'ok':True}
