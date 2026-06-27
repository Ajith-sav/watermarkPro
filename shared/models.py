"""
WatermarkPro v2 — Shared Models & Constants
"""

from typing import Dict

APP_VERSION = "2.0.0"

CLASSIFICATION_COLORS: Dict[str, str] = {
    "PUBLIC":        "#44AA44",
    "INTERNAL":      "#4488CC",
    "CONFIDENTIAL":  "#AAAAAA",
    "RESTRICTED":    "#DDAA22",
    "SECRET":        "#DD4444",
}

SEVERITY_LEVELS = ["INFO", "WARNING", "ERROR", "SECURITY"]

DEFAULT_SETTINGS: Dict[str, str] = {
    "watermark_text":     "{classification} | {username} | {hostname} | {datetime}",
    "font_size":          "20",
    "font_family":        "Arial",
    "font_bold":          "false",
    "opacity":            "0.18",
    "color":              "",
    "rotation":           "-45",
    "spacing_x":          "260",
    "spacing_y":          "160",
    "enabled":            "true",
    "schedule_enabled":   "false",
    "schedule_start":     "08:00",
    "schedule_end":       "18:00",
    "update_interval":    "30",
    "classification":     "CONFIDENTIAL",
    "organization_name":  "My Organization",
    "department":         "",
    "custom_text":        "",
    "show_username":      "true",
    "show_hostname":      "true",
    "show_datetime":      "true",
    "show_classification":"true",
    "screenshot_alert":   "true",
    "app_version":        APP_VERSION,
}

DEFAULT_EXCLUDED_APPS = [
    ("taskmgr.exe",      "Task Manager"),
    ("mmc.exe",          "Microsoft Management Console"),
    ("regedit.exe",      "Registry Editor"),
    ("cmd.exe",          "Command Prompt"),
    ("powershell.exe",   "PowerShell"),
    ("snippingtool.exe", "Snipping Tool"),
    ("SnippingTool.exe", "Snipping Tool (Win11)"),
    ("calc.exe",         "Calculator"),
]
