#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Worker thread for identity change operations."""

import time
from datetime import datetime
from PySide6.QtCore import QThread, Signal as QtSignal

from database.models import AppConfig, ChangeResult
from database.logging import append_log
from core import get_real_ip, get_tor_ip, get_location_for_ip, tor_newnym
from network import send_telegram_notification


class ChangeWorker(QThread):
    """Worker thread to handle identity change operation."""
    done = QtSignal(object)   # ChangeResult
    failed = QtSignal(str)

    def __init__(self, config: AppConfig, wait_seconds: int = 8, retries: int = 2):
        super().__init__()
        self.config = config
        self.wait_seconds = wait_seconds
        self.retries = retries

    def run(self):
        """Execute identity change operation."""
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

            # Telegram notification
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
