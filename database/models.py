#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Data models and configuration classes for the identity management application."""

from dataclasses import dataclass


@dataclass
class AppConfig:
    """Application configuration settings."""
    tor_socks_proxy: str = "socks5h://127.0.0.1:9050"
    tor_control_port: int = 9051
    log_enabled: bool = True
    log_file: str = "identity_history.log"  # JSON Lines
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    virustotal_enabled: bool = False
    virustotal_api_key: str = ""
    block_suspicious_urls: bool = True


@dataclass
class ChangeResult:
    """Result of identity change operation."""
    timestamp: str
    real_ip: str
    old_tor_ip: str
    new_tor_ip: str
    old_country: str
    old_city: str
    new_country: str
    new_city: str
    changed: bool
    note: str = ""


@dataclass
class URLReputationResult:
    """Result of URL reputation check."""
    url: str
    is_safe: bool
    threat_level: str  # clean, suspicious, malicious
    threat_count: int
    analysis_date: str
    details: str = ""
