#!/usr/bin/env python3
"""
Gatekeeper for index.html.

Two things write to this page without a human reading the diff: the nightly
builders, and the weekly Claude session that re-researches the Other Action tab.
This is what stops either of them shipping a broken page — it runs on every push
to main and fails the build loudly.

Checks, cheapest first. No browser needed.
"""
import html.parser
import json
import re
import subprocess
import sys
import tempfile

PAGE = "index.html"
MARKERS = ["FIGHT-HERO", "FIGHT-ROWS", "FIGHT-CARDS", "NRL-HERO", "NRL-ROWS", "NRL-CARDS"]
problems = []


def fail(msg):
    problems.append(msg)


page = open(PAGE).read()


# 1. the generated blocks must still be addressable
for m in MARKERS:
    if not re.search(rf"(<!--BUILD:{m}-->|/\*BUILD:{m}\*/)", page) or \
       not re.search(rf"(<!--/BUILD:{m}-->|/\*/BUILD:{m}\*/)", page):
        fail(f"build marker {m} is missing — the builders would fail or overwrite the wrong region")


# 2. tags must balance, or tabs silently swallow each other
class Balance(html.parser.HTMLParser):
    VOID = {"meta", "link", "br", "img", "input", "hr", "source", "area"}

    def __init__(self):
        super().__init__()
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack:
            fail(f"stray closing </{tag}>")
        elif self.stack[-1] != tag:
            fail(f"mismatched tag: expected </{self.stack[-1]}>, got </{tag}>")
        else:
            self.stack.pop()


b = Balance()
b.feed(re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S))
if b.stack:
    fail(f"unclosed tags: {b.stack}")


# 3. the JavaScript has to actually parse
scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
if not scripts:
    fail("no inline script found — the page would not prune past events")
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
    f.write("\n".join(scripts))
    tmp = f.name
r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
if r.returncode:
    fail("JavaScript syntax error:\n" + r.stderr.strip())


# 4. every event needs a parseable finish time, or it never expires
for ends in re.findall(r'data-ends="([^"]*)"', page):
    if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$", ends):
        fail(f"data-ends is not an ISO timestamp with a Sydney offset: {ends!r}")

rows = re.findall(r"<tr\b([^>]*)>", page)
for attrs in rows:
    if "data-ends" in attrs and "data-sport" not in attrs:
        fail(f"row has data-ends but no data-sport, so it can never feed a hero: <tr{attrs}>")


# 5. no button may open a card that does not exist
ids = set(re.findall(r"^\s{2}([A-Za-z_][\w]*):\s*\{", page, re.M))
for ref in set(re.findall(r"(?:openCard|addCal)\('([^']+)'\)", page)):
    if ref not in ids:
        fail(f"openCard/addCal references '{ref}', which is not defined in any CARDS object")


# 6. the tabs themselves must be intact
for pane in ["pane-fights", "pane-other", "pane-panthers"]:
    if f'id="{pane}"' not in page:
        fail(f"tab {pane} has gone missing")


if problems:
    print(f"index.html FAILED {len(problems)} check(s):\n")
    for p in problems:
        print("  ✗", p)
    sys.exit(1)

print(f"index.html OK — {len(rows)} rows, {len(ids)} cards, {len(scripts)} script blocks, "
      f"all {len(MARKERS)} build markers intact")
