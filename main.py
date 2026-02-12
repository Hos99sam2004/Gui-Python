#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Tor Identity Desktop application.
"""

import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    """Start the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 700)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
