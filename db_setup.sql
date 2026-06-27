-- ============================================================
--  WatermarkPro v2 — PostgreSQL Schema
--  Run once against your PostgreSQL server to set up the DB.
--
--  psql -U postgres -f db_setup.sql
-- ============================================================

-- Create database and user (run as superuser)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'postgres') THEN
    CREATE ROLE postgres WITH LOGIN PASSWORD 'root_123';
  END IF;
END
$$;

-- Create database
SELECT 'CREATE DATABASE watermark OWNER postgres'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'watermark')\gexec

-- Connect to the new database
\c watermark

-- Grant schema permissions
GRANT ALL PRIVILEGES ON DATABASE watermark TO postgres;
GRANT ALL ON SCHEMA public TO postgres;

-- ── Settings ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    key        VARCHAR(120) PRIMARY KEY,
    value      TEXT         NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── Excluded applications ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS excluded_apps (
    id           SERIAL       PRIMARY KEY,
    process_name VARCHAR(200) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL DEFAULT '',
    added_by     VARCHAR(100) NOT NULL DEFAULT 'system',
    added_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── Organisation users ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS org_users (
    id          SERIAL       PRIMARY KEY,
    username    VARCHAR(100) NOT NULL,
    hostname    VARCHAR(150) NOT NULL,
    department  VARCHAR(150) NOT NULL DEFAULT '',
    ip_address  VARCHAR(45)  NOT NULL DEFAULT '',
    os_info     VARCHAR(250) NOT NULL DEFAULT '',
    app_version VARCHAR(30)  NOT NULL DEFAULT '2.0.0',
    first_seen  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_seen   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (username, hostname)
);

-- ── Audit log ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id         SERIAL       PRIMARY KEY,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,
    username   VARCHAR(100) NOT NULL DEFAULT '',
    hostname   VARCHAR(150) NOT NULL DEFAULT '',
    details    TEXT         NOT NULL DEFAULT '',
    severity   VARCHAR(20)  NOT NULL DEFAULT 'INFO'
);

-- ── Configuration profiles ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
    id          SERIAL       PRIMARY KEY,
    name        VARCHAR(100) UNIQUE NOT NULL,
    config_json JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_audit_created  ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_type     ON audit_log (event_type);
CREATE INDEX IF NOT EXISTS idx_audit_severity ON audit_log (severity);
CREATE INDEX IF NOT EXISTS idx_users_hostname ON org_users (hostname);
CREATE INDEX IF NOT EXISTS idx_users_seen     ON org_users (last_seen DESC);

-- ── Grant table-level permissions ────────────────────────────────────────────
GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- ── Default settings ─────────────────────────────────────────────────────────
INSERT INTO settings (key, value) VALUES
  ('watermark_text',    '{classification} | {username} | {hostname} | {datetime}'),
  ('font_size',         '20'),
  ('font_family',       'Arial'),
  ('font_bold',         'false'),
  ('opacity',           '0.18'),
  ('color',             ''),
  ('rotation',          '-45'),
  ('spacing_x',         '260'),
  ('spacing_y',         '200'),
  ('enabled',           'true'),
  ('schedule_enabled',  'false'),
  ('schedule_start',    '08:00'),
  ('schedule_end',      '18:00'),
  ('update_interval',   '30'),
  ('classification',    'CONFIDENTIAL'),
  ('organization_name', 'Mr.A Corporation'),
  ('department',        'IT'),
  ('custom_text',       ''),
  ('show_username',     'true'),
  ('show_hostname',     'true'),
  ('show_datetime',     'true'),
  ('show_classification','true'),
  ('screenshot_alert',  'true'),
  ('admin_password_hash','240be518fabd2724ddb6f04eeb1da5967448d7e831d06d456'),
  -- Default password: admin123 (SHA-256)
  ('app_version',       '1.0.0')
ON CONFLICT (key) DO NOTHING;

-- ── Default excluded apps ────────────────────────────────────────────────────
INSERT INTO excluded_apps (process_name, display_name) VALUES
  ('taskmgr.exe',      'Task Manager'),
  ('mmc.exe',          'Microsoft Management Console'),
  ('regedit.exe',      'Registry Editor'),
  ('cmd.exe',          'Command Prompt'),
  ('powershell.exe',   'PowerShell'),
  ('snippingtool.exe', 'Snipping Tool'),
  ('SnippingTool.exe', 'Snipping Tool (Win11)'),
  ('mspaint.exe',      'MS Paint'),
  ('calc.exe',         'Calculator')
ON CONFLICT (process_name) DO NOTHING;

-- ── Done ─────────────────────────────────────────────────────────────────────
DO $$
BEGIN
  RAISE NOTICE 'Watermark database schema created successfully.';
END
$$;
