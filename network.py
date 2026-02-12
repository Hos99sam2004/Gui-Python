#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Network-related functions (Telegram, VirusTotal)."""

import time
import requests
from datetime import datetime
from database.models import AppConfig, URLReputationResult


def send_telegram_notification(config: AppConfig, message: str) -> None:
    """Send notification message via Telegram."""
    if not config.telegram_enabled:
        return
    if not config.telegram_bot_token or not config.telegram_chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": config.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        requests.post(url, data=payload, timeout=10)
    except Exception:
        pass


def check_url_reputation(url: str, api_key: str) -> URLReputationResult:
    """Check URL reputation using VirusTotal API."""
    if not api_key or not url:
        return URLReputationResult(
            url=url,
            is_safe=False,
            threat_level="unknown",
            threat_count=0,
            analysis_date="",
            details="API key is missing"
        )
    
    try:
        # Scan the URL
        scan_url = "https://www.virustotal.com/api/v3/urls"
        headers = {"x-apikey": api_key}
        files = {"url": (None, url)}
        
        response = requests.post(scan_url, headers=headers, files=files, timeout=10)
        
        if response.status_code != 200:
            return URLReputationResult(
                url=url,
                is_safe=False,
                threat_level="error",
                threat_count=0,
                analysis_date="",
                details=f"VirusTotal API error: {response.status_code}"
            )
        
        scan_data = response.json()
        analysis_id = scan_data["data"]["id"]
        
        # Get analysis results
        analysis_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
        time.sleep(2)  # Wait before checking results
        
        analysis_response = requests.get(analysis_url, headers=headers, timeout=10)
        
        if analysis_response.status_code == 200:
            analysis_data = analysis_response.json()
            stats = analysis_data["data"]["attributes"]["stats"]
            
            threat_count = stats.get("malicious", 0) + stats.get("suspicious", 0)
            
            if stats.get("malicious", 0) > 0:
                threat_level = "malicious"
            elif stats.get("suspicious", 0) > 0:
                threat_level = "suspicious"
            else:
                threat_level = "clean"
            
            is_safe = threat_level == "clean"
            
            details = (
                f"Malicious: {stats.get('malicious', 0)} | "
                f"Suspicious: {stats.get('suspicious', 0)} | "
                f"Clean: {stats.get('undetected', 0)}"
            )
            
            return URLReputationResult(
                url=url,
                is_safe=is_safe,
                threat_level=threat_level,
                threat_count=threat_count,
                analysis_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                details=details
            )
    except requests.exceptions.Timeout:
        return URLReputationResult(
            url=url,
            is_safe=False,
            threat_level="error",
            threat_count=0,
            analysis_date="",
            details="VirusTotal API timeout"
        )
    except Exception as e:
        return URLReputationResult(
            url=url,
            is_safe=False,
            threat_level="error",
            threat_count=0,
            analysis_date="",
            details=f"Error checking reputation: {str(e)}"
        )
