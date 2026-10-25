#!/usr/bin/env python3
"""Build the dedicated Boxing subsection from boxing.json.

Selection policy:
  * every announced headline/title-level heavyweight contest;
  * major champions and recognisable names in other divisions;
  * celebrity/legend exhibitions, isolated from professional contests.

Confirmed contests stay visible until 24 hours after the estimated broadcast
finish. Date-only announcements are kept through the end of their local event
day plus that same grace period. A signed exhibition with no date remains in a
clearly labelled watchlist and never receives a countdown or calendar button.
"""
import html
import json
import re
import sys
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from send_fights import SYD

DATA = "boxing.json"
PAGE = "index.html"
LOOKAHEAD_DAYS = 365
GRACE_HOURS = 24
EVENT_HOURS = 4

CATEGORY_META = {
    "heavyweight": ("Heavyweights", "Every announced headline, title or leading-contender heavyweight bout."),
    "notable": ("Big Names & Title Fights", "Recognisable stars and meaningful world-title fights outside heavyweight."),
    "exhibition": ("Exhibitions & Showcases", "Celebrity and legend events, kept separate so they are never mistaken for professional contests."),
}

WATCH_URLS = {
    "netflix": "https://www.netflix.com/",
    "dazn": "https://www.dazn.com/en-AU/home",
    "kayo": "https://kayosports.com.au/",
    "fox sports": "https://www.foxsports.com.au/",
}


def esc(value):
    return html.escape(str(value or ""), quote=True)


def slug(value):
    return "boxing_" + (re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:42] or "event")


def parse_utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def enrich(event):
    item = dict(event)
    item["_id"] = slug(item.get("name", ""))
    item["_start"] = None
    item["_date_only"] = False
    if item.get("date_utc"):
        item["_start"] = parse_utc(item["date_utc"])
        item["_end"] = item["_start"] + timedelta(hours=EVENT_HOURS)
        item["_sort"] = item["_start"]
    elif item.get("local_date"):
        zone = ZoneInfo(item.get("timezone") or "Australia/Sydney")
        local_day = date.fromisoformat(item["local_date"])
        item["_date_only"] = True
        item["_sort"] = datetime.combine(local_day, time.min, zone).astimezone(timezone.utc)
        item["_end"] = datetime.combine(local_day, time(23, 59), zone).astimezone(timezone.utc)
    else:
        item["_end"] = None
        item["_sort"] = datetime.max.replace(tzinfo=timezone.utc)
    item["_expires"] = item["_end"] + timedelta(hours=GRACE_HOURS) if item["_end"] else None
    return item


def validate(raw):
    problems = []
    seen = set()
    for index, event in enumerate(raw, 1):
        name = event.get("name", "")
        if not name:
            problems.append(f"entry {index} has no name")
        if name.lower() in seen:
            problems.append(f"duplicate event: {name}")
        seen.add(name.lower())
        if event.get("category") not in CATEGORY_META:
            problems.append(f"{name}: invalid category")
        if event.get("status") not in {"confirmed", "date_tbc", "cancelled"}:
            problems.append(f"{name}: invalid status")
        if event.get("status") == "confirmed" and not (event.get("date_utc") or event.get("local_date")):
            problems.append(f"{name}: confirmed but has no date")
        if event.get("status") == "date_tbc" and (event.get("date_utc") or event.get("local_date")):
            problems.append(f"{name}: date_tbc must not carry a guessed date")
        if not str(event.get("link", "")).startswith("https://"):
            problems.append(f"{name}: official source link is missing")
        if not event.get("verified_on"):
            problems.append(f"{name}: verified_on is missing")
    if problems:
        raise ValueError("\n".join(problems))


def load_events(now=None):
    with open(DATA) as source:
        raw = json.load(source)
    validate(raw)
    now = now or datetime.now(timezone.utc)
    horizon = now + timedelta(days=LOOKAHEAD_DAYS)
    events = []
    for event in raw:
        if event.get("status") == "cancelled":
            continue
        item = enrich(event)
        if item["_expires"] and item["_expires"] < now:
            continue
        if item["_sort"] != datetime.max.replace(tzinfo=timezone.utc) and item["_sort"] > horizon:
            continue
        events.append(item)
    return sorted(events, key=lambda item: (item["_sort"], item["name"]))


def short_sydney(value):
    local = value.astimezone(SYD)
    return local.strftime("%a %-d %b")


def when_label(event):
    if event["_start"]:
        local = event["_start"].astimezone(SYD)
        clock = local.strftime("%-I:%M%p").replace(":00", "").lower()
        return f"{local:%a %-d %b} · from {clock} {local:%Z}"
    if event.get("local_date"):
        day = date.fromisoformat(event["local_date"])
        return day.strftime("%a %-d %b") + " local · Sydney start time TBC"
    return "Date, venue and Sydney time TBC"


def date_cell(event):
    if event["_start"]:
        local = event["_start"].astimezone(SYD)
        return f'{local:%a %-d %b}<small>from {local.strftime("%-I:%M%p").lower().replace(":00", "")} {local:%Z}</small>'
    if event.get("local_date"):
        day = date.fromisoformat(event["local_date"])
        return f'{day:%a %-d %b} local<small>Sydney date / time TBC</small>'
    return 'Date TBC<small>announcement watch</small>'


def category_badge(event):
    if event["category"] == "heavyweight":
        return '<span class="badge ppv">Heavyweight</span>'
    if event["category"] == "exhibition":
        return '<span class="badge tbc">Exhibition · Date TBC</span>'
    return '<span class="badge fn">Big Name / Title</span>'


def poster(event, hero=False):
    url = event.get("image")
    if not url:
        return ""
    if hero:
        return f'<div class="faces promo-art"><img src="{esc(url)}" alt="{esc(event["name"])} official promotional artwork" onerror="imgFail(this,\'BX\')"></div>'
    return f'<span class="thumbs media-art"><img class="poster" loading="lazy" src="{esc(url)}" alt="{esc(event["name"])} official promotional artwork" onerror="imgFail(this,\'BX\')"></span>'


def watch_url(event):
    watch = event.get("watch_au", "").lower()
    for needle, url in WATCH_URLS.items():
        if needle in watch:
            return url
    return ""


def data_attrs(event):
    attrs = ' data-sport="box"'
    if event["_end"]:
        attrs += f' data-ends="{event["_end"].astimezone(SYD).isoformat()}"'
    attrs += f' data-card="{event["_id"]}"'
    return attrs


def row_html(event):
    first = event.get("fights", [event["name"]])[0]
    more = len(event.get("fights", [])) - 1
    summary = esc(first) + (f" · plus {more} more announced bout{'s' if more != 1 else ''}" if more > 0 else "")
    links = []
    if watch_url(event):
        links.append(f'<a class="mini buy" href="{esc(watch_url(event))}">Watch · {esc(event.get("watch_au"))}</a>')
    elif event.get("watch_au") and "tbc" not in event["watch_au"].lower():
        links.append(f'<span class="badge fn">{esc(event["watch_au"])}</span>')
    else:
        links.append('<span class="badge tbc">AU Broadcaster TBC</span>')
    links.append(f'<button class="mini" onclick="openCard(\'{event["_id"]}\')">Details</button>')
    if event["_start"]:
        links.append(f'<button class="mini" onclick="addCal(\'{event["_id"]}\')">+ Cal</button>')
    links.append(f'<a class="mini" href="{esc(event["link"])}">Official Source</a>')
    return f'''      <tr{data_attrs(event)}>
        <td class="d">{date_cell(event)}</td><td><span class="sporttag b">Box</span></td>
        <td>{poster(event)}<span class="ev">{esc(event["name"])}</span> {category_badge(event)}<br><span class="sub">{summary}</span></td>
        <td>{esc(event.get("venue") or "Venue TBC")}<br><span class="sub">{esc(event.get("stakes") or event.get("weight") or "")}</span></td>
        <td>{"".join(links)}</td>
      </tr>'''


def hero_html(event):
    watch = watch_url(event)
    watch_button = (f'<a class="btn red" href="{esc(watch)}">Watch · {esc(event.get("watch_au"))}</a>'
                    if watch else '<span class="badge tbc">AU Broadcaster TBC</span>')
    calendar = (f'<button class="btn ghost" onclick="addCal(\'{event["_id"]}\')">+ Calendar</button>'
                if event["_start"] else '')
    countdown = ""
    if event["_end"]:
        countdown = f' <span class="badge soon"><span class="cd" data-until="{event["_end"].astimezone(SYD):%Y-%m-%d}"></span></span>'
    return f'''    <div class="card" data-slot="box" data-ends="{event["_end"].astimezone(SYD).isoformat()}">
      <div class="sport">BOXING &nbsp;{category_badge(event)}{countdown}</div>
      {poster(event, hero=True)}
      <div class="inner">
        <div class="fight hd">{esc(event["name"])}<small>{esc(event.get("stakes") or event.get("weight") or "")}</small></div>
        <div class="when">{esc(when_label(event))}</div>
        <div class="meta">{esc(event.get("venue"))} · {esc(event.get("watch_au") or "AU broadcaster TBC")}</div>
        <div class="btns">{watch_button}<button class="btn ghost" onclick="openCard('{event["_id"]}')">Fight Details</button>{calendar}</div>
      </div>
    </div>'''


def sections_html(events):
    blocks = []
    for category, (title, explanation) in CATEGORY_META.items():
        selected = [event for event in events if event["category"] == category]
        if not selected:
            continue
        rows = "\n".join(row_html(event) for event in selected)
        blocks.append(f'''  <h2>{esc(title)}</h2>
  <div class="streaming-note"><b>{esc(explanation)}</b></div>
  <table class="boxing-table">
    <thead><tr><th>Date / Sydney time</th><th></th><th>Fight</th><th>Venue / Stakes</th><th>Watch / Details</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>''')
    return "\n\n".join(blocks)


def card_js(event):
    bouts = []
    for index, bout in enumerate(event.get("fights") or [event["name"]]):
        bouts.append([bout, "Main Event" if index == 0 else "", 1 if index == 0 else 0])
    status = "Confirmed" if event.get("status") == "confirmed" else "Signed exhibition · new date pending"
    sections = [
        {"h": "What it is", "b": [[event.get("stakes") or event.get("weight") or "Boxing", event.get("promotion", "")], [status, event.get("watch_au", "Broadcaster TBC"), 1]]},
        {"h": "Card as announced", "b": bouts},
        {"h": "Why it is on the radar", "b": [[event.get("include_reason", "Selected under the boxing inclusion rules."), f'Verified {event.get("verified_on", "")}', 1]]},
    ]
    card = {
        "emoji": "🥊",
        "title": event["name"],
        "when": when_label(event),
        "link": event["link"],
        "linkLabel": "Official source ↗",
        "secs": sections,
        "note": "Professional fights, title bouts and exhibitions are classified separately. Dates, undercards and Australian broadcasters are never guessed.",
    }
    if event["_start"]:
        card["cal"] = {
            "s": event["_start"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "e": event["_end"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "loc": f'{event.get("venue", "")} · {event.get("watch_au", "")}'.strip(" ·"),
        }
    return f"  {event['_id']}: " + json.dumps(card, ensure_ascii=False)


def splice(page, marker, block):
    pattern = re.compile(rf"(<!--BUILD:{marker}-->|/\*BUILD:{marker}\*/).*?(<!--/BUILD:{marker}-->|/\*/BUILD:{marker}\*/)", re.S)
    if not pattern.search(page):
        sys.exit(f"marker {marker} not found in {PAGE}")
    return pattern.sub(lambda match: match.group(1) + "\n" + block + "\n" + match.group(2), page, count=1)


def main():
    events = load_events()
    scheduled = [event for event in events if event["_end"]]
    if not scheduled:
        sys.exit("no scheduled boxing events — refusing to blank the Boxing hero")
    page = open(PAGE).read()
    before = page
    page = splice(page, "BOXING-HERO", hero_html(scheduled[0]))
    page = splice(page, "BOXING-SECTIONS", sections_html(events))
    page = splice(page, "BOXING-CARDS", ",\n".join(card_js(event) for event in events))
    if page == before:
        print(f"boxing already current — {len(events)} tracked events")
        return
    with open(PAGE, "w") as target:
        target.write(page)
    counts = {category: len([event for event in events if event["category"] == category]) for category in CATEGORY_META}
    print(f"rebuilt Boxing: {counts['heavyweight']} heavyweights, {counts['notable']} notable, {counts['exhibition']} exhibitions")


if __name__ == "__main__":
    main()
