#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Core functions for IP and Tor operations."""

import subprocess
import requests
from stem import Signal
from stem.control import Controller


def is_tor_active() -> bool:
    """Check if Tor service is running."""
    try:
        subprocess.check_output(["systemctl", "is-active", "--quiet", "tor"])
        return True
    except Exception:
        return False


def get_real_ip() -> str:
    """Get real (non-Tor) IP address."""
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=10)
        return r.json().get("ip", "Not Defined")
    except Exception:
        return "Not Defined"


def get_tor_ip(tor_socks_proxy: str) -> str:
    """Get IP address through Tor."""
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


def get_location_for_ip(ip: str) -> tuple:
    """Get geographic location (country, city) for IP address."""
    if not ip or ip == "Not Defined":
        return "Not Defined", "Not Defined"

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
    """Send NEWNYM signal to Tor to change identity."""
    try:
        with Controller.from_port(port=control_port) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
    except Exception as e:
        raise Exception(f"Failed to connect to Tor control port {control_port}: {str(e)}")
