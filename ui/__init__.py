#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI module for graphical interface components."""

from .styles import get_main_stylesheet, get_dialog_stylesheet
from .main_window import MainWindow
from .dialogs import URLCheckDialog

__all__ = [
    "get_main_stylesheet",
    "get_dialog_stylesheet",
    "MainWindow",
    "URLCheckDialog",
]
