#!/usr/bin/env python3
"""Throwaway: can we get MotoGP from the official (pulselive) API?"""
import json, urllib.request
UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
        return json.load(r)

B = "https://api.motogp.pulselive.com/motogp/v1"
season_uuid = None
try:
    seasons = get(f"{B}/results/seasons")
    print("seasons:", [(s.get("year"), s.get("id")) for s in seasons][:4])
    season_uuid = next((s["id"] for s in seasons if s.get("year") == 2026), None)
except Exception as e:
    print("seasons FAILED:", type(e).__name__, e)

print("\n" + "="*66, "\nEVENTS")
for u in [f"{B}/events?seasonYear=2026", f"{B}/results/events?seasonUuid={season_uuid}"]:
    print("\n", u)
    try:
        d = get(u)
    except Exception as e:
        print("  FAILED:", type(e).__name__, e); continue
    evs = d if isinstance(d, list) else d.get("events", [])
    print("  count:", len(evs))
    for ev in evs[:4]:
        print("   -", ev.get("date_start") or ev.get("dateStart") or ev.get("date"),
              "|", ev.get("name"), "| short:", ev.get("short_name") or ev.get("shortName"),
              "| country:", (ev.get("country") or {}).get("iso") or (ev.get("country") or {}).get("name"),
              "| circuit:", (ev.get("circuit") or {}).get("name"),
              "| status:", ev.get("status"), "| kind:", ev.get("kind"))
        print("     keys:", list(ev)[:14])

print("\n" + "="*66, "\nSTANDINGS")
if season_uuid:
    try:
        cats = get(f"{B}/results/categories?seasonUuid={season_uuid}")
        print("categories:", [(c.get("name"), c.get("id")) for c in cats][:5])
        motogp = next((c["id"] for c in cats if "motogp" in str(c.get("name","")).lower()), None)
        if motogp:
            st = get(f"{B}/results/standings?seasonUuid={season_uuid}&categoryUuid={motogp}")
            cl = st.get("classification", [])
            print("  riders:", len(cl))
            for r in cl[:6]:
                rider = r.get("rider") or {}
                print("   ", r.get("position"), rider.get("full_name") or rider.get("fullName"),
                      "|", r.get("points"), "|", (r.get("team") or {}).get("name"))
    except Exception as e:
        print("  FAILED:", type(e).__name__, e)
