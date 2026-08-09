# BAWA Fight Radar — weekly fight email

Emails Jack, Garry and Jagpreet every **Friday 10am Sydney** with the week's
UFC and boxing, times converted to Sydney.

## Setup (one time, ~5 minutes)

1. Create a **private** repo on github.com and upload these files
   (keep the `.github/workflows/` folder structure exactly).
2. Repo → **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `GMAIL_APP_PASSWORD`
   - Value: your 16-character Google app password, **spaces removed**
3. Done. It runs itself every Friday.

## Test it now

Repo → **Actions** tab → "BAWA Fight Radar" → **Run workflow**.
An email should arrive within a minute or two. If it fails, the log tells you why —
the usual culprit is the app password (check the spaces are stripped).

## How it works

- `send_fights.py` pulls UFC/MMA events from ESPN's public feed (no key needed),
  reads boxing from `boxing.json`, converts everything to Sydney time, and emails
  via Gmail SMTP (port 465 SSL).
- Scheduled twice (10am + 11am Sydney) because GitHub sometimes skips scheduled
  runs; a `.last_sent` marker stops a double-send.
- It **refuses to send an empty email** — no fixtures, no email, run marked failed.
- AU broadcast info only appears when it's reliable (UFC PPV → Main Event $59.95,
  UFC Fight Night → Paramount+, or whatever is set in `boxing.json`). Blank means
  unconfirmed — deliberately never guessed.

## Updating boxing

No reliable free boxing API exists, so `boxing.json` is the source of truth.
Edit it on github.com (pencil icon) when fights are announced — or ask Claude
each week for the current list. Each entry:

```json
{
  "name": "Fighter A vs Fighter B",
  "promotion": "Matchroom",
  "date_utc": "2026-08-29T21:00:00Z",
  "venue": "O2 Arena, London",
  "fights": ["Main event (title)", "Co-feature"],
  "watch_au": "DAZN"
}
```

`date_utc` is the main-event start in UTC (Sydney is UTC+10 winter, +11 summer).
Leave `watch_au` as `""` if the Australian broadcaster isn't confirmed.
