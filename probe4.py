#!/usr/bin/env python3
"""Throwaway: does ESPN carry MotoGP, calendar and standings?"""
import json, urllib.request
UA = {"User-Agent": "Mozilla/5.0"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
        return json.load(r)

B = "https://site.api.espn.com/apis/site/v2/sports/racing"
W = "https://site.web.api.espn.com/apis/v2/sports/racing"
for code in ["mgp", "motogp", "moto-gp"]:
    for u in [f"{B}/{code}/scoreboard?dates=2026", f"{B}/{code}/scoreboard"]:
        print("\n" + "="*66, f"\n{u}")
        try:
            d = get(u)
        except Exception as e:
            print("  FAILED:", type(e).__name__, e); continue
        evs = d.get("events", [])
        print("  events:", len(evs), "| league:", ((d.get("leagues") or [{}])[0]).get("name"))
        for ev in evs[:3]:
            print("   -", ev.get("date"), "|", ev.get("name"), "| short:", ev.get("shortName"),
                  "| sessions:", len(ev.get("competitions") or []),
                  "| status:", ((ev.get("status") or {}).get("type") or {}).get("name"))
    for u in [f"{W}/{code}/standings?season=2026"]:
        print("\n" + "="*66, f"\n{u}")
        try:
            d = get(u)
        except Exception as e:
            print("  FAILED:", type(e).__name__, e); continue
        for g in (d.get("children") or []):
            ents = (g.get("standings") or {}).get("entries") or []
            print("  group:", g.get("name"), "| entries:", len(ents))
            for e in ents[:4]:
                nm = (e.get("athlete") or e.get("team") or {}).get("displayName")
                st = {s.get("name"): s.get("displayValue") for s in e.get("stats", [])}
                print("    -", nm, st)
