#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Logging and history management functions."""

import os
import json
from typing import List, Dict
from .models import ChangeResult, AppConfig


def append_log(config: AppConfig, result: ChangeResult) -> None:
    """Append identity change result to log file."""
    if not config.log_enabled:
        return
    try:
        with open(config.log_file, "a", encoding="utf-8") as f:
            log_entry = {
                "timestamp": result.timestamp,
                "real_ip": result.real_ip,
                "old_tor_ip": result.old_tor_ip,
                "new_tor_ip": result.new_tor_ip,
                "old_country": result.old_country,
                "old_city": result.old_city,
                "new_country": result.new_country,
                "new_city": result.new_city,
                "changed": result.changed,
                "note": result.note,
            }
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception:
        # Don't crash for logging issues
        pass


def read_last_logs(log_file: str, limit: int = 50) -> List[Dict]:
    """Read the last N log entries from log file."""
    if not os.path.exists(log_file):
        return []
    items = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    continue
        return list(reversed(items[-limit:]))  # most recent first
    except Exception:
        return []


def clear_logs(log_file: str) -> bool:
    """Clear all log entries."""
    try:
        if os.path.exists(log_file):
            os.remove(log_file)
        return True
    except Exception:
        return False
