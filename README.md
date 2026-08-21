# 🏈 Silver Dogs — W-5 Flag Football Tracker

A Streamlit app for tracking playing time and stats during and across a youth
flag football season, built for the sideline on a phone. It's designed around
the Mt. Bethel W League (1st & 2nd Grade) rule sheet. Built for **W-5, the
Silver Dogs**. The two rules it actively tracks:

1. **Every player must play an equal amount of time.**
2. **Every player must run the ball or play QB for at least one snap, every game.**

Both are hard to track from memory while you're also coaching 7-year-olds, so
the app tracks them live and tells you who still needs a turn.

## Features

**⚖️ Equal Play Rule Check** — every player is listed in a tap-friendly grid.
Anyone who hasn't had their mandatory quarterback or running back play yet is
highlighted in **red (Needs Touch)**; once they've had it they turn green. The
app tracks this for every game so you can confirm each one is **Compliant**.
**Only two actions satisfy the rule: running the ball, or playing
quarterback.** Tapping `QB` or `RUN` logs it. `PLAY` logs field time only —
playing center, blocking, and catching a pass (including catching a
touchdown) count toward equal playing time but deliberately do *not* satisfy
the mandatory-involvement rule, so they leave a player red.

There is **no center snap** in W League — the QB starts the play already
holding the ball — so field time is counted in **plays**, never snaps.

**🏈 Scoring per player** — every player card has a button for each way the
rule sheet says you can score: `🏈 TD +6`, `TRY +1` (from the 3-yard line) and
`TRY +2` (from the 7). One tap credits the score to that player and updates
the scoreboard, and their touchdowns and points flow through to the live
stats, the season dashboard, and the CSV exports. It's scoring only: if he ran
it in, tap `RUN` as well, because scoring alone doesn't satisfy the QB/Run
rule.

A **safety** sits with the team-level scoring instead, because it credits the
defense rather than a player — and because the rule sheet never assigns it a
point value (see below).

**↩️ Undo and reset** — every player card has its own `↩` button that takes back
just that player's last entry — a play or a touchdown, whichever came last —
for when you tap the kid standing next to the right one. `Undo Last` steps back the most recent entry of any kind, and
`Reset this game's log` clears a single game behind a confirmation, scoped so
you can wipe a botched play log without losing a correct scoreboard.

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
a spreadsheet. Scoring plays and penalties export separately.

**🏆 Rule-accurate scoring** — tap to score: touchdown 6, try 1 point from the
3-yard line or 2 from the 7, safety 2. The running score is built from those
values rather than typed in, and a banner appears once either side is
3 touchdowns ahead (the mercy-rule margin).

**🛑 Penalties & downs** — every penalty from the rule sheet as a button, split
into 3-yard and 6-yard groups, plus a 1st-through-4th down tracker for the
four downs you get to reach the next 9-yard zone.

**📖 Full rules reference** — the complete rule sheet, on its own page, with a
quick-reference version in the sidebar of every page.

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

**Tap any game on the home page to open it directly on the Game Day tracker.**

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
pages/4_📖_Rules.py             # The full W League rule sheet
ui.py                           # Shared styling, the countdown clocks, rules sidebar
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

## One inconsistency in the rule sheet

The *Thirty-Five Second Clock (Rule Change)* section sets a **35-second** play
clock, but the *Delay of Game* penalty still describes "violation of the **25**
second clock." The "(Rule Change)" label suggests 35 is the current number and
the penalty text wasn't updated, so this app counts down from 35. Worth
confirming with your referee at the captains meeting.

## The safety has no stated point value

The rule sheet lists exactly two ways to score: a **touchdown (6)** and the
**try (1 point from the 3-yard line, 2 from the 7)**. A safety appears only in
the clock rules — *"Safety - starts on the snap"* — and is never assigned a
value. Under the NIRSA and NFHS rule books the sheet defers to, a safety is
worth 2, so that's this app's default, but the number is editable when you log
one. Worth settling at the captains meeting.
