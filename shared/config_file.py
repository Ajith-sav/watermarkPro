"""
WatermarkPro v2 — Config File Loader
Reads config.ini from the directory containing the running EXE / script.
"""

import configparser
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CONFIG_NAME = "config.ini"


def _config_dir() -> Path:
    """Return directory that contains config.ini regardless of frozen/script mode."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def load() -> configparser.ConfigParser:
    """Load and return the config.  Raises FileNotFoundError if config.ini missing."""
    cfg_path = _config_dir() / _CONFIG_NAME
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"config.ini not found at {cfg_path}.\n"
            f"Copy config.ini.template to config.ini and fill in your PostgreSQL details."
        )
    cfg = configparser.ConfigParser()
    cfg.read(str(cfg_path), encoding="utf-8")
    logger.debug("Config loaded from %s", cfg_path)
    return cfg


def get_db_kwargs() -> dict:
    """Return psycopg2 connect kwargs from config.ini."""
    cfg = load()
    db = cfg["database"]
    return {
        "host":     db.get("host",     "localhost"),
        "port":     int(db.get("port", "5432")),
        "dbname":   db.get("dbname",   "watermark"),
        "user":     db.get("user",     "postgres"),
        "password": db.get("password", "root_123"),
        "sslmode":  db.get("sslmode",  "prefer"),
    }


def get_app_value(key: str, fallback: str = "") -> str:
    """Read a value from the [app] section."""
    try:
        cfg = load()
        return cfg.get("app", key, fallback=fallback)
    except Exception:
        return fallback
