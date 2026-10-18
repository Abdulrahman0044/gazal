SET search_path TO promptto;
CREATE TABLE IF NOT EXISTS policy_versions(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),version INTEGER NOT NULL,name TEXT NOT NULL,config_json TEXT NOT NULL,reason TEXT NOT NULL,actor_id TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,UNIQUE(account_id,version),UNIQUE(id,account_id));
CREATE TABLE IF NOT EXISTS account_policy(account_id TEXT PRIMARY KEY REFERENCES accounts(id),policy_id TEXT NOT NULL,FOREIGN KEY(policy_id,account_id) REFERENCES policy_versions(id,account_id));
CREATE TABLE IF NOT EXISTS task_rubrics(account_id TEXT NOT NULL,task_id TEXT NOT NULL,policy_id TEXT NOT NULL,rubric_json TEXT NOT NULL,complexity INTEGER NOT NULL,actor_id TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,PRIMARY KEY(account_id,task_id),FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id),FOREIGN KEY(policy_id,account_id) REFERENCES policy_versions(id,account_id));
CREATE TABLE IF NOT EXISTS task_evidence(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,task_id TEXT NOT NULL,text TEXT NOT NULL,actor_id TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id));
CREATE TABLE IF NOT EXISTS policy_assessments(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,task_id TEXT NOT NULL,policy_id TEXT NOT NULL,assessment_json TEXT NOT NULL,quality REAL NOT NULL,actor_id TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,FOREIGN KEY(task_id,account_id) REFERENCES tasks(id,account_id),FOREIGN KEY(policy_id,account_id) REFERENCES policy_versions(id,account_id));
CREATE TABLE IF NOT EXISTS score_snapshots(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),scores_json TEXT NOT NULL,actor_id TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_task_evidence_scope ON task_evidence(account_id,task_id,created_at);
CREATE INDEX IF NOT EXISTS idx_policy_assessment_scope ON policy_assessments(account_id,task_id,created_at);

REVOKE ALL ON ALL TABLES IN SCHEMA promptto FROM PUBLIC, anon, authenticated;
