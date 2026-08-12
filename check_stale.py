#!/usr/bin/env python3
"""
Weekly upkeep nag for the hand-maintained Other Action tab.

The Fights and Panthers tabs rebuild themselves from live feeds. Monster trucks
and motorsport have no feed worth trusting, so that tab is curated by hand — and
the failure mode is silence: it quietly empties out and nobody notices.

This reads the dates already in index.html and emails a reminder when the tab is
running low, listing what is left. It says nothing when there is plenty ahead.
"""
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from send_fights import SYD, send

PAGE = "index.html"
WARN_WEEKS = 6          # nag once the last event is closer than this
WARN_COUNT = 3          # or once fewer than this many remain


def upcoming():
    page = open(PAGE).read()
    pane = page.split('id="pane-other"', 1)[-1].split("<!-- /pane-other -->", 1)[0]
    now = datetime.now(timezone.utc)
    out = []
    for row in re.findall(r"<tr[^>]*data-ends=\"([^\"]+)\"[^>]*>(.*?)</tr>", pane, re.S):
        ends, body = row
        try:
            when = datetime.fromisoformat(ends)
        except ValueError:
            continue
        if when < now:
            continue
        name = re.search(r'<span class="ev">(.*?)</span>', body, re.S)
        out.append((when, re.sub(r"<[^>]+>", "", name.group(1)).strip() if name else "(unnamed)"))
    return sorted(out)


def main():
    events = upcoming()
    horizon = datetime.now(timezone.utc) + timedelta(weeks=WARN_WEEKS)

    if events and len(events) >= WARN_COUNT and events[-1][0] > horizon:
        print(f"Other Action healthy: {len(events)} events, last is "
              f"{events[-1][0].astimezone(SYD):%d %b %Y} — no reminder sent")
        return

    rows = "".join(
        f'<tr><td style="padding:6px 12px 6px 0">{w.astimezone(SYD):%a %d %b %Y}</td>'
        f'<td style="padding:6px 0">{n}</td></tr>'
        for w, n in events
    ) or '<tr><td colspan="2" style="padding:6px 0"><b>Nothing left at all.</b></td></tr>'

    why = ("it is now empty" if not events
           else f"only {len(events)} event{'s' if len(events) != 1 else ''} remain"
                if len(events) < WARN_COUNT
                else f"the last one is {events[-1][0].astimezone(SYD):%d %b}, inside {WARN_WEEKS} weeks")

    html = f"""<html><body style="font-family:Arial,Helvetica,sans-serif;color:#1b1b1b">
      <p style="font-family:'Arial Narrow',Arial;font-size:22px;font-weight:bold;text-transform:uppercase">
        <span style="color:#d20a0a">BAWA</span> Radar · Upkeep</p>
      <p>The <b>Other Action</b> tab needs a top-up — {why}.</p>
      <p>Monster trucks and motorsport have no live feed, so this tab is the one
         part of the radar that does not refresh itself. The Fights and Panthers
         tabs are fine — they rebuild from their feeds every morning.</p>
      <p><b>Still listed:</b></p>
      <table>{rows}</table>
      <p>Ask Claude to top it up, or edit the Other Action table in
         <code>index.html</code> directly.</p>
      <hr><p style="font-size:12px;color:#999">Sent because the radar checks its
         own shelf life every Monday.</p>
    </body></html>"""

    if not os.environ.get("MAIL_TO"):
        print("no MAIL_TO set — would have warned:", why)
        sys.exit(0)
    send("BAWA Radar — Other Action tab needs a top-up", html)
    print("reminder sent:", why)


if __name__ == "__main__":
    main()
