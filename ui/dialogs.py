#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dialog windows for the application."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox
)

from database.models import AppConfig, URLReputationResult
from network import check_url_reputation, send_telegram_notification
from .styles import get_dialog_stylesheet


class URLCheckDialog(QWidget):
    """Dialog window for checking website reputation."""
    
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.url_results = []
        
        self.setWindowTitle("🛡️ Website Reputation Check")
        self.setGeometry(100, 100, 700, 500)
        self.setStyleSheet(get_dialog_stylesheet())
        
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
        """Check URL reputation and block if suspicious."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "⚠️ Missing URL", "Please enter a URL to check.")
            return
        
        if not self.config.virustotal_enabled:
            QMessageBox.warning(
                self, 
                "⚠️ Feature Disabled", 
                "Please enable VirusTotal URL reputation check in main configuration."
            )
            return
        
        if not self.config.virustotal_api_key:
            QMessageBox.warning(
                self, 
                "⚠️ Missing API Key", 
                "Please enter your VirusTotal API key in main configuration."
            )
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
            QMessageBox.information(
                self, 
                "✅ URL is Safe", 
                f"This URL appears to be safe.\n\n{result.details}"
            )
    
    def _add_url_to_list(self, result: URLReputationResult):
        """Add checked URL to the list view with color coding."""
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
