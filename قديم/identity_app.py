#!/usr/bin/env python3
import sys
import os
import time
import json
import requests
import subprocess
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict

from stem import Signal
from stem.control import Controller

from PySide6.QtCore import Qt, QThread, Signal as QtSignal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QLineEdit,
    QHBoxLayout, QVBoxLayout, QTextEdit, QMessageBox, QGroupBox, QFormLayout,
    QSpinBox, QCheckBox, QScrollArea, QListWidget, QListWidgetItem
)


# -----------------------------
# Config + State
# -----------------------------
@dataclass
class AppConfig:
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
    url: str
    is_safe: bool
    threat_level: str  # clean, suspicious, malicious
    threat_count: int
    analysis_date: str
    details: str = ""


# -----------------------------
# Core functions (safe subset)
# -----------------------------
def is_tor_active() -> bool:
    # systemctl may not exist (e.g., Windows). We'll just try.
    try:
        subprocess.check_output(["systemctl", "is-active", "--quiet", "tor"])
        return True
    except Exception:
        return False


def get_real_ip() -> str:
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=10)
        return r.json().get("ip", "Not Defined")
    except Exception:
        return "Not Defined"


def get_tor_ip(tor_socks_proxy: str) -> str:
    proxies = {"http": tor_socks_proxy, "https": tor_socks_proxy}
    urls = [
        "https://check.torproject.org/api/ip",
        "https://httpbin.org/ip",
        "https://api.ipify.org?format=json",
    ]
    for url in urls:
        try:
            r = requests.get(url, proxies=proxies, timeout=12)
            data = r.json()
            if "IP" in data:
                return data["IP"]
            if "origin" in data:
                return data["origin"]
            if "ip" in data:
                return data["ip"]
        except Exception:
            continue
    return "Not Defined"


def get_location_for_ip(ip: str) -> (str, str):
    if not ip or ip == "Not Defined":
        return "Not Defined", "Not Defined"

    # Single provider to keep it stable for demos
    try:
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=10)
        if r.status_code == 200:
            j = r.json()
            country = j.get("country_name") or "Not Defined"
            city = j.get("city") or "Not Defined"
            return country, city
    except Exception:
        pass

    return "Not Defined", "Not Defined"


def tor_newnym(control_port: int) -> None:
    # NOTE: This depends on torrc auth (cookie/password). If it fails, show the error.
    try:
        with Controller.from_port(port=control_port) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
    except Exception as e:
        raise Exception(f"Failed to connect to Tor control port {control_port}: {str(e)}")


def append_log(config: AppConfig, result: ChangeResult) -> None:
    if not config.log_enabled:
        return
    try:
        with open(config.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
    except Exception:
        # Don't crash UI for logging issues
        pass


def read_last_logs(log_file: str, limit: int = 50) -> List[Dict]:
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


def send_telegram_notification(config: AppConfig, message: str) -> None:
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
    """
    Check URL reputation using VirusTotal API.
    Returns URLReputationResult with safety information.
    """
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


# -----------------------------
# Worker thread for "Change Identity"
# -----------------------------
class ChangeWorker(QThread):
    done = QtSignal(object)   # ChangeResult
    failed = QtSignal(str)

    def __init__(self, config: AppConfig, wait_seconds: int = 8, retries: int = 2):
        super().__init__()
        self.config = config
        self.wait_seconds = wait_seconds
        self.retries = retries

    def run(self):
        try:
            real_ip = get_real_ip()
            old_ip = get_tor_ip(self.config.tor_socks_proxy)
            old_country, old_city = get_location_for_ip(old_ip)

            # Try NEWNYM + small retries to increase chance of IP change
            note = ""
            new_ip = old_ip
            for attempt in range(self.retries + 1):
                tor_newnym(self.config.tor_control_port)
                time.sleep(self.wait_seconds)
                new_ip = get_tor_ip(self.config.tor_socks_proxy)
                if new_ip != "Not Defined" and new_ip != old_ip:
                    break
                note = "Circuit refreshed but exit IP may stay the same (normal sometimes)."

            new_country, new_city = get_location_for_ip(new_ip)
            changed = (new_ip != "Not Defined" and old_ip != "Not Defined" and new_ip != old_ip)

            res = ChangeResult(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                real_ip=real_ip,
                old_tor_ip=old_ip,
                new_tor_ip=new_ip,
                old_country=old_country,
                old_city=old_city,
                new_country=new_country,
                new_city=new_city,
                changed=changed,
                note=note
            )

            append_log(self.config, res)

            # Telegram
            msg = (
                "🔔 <b>Identity Update</b>\n\n"
                f"<b>Real IP:</b> <code>{real_ip}</code>\n\n"
                f"<b>Old Tor IP:</b> <code>{old_ip}</code>\n"
                f"<b>Old Location:</b> {old_country} / {old_city}\n\n"
                f"<b>New Tor IP:</b> <code>{new_ip}</code>\n"
                f"<b>New Location:</b> {new_country} / {new_city}\n\n"
                f"<b>Changed:</b> {'Yes ✅' if changed else 'No ⚠️'}\n"
            )
            if note:
                msg += f"\n<i>{note}</i>\n"
            send_telegram_notification(self.config, msg)

            self.done.emit(res)
        except Exception as e:
            self.failed.emit(str(e))


# -----------------------------
# UI - URL Check Dialog
# -----------------------------
class URLCheckDialog(QWidget):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.url_results = []
        
        self.setWindowTitle("🛡️ Website Reputation Check")
        self.setGeometry(100, 100, 700, 500)
        
        # Apply stylesheet
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                            stop:0 #1a1a2e, stop:0.5 #16213e, stop:1 #0f3460);
            }
            QGroupBox {
                border: 3px solid;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                font-weight: bold;
                color: #ffffff;
                padding-left: 10px;
                padding-right: 10px;
                padding-bottom: 10px;
            }
            QGroupBox#configGroup {
                border-color: #ff6b9d;
                background-color: rgba(255, 107, 157, 0.05);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                font-size: 12pt;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #00d4ff, stop:1 #0099cc);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 11pt;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #00e8ff, stop:1 #00b3e6);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #0099cc, stop:1 #006699);
            }
            QLabel {
                color: #ffffff;
                font-size: 10pt;
            }
            QLineEdit {
                border: 2px solid #00d4ff;
                border-radius: 4px;
                padding: 6px;
                background-color: #0f3460;
                color: #00ff88;
                selection-background-color: #00d4ff;
                selection-color: #000000;
            }
            QLineEdit:focus {
                border: 2px solid #ff6b9d;
            }
            QListWidget {
                border: 2px solid #00d4ff;
                border-radius: 4px;
                background-color: #0a1929;
                color: #00ff88;
            }
            QListWidget::item {
                padding: 8px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #00d4ff;
                color: #000000;
            }
        """)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # URL Check Box
        url_check_box = QGroupBox("🔍 Check Website Reputation")
        url_check_box.setObjectName("configGroup")
        url_check_layout = QFormLayout(url_check_box)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL to check (e.g., https://example.com)")
        self.url_input.setMaximumWidth(400)
        self.check_url_btn = QPushButton("🔍 Check URL Safety")
        self.check_url_btn.clicked.connect(self.check_url_safety)
        
        url_check_layout.addRow("🌐 URL to check:", self.url_input)
        url_check_layout.addWidget(self.check_url_btn)
        
        # List view for checked URLs
        self.url_list = QListWidget()
        self.url_list.setMaximumHeight(300)
        
        # Results
        results_box = QGroupBox("📋 Check Results")
        results_box.setObjectName("configGroup")
        results_layout = QVBoxLayout(results_box)
        results_layout.addWidget(self.url_list)
        
        # Add to main layout
        layout.addWidget(url_check_box)
        layout.addWidget(results_box, 1)
        
    def check_url_safety(self):
        """Check URL reputation and block if suspicious"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "⚠️ Missing URL", "Please enter a URL to check.")
            return
        
        if not self.config.virustotal_enabled:
            QMessageBox.warning(self, "⚠️ Feature Disabled", "Please enable VirusTotal URL reputation check in main configuration.")
            return
        
        if not self.config.virustotal_api_key:
            QMessageBox.warning(self, "⚠️ Missing API Key", "Please enter your VirusTotal API key in main configuration.")
            return
        
        # Check reputation
        result = check_url_reputation(url, self.config.virustotal_api_key)
        
        # Add result to list view
        self._add_url_to_list(result)
        
        # Block or allow connection
        if not result.is_safe and self.config.block_suspicious_urls:
            self.url_input.clear()
            
            # Send alert notification
            alert_msg = (
                f"🚨 <b>SUSPICIOUS URL BLOCKED</b>\n\n"
                f"<b>URL:</b> {result.url}\n"
                f"<b>Threat Level:</b> {result.threat_level.upper()}\n"
                f"<b>Threats:</b> {result.threat_count}\n"
                f"<b>Details:</b> {result.details}"
            )
            send_telegram_notification(self.config, alert_msg)
            
            QMessageBox.critical(
                self, 
                "🚫 Connection Blocked",
                f"This URL appears to be dangerous!\n\n"
                f"Threat Level: {result.threat_level.upper()}\n"
                f"Threats Detected: {result.threat_count}\n\n"
                f"Details:\n{result.details}\n\n"
                f"Connection has been blocked for your safety."
            )
        elif result.is_safe:
            self.url_input.clear()
            QMessageBox.information(self, "✅ URL is Safe", f"This URL appears to be safe.\n\n{result.details}")
    
    def _add_url_to_list(self, result: URLReputationResult):
        """Add checked URL to the list view with color coding"""
        # Create list item with appropriate emoji and formatting
        if result.is_safe:
            status_text = "✅ SAFE"
            color = "#00ff88"  # Green
        elif result.threat_level == "suspicious":
            status_text = "⚠️ SUSPICIOUS"
            color = "#ffd700"  # Gold
        elif result.threat_level == "malicious":
            status_text = "❌ MALICIOUS"
            color = "#ff6b9d"  # Red
        else:
            status_text = "❓ UNKNOWN"
            color = "#ffffff"  # White
        
        # Format the URL for display (truncate if too long)
        display_url = result.url
        if len(display_url) > 60:
            display_url = display_url[:57] + "..."
        
        # Create item text
        item_text = f"{status_text} | {display_url} | Threats: {result.threat_count}"
        
        # Create and add list item
        item = QListWidgetItem(item_text)
        item.setForeground(QColor(color))
        item.setFont(QFont("Courier New", 9))
        
        # Store the full result in item data
        item.setData(Qt.UserRole, result)
        
        # Add to list
        self.url_list.insertItem(0, item)
        self.url_results.append(result)


# -----------------------------
# UI
# -----------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tor Identity Desktop (PySide6) 🔐")
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                            stop:0 #1a1a2e, stop:0.5 #16213e, stop:1 #0f3460);
            }
            QGroupBox {
                border: 3px solid;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                font-weight: bold;
                color: #ffffff;
                padding-left: 10px;
                padding-right: 10px;
                padding-bottom: 10px;
            }
            QGroupBox#statusGroup {
                border-color: #00d4ff;
                background-color: rgba(0, 212, 255, 0.05);
            }
            QGroupBox#configGroup {
                border-color: #ff6b9d;
                background-color: rgba(255, 107, 157, 0.05);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                font-size: 12pt;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #00d4ff, stop:1 #0099cc);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 11pt;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #00e8ff, stop:1 #00b3e6);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #0099cc, stop:1 #006699);
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #999999;
            }
            QLabel {
                color: #ffffff;
                font-size: 10pt;
            }
            QLineEdit {
                border: 2px solid #00d4ff;
                border-radius: 4px;
                padding: 6px;
                background-color: #0f3460;
                color: #00ff88;
                selection-background-color: #00d4ff;
                selection-color: #000000;
            }
            QLineEdit:focus {
                border: 2px solid #ff6b9d;
            }
            QSpinBox {
                border: 2px solid #00d4ff;
                border-radius: 4px;
                padding: 5px;
                background-color: #0f3460;
                color: #00ff88;
            }
            QSpinBox:focus {
                border: 2px solid #ff6b9d;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #00d4ff;
                border: none;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #00d4ff;
                border-radius: 3px;
                background-color: #0f3460;
            }
            QCheckBox::indicator:checked {
                background-color: #00d4ff;
            }
            QTextEdit {
                border: 2px solid #00d4ff;
                border-radius: 6px;
                background-color: #0a1929;
                color: #00ff88;
                font-family: 'Courier New', monospace;
                font-size: 9pt;
            }
            QTextEdit:focus {
                border: 2px solid #ff6b9d;
            }
        """)

        self.config = AppConfig()
        self.worker = None
        self.url_results = []  # Store URL check results

        root = QWidget()
        self.setCentralWidget(root)

        # Status group
        status_box = QGroupBox("📊 Status")
        status_box.setObjectName("statusGroup")
        status_layout = QFormLayout(status_box)

        self.tor_active_lbl = QLabel("-")
        self.tor_active_lbl.setFont(QFont("Arial", 11, QFont.Bold))
        
        self.real_ip_lbl = QLabel("-")
        self.real_ip_lbl.setFont(QFont("Courier New", 11, QFont.Bold))
        self.real_ip_lbl.setStyleSheet("color: #ff6b9d;")
        
        self.tor_ip_lbl = QLabel("-")
        self.tor_ip_lbl.setFont(QFont("Courier New", 11, QFont.Bold))
        self.tor_ip_lbl.setStyleSheet("color: #00ff88;")
        
        self.tor_loc_lbl = QLabel("-")
        self.tor_loc_lbl.setFont(QFont("Arial", 10))
        self.tor_loc_lbl.setStyleSheet("color: #ffd700;")

        status_layout.addRow("🔷 Tor service active:", self.tor_active_lbl)
        status_layout.addRow("🌍 Real IP:", self.real_ip_lbl)
        status_layout.addRow("🔐 Tor IP:", self.tor_ip_lbl)
        status_layout.addRow("📍 Tor Location:", self.tor_loc_lbl)

        # Config group
        cfg_box = QGroupBox("⚙️ Configuration")
        cfg_box.setObjectName("configGroup")
        cfg_layout = QFormLayout(cfg_box)

        self.socks_input = QLineEdit(self.config.tor_socks_proxy)
        self.socks_input.setMaximumWidth(400)
        self.control_port_input = QSpinBox()
        self.control_port_input.setRange(1, 65535)
        self.control_port_input.setValue(self.config.tor_control_port)
        self.control_port_input.setMaximumWidth(150)

        self.wait_input = QSpinBox()
        self.wait_input.setRange(1, 60)
        self.wait_input.setValue(8)
        self.wait_input.setMaximumWidth(150)

        self.retry_input = QSpinBox()
        self.retry_input.setRange(0, 5)
        self.retry_input.setValue(2)
        self.retry_input.setMaximumWidth(150)

        self.log_enabled_cb = QCheckBox("Enable logging")
        self.log_enabled_cb.setChecked(self.config.log_enabled)
        self.log_file_input = QLineEdit(self.config.log_file)
        self.log_file_input.setMaximumWidth(400)

        self.telegram_enabled_cb = QCheckBox("Enable Telegram notifications")
        self.telegram_enabled_cb.setChecked(self.config.telegram_enabled)
        self.telegram_token_input = QLineEdit(self.config.telegram_bot_token)
        self.telegram_chat_input = QLineEdit(self.config.telegram_chat_id)
        self.telegram_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.telegram_token_input.setMaximumWidth(400)
        self.telegram_chat_input.setMaximumWidth(400)

        self.virustotal_enabled_cb = QCheckBox("Enable URL Reputation Check (VirusTotal)")
        self.virustotal_enabled_cb.setChecked(self.config.virustotal_enabled)
        self.virustotal_api_input = QLineEdit(self.config.virustotal_api_key)
        self.virustotal_api_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.virustotal_api_input.setPlaceholderText("Enter your VirusTotal API key")
        self.virustotal_api_input.setMaximumWidth(400)
        self.block_suspicious_cb = QCheckBox("Block suspicious URLs")
        self.block_suspicious_cb.setChecked(self.config.block_suspicious_urls)

        cfg_layout.addRow("🔌 Tor SOCKS proxy:", self.socks_input)
        cfg_layout.addRow("🎛️ Tor Control port:", self.control_port_input)
        cfg_layout.addRow("⏱️ Wait seconds:", self.wait_input)
        cfg_layout.addRow("🔄 Retries:", self.retry_input)
        cfg_layout.addRow(self.log_enabled_cb)
        cfg_layout.addRow("📄 Log file:", self.log_file_input)
        cfg_layout.addRow(self.telegram_enabled_cb)
        cfg_layout.addRow("🤖 Telegram bot token:", self.telegram_token_input)
        cfg_layout.addRow("💬 Telegram chat id:", self.telegram_chat_input)
        cfg_layout.addRow(self.virustotal_enabled_cb)
        cfg_layout.addRow("🔐 VirusTotal API key:", self.virustotal_api_input)
        cfg_layout.addRow(self.block_suspicious_cb)

        # Buttons
        btn_row = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 Refresh Status")
        self.change_btn = QPushButton("🔑 Change Identity (Tor)")
        self.load_hist_btn = QPushButton("📋 Load History")
        self.url_check_open_btn = QPushButton("🛡️ URL Reputation Check")

        btn_row.addWidget(self.refresh_btn)
        btn_row.addWidget(self.change_btn)
        btn_row.addWidget(self.load_hist_btn)
        btn_row.addWidget(self.url_check_open_btn)

        # Output
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("النتائج والسجل سيظهر هنا... / Results and history will appear here...")

        # Layout
        main_layout = QVBoxLayout(root)
        main_layout.addWidget(status_box)
        main_layout.addWidget(cfg_box)
        main_layout.addLayout(btn_row)
        main_layout.addWidget(self.output, 1)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Wiring
        self.refresh_btn.clicked.connect(self.refresh_status)
        self.change_btn.clicked.connect(self.change_identity)
        self.load_hist_btn.clicked.connect(self.load_history)
        self.url_check_open_btn.clicked.connect(self.open_url_check_dialog)

        # Initial
        self.refresh_status()
        self.load_history()

    def _sync_config_from_ui(self):
        self.config.tor_socks_proxy = self.socks_input.text().strip() or self.config.tor_socks_proxy
        self.config.tor_control_port = int(self.control_port_input.value())
        self.config.log_enabled = self.log_enabled_cb.isChecked()
        self.config.log_file = self.log_file_input.text().strip() or self.config.log_file
        self.config.telegram_enabled = self.telegram_enabled_cb.isChecked()
        self.config.telegram_bot_token = self.telegram_token_input.text().strip()
        self.config.telegram_chat_id = self.telegram_chat_input.text().strip()
        self.config.virustotal_enabled = self.virustotal_enabled_cb.isChecked()
        self.config.virustotal_api_key = self.virustotal_api_input.text().strip()
        self.config.block_suspicious_urls = self.block_suspicious_cb.isChecked()

    def refresh_status(self):
        self._sync_config_from_ui()

        try:
            active = is_tor_active()
            self.tor_active_lbl.setText("✅ Yes" if active else "⚠️ Unknown/No")
            self.tor_active_lbl.setStyleSheet("color: green;" if active else "color: orange;")

            real_ip = get_real_ip()
            tor_ip = get_tor_ip(self.config.tor_socks_proxy)
            country, city = get_location_for_ip(tor_ip)

            if tor_ip == "Not Defined":
                self.tor_ip_lbl.setStyleSheet("color: red;")
            else:
                self.tor_ip_lbl.setStyleSheet("color: green;")

            self.real_ip_lbl.setText(real_ip)
            self.tor_ip_lbl.setText(tor_ip)
            self.tor_loc_lbl.setText(f"{country} / {city}")

            self.output.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Status refreshed successfully.")
        except Exception as e:
            self.output.append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error refreshing status: {str(e)}")
            self.tor_active_lbl.setText("❌ Connection Error")
            self.tor_active_lbl.setStyleSheet("color: red;")

    def change_identity(self):
        self._sync_config_from_ui()

        self.change_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)

        wait_s = int(self.wait_input.value())
        retries = int(self.retry_input.value())

        self.output.append("\n" + "="*60)
        self.output.append("🔑 Change Identity requested")
        self.output.append("Sending NEWNYM to Tor...")
        self.output.append("="*60)

        self.worker = ChangeWorker(self.config, wait_seconds=wait_s, retries=retries)
        self.worker.done.connect(self.on_change_done)
        self.worker.failed.connect(self.on_change_failed)
        self.worker.start()

    def on_change_done(self, res: ChangeResult):
        self.change_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)

        status_emoji = "✅" if res.changed else "⚠️"
        self.output.append(
            f"\n{status_emoji} [{res.timestamp}] Change Identity Results:\n"
            f"   Real IP: {res.real_ip}\n"
            f"   Old Tor IP: {res.old_tor_ip} ({res.old_country}/{res.old_city})\n"
            f"   New Tor IP: {res.new_tor_ip} ({res.new_country}/{res.new_city})\n"
            f"   Changed: {'✅ Yes' if res.changed else '⚠️ No'}\n"
        )
        if res.note:
            self.output.append(f"   Note: {res.note}\n")

        # Update status labels
        self.real_ip_lbl.setText(res.real_ip)
        self.tor_ip_lbl.setText(res.new_tor_ip)
        self.tor_ip_lbl.setStyleSheet("color: green;")
        self.tor_loc_lbl.setText(f"{res.new_country} / {res.new_city}")

    def on_change_failed(self, err: str):
        self.change_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        
        # Enhanced error messages
        error_msg = str(err)
        display_msg = error_msg
        
        if "Connection refused" in error_msg or "10061" in error_msg:
            display_msg = (
                "❌ فشل الاتصال بـ Tor Control\n\n"
                "Make sure:\n"
                "✓ Tor is running\n"
                "✓ Control port is configured correctly\n"
                f"✓ Control port matches your torrc config\n\n"
                f"Error: {error_msg}"
            )
        elif "timed out" in error_msg.lower():
            display_msg = (
                "⏱️ Request timed out\n\n"
                "The connection took too long.\n"
                "This might be a network issue.\n\n"
                f"Error: {error_msg}"
            )
        
        QMessageBox.critical(self, "❌ Change Failed", display_msg)
        self.output.append(f"\n❌ ERROR: {error_msg}\n")

    def open_url_check_dialog(self):
        """Open the URL reputation check dialog window"""
        self._sync_config_from_ui()
        self.url_dialog = URLCheckDialog(self.config)
        self.url_dialog.show()

    def load_history(self):
        self._sync_config_from_ui()
        items = read_last_logs(self.config.log_file, limit=50)
        if not items:
            self.output.append("\n📋 No history found yet.\n")
            return

        self.output.append("\n" + "="*60)
        self.output.append("📋 History (latest 50 entries)")
        self.output.append("="*60)
        for it in items:
            ts = it.get("timestamp", "?")
            old_ip = it.get("old_tor_ip", "?")
            new_ip = it.get("new_tor_ip", "?")
            changed = it.get("changed", False)
            emoji = "✅" if changed else "⚠️"
            self.output.append(f"{emoji} [{ts}] {old_ip} → {new_ip}")
        self.output.append("="*60 + "\n")


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(900, 700)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
