-- Canonical application tables and indexes, shared by backend and SQL export.

        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,pw_hash TEXT NOT NULL,is_super INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY,name TEXT NOT NULL,slug TEXT UNIQUE NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memberships(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),user_id TEXT NOT NULL REFERENCES users(id),role TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,UNIQUE(account_id,user_id));
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),name TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'active',due_date TEXT,created_at TEXT NOT NULL, UNIQUE(id,account_id));
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),project_id TEXT NOT NULL,assignee_id TEXT,title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',priority TEXT NOT NULL DEFAULT 'medium',complexity INTEGER NOT NULL DEFAULT 3,status TEXT NOT NULL DEFAULT 'backlog',due_date TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,submitted_at TEXT,approved_at TEXT,FOREIGN KEY(project_id,account_id) REFERENCES projects(id,account_id),FOREIGN KEY(assignee_id) REFERENCES users(id), UNIQUE(id,account_id));
        CREATE TABLE IF NOT EXISTS task_events(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,task_id TEXT NOT NULL,actor_id TEXT NOT NULL,event_type TEXT NOT NULL,old_status TEXT,new_status TEXT,notes TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id));
        CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,task_id TEXT NOT NULL,reviewer_id TEXT NOT NULL,decision TEXT NOT NULL,quality DOUBLE PRECISION,notes TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id));
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),expires_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_memberships_account ON memberships(account_id,active);
        CREATE INDEX IF NOT EXISTS idx_projects_account ON projects(account_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_account_status ON tasks(account_id,status);
        CREATE INDEX IF NOT EXISTS idx_tasks_account_due ON tasks(account_id,due_date);
        
CREATE TABLE IF NOT EXISTS traction_sources(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,project_id TEXT NOT NULL,metric TEXT NOT NULL,mode TEXT NOT NULL,secret TEXT,created_at TEXT NOT NULL,UNIQUE(account_id,project_id,metric),FOREIGN KEY(project_id,account_id) REFERENCES projects(id,account_id));
        CREATE TABLE IF NOT EXISTS traction_values(account_id TEXT NOT NULL,project_id TEXT NOT NULL,metric TEXT NOT NULL,day TEXT NOT NULL,value NUMERIC(20,2) NOT NULL,source_id TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(account_id,project_id,metric,day));
        CREATE TABLE IF NOT EXISTS traction_imports(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,project_id TEXT NOT NULL,rows_json TEXT NOT NULL,actor_id TEXT NOT NULL,committed INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS traction_receipts(source_id TEXT NOT NULL,event_id TEXT NOT NULL,received_at TEXT NOT NULL,PRIMARY KEY(source_id,event_id));
CREATE TABLE IF NOT EXISTS score_exceptions(account_id TEXT NOT NULL,task_id TEXT NOT NULL,adjusted_due TEXT,excluded INTEGER NOT NULL DEFAULT 0,reason TEXT NOT NULL,actor_id TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(account_id,task_id),FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id));
    CREATE TABLE IF NOT EXISTS score_exception_events(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,task_id TEXT NOT NULL,actor_id TEXT NOT NULL,details TEXT NOT NULL,created_at TEXT NOT NULL);
    
CREATE TABLE IF NOT EXISTS project_members(account_id TEXT NOT NULL,project_id TEXT NOT NULL,user_id TEXT NOT NULL REFERENCES users(id),joined_at TEXT NOT NULL,PRIMARY KEY(account_id,project_id,user_id),FOREIGN KEY(project_id,account_id) REFERENCES projects(id,account_id));
    CREATE TABLE IF NOT EXISTS invitations(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),project_id TEXT,email TEXT NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL,token_hash TEXT UNIQUE NOT NULL,expires_at TEXT NOT NULL,accepted_at TEXT,invited_by TEXT NOT NULL REFERENCES users(id),email_status TEXT NOT NULL DEFAULT 'not_configured',FOREIGN KEY(project_id,account_id) REFERENCES projects(id,account_id));
    CREATE TABLE IF NOT EXISTS notifications(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),user_id TEXT NOT NULL REFERENCES users(id),title TEXT NOT NULL,message TEXT NOT NULL,created_at TEXT NOT NULL,is_read INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS reminder_receipts(account_id TEXT NOT NULL,task_id TEXT NOT NULL,day TEXT NOT NULL,PRIMARY KEY(account_id,task_id,day));
CREATE TABLE IF NOT EXISTS invitation_revocations(invitation_id TEXT PRIMARY KEY REFERENCES invitations(id),account_id TEXT NOT NULL REFERENCES accounts(id),actor_id TEXT NOT NULL REFERENCES users(id),revoked_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(account_id,user_id,is_read,created_at);
    CREATE INDEX IF NOT EXISTS idx_invitations_account_email ON invitations(account_id,email);
    CREATE INDEX IF NOT EXISTS idx_traction_values_scope ON traction_values(account_id,project_id,day);
    CREATE INDEX IF NOT EXISTS idx_task_reviews_scope ON reviews(account_id,task_id,decision,created_at);
    CREATE INDEX IF NOT EXISTS idx_project_members_user ON project_members(account_id,user_id);
    CREATE INDEX IF NOT EXISTS idx_score_exception_events_scope ON score_exception_events(account_id,task_id,created_at);
CREATE TABLE IF NOT EXISTS policy_versions(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),version INTEGER NOT NULL,name TEXT NOT NULL,config_json TEXT NOT NULL,reason TEXT NOT NULL,actor_id TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,UNIQUE(account_id,version),UNIQUE(id,account_id));
CREATE TABLE IF NOT EXISTS account_policy(account_id TEXT PRIMARY KEY REFERENCES accounts(id),policy_id TEXT NOT NULL,FOREIGN KEY(policy_id,account_id) REFERENCES policy_versions(id,account_id));
CREATE TABLE IF NOT EXISTS task_rubrics(account_id TEXT NOT NULL,task_id TEXT NOT NULL,policy_id TEXT NOT NULL,rubric_json TEXT NOT NULL,complexity INTEGER NOT NULL,actor_id TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,PRIMARY KEY(account_id,task_id),FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id),FOREIGN KEY(policy_id,account_id) REFERENCES policy_versions(id,account_id));
CREATE TABLE IF NOT EXISTS task_evidence(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,task_id TEXT NOT NULL,text TEXT NOT NULL,actor_id TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id));
CREATE TABLE IF NOT EXISTS policy_assessments(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,task_id TEXT NOT NULL,policy_id TEXT NOT NULL,assessment_json TEXT NOT NULL,quality DOUBLE PRECISION NOT NULL,actor_id TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id),FOREIGN KEY(policy_id,account_id) REFERENCES policy_versions(id,account_id));
CREATE TABLE IF NOT EXISTS score_snapshots(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),scores_json TEXT NOT NULL,actor_id TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_task_evidence_scope ON task_evidence(account_id,task_id,created_at);
CREATE INDEX IF NOT EXISTS idx_policy_assessment_scope ON policy_assessments(account_id,task_id,created_at);

CREATE TABLE IF NOT EXISTS work_sessions(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),user_id TEXT NOT NULL REFERENCES users(id),task_id TEXT,status TEXT NOT NULL,started_at TEXT NOT NULL,ended_at TEXT,updated_at TEXT NOT NULL,UNIQUE(id,account_id),FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id));
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_work_session ON work_sessions(account_id,user_id) WHERE ended_at IS NULL;
CREATE TABLE IF NOT EXISTS work_session_events(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,session_id TEXT NOT NULL,user_id TEXT NOT NULL REFERENCES users(id),status TEXT NOT NULL,task_id TEXT,note TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(session_id,account_id) REFERENCES work_sessions(id,account_id),FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id));
CREATE TABLE IF NOT EXISTS employee_presence(account_id TEXT NOT NULL REFERENCES accounts(id),user_id TEXT NOT NULL REFERENCES users(id),last_seen TEXT NOT NULL,PRIMARY KEY(account_id,user_id));
CREATE TABLE IF NOT EXISTS daily_updates(account_id TEXT NOT NULL REFERENCES accounts(id),user_id TEXT NOT NULL REFERENCES users(id),day TEXT NOT NULL,priorities TEXT NOT NULL,achievements TEXT NOT NULL,blockers TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(account_id,user_id,day));
CREATE TABLE IF NOT EXISTS daily_update_events(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),user_id TEXT NOT NULL REFERENCES users(id),day TEXT NOT NULL,details_json TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS time_corrections(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,session_id TEXT NOT NULL,user_id TEXT NOT NULL REFERENCES users(id),requested_start TEXT NOT NULL,requested_end TEXT NOT NULL,reason TEXT NOT NULL,decision TEXT NOT NULL,decided_by TEXT REFERENCES users(id),decision_notes TEXT,decided_at TEXT,created_at TEXT NOT NULL,FOREIGN KEY(session_id,account_id) REFERENCES work_sessions(id,account_id));
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_pending_time_correction ON time_corrections(account_id,session_id) WHERE decision='pending';
CREATE INDEX IF NOT EXISTS idx_work_sessions_user ON work_sessions(account_id,user_id,started_at);
CREATE INDEX IF NOT EXISTS idx_work_events_session ON work_session_events(account_id,session_id,created_at);
CREATE INDEX IF NOT EXISTS idx_daily_updates_account ON daily_updates(account_id,day);
