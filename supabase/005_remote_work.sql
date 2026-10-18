SET search_path TO promptto;
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

REVOKE ALL ON ALL TABLES IN SCHEMA promptto FROM PUBLIC, anon, authenticated;
