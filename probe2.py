#!/usr/bin/env python3
"""Throwaway: find usable ESPN feeds for Man Utd and Formula 1."""
import json
import urllib.request

def get(url):
    with urllib.request.urlopen(url, timeout=25) as r:
        return json.load(r)

B = "https://site.api.espn.com/apis/site/v2/sports"

print("=" * 70, "\nFOOTBALL — find Manchester United's team id")
try:
    d = get(f"{B}/soccer/eng.1/teams")
    teams = d["sports"][0]["leagues"][0]["teams"]
    for t in teams:
        if "United" in t["team"]["displayName"]:
            print("  ", t["team"]["id"], t["team"]["displayName"], "|", t["team"].get("abbreviation"))
except Exception as e:
    print("  FAILED:", e)

print("\n" + "=" * 70, "\nFOOTBALL — team schedule endpoint (all comps?)")
for tid in ["360"]:
    for url in [f"{B}/soccer/eng.1/teams/{tid}/schedule",
                f"{B}/soccer/eng.1/scoreboard?dates=20260815-20260930"]:
        print("\n ", url)
        try:
            d = get(url)
            print("   keys:", list(d)[:10])
            evs = d.get("events", [])
            print("   events:", len(evs))
            for ev in evs[:4]:
                c = (ev.get("competitions") or [{}])[0]
                names = [(t.get("homeAway"), (t.get("team") or {}).get("displayName")) for t in c.get("competitors", [])]
                print("    -", ev.get("date"), "|", ev.get("name"),
                      "| venue:", (c.get("venue") or {}).get("fullName"),
                      "| league:", ((d.get("leagues") or [{}])[0]).get("abbreviation"),
                      "|", names)
        except Exception as e:
            print("   FAILED:", e)

print("\n" + "=" * 70, "\nFORMULA 1")
for url in [f"{B}/racing/f1/scoreboard?dates=2026",
            f"{B}/racing/f1/scoreboard",
            f"{B}/racing/f1/calendar"]:
    print("\n ", url)
    try:
        d = get(url)
        print("   keys:", list(d)[:12])
        evs = d.get("events", []) or d.get("sports", [])
        print("   events:", len(evs))
        for ev in (d.get("events") or [])[:5]:
            print("    -", ev.get("date"), "|", ev.get("name"), "| short:", ev.get("shortName"))
            print("      keys:", list(ev)[:14])
            comps = ev.get("competitions") or []
            if comps:
                c = comps[0]
                print("      circuit:", ((c.get("circuit") or {}).get("fullName")),
                      "| venue:", (c.get("venue") or {}).get("fullName"),
                      "| type:", (c.get("type") or {}).get("text"),
                      "| status:", ((ev.get("status") or {}).get("type") or {}).get("name"))
                print("      n competitions (sessions):", len(comps))
                for cc in comps[:4]:
                    print("        *", cc.get("date"), (cc.get("type") or {}).get("text"))
    except Exception as e:
        print("   FAILED:", e)
