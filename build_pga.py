#!/usr/bin/env python3
"""Rebuild the PGA Golf tab from ESPN's public PGA TOUR calendar.

ESPN provides the live event state and published tournament date range, but its
calendar placeholders are not tee times.  This builder therefore gives Sydney
viewers an honest viewing window and links to Kayo for the exact live sessions.
Course, purse, FedExCup and previous-winner context is checked against the
official PGA TOUR schedule and kept here as a small, reviewable lookup table.
"""
import html
import json
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime, time, timedelta, timezone

from send_fights import SYD

PAGE = "index.html"
FEED = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard?dates={}-{}"
SCHEDULE = "https://www.pgatour.com/schedule"
STANDINGS = "https://www.pgatour.com/fedexcup/rankings.html"
WATCH = "https://kayosports.com.au/sports/sport!golf"


EVENT_INFO = {
    "bmw championship": {
        "course": "Bellerive Country Club", "place": "St. Louis, Missouri",
        "stage": "FedExCup Playoffs · top 50", "purse": "$20m · 750 points",
        "previous": "Scottie Scheffler", "badge": "Playoffs", "flag": "🇺🇸",
    },
    "tour championship": {
        "course": "East Lake Golf Club", "place": "Atlanta, Georgia",
        "stage": "FedExCup finale · top 30", "purse": "$40m bonus pool",
        "previous": "Tommy Fleetwood", "badge": "Finale", "flag": "🇺🇸",
    },
    "biltmore championship asheville": {
        "course": "The Cliffs at Walnut Cove", "place": "Asheville, North Carolina",
        "stage": "FedExCup Fall", "purse": "$5m · 500 points",
        "previous": "New tournament", "badge": "New", "flag": "🇺🇸",
    },
    "presidents cup": {
        "course": "Medinah Country Club No. 3", "place": "Medinah, Illinois",
        "stage": "USA v International Team", "purse": "Team match play",
        "previous": "USA", "badge": "Team Golf", "flag": "🌍",
    },
    "bank of utah championship": {
        "course": "Black Desert Resort", "place": "Ivins, Utah",
        "stage": "FedExCup Fall", "purse": "$6m · 500 points",
        "previous": "Michael Brennan", "badge": "Fall", "flag": "🇺🇸",
    },
    "baycurrent classic": {
        "course": "Yokohama Country Club", "place": "Yokohama, Japan",
        "stage": "FedExCup Fall", "purse": "$8m · 500 points",
        "previous": "Xander Schauffele", "badge": "Good Time", "flag": "🇯🇵",
    },
    "butterfield bermuda championship": {
        "course": "Port Royal Golf Course", "place": "Southampton, Bermuda",
        "stage": "FedExCup Fall", "purse": "$6m · 500 points",
        "previous": "Adam Schenk", "badge": "Fall", "flag": "🇧🇲",
    },
    "vidantaworld mexico open": {
        "course": "Vidanta Vallarta", "place": "Vallarta, Mexico",
        "stage": "FedExCup Fall", "purse": "$6m · 500 points",
        "previous": "Brian Campbell", "badge": "Fall", "flag": "🇲🇽",
    },
    "world wide technology championship": {
        "course": "El Cardonal at Diamante", "place": "Los Cabos, Mexico",
        "stage": "FedExCup Fall", "purse": "$6m · 500 points",
        "previous": "Ben Griffin", "badge": "Fall", "flag": "🇲🇽",
    },
    "good good championship": {
        "course": "Omni Barton Creek · Fazio Canyons", "place": "Austin, Texas",
        "stage": "FedExCup Fall", "purse": "$6m · 500 points",
        "previous": "New tournament", "badge": "New", "flag": "🇺🇸",
    },
    "the rsm classic": {
        "course": "Sea Island Golf Club · Seaside", "place": "St. Simons Island, Georgia",
        "stage": "FedExCup Fall", "purse": "$7.4m · 500 points",
        "previous": "Sami Valimaki", "badge": "Fall", "flag": "🇺🇸",
    },
    "rsm classic": {
        "course": "Sea Island Golf Club · Seaside", "place": "St. Simons Island, Georgia",
        "stage": "FedExCup Fall", "purse": "$7.4m · 500 points",
        "previous": "Sami Valimaki", "badge": "Fall", "flag": "🇺🇸",
    },
    "hero world challenge": {
        "course": "Albany Golf Course", "place": "New Providence, Bahamas",
        "stage": "Unofficial PGA TOUR event", "purse": "$5m",
        "previous": "Hideki Matsuyama", "badge": "Special", "flag": "🇧🇸",
    },
    "pga tour q school presented by korn ferry": {
        "course": "Dye's Valley Course", "place": "Ponte Vedra Beach, Florida",
        "stage": "PGA TOUR Q-School", "purse": "$1.2m",
        "previous": "AJ Ewart", "badge": "Tour Cards", "flag": "🇺🇸",
    },
}

# Dated snapshot. The button beside it always opens the official live table.
FEDEX_CHECKED = "18 Aug 2026"
FEDEX_TOP = [
    (1, "Scottie Scheffler", "4,123"), (2, "Matt Fitzpatrick", "3,329"),
    (3, "Cameron Young", "3,086"), (4, "Wyndham Clark", "2,255"),
    (5, "Chris Gotterup", "2,254"), (6, "Collin Morikawa", "2,229"),
    (7, "Si Woo Kim", "2,188"), (8, "Sam Burns", "2,078"),
    (9, "Tommy Fleetwood", "2,046"), (10, "Ludvig Åberg", "1,929"),
    (16, "Min Woo Lee 🇦🇺", "1,470"),
]


def esc(value):
    return html.escape(str(value or ""), quote=True)


def parse_day(value):
    try:
        return date.fromisoformat(value[:10])
    except (AttributeError, ValueError):
        return None


def normalise(name):
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def metadata(name):
    key = normalise(name)
    if key in EVENT_INFO:
        return EVENT_INFO[key]
    for known, info in EVENT_INFO.items():
        if known in key or key in known:
            return info
    return {
        "course": "Course TBC", "place": "Location TBC", "stage": "PGA TOUR",
        "purse": "See official schedule", "previous": "See official schedule",
        "badge": "PGA TOUR", "flag": "⛳",
    }


def collect():
    today = datetime.now(SYD).date()
    # ESPN accepts the remainder-of-year range but rejects a few wider variants.
    # An in-progress event still appears when the range begins today.
    start = today
    url = FEED.format(start.strftime("%Y%m%d"), f"{today.year}1231")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.load(response)
    except Exception as exc:
        # ESPN occasionally rejects urllib's TLS fingerprint while accepting a
        # normal curl request. GitHub's Ubuntu runner includes curl, so use it
        # as a narrow fallback for this same read-only URL.
        fallback = subprocess.run(["curl", "-fsSL", url], capture_output=True, text=True)
        if fallback.returncode:
            detail = f" HTTP {exc.code}" if hasattr(exc, "code") else ""
            sys.exit(f"PGA calendar fetch failed ({type(exc).__name__}{detail}) — leaving the tab alone")
        try:
            data = json.loads(fallback.stdout)
        except json.JSONDecodeError:
            sys.exit("PGA calendar returned invalid JSON — leaving the tab alone")

    events = []
    for event in data.get("events", []):
        starts = parse_day(event.get("date"))
        ends = parse_day(event.get("endDate")) or starts
        if not starts or not ends or ends < today:
            continue
        status = ((event.get("status") or {}).get("type") or {}).get("name", "")
        if status == "STATUS_CANCELED":
            continue
        links = event.get("links") or []
        scores = next((item.get("href") for item in links if item.get("href")), SCHEDULE)
        events.append({
            "id": str(event.get("id") or starts.strftime("%Y%m%d")),
            "name": event.get("name") or "PGA TOUR event", "start": starts, "end": ends,
            "status": status, "scores": scores, "info": metadata(event.get("name")),
        })
    events.sort(key=lambda item: item["start"])
    return events


def cid(event):
    return "pga" + re.sub(r"\W", "", event["id"])


def end_stamp(event):
    finish = datetime.combine(event["end"] + timedelta(days=1), time(12), tzinfo=SYD)
    return finish.isoformat()


def date_range(event, long=False):
    start, end = event["start"], event["end"]
    if start == end:
        return start.strftime("%-d %B %Y" if long else "%a %-d %b")
    if start.month == end.month:
        return f"{start:%-d}–{end.strftime('%-d %B %Y' if long else '%-d %b')}"
    return f"{start.strftime('%-d %b')}–{end.strftime('%-d %b %Y' if long else '%-d %b')}"


def viewing(event):
    if event["info"]["flag"] == "🇯🇵":
        return "Sydney-friendly daytime and evening coverage"
    return "Live coverage usually runs Thu night–Mon morning Sydney"


def badge(event):
    label = event["info"]["badge"]
    style = "home" if label in ("Good Time", "Playoffs", "Finale") else "fn"
    return f'<span class="badge {style}">{esc(label)}</span>'


def row(event):
    info = event["info"]
    return f"""      <tr data-sport="pga" data-ends="{end_stamp(event)}" data-card="{cid(event)}">
        <td class="d">{event['start']:%a %-d %b}<small>to {event['end']:%a %-d %b}</small></td>
        <td><span class="sporttag m">PGA</span></td>
        <td><span class="flag" style="margin-right:6px">{info['flag']}</span><span class="ev">{esc(event['name'])}</span> {badge(event)}<br><span class="sub">{esc(viewing(event))} · {esc(info['stage'])}</span></td>
        <td>{esc(info['course'])}<small>{esc(info['place'])}</small></td>
        <td><a class="mini buy" href="{esc(WATCH)}">Watch · Kayo</a><a class="mini" href="{esc(event['scores'])}">Scores</a><button class="mini" onclick="openCard('{cid(event)}')">Details</button><button class="mini" onclick="addCal('{cid(event)}')">+ Cal</button></td>
      </tr>"""


def hero(event):
    info = event["info"]
    return f"""    <div class="card" data-slot="pga" data-ends="{end_stamp(event)}">
      <div class="sport">Next Tournament &nbsp;{badge(event)} <span class="badge soon"><span class="cd" data-until="{event['start']:%Y-%m-%d}"></span></span></div>
      <div class="crest dark">
        <div class="big"><span style="font-size:2.2rem;vertical-align:middle">{info['flag']}</span> {esc(event['name'])} <em>⛳</em></div>
        <div class="lil">{esc(info['course'])} · {esc(info['place'])}</div>
      </div>
      <div class="inner">
        <div class="fight hd">{esc(event['name'])}<small>{esc(viewing(event))}</small></div>
        <div class="when">Tournament · <span class="t">{esc(date_range(event, True))}</span></div>
        <div class="meta">{esc(info['stage'])} · {esc(info['purse'])} · previous winner: {esc(info['previous'])}</div>
        <div class="dr-note2" style="margin-top:12px">Tournament dates are confirmed. Exact Australian live-session times publish on Kayo closer to each round.</div>
        <div class="btns">
          <a class="btn red" href="{esc(WATCH)}">Watch · Kayo</a>
          <a class="btn ghost" href="{esc(event['scores'])}">Leaderboard</a>
          <button class="btn ghost" onclick="openCard('{cid(event)}')">Tournament Details</button>
          <button class="btn ghost" onclick="addCal('{cid(event)}')">+ Calendar</button>
        </div>
      </div>
    </div>"""


def card(event):
    info = event["info"]
    # A broad planning hold, explicitly marked approximate: published event
    # dates are reliable while each day's broadcast start is not yet fixed.
    start_local = datetime.combine(event["start"], time(18), tzinfo=SYD)
    end_local = datetime.combine(event["end"] + timedelta(days=1), time(11), tzinfo=SYD)
    blocks = [
        [event["name"], info["stage"], 1],
        ["Tournament dates", date_range(event, True)],
        ["Course", info["course"]], ["Location", info["place"]],
        ["Purse / points", info["purse"]], ["Previous winner", info["previous"]],
        ["Sydney viewing", viewing(event)],
    ]
    return f"""  {cid(event)}: {{
    emoji:"⛳",
    cal:{{s:"{start_local.astimezone(timezone.utc):%Y-%m-%dT%H:%M:%S}Z",e:"{end_local.astimezone(timezone.utc):%Y-%m-%dT%H:%M:%S}Z",loc:{json.dumps(info['course'] + ', ' + info['place'])},approx:true}},
    title:{json.dumps(event['name'])},
    when:{json.dumps(date_range(event, True) + ' · PGA TOUR')},
    link:{json.dumps(SCHEDULE)},
    linkLabel:"Official PGA TOUR schedule ↗",
    secs:[{{h:"The Tournament",b:{json.dumps(blocks, ensure_ascii=False)}}},{{h:"Follow It Live",b:{json.dumps([["Australian TV", "Fox Sports via Kayo"], ["Leaderboard", event['scores']], ["Timing", "Exact tee and broadcast times publish tournament week"]], ensure_ascii=False)}}}],
    note:"The calendar button creates a broad tournament planning hold, not a claimed tee time. Check Kayo and the live leaderboard before play."
  }}"""


def ladder_rows(players):
    return "".join(
        f'<tr{lead}><td class="pos">{pos}</td><td class="who">{esc(player)}</td><td class="pts">{points}</td></tr>'
        for pos, player, points in players
        for lead in (' class="lead"' if pos == 1 else '',)
    )


def standings_table(limit=8):
    rows = ladder_rows(FEDEX_TOP[:limit])
    return f"""    <div class="card" data-slot="table">
      <div class="sport">FedExCup &nbsp;<span class="badge fn">Playoffs</span></div>
      <div class="inner" style="padding-top:14px">
        <table class="ladder"><thead><tr><th></th><th>Player</th><th class="pts">Pts</th></tr></thead><tbody>{rows}</tbody></table>
        <div class="dr-note2" style="margin-top:12px">Snapshot checked {FEDEX_CHECKED}. Top 50 reach the BMW Championship; top 30 reach the TOUR Championship. <a href="{STANDINGS}" style="color:var(--grey)">Live official standings ↗</a></div>
      </div>
    </div>"""


def full_standings():
    rows = ladder_rows(FEDEX_TOP)
    return f"""<div class="meta" style="margin-bottom:8px">Top 10 plus Australian watch · checked {FEDEX_CHECKED}</div>
<table class="ladder" style="border:1px solid var(--faint);padding:0 10px"><thead><tr><th></th><th>Player</th><th class="pts">Pts</th></tr></thead><tbody>{rows}</tbody></table>
<div class="dr-note2" style="margin-top:12px"><b>Aussie watch:</b> Min Woo Lee enters the playoffs at No. 16. The TOUR Championship is 72-hole stroke play with all 30 qualifiers starting level. <a href="{STANDINGS}" style="color:var(--grey)">Open the live FedExCup table ↗</a></div>"""


def splice(page, marker, block):
    pattern = re.compile(rf"(<!--BUILD:{marker}-->|/\*BUILD:{marker}\*/).*?(<!--/BUILD:{marker}-->|/\*/BUILD:{marker}\*/)", re.S)
    if not pattern.search(page):
        sys.exit(f"marker {marker} not found in {PAGE}")
    return pattern.sub(lambda match: match.group(1) + "\n" + block + "\n" + match.group(2), page, count=1)


def main():
    events = collect()
    if not events:
        print("no upcoming PGA TOUR events returned — leaving the tab as it is")
        return

    print(f"{len(events)} upcoming PGA TOUR events:")
    for event in events[:6]:
        print(f"  {date_range(event):18} {event['name']}")

    page = open(PAGE).read()
    before = page
    page = splice(page, "PGA-TABLE", standings_table())
    page = splice(page, "PGA-HERO", hero(events[0]))
    page = splice(page, "PGA-ROWS", "\n".join(row(event) for event in events))
    page = splice(page, "PGA-FULL", full_standings())
    page = splice(page, "PGA-CARDS", ",\n".join(card(event) for event in events))
    if page == before:
        print("PGA tab already current")
        return
    open(PAGE, "w").write(page)
    print(f"rebuilt the PGA Golf tab: {len(events)} tournaments ahead")


if __name__ == "__main__":
    main()
