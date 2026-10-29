#!/usr/bin/env python3
"""
The month-at-a-glance calendar for the Friday email.

Jack wanted the email to carry a graphic like a tourism "what's on this month"
poster, where tapping an event opens that event on the radar.

It is deliberately NOT an image. An image cannot have per-event links: Gmail,
Outlook and Apple Mail all strip <map>/<area>, so a picture of a calendar is a
dead end the moment you want the squares to be clickable. This builds the same
look out of a plain HTML table with inline styles, which every mail client
renders, and every event is a real <a>. It also means the text stays
selectable, scales with the reader's font size, and costs nothing to load.

Everything comes from index.html, the same as weekend.py, so the calendar can
never advertise something the site does not show.
"""
import html as html_mod
import re
from calendar import Calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import weekend

SYD = ZoneInfo("Australia/Sydney")
SITE = "https://jagdipsandher-sys.github.io/bawa-fight-radar/"
# Pre-rendered month banners, built by make_banner.py and committed. See the
# note at the top of that file for why they are files rather than built here.
BANNER = SITE + "img/month-{ym}.jpg"

# Which tabs feed the calendar, in the order a clash is resolved. The boys are
# here for the fights, so combat wins a crowded square and tennis loses it.
# (tab, short label, chip background, chip text colour)
SOURCES = [
    ("fights",   "UFC",     "#fdecec", "#a81414"),
    ("boxing",   "Boxing",  "#fdecec", "#a81414"),
    ("bkfc",     "BKFC",    "#fdecec", "#a81414"),
    ("panthers", "Panthers", "#eaf3ea", "#1f5c2e"),
    ("raiders",  "Raiders", "#eaf3ea", "#1f5c2e"),
    ("united",   "Man Utd", "#eaf0fa", "#1b3f82"),
    ("nba",      "NBA",     "#eaf0fa", "#1b3f82"),
    ("f1",       "F1",      "#fdf3e3", "#8a5a08"),
    ("motogp",   "MotoGP",  "#fdf3e3", "#8a5a08"),
    ("other",    "Motor",   "#fdf3e3", "#8a5a08"),
    ("pga",      "Golf",    "#f1eefa", "#4a3b86"),
    ("tennis",   "Tennis",  "#f1eefa", "#4a3b86"),
    ("comedy",   "Comedy",  "#fbeef5", "#8a2f63"),
    ("sydney",   "Sydney",  "#fbeef5", "#8a2f63"),
]

MAX_PER_DAY = 3

# A row carries data-ends, the FINISH time, which is right for pruning the
# page and wrong for a calendar: an 11:30pm Saturday kick-off finishes after
# midnight and would land on Sunday's square. The date cell already reads
# "Sat 31 Oct", so the start day is taken from there, with the finish time
# only as a fallback.
_DAYTXT = re.compile(r"\b(\d{1,2})\s+"
                     r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", re.I)
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"])}


def start_day(row):
    """(day, month) the event STARTS on."""
    m = _DAYTXT.search(row.get("day") or "")
    if not m:
        return row["when"].day, row["when"].month
    return int(m.group(1)), _MONTHS[m.group(2).lower()]
          # a square fits three chips before it stops being readable


def esc(t):
    return html_mod.escape(str(t or ""), quote=True)


def target_month(today=None):
    """Which month the email should show.

    Looking a week out, so the last Friday of a month advertises the next one
    rather than four empty squares.
    """
    today = today or datetime.now(SYD)
    d = today + timedelta(days=7)
    return d.year, d.month


# Tabs where the chip label already names our team, so repeating it in the
# square wastes the only few words a square has. "Man Utd v AS Roma" under a
# MAN UTD chip becomes "v AS Roma"; "Chelsea v Man Utd" becomes "at Chelsea".
OUR_TEAM = {"united": "Man Utd", "nba": "Wolves",
            "panthers": "Panthers", "raiders": "Raiders"}

# Tournament tabs run several events at once and would otherwise fill a square
# on their own. One a day is enough to say "there is tennis on".
PER_DAY_CAP = {"tennis": 1, "pga": 1, "comedy": 1, "sydney": 1}

CHARS = 20          # past this a chip wraps to four lines and the row balloons


def _short(name, tab=""):
    """Fit an event into a calendar square."""
    n = re.sub(r"^(UFC\s*\d+:\s*|UFC Fight Night:\s*)", "", name).strip()
    n = re.sub(r"\bGrand Prix of\b", "GP", n)
    n = re.sub(r"\bGrand Prix\b", "GP", n)
    n = re.sub(r"\s+vs?\.?\s+", " v ", n)

    us = OUR_TEAM.get(tab)
    if us and f" v {us}" in n:
        n = "at " + n.split(f" v {us}")[0].strip()      # away game
    elif us and n.startswith(f"{us} v "):
        n = "v " + n[len(us) + 3:].strip()              # home game

    n = re.sub(r"\s{2,}", " ", n).strip()
    return n if len(n) <= CHARS else n[:CHARS - 1].rstrip(" ,.:") + "\u2026"


def collect(year, month, page_path="index.html", now=None):
    """Every event in that month, keyed by day number."""
    now = now or datetime.now(SYD)
    page = open(page_path, encoding="utf-8").read()
    panes = weekend.panes(page)

    first = datetime(year, month, 1, tzinfo=SYD)
    nxt = datetime(year + (month == 12), (month % 12) + 1, 1, tzinfo=SYD)
    last = nxt - timedelta(minutes=1)

    days = {}
    for order, (tab, label, bg, fg) in enumerate(SOURCES):
        if tab not in panes:
            continue
        body = panes[tab]
        # weekend.rows_between gives name/day/when but drops the card id, which
        # is the whole point of this calendar, so the ids are read alongside it
        cards = re.findall(r"<tr[^>]*data-ends=\"([^\"]+)\"[^>]*data-card=\"([^\"]+)\"", body)
        by_end = dict(cards)
        for r in weekend.rows_between(body, first, last):
            if not r["name"]:
                continue
            d, mth = start_day(r)
            if mth != month:          # starts in a neighbouring month
                continue
            days.setdefault(d, []).append({
                "order": order, "tab": tab, "label": label,
                "bg": bg, "fg": fg,
                "name": r["name"],
                "short": _short(r["name"], tab),
                "card": by_end.get(r["when"].isoformat(), ""),
                "past": r["when"] < now,
            })
    for d in days:
        days[d].sort(key=lambda e: (e["order"], e["name"]))
        kept, seen = [], {}
        for e in days[d]:
            seen[e["tab"]] = seen.get(e["tab"], 0) + 1
            cap = PER_DAY_CAP.get(e["tab"])
            if cap and seen[e["tab"]] > cap:
                continue
            kept.append(e)
        days[d] = kept
    return days


def link_for(e):
    tab = e["tab"]
    return f"{SITE}#{tab}/{e['card']}" if e["card"] else f"{SITE}#{tab}"


# ---------------------------------------------------------------------------
# Rendering.
#
# Email HTML is 1999 HTML: tables, inline styles, no <style> block worth
# trusting, no flexbox, no grid, no background-image. Outlook on Windows
# renders through Word, so every cell carries its own width and padding and
# nothing relies on CSS inheritance.
# ---------------------------------------------------------------------------
HD = "'Arial Narrow','Helvetica Neue Condensed',Arial,Helvetica,sans-serif"
BODY = "'Helvetica Neue',Helvetica,Arial,sans-serif"
INK = "#141416"
EDGE = "#e2e2de"

DOW = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]


def _chip(e):
    """One event inside a day square. The whole chip is the link."""
    dim = ";opacity:.45" if e["past"] else ""
    return (
        f'<a href="{esc(link_for(e))}" target="_blank" '
        f'style="display:block;margin:0 0 3px 0;padding:3px 4px;border-radius:3px;'
        f'background:{e["bg"]};color:{e["fg"]};text-decoration:none;'
        f'font-family:{BODY};font-size:10px;line-height:1.25;'
        f'word-break:break-word;overflow-wrap:break-word{dim}">'
        f'<span style="font-weight:bold;font-size:8px;letter-spacing:.4px;'
        f'text-transform:uppercase;color:{e["fg"]}">{esc(e["label"])}</span><br>'
        f'<span style="color:{e["fg"]}">{esc(e["short"])}</span></a>'
    )


def _cell(day, events, month_name, in_month, today_num):
    if not in_month:
        return ('<td style="width:80px;height:86px;border:1px solid ' + EDGE +
                ';background:#fafaf7;padding:0">&nbsp;</td>')
    is_today = day == today_num
    past = all(e["past"] for e in events) and events
    numcol = "#b6b6ae" if past else INK
    bg = "#fffaf7" if is_today else "#ffffff"
    ring = f"border:2px solid {INK};" if is_today else f"border:1px solid {EDGE};"

    chips = "".join(_chip(e) for e in events[:MAX_PER_DAY])
    extra = ""
    if len(events) > MAX_PER_DAY:
        n = len(events) - MAX_PER_DAY
        extra = (f'<a href="{SITE}" target="_blank" style="display:block;'
                 f'font-family:{BODY};font-size:9px;color:#6b6b63;'
                 f'text-decoration:none;padding-left:4px">+{n} more</a>')
    return (
        f'<td valign="top" style="width:80px;height:86px;{ring}background:{bg};'
        f'padding:3px">'
        f'<div style="font-family:{HD};font-size:13px;font-weight:bold;'
        f'color:{numcol};padding:0 0 2px 3px">{day}</div>'
        f'{chips}{extra}</td>'
    )


def _main_event(days):
    """The fight to put on the banner strip: the next combat event still to
    come this month, else the first one of the month."""
    fights = [e for d in sorted(days) for e in days[d]
              if e["label"] in ("UFC", "Boxing", "BKFC")]
    if not fights:
        return None
    return next((e for e in fights if not e["past"]), fights[0])


def render(year=None, month=None, page_path="index.html", now=None):
    """The whole calendar block, ready to drop into the email body."""
    now = now or datetime.now(SYD)
    if year is None or month is None:
        year, month = target_month(now)
    days = collect(year, month, page_path, now)
    if not days:
        return ""

    first = datetime(year, month, 1, tzinfo=SYD)
    month_name = f"{first:%B}".upper()
    today_num = now.day if (now.year, now.month) == (year, month) else None

    # The banner is an image, so it has to survive a client that blocks
    # images: the alt text carries the month, and the main event bar below it
    # is live HTML that always shows.
    head = (
        f'<tr><td colspan="7" style="padding:0;background:{INK}">'
        f'<a href="{SITE}" target="_blank" style="text-decoration:none">'
        f'<img src="{BANNER.format(ym=f"{year}{month:02d}")}" width="560" '
        f'alt="Whats on this month · {month_name} {year} · BAWA Fight Radar" '
        f'style="display:block;width:100%;max-width:560px;height:auto;border:0;'
        f'font-family:{HD};font-size:18px;color:#ffffff;padding:14px 0">'
        f'</a></td></tr>'
    )
    main = _main_event(days)
    if main:
        head += (
            f'<tr><td colspan="7" style="background:{INK};padding:9px 12px" align="center">'
            f'<a href="{esc(link_for(main))}" target="_blank" style="text-decoration:none">'
            f'<span style="font-family:{BODY};font-size:9px;letter-spacing:4px;'
            f'text-transform:uppercase;color:#9b9ba1">Main event&nbsp;&nbsp;</span>'
            f'<span style="font-family:{HD};font-size:17px;font-weight:bold;'
            f'letter-spacing:1px;color:#ffffff">{esc(main["label"].upper())} '
            f'&middot; {esc(main["short"].upper())}</span></a></td></tr>'
        )
    dow = "<tr>" + "".join(
        f'<td align="center" style="background:#1d1d20;padding:5px 0;'
        f'font-family:{HD};font-size:10px;letter-spacing:1px;color:#e8e8e6">{d}</td>'
        for d in DOW) + "</tr>"

    weeks = Calendar(firstweekday=6).monthdayscalendar(year, month)  # Sunday first
    body = ""
    for wk in weeks:
        body += "<tr>" + "".join(
            _cell(d, days.get(d, []), month_name, d != 0, today_num) for d in wk
        ) + "</tr>"

    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'width="560" style="width:560px;border-collapse:collapse;'
        f'table-layout:fixed;margin:0 0 6px 0">'
        f'{head}{dow}{body}</table>'
        f'<div style="font-family:{BODY};font-size:11px;color:#6b6b63;'
        f'padding:0 0 14px 0">Tap any event to open it on the radar.</div>'
    )


if __name__ == "__main__":
    y, m = target_month()
    print(render(y, m))
