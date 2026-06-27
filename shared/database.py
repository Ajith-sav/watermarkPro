"""
WatermarkPro v2 — PostgreSQL Database Manager
Thread-safe connection pool; all CRUD for settings, users, audit, exclusions.
"""

import hashlib
import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool

from shared.models import DEFAULT_SETTINGS, DEFAULT_EXCLUDED_APPS

logger = logging.getLogger(__name__)

_DEFAULT_ADMIN_HASH = hashlib.sha256("admin123".encode()).hexdigest()


class DatabaseManager:
    """
    PostgreSQL-backed persistence layer.
    Provides the exact same interface as the original SQLite version
    so all other modules remain unchanged.
    """

    def __init__(self, **pg_kwargs):
        """
        pg_kwargs: host, port, dbname, user, password, sslmode
        """
        self._kwargs = pg_kwargs
        self._pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
        self._connect_with_retry()

    # ── Pool ─────────────────────────────────────────────────────────────────

    def _connect_with_retry(self, attempts: int = 5, delay: float = 3.0) -> None:
        last_err = None
        for attempt in range(1, attempts + 1):
            try:
                self._pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    connect_timeout=10,
                    **self._kwargs,
                )
                logger.info("PostgreSQL pool connected (attempt %d)", attempt)
                return
            except psycopg2.OperationalError as e:
                last_err = e
                logger.warning("DB connect attempt %d/%d failed: %s", attempt, attempts, e)
                if attempt < attempts:
                    time.sleep(delay)
        raise ConnectionError(f"Cannot connect to PostgreSQL after {attempts} attempts: {last_err}")

    @contextmanager
    def _cursor(self, commit: bool = False):
        """Context manager that borrows a pooled connection and returns it."""
        conn = self._pool.getconn()
        try:
            conn.autocommit = False
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
            if commit:
                conn.commit()
            else:
                conn.rollback()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def close(self) -> None:
        if self._pool:
            self._pool.closeall()

    # ── Settings ──────────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        try:
            with self._cursor() as cur:
                cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
                row = cur.fetchone()
                return row["value"] if row else default
        except Exception as e:
            logger.error("get(%s): %s", key, e)
            return default

    def set(self, key: str, value: Any) -> None:
        with self._cursor(commit=True) as cur:
            cur.execute(
                """INSERT INTO settings (key, value, updated_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (key) DO UPDATE
                       SET value = EXCLUDED.value,
                           updated_at = NOW()""",
                (key, str(value)),
            )

    def get_all(self) -> Dict[str, str]:
        with self._cursor() as cur:
            cur.execute("SELECT key, value FROM settings")
            return {r["key"]: r["value"] for r in cur.fetchall()}

    def bulk_set(self, data: Dict[str, Any]) -> None:
        with self._cursor(commit=True) as cur:
            for k, v in data.items():
                cur.execute(
                    """INSERT INTO settings (key, value, updated_at) VALUES (%s, %s, NOW())
                       ON CONFLICT (key) DO UPDATE
                           SET value = EXCLUDED.value, updated_at = NOW()""",
                    (k, str(v)),
                )

    def ensure_defaults(self) -> None:
        """Insert any missing default settings (idempotent)."""
        with self._cursor(commit=True) as cur:
            for k, v in DEFAULT_SETTINGS.items():
                cur.execute(
                    "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (k, v),
                )
            for proc, name in DEFAULT_EXCLUDED_APPS:
                cur.execute(
                    "INSERT INTO excluded_apps (process_name, display_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (proc, name),
                )
            # Ensure admin password hash exists
            cur.execute(
                "INSERT INTO settings (key, value) VALUES ('admin_password_hash', %s) ON CONFLICT DO NOTHING",
                (_DEFAULT_ADMIN_HASH,),
            )

    # ── Authentication ────────────────────────────────────────────────────────

    def verify_password(self, password: str) -> bool:
        stored = self.get("admin_password_hash", "")
        logger.debug("Verifying password: stored hash=%s, provided hash=%s",
                     stored, hashlib.sha256(password.encode()).hexdigest())
        return stored == hashlib.sha256(password.encode()).hexdigest()

    def set_password(self, new_password: str) -> None:
        self.set("admin_password_hash", hashlib.sha256(new_password.encode()).hexdigest())

    # ── Excluded apps ─────────────────────────────────────────────────────────

    def get_excluded_apps(self) -> List[Dict]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM excluded_apps ORDER BY display_name")
            return [dict(r) for r in cur.fetchall()]

    def get_excluded_names(self) -> List[str]:
        with self._cursor() as cur:
            cur.execute("SELECT process_name FROM excluded_apps")
            return [r["process_name"].lower() for r in cur.fetchall()]

    def add_excluded_app(self, process_name: str, display_name: str = "",
                         added_by: str = "admin") -> bool:
        try:
            with self._cursor(commit=True) as cur:
                cur.execute(
                    "INSERT INTO excluded_apps (process_name, display_name, added_by) VALUES (%s, %s, %s)",
                    (process_name.lower(), display_name, added_by),
                )
            return True
        except psycopg2.IntegrityError:
            return False

    def remove_excluded_app(self, app_id: int) -> None:
        with self._cursor(commit=True) as cur:
            cur.execute("DELETE FROM excluded_apps WHERE id = %s", (app_id,))

    # ── Org users ─────────────────────────────────────────────────────────────

    def register_user(self, username: str, hostname: str, department: str = "",
                      ip_address: str = "", app_version: str = "2.0.0",
                      os_info: str = "") -> None:
        with self._cursor(commit=True) as cur:
            cur.execute(
                """INSERT INTO org_users
                       (username, hostname, department, ip_address, app_version, os_info)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (username, hostname) DO UPDATE SET
                       last_seen   = NOW(),
                       ip_address  = EXCLUDED.ip_address,
                       app_version = EXCLUDED.app_version,
                       os_info     = EXCLUDED.os_info,
                       department  = CASE
                           WHEN EXCLUDED.department <> '' THEN EXCLUDED.department
                           ELSE org_users.department END""",
                (username, hostname, department, ip_address, app_version, os_info),
            )

    def get_org_users(self) -> List[Dict]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM org_users ORDER BY last_seen DESC")
            return [dict(r) for r in cur.fetchall()]

    def get_user_count(self) -> int:
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM org_users")
            return cur.fetchone()["n"]

    def get_active_user_count(self, hours: int = 24) -> int:
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM org_users WHERE last_seen >= NOW() - INTERVAL '%s hours'",
                (hours,),
            )
            return cur.fetchone()["n"]

    # ── Audit log ─────────────────────────────────────────────────────────────

    def log(self, event_type: str, details: str = "", severity: str = "INFO",
            username: str = "", hostname: str = "") -> None:
        try:
            with self._cursor(commit=True) as cur:
                cur.execute(
                    """INSERT INTO audit_log (event_type, username, hostname, details, severity)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (event_type, username, hostname, details, severity),
                )
        except Exception as e:
            logger.error("audit log write failed: %s", e)

    def get_audit_log(self, limit: int = 500, event_type: Optional[str] = None,
                      severity: Optional[str] = None) -> List[Dict]:
        conditions: list = []
        params: list = []
        query = "SELECT * FROM audit_log"
        if event_type:
            conditions.append("event_type = %s"); params.append(event_type)
        if severity:
            conditions.append("severity = %s"); params.append(severity)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        with self._cursor() as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    def clear_audit_log(self) -> None:
        with self._cursor(commit=True) as cur:
            cur.execute("DELETE FROM audit_log")

    # ── Profiles ──────────────────────────────────────────────────────────────

    def save_profile(self, name: str, config: Dict) -> None:
        with self._cursor(commit=True) as cur:
            cur.execute(
                """INSERT INTO profiles (name, config_json) VALUES (%s, %s)
                   ON CONFLICT (name) DO UPDATE SET config_json = EXCLUDED.config_json""",
                (name, json.dumps(config)),
            )

    def get_profiles(self) -> List[Dict]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM profiles ORDER BY name")
            return [dict(r) for r in cur.fetchall()]

    def load_profile(self, name: str) -> Optional[Dict]:
        with self._cursor() as cur:
            cur.execute("SELECT config_json FROM profiles WHERE name = %s", (name,))
            row = cur.fetchone()
            return row["config_json"] if row else None

    def delete_profile(self, name: str) -> None:
        with self._cursor(commit=True) as cur:
            cur.execute("DELETE FROM profiles WHERE name = %s", (name,))

    # ── Export ────────────────────────────────────────────────────────────────

    def export_audit_csv(self, path: Path, limit: int = 5000) -> int:
        import csv
        rows = self.get_audit_log(limit=limit)
        if not rows:
            return 0
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return len(rows)

    def export_json(self, path: Path) -> None:
        data = {
            "settings":      self.get_all(),
            "excluded_apps": self.get_excluded_apps(),
            "org_users":     self.get_org_users(),
            "profiles":      self.get_profiles(),
            "exported_at":   datetime.now().isoformat(),
        }
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
