#!/usr/bin/env python3
"""TEMPORARY probe 2 — which dates= format do the broken sports now accept?"""
import json, urllib.request
from datetime import datetime, timedelta, timezone

now = datetime.now(timezone.utc)
d0 = now.strftime("%Y%m%d")
d6 = (now + timedelta(days=6)).strftime("%Y%m%d")
SITE = "https://site.api.espn.com/apis/site/v2/sports"
SPORTS = [("rugby-league/3", "NRL"), ("soccer/eng.1", "Prem"), ("basketball/nba", "NBA")]

FORMATS = [
    ("range  dates=A-B",      f"?dates={d0}-{d6}"),
    ("single dates=A",        f"?dates={d0}"),
    ("month  dates=YYYYMM",   f"?dates={now:%Y%m}"),
    ("year   dates=YYYY",     f"?dates={now:%Y}"),
    ("none",                  ""),
    ("limit only",            "?limit=100"),
]

for path, label in SPORTS:
    print(f"=== {label}  ({path}) ===")
    for fmt_label, q in FORMATS:
        url = f"{SITE}/{path}/scoreboard{q}"
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                d = json.load(r)
                evs = d.get("events", [])
                when = ""
                if evs:
                    when = evs[0].get("date", "")[:10] + " .. " + evs[-1].get("date", "")[:10]
                print(f"   {r.status}  {fmt_label:<22} events={len(evs):<4} {when}")
        except Exception as e:
            print(f"   {getattr(e,'code',type(e).__name__)}  {fmt_label}")
    print()
