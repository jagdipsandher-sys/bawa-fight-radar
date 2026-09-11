#!/usr/bin/env python3
"""TEMPORARY probe — deleted after this run.

Confirms the automatic headshots actually resolve for the real fighters on
the upcoming cards, rather than assuming the URL pattern works.
"""
import urllib.request
from datetime import datetime, timezone

from send_fights import SYD, fetch_ufc
from build_radar import ESPN_HEADSHOT, photo_for, main_line, fighters


def status(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.status, r.headers.get("Content-Length", "?")
    except Exception as e:
        return getattr(e, "code", type(e).__name__), ""


now = datetime.now(timezone.utc)
events = fetch_ufc(now, now + __import__("datetime").timedelta(days=40))

print("=" * 72)
print("REAL CARDS — times and headshot resolution")
print("=" * 72)
for ev in events:
    syd = ev["when_utc"].astimezone(SYD)
    print(f"\n{ev['name']}")
    print(f"  card starts : {syd:%a %d %b %-I:%M%p} {syd.tzname()}")
    if ev.get("main_utc"):
        m = ev["main_utc"].astimezone(SYD)
        print(f"  main event  : {m:%a %d %b %-I:%M%p} {m.tzname()}")
    print(f"  page shows  : from {syd:%-I:%M%p}{main_line(ev)}".lower().replace(":00", ""))
    for n in fighters(ev):
        url = photo_for(n, ev.get("ids"))
        if not url:
            print(f"    {n}: no photo -> initials")
            continue
        code, size = status(url)
        src = "espn-auto" if url.startswith(ESPN_HEADSHOT[:40]) else "photos.json"
        ok = "OK" if code == 200 else "-> falls back to initials"
        print(f"    {n}: {code} ({src}, {size} bytes) {ok}")
