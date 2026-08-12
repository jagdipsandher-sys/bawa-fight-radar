#!/usr/bin/env python3
"""
Rebuilds the Fights tab of index.html so the radar always shows a ROLLING
FOUR WEEKS, rather than a hand-typed list that runs dry after a month.

  UFC / MMA : ESPN's public JSON feed — the same one the Friday email uses
  Boxing    : boxing.json in this repo
  Photos    : photos.json  (surname -> headshot; missing ones show initials)
  Flags     : aussies.json (surname -> AU/NZ flag + badge)

Only the blocks between the BUILD: markers are touched. The Other Action and
Panthers tabs are hand-maintained and are left exactly as they are.

Run it as often as you like — it is idempotent, and it rewrites nothing if the
generated block has not changed, so it will not churn the git history.
"""
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from send_fights import SYD, au_watch, fetch_ufc, load_boxing

WEEKS_AHEAD = 4
PAGE = "index.html"

WATCH_URL = {
    "paramount+": "https://www.paramountplus.com/au/",
    "main event": "https://www.mainevent.com.au/",
    "dazn": "https://www.dazn.com/",
    "kayo": "https://kayosports.com.au/",
    "stan": "https://www.stan.com.au/sport",
}


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return default


PHOTOS = {k.lower(): v for k, v in load("photos.json", {}).items() if not k.startswith("_")}
FLAGS_RAW = load("aussies.json", {})
FLAGS = {n.lower(): ("🇦🇺" if cc == "AU" else "🇳🇿")
         for cc, names in FLAGS_RAW.items() if cc != "_comment" for n in names}


def esc(t):
    return html.escape(str(t), quote=True)


def initials(name):
    bits = [b for b in re.split(r"[\s'-]+", name.strip()) if b]
    return (bits[0][0] + bits[-1][0]).upper() if len(bits) > 1 else (name[:2] or "??").upper()


def photo_for(name):
    low = name.lower()
    for key, url in PHOTOS.items():
        if key in low:
            return url
    return None


def flag_for(name):
    low = name.lower()
    for key, flag in FLAGS.items():
        if key in low:
            return flag
    return ""


def watch_url(watch):
    low = (watch or "").lower()
    for key, url in WATCH_URL.items():
        if key in low:
            return url
    return ""


def slug(ev):
    base = re.sub(r"[^a-z0-9]+", "", ev["name"].lower())[:22]
    return f"{base or 'event'}{ev['when_utc']:%m%d}"


def syd(dt):
    return dt.astimezone(SYD)


def day_label(dt):
    d = syd(dt)
    return d.strftime("%a %-d %b")


def time_label(dt):
    d = syd(dt)
    return d.strftime("%-I:%M%p").lower().replace(":00", "")


def ends_at(ev):
    """Roughly when the broadcast is over — after this the event drops off."""
    hours = 6 if ev["sport"].startswith("UFC") else 4
    return (ev["when_utc"] + timedelta(hours=hours)).astimezone(SYD).isoformat()


def is_ppv(ev):
    return "ppv" in (ev.get("watch") or "").lower() or "main event" in (ev.get("watch") or "").lower()


def order_fights(ev):
    """Make sure the real headliner is first.

    Reversing ESPN's running order usually does it, but the event name is the
    reliable signal — "UFC 330: Makhachev vs Machado Garry" names its own main
    event — so promote the bout whose surnames both appear in the title.
    """
    title = ev["name"].lower()
    for i, bout in enumerate(ev["fights"]):
        parts = re.split(r"\s+vs\.?\s+", bout)
        if len(parts) == 2 and all(p.strip().split()[-1].lower() in title for p in parts if p.strip()):
            ev["fights"].insert(0, ev["fights"].pop(i))
            break
    return ev


def fighters(ev):
    """Names in the headline bout, for photos and flags."""
    if not ev["fights"]:
        return []
    return [n.strip() for n in re.split(r"\s+vs\.?\s+", ev["fights"][0], maxsplit=1)]


def thumbs_html(ev, big=False):
    names = fighters(ev)
    if not names:
        return ""
    out = []
    for i, n in enumerate(names[:2]):
        flag = flag_for(n)
        cls = " class=\"oz\"" if flag and not big else ""
        url = photo_for(n)
        if big and i == 1:
            out.append('<span class="vs">VS</span>')
        if url:
            out.append(f'<img{cls} src="{esc(url)}" alt="{esc(n)}" onerror="imgFail(this,\'{initials(n)}\')">')
        else:
            out.append(f'<span class="av{" oz" if flag and not big else ""}">{initials(n)}</span>')
    wrap = "faces" if big else "thumbs"
    return f'<{"div" if big else "span"} class="{wrap}">{"".join(out)}</{"div" if big else "span"}>'


def bout_line(bout):
    """Add flags to a 'A vs B' string."""
    parts = re.split(r"(\s+vs\.?\s+)", bout)
    return "".join(p + (f' <span class="flag">{flag_for(p)}</span>' if flag_for(p) else "")
                   if i % 2 == 0 else p for i, p in enumerate(parts))


def aussie_badge(ev):
    hits = [b for b in ev["fights"] if flag_for(b)]
    if not hits:
        return ""
    return ' <span class="badge aus">Aussie / NZ on the card</span>'


def row_html(ev):
    cid = slug(ev)
    tag = "u" if ev["sport"].startswith("UFC") else "b"
    tagtxt = "UFC" if tag == "u" else "Box"
    ppv = is_ppv(ev)
    badge = '<span class="badge ppv">Pay-Per-View</span>' if ppv else '<span class="badge fn">Fight Night</span>'
    sub = bout_line(ev["fights"][0]) if ev["fights"] else "Card to be announced"
    if len(ev["fights"]) > 1:
        sub += " · plus " + str(len(ev["fights"]) - 1) + " more bouts"
    watch = ev.get("watch") or ""
    url = watch_url(watch)
    buy = (f'<a class="mini buy" href="{esc(url)}">{"Buy PPV" if ppv else "Watch"} · {esc(watch.split("(")[0].strip()[:22])}</a>'
           if url else '<span class="badge tbc">AU Broadcaster TBC</span>')
    venue = ev.get("venue") or ""
    return f"""      <tr{' class="big"' if ppv else ''} data-sport="{'ufc' if tag == 'u' else 'box'}" data-ends="{ends_at(ev)}" data-card="{cid}">
        <td class="d">{day_label(ev['when_utc'])}<small>from {time_label(ev['when_utc'])}</small></td>
        <td><span class="sporttag {tag}">{tagtxt}</span></td>
        <td>{thumbs_html(ev)}<span class="ev">{esc(ev['name'])}</span> {badge}{aussie_badge(ev)}<br><span class="sub">{sub}</span></td>
        <td>{esc(venue)}</td>
        <td>{buy}<button class="mini" onclick="openCard('{cid}')">Full Card</button><button class="mini" onclick="addCal('{cid}')">+ Cal</button></td>
      </tr>"""


def hero_html(ev, sport_label):
    cid = slug(ev)
    ppv = is_ppv(ev)
    badge = '<span class="badge ppv">Pay-Per-View</span>' if ppv else '<span class="badge fn">Fight Night</span>'
    watch = ev.get("watch") or ""
    url = watch_url(watch)
    btn = (f'<a class="btn red" href="{esc(url)}">{"Buy PPV" if ppv else "Watch"} · {esc(watch.split("(")[0].strip()[:22])}</a>'
           if url else '<span class="badge tbc">AU Broadcaster TBC</span>')
    head = bout_line(ev["fights"][0]) if ev["fights"] else "Card to be announced"
    bullets = "".join(f"<li>{bout_line(b)}</li>" for b in ev["fights"][1:4])
    faces = thumbs_html(ev, big=True)
    return f"""    <div class="card" data-slot="{'ufc' if ev['sport'].startswith('UFC') else 'box'}" data-ends="{ends_at(ev)}">
      <div class="sport">{esc(sport_label)} &nbsp;{badge}{aussie_badge(ev)} <span class="badge soon"><span class="cd" data-until="{syd(ev['when_utc']):%Y-%m-%d}"></span></span></div>
      {faces}
      <div class="inner">
        <div class="fight hd">{esc(ev['name'])}
          <small>{head}</small>
        </div>
        <div class="when">{day_label(ev['when_utc'])} · <span class="t">From {time_label(ev['when_utc'])} AEST</span></div>
        <div class="meta">{esc(ev.get('venue') or '')}{' · ' if ev.get('venue') else ''}{esc(watch) or 'AU broadcaster not confirmed'}</div>
        {'<ul class="mc">' + bullets + '</ul>' if bullets else ''}
        <div class="btns">
          {btn}
          <button class="btn ghost" onclick="openCard('{cid}')">Full Card</button>
          <button class="btn ghost" onclick="addCal('{cid}')">+ Calendar</button>
        </div>
      </div>
    </div>"""


def card_js(ev):
    cid = slug(ev)
    start = ev["when_utc"]
    end = start + timedelta(hours=3)
    bouts = ",".join(
        '["{}","{}"{}]'.format(
            b.replace('"', "'"),
            "Main Event" if i == 0 else "",
            ",1" if i == 0 or flag_for(b) else "",
        )
        for i, b in enumerate(ev["fights"])
    ) or '["Card to be announced",""]'
    loc = (ev.get("venue") or "") + (" · " if ev.get("venue") else "") + (ev.get("watch") or "watch at home")
    when = f"{day_label(start)} · from {time_label(start)} AEST" + (f" · {ev['venue']}" if ev.get("venue") else "")
    return f"""  {cid}: {{
    emoji:"🥊",
    cal:{{s:"{start:%Y-%m-%dT%H:%M:%S}Z",e:"{end:%Y-%m-%dT%H:%M:%S}Z",loc:{json.dumps(loc)}}},
    title:{json.dumps(ev['name'])},
    when:{json.dumps(when)},
    link:{json.dumps(ev.get('link') or ('https://www.ufc.com/events' if ev['sport'].startswith('UFC') else 'https://www.dazn.com/'))},
    secs:[{{h:"Card as announced",b:[{bouts}]}}],
    note:"Card built automatically from the live fixture feed — bout order can change during fight week."
  }}"""


def splice(page, marker, block):
    pat = re.compile(rf"(<!--BUILD:{marker}-->|/\*BUILD:{marker}\*/).*?(<!--/BUILD:{marker}-->|/\*/BUILD:{marker}\*/)", re.S)
    if not pat.search(page):
        sys.exit(f"marker {marker} not found in {PAGE}")
    return pat.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), page, count=1)


def main():
    now = datetime.now(timezone.utc)
    end = now + timedelta(weeks=WEEKS_AHEAD)

    events = fetch_ufc(now, end, limit=16) + load_boxing(now, end)
    events = [e for e in events if now <= e["when_utc"] <= end]
    events.sort(key=lambda e: e["when_utc"])
    for e in events:
        e.setdefault("watch", "")
        if e["sport"].startswith("UFC") and not e["watch"]:
            e["watch"] = au_watch(e["name"])
        order_fights(e)

    if not events:
        sys.exit("no events in the next four weeks — refusing to blank the radar")

    ufc = [e for e in events if e["sport"].startswith("UFC")]
    box = [e for e in events if not e["sport"].startswith("UFC")]

    heroes = []
    if ufc:
        heroes.append(hero_html(ufc[0], "UFC"))
    if box:
        heroes.append(hero_html(box[0], box[0]["sport"]))
    if len(heroes) == 1:                      # keep the two-up grid balanced
        heroes.append(hero_html(events[1], events[1]["sport"]) if len(events) > 1 else "")

    page = open(PAGE).read()
    before = page
    page = splice(page, "FIGHT-HERO", "\n".join(h for h in heroes if h))
    page = splice(page, "FIGHT-ROWS", "\n".join(row_html(e) for e in events))
    page = splice(page, "FIGHT-CARDS", ",\n".join(card_js(e) for e in events))

    if page == before:
        print(f"radar already current — {len(events)} events in the next {WEEKS_AHEAD} weeks")
        return

    with open(PAGE, "w") as f:
        f.write(page)
    print(f"rebuilt {PAGE}: {len(events)} events to {syd(end):%a %d %b} "
          f"({len(ufc)} UFC, {len(box)} boxing)")


if __name__ == "__main__":
    main()
