CREATE SCHEMA IF NOT EXISTS promptto;
REVOKE ALL ON SCHEMA promptto FROM PUBLIC, anon, authenticated;
SET search_path TO promptto;

        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,pw_hash TEXT NOT NULL,is_super INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY,name TEXT NOT NULL,slug TEXT UNIQUE NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memberships(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),user_id TEXT NOT NULL REFERENCES users(id),role TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,UNIQUE(account_id,user_id));
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),name TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'active',due_date TEXT,created_at TEXT NOT NULL, UNIQUE(id,account_id));
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),project_id TEXT NOT NULL,assignee_id TEXT,title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',priority TEXT NOT NULL DEFAULT 'medium',complexity INTEGER NOT NULL DEFAULT 3,status TEXT NOT NULL DEFAULT 'backlog',due_date TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,submitted_at TEXT,approved_at TEXT,FOREIGN KEY(project_id,account_id) REFERENCES projects(id,account_id),FOREIGN KEY(assignee_id) REFERENCES users(id), UNIQUE(id,account_id));
        CREATE TABLE IF NOT EXISTS task_events(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,task_id TEXT NOT NULL,actor_id TEXT NOT NULL,event_type TEXT NOT NULL,old_status TEXT,new_status TEXT,notes TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id));
        CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,task_id TEXT NOT NULL,reviewer_id TEXT NOT NULL,decision TEXT NOT NULL,quality INTEGER,notes TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id));
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),expires_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_memberships_account ON memberships(account_id,active);
        CREATE INDEX IF NOT EXISTS idx_projects_account ON projects(account_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_account_status ON tasks(account_id,status);
        CREATE INDEX IF NOT EXISTS idx_tasks_account_due ON tasks(account_id,due_date);
        
CREATE TABLE IF NOT EXISTS traction_sources(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,project_id TEXT NOT NULL,metric TEXT NOT NULL,mode TEXT NOT NULL,secret TEXT,created_at TEXT NOT NULL,UNIQUE(account_id,project_id,metric),FOREIGN KEY(project_id,account_id) REFERENCES projects(id,account_id));
        CREATE TABLE IF NOT EXISTS traction_values(account_id TEXT NOT NULL,project_id TEXT NOT NULL,metric TEXT NOT NULL,day TEXT NOT NULL,value REAL NOT NULL,source_id TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(account_id,project_id,metric,day));
        CREATE TABLE IF NOT EXISTS traction_imports(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,project_id TEXT NOT NULL,rows_json TEXT NOT NULL,actor_id TEXT NOT NULL,committed INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS traction_receipts(source_id TEXT NOT NULL,event_id TEXT NOT NULL,received_at TEXT NOT NULL,PRIMARY KEY(source_id,event_id));
CREATE TABLE IF NOT EXISTS score_exceptions(account_id TEXT NOT NULL,task_id TEXT NOT NULL,adjusted_due TEXT,excluded INTEGER NOT NULL DEFAULT 0,reason TEXT NOT NULL,actor_id TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(account_id,task_id),FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id));
    CREATE TABLE IF NOT EXISTS score_exception_events(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,task_id TEXT NOT NULL,actor_id TEXT NOT NULL,details TEXT NOT NULL,created_at TEXT NOT NULL);
    
REVOKE ALL ON ALL TABLES IN SCHEMA promptto FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA promptto REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
