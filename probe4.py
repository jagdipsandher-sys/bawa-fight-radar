#!/usr/bin/env python3
"""Throwaway: exact shape of the official MotoGP feed."""
import json, urllib.request
UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
        return json.load(r)

B = "https://api.motogp.pulselive.com/motogp/v1"
evs = get(f"{B}/events?seasonYear=2026")
print("events:", len(evs))
print("\nFIRST EVENT, VERBATIM:")
print(json.dumps(evs[0], indent=1)[:1400])
print("\nkinds seen:", sorted({str(e.get("kind")) for e in evs}))
print("test flags:", sorted({str(e.get("test")) for e in evs}))
print("\nFIRST 8 NON-TEST:")
for e in [x for x in evs if str(x.get("kind")).upper() != "TEST"][:8]:
    c = e.get("country")
    print("  ", e.get("date_start"), "->", e.get("date_end"), "|", e.get("name"),
          "| country:", c if isinstance(c, str) else (c or {}).get("iso") or (c or {}).get("name"),
          "| circuit:", (e.get("circuit") if isinstance(e.get("circuit"), str)
                         else (e.get("circuit") or {}).get("name")),
          "| status:", e.get("status"))

print("\nSTANDINGS")
try:
    seasons = get(f"{B}/results/seasons")
    su = next((s["id"] for s in seasons if s.get("year") == 2026), None)
    cats = get(f"{B}/results/categories?seasonUuid={su}")
    print("categories:", [(c.get("name"), c.get("legacy_id")) for c in cats])
    mid = next((c["id"] for c in cats if "motogp" in str(c.get("name","")).lower()), None)
    st = get(f"{B}/results/standings?seasonUuid={su}&categoryUuid={mid}")
    cl = st.get("classification", [])
    print("riders:", len(cl))
    for r in cl[:6]:
        rd = r.get("rider") or {}
        print("  ", r.get("position"), rd.get("full_name") or rd.get("name"),
              "| pts:", r.get("points"), "| team:", (r.get("team") or {}).get("name"))
except Exception as e:
    print("  FAILED:", type(e).__name__, e)
