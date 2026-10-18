-- Apply in the Supabase SQL Editor after migrations, using the migration owner.
-- Provision a login password securely for this role before using it in SUPABASE_DB_URL.
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='gazal_app') THEN
  CREATE ROLE gazal_app NOLOGIN;
 END IF;
END $$;
GRANT USAGE ON SCHEMA promptto TO gazal_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA promptto TO gazal_app;
REVOKE UPDATE, DELETE ON promptto.policy_versions, promptto.task_rubrics,
 promptto.task_evidence, promptto.policy_assessments, promptto.score_snapshots,
 promptto.score_exception_events, promptto.task_events, promptto.work_session_events,
 promptto.daily_update_events, promptto.invitation_revocations FROM gazal_app;
DO $$ BEGIN IF to_regclass('promptto.schema_migrations') IS NOT NULL THEN REVOKE ALL ON promptto.schema_migrations FROM gazal_app; END IF; END $$;
