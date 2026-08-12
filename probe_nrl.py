#!/usr/bin/env python3
"""Throwaway: find out whether ESPN exposes an NRL fixture feed we can use."""
import json
import urllib.request

CANDIDATES = [
    "https://site.api.espn.com/apis/site/v2/sports/rugby-league/3/scoreboard?dates=20260813-20260910",
    "https://site.api.espn.com/apis/site/v2/sports/rugby-league/nrl/scoreboard?dates=20260813-20260910",
    "https://site.api.espn.com/apis/site/v2/sports/rugby/3/scoreboard?dates=20260813-20260910",
    "https://site.api.espn.com/apis/site/v2/sports/rugby-league/3/teams",
]

for url in CANDIDATES:
    print("\n" + "=" * 70)
    print(url)
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            data = json.load(r)
    except Exception as e:
        print("  FAILED:", type(e).__name__, e)
        continue
    print("  top-level keys:", list(data)[:12])
    evs = data.get("events") or []
    print("  events:", len(evs))
    for ev in evs[:3]:
        comps = ev.get("competitions", [{}])
        c = comps[0] if comps else {}
        print("   -", ev.get("date"), "|", ev.get("name"))
        print("     shortName:", ev.get("shortName"))
        print("     venue:", (c.get("venue") or {}).get("fullName"))
        for t in c.get("competitors", []):
            print("       ", t.get("homeAway"), (t.get("team") or {}).get("displayName"))
    if "sports" in data:
        try:
            teams = data["sports"][0]["leagues"][0]["teams"]
            print("  teams:", [t["team"]["displayName"] for t in teams][:20])
        except Exception as e:
            print("  team parse failed:", e)
