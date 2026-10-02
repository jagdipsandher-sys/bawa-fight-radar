#!/usr/bin/env python3
"""TEMPORARY — is the NRL feed healthy, or is the season simply over? Deleted after."""
import json, urllib.request

FEEDS = {
  "rugby-league/3": "https://site.api.espn.com/apis/site/v2/sports/rugby-league/3/scoreboard?dates={}",
}
for label, feed in FEEDS.items():
    for ym in ["202608", "202609", "202610", "202611", "202702", "202703"]:
        try:
            with urllib.request.urlopen(feed.format(ym), timeout=30) as r:
                data = json.load(r)
        except Exception as e:
            print(f"{label} {ym}: FAILED {type(e).__name__}: {e}")
            continue
        evs = data.get("events", [])
        print(f"{label} {ym}: {len(evs)} events")
        for ev in evs[:12]:
            comp = (ev.get("competitions") or [{}])[0]
            names = [ (t.get("team") or {}).get("displayName","?") + "/" + str(t.get("homeAway"))
                      for t in comp.get("competitors", []) ]
            print(f"    {ev.get('date')}  {ev.get('name')}   -> {names}")
