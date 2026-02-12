#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stylesheet definitions for UI components."""


def get_main_stylesheet() -> str:
    """Get stylesheet for main window."""
    return """
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
"""


def get_dialog_stylesheet() -> str:
    """Get stylesheet for dialog windows."""
    return """
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
"""
