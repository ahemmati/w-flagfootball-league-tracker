# Flag Football Tracker

A minimal Streamlit app for tracking playing time and stats during and across
a youth flag football season, built around two specific rules from the Mt.
Bethel W-League rule sheet:

1. **Every player must play an equal amount of time.**
2. **Every player must run the ball or play QB for at least one snap, every game.**

Both are hard to track by memory while you're also coaching 7-year-olds. This
app logs a "snap" every time you tap **Log Play**, and flags live, during the
game, who's behind on playing time or still needs a QB/Runner turn.

## Quick start (local, in VS Code)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

That opens the app at `http://localhost:8501`. A local file, `flagfootball.db`
(SQLite), holds all your data — it's gitignored, so it stays on your machine
and never gets pushed.

## How it's organized

```
app.py                          # Home page: roster + game management
pages/1_🏈_Game_Day.py          # Live in-game tracking (the main screen you'll use)
pages/2_📊_Season_Dashboard.py  # Season-wide fairness + stats
pages/3_📋_Export.py            # CSV backups + end-of-season summary
data_store.py                   # ALL database logic lives here — nothing else touches SQLite directly
```

`data_store.py` is deliberately the only file that knows it's SQLite. If you
outgrow it (see below), you rewrite the functions in that one file and the
three page files don't change at all.

## Using it on game day

1. On the home page, make sure your roster and the game are entered.
2. Go to **Game Day**, pick the game and half.
3. Check off who's on the field, pick the QB and (if it's a run play) the
   runner, tap **Log Play**. Repeat each play.
4. The live status panel below tells you in real time who still needs a
   QB/Runner snap and who's falling behind on total snaps — that's your cue
   for who to rotate in next.
5. At the end, punch in the final score.

## ⚠️ About persistence — read this before relying on it for a real season

This currently stores data in a local SQLite file. That's great for testing
in VS Code, but if you deploy this to **Streamlit Community Cloud**, the
disk is not guaranteed to survive a redeploy (e.g. every time you push new
code, the database can reset). Two ways to handle that:

- **Cheap insurance, zero setup:** use the **Export** page to download CSVs
  after every game. Worst case you re-enter a game's worth of data, not a
  season's.
- **The real fix:** swap the backend in `data_store.py` from SQLite to
  Google Sheets (free, and lets you eyeball raw data without opening the
  app). This is a contained change — swap out `get_conn()` and the raw SQL
  in each function for `gspread` calls, keep the same function signatures.
  Ask Claude Code to do this once the game-day workflow feels right; no
  reason to set up a Google Cloud service account before you know the app
  is the one you want.

## Ideas for next iterations (hand these to Claude Code as you go)

- Defense-side tracking is already wired into the schema (`side` column) but
  the Game Day UI doesn't surface a separate defensive rule check yet — could
  add "played both sides" as a season stat.
- A "typical lineup" quick-select (save common groups of 7 so you're not
  tapping the same names in every play).
- Flag-pull counter as a defensive stat, for a "top tacklers" end-of-season
  shoutout alongside the QB/Runner/TD ones already there.
- If you want other coaches using their *own* copy: this whole folder is
  designed to be forked — each coach clones it, gets their own local
  `flagfootball.db`, and can deploy their own instance to Streamlit Cloud
  under their own account. No shared login or multi-tenant logic needed for
  that.
