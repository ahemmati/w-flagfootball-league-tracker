# 🏈 Flag Football Tracker

A Streamlit app for tracking playing time and stats during and across a youth
flag football season, built for the sideline on a phone. It's designed around
two specific rules from the Mt. Bethel W League rule sheet:

1. **Every player must play an equal amount of time.**
2. **Every player must run the ball or play QB for at least one snap, every game.**

Both are hard to track from memory while you're also coaching 7-year-olds, so
the app tracks them live and tells you who still needs a turn.

## Features

**⚖️ Equal Play Rule Check** — every player is listed in a tap-friendly grid.
Anyone who hasn't had their mandatory quarterback or running back play yet is
highlighted in **red (Needs Touch)**; once they've had it they turn green. The
app tracks this for every game so you can confirm each one is **Compliant**.
Tapping `QB` or `RUN` logs the mandatory play; `SNAP` logs field time only,
which counts toward equal playing time but deliberately does *not* satisfy the
rule.

**⏱️ Active Play Clock** — a large, interactive 35-second play clock built for
mobile screens. It turns **red below 5 seconds** to help you avoid the 3-yard
"Delay of Game" penalty. It runs in the browser and remembers where it is, so
it keeps ticking while you tap around the rest of the page.

**🟢 Game State & Timeouts** — tap to track your **2 timeouts per half**, and
switch to the 2nd half in one tap. Each half keeps its own count, so the 2nd
half automatically starts with a fresh 2 (and going back to the 1st half still
shows what you actually spent there).

**📋 Export Game Data** — one tap downloads a clean CSV of all player touches
and snaps, at the end of a game or any time, so you can review season stats in
a spreadsheet.

## Roster & schedule

The roster and the season schedule are seeded automatically on first run:

| Date | Time | Opponent |
|---|---|---|
| Sat Aug 29, 2026 | 11:00 AM | W2 |
| Sat Sep 12, 2026 | 11:00 AM | W3 |
| Thu Sep 17, 2026 | 5:15 PM | W6 |
| Sat Oct 3, 2026 | 9:00 AM | W1 |
| Sat Oct 10, 2026 | 9:00 AM | W4 |
| Sat Oct 17, 2026 | 11:00 AM | W2 |
| Sat Oct 24, 2026 | 9:00 AM | W1 |
| Sat Oct 31, 2026 | 11:00 AM | W4 |

Players: Ryan, Aidin, Rhett, Jacob, Patrick, Walker, Marshall, Lincoln, Julian.

You can **add** players and games at any time from the Roster page. There is
intentionally **no way to delete a player** — snap history points at the
roster, so removing someone would take their season stats with them. Seeding
is idempotent: it matches players by name and games by (date, opponent), so
restarting the app never creates duplicates or overwrites what you've logged.

## Quick start (local, in VS Code)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

That opens the app at `http://localhost:8501`. To use it on your phone on the
sideline, run it on your laptop and open the **Network URL** Streamlit prints,
or deploy it to Streamlit Community Cloud.

A local file, `flagfootball.db` (SQLite), holds all your data — it's gitignored,
so it stays on your machine and never gets pushed.

## How it's organized

```
app.py                          # Home: roster + schedule
pages/1_🏈_Game_Day.py          # Live in-game tracking (the main sideline screen)
pages/2_📊_Season_Dashboard.py  # Season-wide fairness, stats, compliance per game
pages/3_📋_Export.py            # Per-game and season CSV exports
ui.py                           # Shared styling + the play clock component
data_store.py                   # ALL database logic — nothing else touches SQLite
```

`data_store.py` is deliberately the only file that knows it's SQLite. If you
outgrow it, you rewrite the functions in that one file and the page files don't
change at all.

## A note on deploying

If you deploy to Streamlit Community Cloud, the SQLite file lives on ephemeral
disk and **can reset on redeploy**. Download your CSVs after each game (the
Export page) until you wire `data_store.py` up to a persistent backend such as
Google Sheets, Supabase, or Postgres.
