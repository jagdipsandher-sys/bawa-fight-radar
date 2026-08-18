#!/usr/bin/env python3
"""Rebuild the combined ATP/WTA Tennis tab.

The ESPN feeds provide live tournament windows and status for both tours.  The
official ATP and WTA calendars supply the tour level, surface and location
context. Match start times are deliberately not inferred from an event-wide
timestamp: orders of play are published tournament-by-tournament and can move.
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
FEED = "https://site.api.espn.com/apis/site/v2/sports/tennis/{}/scoreboard?dates={}-{}"
ATP_CALENDAR = "https://www.atptour.com/en/tournaments/"
WTA_CALENDAR = "https://www.wtatennis.com/tournaments"
ATP_RANKINGS = "https://www.atptour.com/en/rankings/singles"
WTA_RANKINGS = "https://www.wtatennis.com/rankings/singles"
ESPN_SCORES = "https://www.espn.com.au/tennis/scoreboard"
BEIN = "https://www.beinsports.com/en-au/tennis"
STAN = "https://www.stan.com.au/watch/sport/tennis"
STAN_US_OPEN = "https://www.stan.com.au/watch/sport/tennis/us-open"


EVENT_INFO = {
    "cincinnati open": ("Mason, Ohio, USA", "Hard", "ATP Masters 1000 + WTA 1000", "🇺🇸"),
    "winston salem open": ("Winston-Salem, North Carolina, USA", "Hard", "ATP 250", "🇺🇸"),
    "abierto gnp seguros": ("Monterrey, Mexico", "Hard", "WTA 500", "🇲🇽"),
    "us open": ("New York, USA", "Hard", "Grand Slam", "🇺🇸"),
    "chengdu open": ("Chengdu, China", "Hard", "ATP 250", "🇨🇳"),
    "hangzhou open": ("Hangzhou, China", "Hard", "ATP 250", "🇨🇳"),
    "guadalajara open akron presented by santander": ("Guadalajara, Mexico", "Hard", "WTA 500", "🇲🇽"),
    "sp open": ("São Paulo, Brazil", "Hard", "WTA 250", "🇧🇷"),
    "korea open": ("Seoul, South Korea", "Hard", "WTA 500", "🇰🇷"),
    "singapore tennis open": ("Singapore", "Indoor hard", "WTA 250", "🇸🇬"),
    "kinoshita group japan open tennis championships": ("Tokyo, Japan", "Hard", "ATP 500", "🇯🇵"),
    "china open": ("Beijing, China", "Hard", "ATP 500 + WTA 1000", "🇨🇳"),
    "rolex shanghai masters": ("Shanghai, China", "Hard", "ATP Masters 1000", "🇨🇳"),
    "wuhan open": ("Wuhan, China", "Hard", "WTA 1000", "🇨🇳"),
    "almaty open": ("Almaty, Kazakhstan", "Indoor hard", "ATP 250", "🇰🇿"),
    "bnp paribas fortis european open": ("Brussels, Belgium", "Indoor hard", "ATP 250", "🇧🇪"),
    "grand prix auvergne rhone alpes": ("Lyon, France", "Indoor hard", "ATP 250", "🇫🇷"),
    "ningbo open": ("Ningbo, China", "Hard", "WTA 500", "🇨🇳"),
    "kinoshita group japan open": ("Osaka, Japan", "Hard", "WTA 250", "🇯🇵"),
    "erste bank open": ("Vienna, Austria", "Indoor hard", "ATP 500", "🇦🇹"),
    "swiss indoors basel": ("Basel, Switzerland", "Indoor hard", "ATP 500", "🇨🇭"),
    "guangzhou open": ("Guangzhou, China", "Hard", "WTA 250", "🇨🇳"),
    "toray pan pacific open tennis": ("Tokyo, Japan", "Hard", "WTA 500", "🇯🇵"),
    "rolex paris masters": ("Paris, France", "Indoor hard", "ATP Masters 1000", "🇫🇷"),
    "prudential hong kong tennis open": ("Hong Kong", "Hard", "WTA 250", "🇭🇰"),
    "chennai open": ("Chennai, India", "Hard", "WTA 250", "🇮🇳"),
    "bybit stockholm open": ("Stockholm, Sweden", "Indoor hard", "ATP 250", "🇸🇪"),
    "wta finals": ("Indian Wells, California, USA", "Hard", "WTA Finals", "🇺🇸"),
    "nitto atp finals": ("Turin, Italy", "Indoor hard", "ATP Finals", "🇮🇹"),
    "next gen atp finals presented by pif": ("Jeddah, Saudi Arabia", "Indoor hard", "Next Gen ATP Finals", "🇸🇦"),
    "davis cup qualifiers 2nd round": ("Multiple host cities", "Various", "Davis Cup", "🌍"),
    "billie jean king cup finals": ("Shenzhen, China", "Indoor hard", "BJK Cup Finals", "🌍"),
    "laver cup": ("The O2, London", "Indoor hard", "Team Europe v Team World", "🌍"),
    "davis cup final 8": ("BolognaFiere, Bologna, Italy", "Indoor hard", "Davis Cup Final 8", "🌍"),
}

# ESPN also carries WTA 125 events. The product brief is the main WTA Tour, so
# keep only events present on the official WTA main-tour calendar.
WTA_MAIN = {
    "cincinnati open", "abierto gnp seguros", "us open",
    "guadalajara open akron presented by santander", "sp open", "korea open",
    "singapore tennis open", "china open", "wuhan open", "ningbo open",
    "kinoshita group japan open", "guangzhou open", "toray pan pacific open tennis",
    "prudential hong kong tennis open", "chennai open", "wta finals",
}

MANUAL_EVENTS = [
    ("Davis Cup Qualifiers 2nd Round", date(2026, 9, 18), date(2026, 9, 20), "ATP", "https://www.daviscup.com/en/calendar"),
    ("Billie Jean King Cup Finals", date(2026, 9, 22), date(2026, 9, 27), "WTA", "https://www.billiejeankingcup.com/en/more"),
    ("Laver Cup", date(2026, 9, 25), date(2026, 9, 27), "ATP", "https://lavercup.com/schedule"),
    ("Davis Cup Final 8", date(2026, 11, 24), date(2026, 11, 29), "ATP", "https://www.daviscup.com/en/final-8-tickets"),
]

RANKINGS_CHECKED = "18 Aug 2026"
ATP_TOP = [
    (1, "Jannik Sinner", "13,450"), (2, "Carlos Alcaraz", "8,160"),
    (3, "Alexander Zverev", "8,090"), (4, "Felix Auger-Aliassime", "4,740"),
    (5, "Novak Djokovic", "3,760"), (6, "Ben Shelton", "3,670"),
    (7, "Daniil Medvedev", "3,580"), (8, "Alex de Minaur 🇦🇺", "3,560"),
    (9, "Taylor Fritz", "3,375"), (10, "Flavio Cobolli", "3,330"),
]
WTA_TOP = [
    (1, "Aryna Sabalenka", "8,670"), (2, "Elena Rybakina", "8,316"),
    (3, "Jessica Pegula", "6,680"), (4, "Coco Gauff", "5,919"),
    (5, "Iga Swiatek", "5,419"), (6, "Mirra Andreeva", "5,323"),
    (7, "Karolina Muchova", "5,048"), (8, "Linda Noskova", "5,016"),
    (9, "Elina Svitolina", "4,634"), (10, "Amanda Anisimova", "4,353"),
]


def esc(value):
    return html.escape(str(value or ""), quote=True)


def normalise(value):
    value = str(value or "").lower().replace("–", "-")
    value = value.translate(str.maketrans("áàäâãåéèëêíìïîóòöôõúùüûñçřšž", "aaaaaaeeeeiiiiooooouuuuncrsz"))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def parse_day(value):
    try:
        return date.fromisoformat(value[:10])
    except (AttributeError, ValueError):
        return None


def load_json(url):
    try:
        request = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
        })
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)
    except Exception as first_error:
        fallback = subprocess.run(["curl", "-fsSL", url], capture_output=True, text=True)
        if fallback.returncode:
            detail = f" HTTP {first_error.code}" if hasattr(first_error, "code") else ""
            sys.exit(f"tennis feed failed ({type(first_error).__name__}{detail}) — leaving the tab alone")
        try:
            return json.loads(fallback.stdout)
        except json.JSONDecodeError:
            sys.exit("tennis feed returned invalid JSON — leaving the tab alone")


def event_link(event):
    return next((item.get("href") for item in event.get("links", []) if item.get("href")), ESPN_SCORES)


def collect_feed(tour):
    today = datetime.now(SYD).date()
    url = FEED.format(tour, today.strftime("%Y%m%d"), f"{today.year}1231")
    events = []
    for item in load_json(url).get("events", []):
        name = item.get("name") or "Tennis tournament"
        key = normalise(name)
        if tour == "wta" and key not in WTA_MAIN:
            continue
        start, end = parse_day(item.get("date")), parse_day(item.get("endDate"))
        if not start or not end or end < today:
            continue
        if key not in EVENT_INFO:
            print(f"  skipping unmapped {tour.upper()} event: {name}")
            continue
        events.append({
            "id": str(item.get("id") or key), "name": name, "start": start, "end": end,
            "tour": tour.upper(), "scores": event_link(item), "info": EVENT_INFO[key],
        })
    return events


def collect():
    today = datetime.now(SYD).date()
    merged = {}
    for event in collect_feed("atp") + collect_feed("wta"):
        key = normalise(event["name"])
        existing = merged.get(key)
        if existing:
            existing["tour"] = "ATP + WTA"
            existing["start"] = min(existing["start"], event["start"])
            existing["end"] = max(existing["end"], event["end"])
        else:
            merged[key] = event
    for name, start, end, tour, link in MANUAL_EVENTS:
        if end < today:
            continue
        key = normalise(name)
        merged[key] = {
            "id": key, "name": name, "start": start, "end": end, "tour": tour,
            "scores": link, "info": EVENT_INFO[key],
        }
    return sorted(merged.values(), key=lambda event: (event["start"], event["name"]))


def cid(event):
    slug = re.sub(r"[^a-z0-9]", "", normalise(event["name"]))[:30]
    return f"ten{event['start']:%m%d}{slug}"


def date_range(event, long=False):
    start, end = event["start"], event["end"]
    if start == end:
        return start.strftime("%-d %B %Y" if long else "%a %-d %b")
    if start.month == end.month:
        return f"{start:%-d}–{end.strftime('%-d %B %Y' if long else '%-d %b')}"
    return f"{start.strftime('%-d %b')}–{end.strftime('%-d %b %Y' if long else '%-d %b')}"


def end_stamp(event):
    return datetime.combine(event["end"] + timedelta(days=1), time(12), tzinfo=SYD).isoformat()


def viewing(event):
    place = event["info"][0].lower()
    if any(region in place for region in ("china", "japan", "korea", "singapore", "hong kong")):
        return "Sydney-friendly daytime and evening sessions"
    if any(region in place for region in ("usa", "mexico", "brazil")):
        return "Live play usually lands overnight and through the Sydney morning"
    if any(region in place for region in ("india", "saudi")):
        return "Afternoon and evening viewing in Sydney"
    return "European sessions usually run from Sydney evening into the night"


def watch(event):
    key = normalise(event["name"])
    if key == "us open":
        return "Stan Sport", STAN_US_OPEN
    if key == "laver cup":
        return "Stan Sport", STAN
    return "beIN Sports", BEIN


def badge(event):
    level = event["info"][2]
    style = "home" if ("Grand Slam" in level or "1000" in level) else "fn"
    label = "Grand Slam" if "Grand Slam" in level else ("1000" if "1000" in level else level)
    return f'<span class="badge {style}">{esc(label)}</span>'


def row(event):
    place, surface, level, flag = event["info"]
    service, watch_url = watch(event)
    return f"""      <tr data-sport="tennis" data-ends="{end_stamp(event)}" data-card="{cid(event)}">
        <td class="d">{event['start']:%a %-d %b}<small>to {event['end']:%a %-d %b}</small></td>
        <td><span class="sporttag m">{esc(event['tour'])}</span></td>
        <td><span class="flag" style="margin-right:6px">{flag}</span><span class="ev">{esc(event['name'])}</span> {badge(event)}<br><span class="sub">{esc(viewing(event))} · {esc(surface)}</span></td>
        <td>{esc(place)}<small>{esc(level)}</small></td>
        <td><a class="mini buy" href="{esc(watch_url)}">Watch · {esc(service)}</a><a class="mini" href="{esc(event['scores'])}">Scores</a><button class="mini" onclick="openCard('{cid(event)}')">Details</button><button class="mini" onclick="addCal('{cid(event)}')">+ Cal</button></td>
      </tr>"""


def hero(event):
    place, surface, level, flag = event["info"]
    service, watch_url = watch(event)
    today = datetime.now(SYD).date()
    live = event["start"] <= today <= event["end"]
    state = '<span class="badge home">On Now</span>' if live else '<span class="badge soon">Coming Up</span>'
    countdown_to = event["end"] if live else event["start"]
    return f"""    <div class="card" data-slot="tennis" data-ends="{end_stamp(event)}">
      <div class="sport">{'Current' if live else 'Next'} Tournament &nbsp;{state} {badge(event)} <span class="badge soon"><span class="cd" data-until="{countdown_to:%Y-%m-%d}"></span></span></div>
      <div class="crest dark">
        <div class="big"><span style="font-size:2.2rem;vertical-align:middle">{flag}</span> {esc(event['name'])} <em>🎾</em></div>
        <div class="lil">{esc(event['tour'])} · {esc(level)} · {esc(place)}</div>
      </div>
      <div class="inner">
        <div class="fight hd">{esc(event['name'])}<small>{esc(viewing(event))}</small></div>
        <div class="when">Tournament window · <span class="t">{esc(date_range(event, True))}</span></div>
        <div class="meta">{esc(surface)} · {esc(level)} · Australian coverage: {esc(service)}</div>
        <div class="dr-note2" style="margin-top:12px">The event window can include qualifying. Exact match times appear in the live order of play and are not guessed here.</div>
        <div class="btns">
          <a class="btn red" href="{esc(watch_url)}">Watch · {esc(service)}</a>
          <a class="btn ghost" href="{esc(event['scores'])}">Live Scores</a>
          <button class="btn ghost" onclick="openCard('{cid(event)}')">Tournament Details</button>
          <button class="btn ghost" onclick="addCal('{cid(event)}')">+ Calendar</button>
        </div>
      </div>
    </div>"""


def official_link(event):
    if normalise(event["name"]) == "us open":
        return "https://www.usopen.org/"
    if event["tour"] == "WTA":
        return WTA_CALENDAR
    return ATP_CALENDAR


def card(event):
    place, surface, level, _flag = event["info"]
    service, watch_url = watch(event)
    start_local = datetime.combine(event["start"], time(9), tzinfo=SYD)
    end_local = datetime.combine(event["end"] + timedelta(days=1), time(9), tzinfo=SYD)
    blocks = [
        [event["name"], event["tour"], 1], ["Tournament window", date_range(event, True)],
        ["Level", level], ["Surface", surface], ["Location", place],
        ["Australian coverage", service], ["Sydney viewing", viewing(event)],
    ]
    live_blocks = [["Scores / order of play", event["scores"]], ["Watch", watch_url],
                   ["Timing", "Exact match times publish in the order of play"]]
    return f"""  {cid(event)}: {{
    emoji:"🎾",
    cal:{{s:"{start_local.astimezone(timezone.utc):%Y-%m-%dT%H:%M:%S}Z",e:"{end_local.astimezone(timezone.utc):%Y-%m-%dT%H:%M:%S}Z",loc:{json.dumps(place)},approx:true}},
    title:{json.dumps(event['name'])},
    when:{json.dumps(date_range(event, True) + ' · ' + event['tour'])},
    link:{json.dumps(official_link(event))},
    linkLabel:"Official tournament calendar ↗",
    secs:[{{h:"The Tournament",b:{json.dumps(blocks, ensure_ascii=False)}}},{{h:"Follow It Live",b:{json.dumps(live_blocks, ensure_ascii=False)}}}],
    note:"The calendar button creates a broad tournament hold, not a claimed match time. Check the live order of play before each session."
  }}"""


def ladder_rows(players, aussie=False):
    rows = []
    for pos, player, points in players:
        cls = ' class="lead"' if pos == 1 else (' class="me"' if aussie and "🇦🇺" in player else "")
        rows.append(f'<tr{cls}><td class="pos">{pos}</td><td class="who">{esc(player)}</td><td class="pts">{points}</td></tr>')
    return "".join(rows)


def rankings_card():
    return f"""    <div class="card" data-slot="table">
      <div class="sport">World Rankings &nbsp;<span class="badge fn">ATP + WTA</span></div>
      <div class="inner" style="padding-top:14px">
        <div class="when">Men</div>
        <table class="ladder"><thead><tr><th></th><th>ATP</th><th class="pts">Pts</th></tr></thead><tbody>{ladder_rows(ATP_TOP[:5], True)}</tbody></table>
        <div class="when" style="margin-top:14px">Women</div>
        <table class="ladder"><thead><tr><th></th><th>WTA</th><th class="pts">Pts</th></tr></thead><tbody>{ladder_rows(WTA_TOP[:5])}</tbody></table>
        <div class="dr-note2" style="margin-top:12px">Official rankings snapshot checked {RANKINGS_CHECKED}. <a href="{ATP_RANKINGS}" style="color:var(--grey)">ATP live ↗</a> · <a href="{WTA_RANKINGS}" style="color:var(--grey)">WTA live ↗</a></div>
      </div>
    </div>"""


def full_rankings():
    return f"""<div class="hero">
  <div class="card"><div class="sport">ATP Singles &nbsp;<span class="badge fn">Top 10</span></div><div class="inner" style="padding-top:14px"><table class="ladder"><thead><tr><th></th><th>Player</th><th class="pts">Pts</th></tr></thead><tbody>{ladder_rows(ATP_TOP, True)}</tbody></table><div class="dr-note2" style="margin-top:12px"><b>Aussie watch:</b> Alex de Minaur is world No. 8. <a href="{ATP_RANKINGS}" style="color:var(--grey)">Live ATP rankings ↗</a></div></div></div>
  <div class="card"><div class="sport">WTA Singles &nbsp;<span class="badge fn">Top 10</span></div><div class="inner" style="padding-top:14px"><table class="ladder"><thead><tr><th></th><th>Player</th><th class="pts">Pts</th></tr></thead><tbody>{ladder_rows(WTA_TOP)}</tbody></table><div class="dr-note2" style="margin-top:12px"><b>Aussie watch:</b> Maya Joint leads Australia's women; use the live table for her changing rank. <a href="{WTA_RANKINGS}" style="color:var(--grey)">Live WTA rankings ↗</a></div></div></div>
</div>
<div class="meta" style="margin-top:10px">Rankings snapshot checked {RANKINGS_CHECKED}; the linked official tables are live.</div>"""


def splice(page, marker, block):
    pattern = re.compile(rf"(<!--BUILD:{marker}-->|/\*BUILD:{marker}\*/).*?(<!--/BUILD:{marker}-->|/\*/BUILD:{marker}\*/)", re.S)
    if not pattern.search(page):
        sys.exit(f"marker {marker} not found in {PAGE}")
    return pattern.sub(lambda match: match.group(1) + "\n" + block + "\n" + match.group(2), page, count=1)


def main():
    events = collect()
    if not events:
        print("no upcoming ATP/WTA events returned — leaving the Tennis tab alone")
        return
    print(f"{len(events)} upcoming ATP/WTA events:")
    for event in events[:8]:
        print(f"  {date_range(event):18} {event['tour']:9} {event['name']}")

    page = open(PAGE).read()
    before = page
    page = splice(page, "TENNIS-TABLE", rankings_card())
    page = splice(page, "TENNIS-HERO", hero(events[0]))
    page = splice(page, "TENNIS-ROWS", "\n".join(row(event) for event in events))
    page = splice(page, "TENNIS-FULL", full_rankings())
    page = splice(page, "TENNIS-CARDS", ",\n".join(card(event) for event in events))
    if page == before:
        print("Tennis tab already current")
        return
    open(PAGE, "w").write(page)
    print(f"rebuilt the Tennis tab: {len(events)} tournaments ahead")


if __name__ == "__main__":
    main()
