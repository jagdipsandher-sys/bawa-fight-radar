#!/usr/bin/env python3
"""TEMPORARY probe — deleted after use.

Four builders report every single fetch as HTTPError while others on the same
host are fine. The builders only print the exception TYPE, so the actual
status code has never been seen. This gets it, and tests whether an obvious
alternative path works.
"""
import json
import urllib.request
from datetime import datetime, timedelta, timezone

now = datetime.now(timezone.utc)
a, b = now.strftime("%Y%m%d"), (now + timedelta(days=6)).strftime("%Y%m%d")

SITE = "https://site.api.espn.com/apis/site/v2/sports"

CHECKS = [
    ("WORKS NOW  mma/ufc",        f"{SITE}/mma/ufc/scoreboard?dates={a}-{b}"),
    ("WORKS NOW  racing/f1",      f"{SITE}/racing/f1/scoreboard?dates={a}-{b}"),
    ("BROKEN     rugby-league/3", f"{SITE}/rugby-league/3/scoreboard?dates={a}-{b}"),
    ("BROKEN     soccer/eng.1",   f"{SITE}/soccer/eng.1/scoreboard?dates={a}-{b}"),
    ("BROKEN     basketball/nba", f"{SITE}/basketball/nba/scoreboard?dates={a}-{b}"),
]

print("=" * 72)
print("A. WHAT IS THE ACTUAL STATUS CODE?")
print("=" * 72)
for label, url in CHECKS:
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            d = json.load(r)
            print(f"  {r.status}  {label}   events={len(d.get('events', []))}")
    except Exception as e:
        code = getattr(e, "code", type(e).__name__)
        reason = getattr(e, "reason", "")
        print(f"  {code}  {label}   {reason}")

print()
print("=" * 72)
print("B. DO THESE WORK WITHOUT THE dates PARAMETER?")
print("=" * 72)
for label, base in [("rugby-league/3", f"{SITE}/rugby-league/3/scoreboard"),
                    ("soccer/eng.1", f"{SITE}/soccer/eng.1/scoreboard"),
                    ("basketball/nba", f"{SITE}/basketball/nba/scoreboard")]:
    try:
        with urllib.request.urlopen(base, timeout=25) as r:
            d = json.load(r)
            print(f"  {r.status}  {label}   events={len(d.get('events', []))}")
    except Exception as e:
        print(f"  {getattr(e, 'code', type(e).__name__)}  {label}")

print()
print("=" * 72)
print("C. DOES A BROWSER USER AGENT CHANGE ANYTHING?")
print("=" * 72)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"}
for label, url in CHECKS[2:]:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.load(r)
            print(f"  {r.status}  {label}   events={len(d.get('events', []))}  <-- UA FIXES IT")
    except Exception as e:
        print(f"  {getattr(e, 'code', type(e).__name__)}  {label}")

print()
print("=" * 72)
print("D. ALTERNATIVE HOST (the one build_standings.py uses and which works)")
print("=" * 72)
CORE = "https://site.web.api.espn.com/apis/site/v2/sports"
for label, path in [("rugby-league/3", "rugby-league/3"),
                    ("soccer/eng.1", "soccer/eng.1"),
                    ("basketball/nba", "basketball/nba")]:
    url = f"{CORE}/{path}/scoreboard?dates={a}-{b}"
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            d = json.load(r)
            print(f"  {r.status}  {label}   events={len(d.get('events', []))}  <-- HOST FIXES IT")
    except Exception as e:
        print(f"  {getattr(e, 'code', type(e).__name__)}  {label}")
