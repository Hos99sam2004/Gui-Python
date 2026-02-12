#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main window for the identity management application."""

from datetime import datetime
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QGroupBox, QFormLayout, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QCheckBox, QTextEdit, QMessageBox
)

from database.models import AppConfig, ChangeResult
from database.logging import read_last_logs
from core import is_tor_active, get_real_ip, get_tor_ip, get_location_for_ip
from worker import ChangeWorker
from .styles import get_main_stylesheet
from .dialogs import URLCheckDialog


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tor Identity Desktop (PySide6) 🔐")
        self.setStyleSheet(get_main_stylesheet())

        self.config = AppConfig()
        self.worker = None
        self.url_results = []

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
        """Sync configuration from UI inputs."""
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
        """Refresh current IP and status information."""
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
        """Start identity change operation."""
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
        """Handle successful identity change."""
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
        """Handle identity change failure."""
        self.change_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        
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
        """Open the URL reputation check dialog window."""
        self._sync_config_from_ui()
        self.url_dialog = URLCheckDialog(self.config)
        self.url_dialog.show()

    def load_history(self):
        """Load and display change history."""
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
