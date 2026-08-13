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
SRC_PL = "https://www.espn.com.au/football/standings/_/league/eng.1"
SRC_F1 = "https://www.espn.com.au/f1/standings"
ME = "Manchester United"
SHORT = {"Manchester United": "Man Utd", "Manchester City": "Man City",
         "Tottenham Hotspur": "Spurs", "Brighton & Hove Albion": "Brighton",
         "Nottingham Forest": "Forest", "Wolverhampton Wanderers": "Wolves",
         "AFC Bournemouth": "Bournemouth", "Newcastle United": "Newcastle",
         "West Ham United": "West Ham", "Leeds United": "Leeds"}


def esc(t):
    return html.escape(str(t or ""), quote=True)


def get(urls, year=None):
    year = year or datetime.now(timezone.utc).year
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


def pl_rows(data):
    """Flatten a standings payload into rows, or None if it has no table."""
    if not data:
        return None, ""
    group = (data.get("children") or [data])[0]
    entries = (group.get("standings") or {}).get("entries") or []
    if not entries:
        return None, ""
    rows = [{
        "name": name_of(e),
        "rank": int(stat(e, "rank") or 0),
        "pts": points_of(e) or "0",
        "played": stat(e, "gamesPlayed", "GP") or "0",
        "won": stat(e, "wins", "W") or "0",
        "drawn": stat(e, "ties", "D") or "0",
        "lost": stat(e, "losses", "L") or "0",
        "gd": stat(e, "pointDifferential", "GD") or "0",
    } for e in entries]
    rows.sort(key=lambda r: r["rank"])
    return rows, group.get("name", "")


def played_any(rows):
    return any(r["played"] not in ("0", "", None) for r in rows or [])


def source_note(url, label):
    return (f'<div class="dr-note2" style="margin-top:12px">Numbers from '
            f'<a href="{url}" style="color:var(--grey)">{esc(label)}</a> — click through for '
            f'the full detail, form guide and results.</div>')


# ---------------------------------------------------------------- premier league
def pl_data():
    """This season's table, or last season's final one if it hasn't kicked off.

    A brand-new season returns twenty clubs on nil in alphabetical order, which
    looks like a real ladder and isn't. Last season's finish is at least true,
    and it answers "who's actually winning" better than an empty box.
    """
    year = datetime.now(timezone.utc).year
    rows, season = pl_rows(get(PL, year))
    if played_any(rows):
        return rows, season, False
    prev, prev_season = pl_rows(get(PL, year - 1))
    if played_any(prev):
        return prev, prev_season, True
    return rows, season, False


def pl_panel(rows, season, is_last):
    if not played_any(rows):
        return not_started("Premier League", "Table",
                           f"{season or 'The season'} hasn't kicked off yet and there is no "
                           f"previous table to fall back on.")
    top = rows[:6]
    mine = next((r for r in rows if r["name"] == ME), None)
    show, gapped = list(top), False
    if mine and mine not in top:
        gapped, show = True, top + [mine]

    body = ""
    for i, r in enumerate(show):
        if gapped and i == len(top):
            body += '<tr><td class="gap" colspan="5"></td></tr>'
        cls = ' class="me"' if r["name"] == ME else (' class="lead"' if r["rank"] == 1 else "")
        body += (f'<tr{cls}><td class="pos">{r["rank"]}</td>'
                 f'<td class="who">{esc(SHORT.get(r["name"], r["name"]))}</td>'
                 f'<td class="num">{esc(r["played"])}</td>'
                 f'<td class="num">{esc(r["gd"])}</td>'
                 f'<td class="pts">{esc(r["pts"])}</td></tr>')

    leader, gap = rows[0], ""
    if mine:
        try:
            d = int(leader["pts"]) - int(mine["pts"])
            gap = (f"United finished {d} behind {SHORT.get(leader['name'], leader['name'])}." if is_last
                   else f"United are {d} point{'s' if d != 1 else ''} behind "
                        f"{SHORT.get(leader['name'], leader['name'])}." if d > 0
                   else "United are top of the league.")
        except ValueError:
            pass

    table = ('<table class="ladder"><thead><tr><th></th><th>Club</th>'
             '<th class="num">P</th><th class="num">GD</th><th class="pts">Pts</th></tr></thead>'
             f'<tbody>{body}</tbody></table>')
    sub = "Last Season" if is_last else f"After {leader['played']} games"
    note = (gap + (" New season starts from zero on 22 August." if is_last else "")).strip()
    return card("Premier League", sub, table, note)


def pl_full(rows, season, is_last):
    """The whole twenty, full width, at the bottom of the tab."""
    if not played_any(rows):
        return ('<table><tbody><tr><td class="gone">No table yet — the season hasn\'t started '
                'and there is nothing to show.</td></tr></tbody></table>')
    body = ""
    for r in rows:
        cls = ' class="me"' if r["name"] == ME else (' class="lead"' if r["rank"] == 1 else "")
        body += (f'<tr{cls}><td class="pos">{r["rank"]}</td>'
                 f'<td class="who">{esc(r["name"])}</td>'
                 f'<td class="num">{esc(r["played"])}</td><td class="num">{esc(r["won"])}</td>'
                 f'<td class="num">{esc(r["drawn"])}</td><td class="num">{esc(r["lost"])}</td>'
                 f'<td class="num">{esc(r["gd"])}</td><td class="pts">{esc(r["pts"])}</td></tr>')
    label = f"{season} — final table" if is_last else season
    return (f'<div class="meta" style="margin-bottom:8px">{esc(label)}</div>'
            '<table class="ladder" style="border:1px solid var(--faint);padding:0 10px">'
            '<thead><tr><th></th><th>Club</th><th class="num">P</th><th class="num">W</th>'
            '<th class="num">D</th><th class="num">L</th><th class="num">GD</th>'
            '<th class="pts">Pts</th></tr></thead>'
            f'<tbody>{body}</tbody></table>'
            + source_note(SRC_PL, "ESPN Premier League standings"))


# ---------------------------------------------------------------------------- f1
def f1_data():
    data = get(F1)
    groups = {g.get("name", ""): (g.get("standings") or {}).get("entries") or []
              for g in ((data or {}).get("children") or [])}
    def rows(kind):
        ents = next((v for k, v in groups.items() if kind in k.lower()), [])
        out = [{"name": name_of(e), "rank": int(stat(e, "rank") or 0), "pts": points_of(e)}
               for e in ents]
        return sorted(out, key=lambda r: r["rank"])
    return rows("driver"), rows("constructor")


def f1_ladder(rows, head, limit=None):
    body = ""
    for r in (rows[:limit] if limit else rows):
        cls = ' class="lead"' if r["rank"] == 1 else ""
        body += (f'<tr{cls}><td class="pos">{r["rank"]}</td>'
                 f'<td class="who">{esc(r["name"])}</td>'
                 f'<td class="pts">{esc(r["pts"] or "—")}</td></tr>')
    return (f'<table class="ladder"><thead><tr><th></th><th>{esc(head)}</th>'
            f'<th class="pts">Pts</th></tr></thead><tbody>{body}</tbody></table>')


def f1_panel(drivers, teams):
    if not drivers or all(r["pts"] in (None, "", "0") for r in drivers):
        return not_started("Formula 1", "Championship",
                           "No races run yet this season — the championship starts from round one.")
    inner = f1_ladder(drivers, "Driver", limit=8)
    if teams:
        inner += ('<div class="when" style="margin-top:16px">Constructors</div>'
                  + f1_ladder(teams, "Team", limit=3))
    lead, note = drivers[0], ""
    if len(drivers) > 1 and lead["pts"] and drivers[1]["pts"]:
        try:
            note = (f"{lead['name']} leads by {int(lead['pts']) - int(drivers[1]['pts'])} points "
                    f"from {drivers[1]['name']}.")
        except ValueError:
            pass
    return card("Formula 1", "Championship", inner, note)


def f1_full(drivers, teams):
    if not drivers:
        return ('<table><tbody><tr><td class="gone">No championship table published yet.'
                '</td></tr></tbody></table>')
    out = ('<div class="meta" style="margin-bottom:8px">Drivers\' championship — every driver</div>'
           + f1_ladder(drivers, "Driver").replace('class="ladder"',
             'class="ladder" style="border:1px solid var(--faint);padding:0 10px"'))
    if teams:
        out += ('<div class="meta" style="margin:20px 0 8px">Constructors\' championship</div>'
                + f1_ladder(teams, "Team").replace('class="ladder"',
                  'class="ladder" style="border:1px solid var(--faint);padding:0 10px"'))
    return out + source_note(SRC_F1, "ESPN F1 standings")


def splice(page, marker, block):
    pat = re.compile(rf"(<!--BUILD:{marker}-->).*?(<!--/BUILD:{marker}-->)", re.S)
    if not pat.search(page):
        sys.exit(f"marker {marker} not found in {PAGE}")
    return pat.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), page, count=1)


def main():
    print("Premier League:")
    pl_r, pl_season, is_last = pl_data()
    print(f"  {len(pl_r or [])} clubs, season {pl_season!r}, using last season: {is_last}")
    print("Formula 1:")
    drivers, teams = f1_data()
    print(f"  {len(drivers)} drivers, {len(teams)} constructors")

    page = open(PAGE).read()
    before = page
    page = splice(page, "UTD-TABLE", pl_panel(pl_r, pl_season, is_last))
    page = splice(page, "F1-TABLE", f1_panel(drivers, teams))
    page = splice(page, "UTD-FULL", pl_full(pl_r, pl_season, is_last))
    page = splice(page, "F1-FULL", f1_full(drivers, teams))
    if page == before:
        print("standings already current")
        return
    open(PAGE, "w").write(page)
    print("standings panels rebuilt")


if __name__ == "__main__":
    main()
