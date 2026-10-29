#!/usr/bin/env python3
"""
Builds the month banner that sits at the top of the calendar in the Friday
email.

WHY A PRE-RENDERED FILE
The banner is HTML and CSS rendered to a JPEG by a headless browser. The
weekly send runs in GitHub Actions with no browser, so the banners for the
months ahead are rendered here, committed, and simply picked by name at send
time. That keeps the email build dependency free and means a bad render can
never take the Friday email down.

WHAT IS AND IS NOT IN THE IMAGE
Only the things that cannot go stale: the month, the year and the branding.
The main event line is deliberately NOT baked in, because fight cards get
announced and changed all month. That line is live HTML underneath the image,
so it is always right and, unlike a picture, it can be tapped.

Run:  python make_banner.py            12 months from this month
      python make_banner.py 2026 11    one month
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SYD = ZoneInfo("Australia/Sydney")
OUT = Path("img")
PHOTO = Path("img/hero-source.jpg")      # the imagery behind the type

TPL = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Oswald:wght@500;700&display=swap" rel="stylesheet">
<style>
 html,body{{margin:0}}
 .w{{position:relative;width:1120px;height:400px;overflow:hidden;
    background:linear-gradient(180deg,#ffffff 0%,#f0efed 62%,#e4e3e0 100%)}}
 /* Jack asked for the imagery about ten per cent more visible, so the photo
    is lifted from .30 to .40 and the white wash over it eased back. */
 .photo{{position:absolute;left:0;top:0;width:1120px;height:400px;overflow:hidden;opacity:.40}}
 /* hero-source.jpg is already cropped to the imagery, so it simply fills the
    banner: full width, centred vertically. */
 .photo img{{position:absolute;width:1120px;height:auto;left:0;top:-156px;
   filter:brightness(1.62) contrast(.80) saturate(.62) grayscale(.30)}}
 .wash{{position:absolute;inset:0;background:linear-gradient(180deg,
   rgba(255,255,255,.70),rgba(255,255,255,.34) 45%,rgba(255,255,255,.82))}}
 .rule{{position:absolute;left:0;right:0;top:0;height:9px;background:#d20a0a}}
 .script{{position:absolute;left:0;right:0;top:52px;text-align:center;font-family:'Oswald',sans-serif;
   font-weight:500;font-size:18px;letter-spacing:9px;text-transform:uppercase;color:#d20a0a}}
 .month{{position:absolute;left:0;right:0;top:86px;text-align:center;font-family:'Anton',sans-serif;
   font-size:140px;letter-spacing:2px;color:#121214;line-height:.92}}
 .yr{{position:absolute;left:0;right:0;top:238px;text-align:center;font-family:'Anton',sans-serif;
   font-size:24px;letter-spacing:16px;color:#6f6f75}}
 .lock{{position:absolute;left:0;right:0;bottom:34px;text-align:center;font-family:'Anton',sans-serif;
   font-size:20px;letter-spacing:5px;color:#121214}}
 .lock span{{color:#d20a0a}}
</style></head><body>
<div class="w">
  <div class="photo"><img src="{photo}"></div>
  <div class="wash"></div>
  <div class="rule"></div>
  <div class="script">Whats on this month</div>
  <div class="month">{month}</div>
  <div class="yr">{year}</div>
  <div class="lock">BAWA<span> FIGHT RADAR</span></div>
</div></body></html>"""

SHOT = """import {{ chromium }} from 'playwright';
const b = await chromium.launch({{ executablePath: '/opt/pw-browsers/chromium' }});
const p = await b.newPage({{ viewport:{{width:1120,height:400}} }});
await p.goto('file://{html}');
await p.evaluate(()=>document.fonts.ready);
await p.waitForTimeout(1500);
await p.locator('.w').screenshot({{ path:'{out}', type:'jpeg', quality:84 }});
await b.close();
"""


def months(n=12, start=None):
    d = start or datetime.now(SYD)
    out = []
    y, m = d.year, d.month
    for _ in range(n):
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def build(year, month):
    name = datetime(year, month, 1).strftime("%B").upper()
    # the html and the render script both live beside node_modules, because
    # node resolves "playwright" relative to the script, not the cwd
    html = Path(f"_banner_{year}{month:02d}.html")
    out = OUT / f"month-{year}{month:02d}.jpg"
    html.write_text(TPL.format(photo=PHOTO.resolve(), month=name, year=year))
    shot = Path("_shot_banner.mjs")
    shot.write_text(SHOT.format(html=html.resolve(), out=out.resolve()))
    try:
        subprocess.run(["node", str(shot)], check=True)
    finally:
        shot.unlink(missing_ok=True)
        html.unlink(missing_ok=True)
    print(f"  {out}  ({out.stat().st_size // 1024} KB)")


def main():
    OUT.mkdir(exist_ok=True)
    if not PHOTO.exists():
        sys.exit(f"missing {PHOTO} — the background imagery")
    if len(sys.argv) == 3:
        build(int(sys.argv[1]), int(sys.argv[2]))
        return
    print("rendering month banners:")
    for y, m in months(12):
        build(y, m)


if __name__ == "__main__":
    main()
