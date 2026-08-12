#!/usr/bin/env python3
"""Throwaway: what fields does the ESPN NRL feed give us for a Panthers game?"""
import json
import urllib.request

FEED = "https://site.api.espn.com/apis/site/v2/sports/rugby-league/3/scoreboard?dates={}"


def get(rng):
    with urllib.request.urlopen(FEED.format(rng), timeout=25) as r:
        return json.load(r)


# 1. how far ahead will it serve?
for rng in ["20260813-20260910", "20260813-20261012", "20260813-20261231"]:
    try:
        d = get(rng)
        evs = d.get("events", [])
        print(f"{rng}: {len(evs)} events, last = {evs[-1]['date'] if evs else '-'}")
    except Exception as e:
        print(f"{rng}: FAILED {e}")

# 2. every field on one Panthers fixture
d = get("20260813-20261012")
for ev in d.get("events", []):
    if "Panthers" in ev.get("name", ""):
        print("\n=== FULL EVENT KEYS ===", list(ev))
        print(json.dumps(ev, indent=1)[:2600])
        break

# 3. all Panthers fixtures in the window
print("\n=== PANTHERS FIXTURES ===")
for ev in d.get("events", []):
    if "Panthers" not in ev.get("name", ""):
        continue
    c = (ev.get("competitions") or [{}])[0]
    home = next((t for t in c.get("competitors", []) if t.get("homeAway") == "home"), {})
    away = next((t for t in c.get("competitors", []) if t.get("homeAway") == "away"), {})
    print(" ", ev["date"], "|", ev.get("name"),
          "| venue:", (c.get("venue") or {}).get("fullName"),
          "| home:", (home.get("team") or {}).get("displayName"),
          "| away:", (away.get("team") or {}).get("displayName"),
          "| status:", ((ev.get("status") or {}).get("type") or {}).get("name"))
