#!/usr/bin/env python3
"""
Builds the "who's actually winning" panel on the Man Utd and F1 tabs.

Premier League table and the F1 drivers' and constructors' championships, from
ESPN's standings feed, rendered as the left-hand card on each tab.

Two things this is careful about:

  * A table of zeroes is worse than no table. Before a season's first ball is
    kicked ESPN returns every club on 0 points in ALPHABETICAL order, which
    reads exactly like a real ladder and is completely meaningless. When no
    games have been played this says so instead.
  * Stat names differ between sports and change over time, so points are found
    by looking for a points-ish stat rather than assuming a key.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

PAGE = "index.html"
UA = {"User-Agent": "Mozilla/5.0 (compatible; bawa-radar/1.0)"}
PL = ["https://site.web.api.espn.com/apis/v2/sports/soccer/eng.1/standings?season={year}",
      "https://site.api.espn.com/apis/v2/sports/soccer/eng.1/standings"]
F1 = ["https://site.web.api.espn.com/apis/v2/sports/racing/f1/standings?season={year}",
      "https://site.api.espn.com/apis/v2/sports/racing/f1/standings"]
ME = "Manchester United"
SHORT = {"Manchester United": "Man Utd", "Manchester City": "Man City",
         "Tottenham Hotspur": "Spurs", "Brighton & Hove Albion": "Brighton",
         "Nottingham Forest": "Forest", "Wolverhampton Wanderers": "Wolves",
         "AFC Bournemouth": "Bournemouth", "Newcastle United": "Newcastle",
         "West Ham United": "West Ham", "Leeds United": "Leeds"}


def esc(t):
    return html.escape(str(t or ""), quote=True)


def get(urls):
    year = datetime.now(timezone.utc).year
    for u in urls:
        try:
            req = urllib.request.Request(u.format(year=year), headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.load(r)
        except Exception as e:
            print(f"  {u.split('?')[0]}: {type(e).__name__}")
    return None


def stat(entry, *wanted):
    """Pull a stat by name, abbreviation or display name — feeds rename these."""
    for s in entry.get("stats", []):
        keys = {str(s.get(k, "")).lower() for k in ("name", "abbreviation", "shortDisplayName", "displayName")}
        if keys & {w.lower() for w in wanted}:
            v = s.get("displayValue")
            if v not in (None, ""):
                return v
    return None


def points_of(entry):
    v = stat(entry, "points", "pts", "championshipPts", "totalPoints")
    if v is not None:
        return v
    for s in entry.get("stats", []):                     # last resort: anything point-ish
        if "point" in str(s.get("name", "")).lower() and s.get("displayValue"):
            return s["displayValue"]
    return None


def name_of(entry):
    for key in ("team", "athlete"):
        n = (entry.get(key) or {}).get("displayName")
        if n:
            return n
    return entry.get("note") or "—"


def card(title, sub, inner, note=""):
    return f"""    <div class="card" data-slot="table">
      <div class="sport">{esc(title)} &nbsp;<span class="badge fn">{esc(sub)}</span></div>
      <div class="inner" style="padding-top:14px">
        {inner}
        {'<div class="dr-note2" style="margin-top:12px">' + esc(note) + '</div>' if note else ''}
      </div>
    </div>"""


def not_started(title, sub, message):
    return card(title, sub, f'<div class="fight hd">Not Started Yet<small>{esc(message)}</small></div>')


# ---------------------------------------------------------------- premier league
def premier_league():
    data = get(PL)
    if not data:
        return not_started("Premier League", "Table", "Standings feed unavailable right now.")
    group = (data.get("children") or [data])[0]
    entries = (group.get("standings") or {}).get("entries") or []
    if not entries:
        return not_started("Premier League", "Table", "No table published yet.")

    rows = []
    for e in entries:
        rows.append({
            "name": name_of(e),
            "rank": int(stat(e, "rank") or 0),
            "pts": points_of(e) or "0",
            "played": stat(e, "gamesPlayed", "GP") or "0",
            "gd": stat(e, "pointDifferential", "GD") or "0",
        })
    if all(r["played"] in ("0", "", None) for r in rows):
        season = group.get("name", "the season")
        return not_started(
            "Premier League", "Table",
            f"{season} hasn't kicked off — the table fills in from the first round. "
            f"Until then every club sits on nothing, so showing a ladder would just be alphabetical order.")

    rows.sort(key=lambda r: r["rank"])
    top = rows[:6]
    mine = next((r for r in rows if r["name"] == ME), None)
    show, gapped = list(top), False
    if mine and mine not in top:
        gapped = True
        show.append(mine)

    body = ""
    for i, r in enumerate(show):
        if gapped and i == len(top):
            body += '<tr><td class="gap" colspan="5"></td></tr>'
        cls = " class=\"me\"" if r["name"] == ME else (" class=\"lead\"" if r["rank"] == 1 else "")
        body += (f'<tr{cls}><td class="pos">{r["rank"]}</td>'
                 f'<td class="who">{esc(SHORT.get(r["name"], r["name"]))}</td>'
                 f'<td class="num">{esc(r["played"])}</td>'
                 f'<td class="num">{esc(r["gd"])}</td>'
                 f'<td class="pts">{esc(r["pts"])}</td></tr>')

    leader = rows[0]
    gap = ""
    if mine:
        try:
            d = int(leader["pts"]) - int(mine["pts"])
            gap = (f"United are {d} point{'s' if d != 1 else ''} behind {SHORT.get(leader['name'], leader['name'])}"
                   if d > 0 else "United are top of the league")
        except ValueError:
            pass

    table = ('<table class="ladder"><thead><tr><th></th><th>Club</th>'
             '<th class="num">P</th><th class="num">GD</th><th class="pts">Pts</th></tr></thead>'
             f'<tbody>{body}</tbody></table>')
    return card("Premier League", f"After {leader['played']} games", table, gap)


# ---------------------------------------------------------------------------- f1
def formula_one():
    data = get(F1)
    if not data:
        return not_started("Formula 1", "Championship", "Standings feed unavailable right now.")

    groups = {g.get("name", ""): (g.get("standings") or {}).get("entries") or []
              for g in (data.get("children") or [])}
    drivers = next((v for k, v in groups.items() if "driver" in k.lower()), [])
    teams = next((v for k, v in groups.items() if "constructor" in k.lower()), [])
    if not drivers:
        return not_started("Formula 1", "Championship", "No championship table published yet.")

    rows = sorted(
        ({"name": name_of(e), "rank": int(stat(e, "rank") or 0), "pts": points_of(e)} for e in drivers),
        key=lambda r: r["rank"])
    if all(r["pts"] in (None, "", "0") for r in rows):
        return not_started("Formula 1", "Championship",
                           "No races run yet this season — the championship starts from round one.")

    body = ""
    for r in rows[:8]:
        cls = ' class="lead"' if r["rank"] == 1 else ""
        body += (f'<tr{cls}><td class="pos">{r["rank"]}</td>'
                 f'<td class="who">{esc(r["name"])}</td>'
                 f'<td class="pts">{esc(r["pts"] or "—")}</td></tr>')
    table = ('<table class="ladder"><thead><tr><th></th><th>Driver</th>'
             '<th class="pts">Pts</th></tr></thead>'
             f'<tbody>{body}</tbody></table>')

    if teams:
        trows = sorted(({"name": name_of(e), "rank": int(stat(e, "rank") or 0), "pts": points_of(e)}
                        for e in teams), key=lambda r: r["rank"])[:3]
        tbody = "".join(f'<tr><td class="pos">{r["rank"]}</td><td class="who">{esc(r["name"])}</td>'
                        f'<td class="pts">{esc(r["pts"] or "—")}</td></tr>' for r in trows)
        table += ('<div class="when" style="margin-top:16px">Constructors</div>'
                  f'<table class="ladder"><tbody>{tbody}</tbody></table>')

    lead = rows[0]
    note = ""
    if len(rows) > 1 and lead["pts"] and rows[1]["pts"]:
        try:
            note = (f"{lead['name']} leads by {int(lead['pts']) - int(rows[1]['pts'])} points "
                    f"from {rows[1]['name']}.")
        except ValueError:
            pass
    return card("Formula 1", "Championship", table, note)


def splice(page, marker, block):
    pat = re.compile(rf"(<!--BUILD:{marker}-->).*?(<!--/BUILD:{marker}-->)", re.S)
    if not pat.search(page):
        sys.exit(f"marker {marker} not found in {PAGE}")
    return pat.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), page, count=1)


def main():
    print("Premier League:")
    pl = premier_league()
    print("Formula 1:")
    f1 = formula_one()

    page = open(PAGE).read()
    before = page
    page = splice(page, "UTD-TABLE", pl)
    page = splice(page, "F1-TABLE", f1)
    if page == before:
        print("standings already current")
        return
    open(PAGE, "w").write(page)
    print("standings panels rebuilt")


if __name__ == "__main__":
    main()
