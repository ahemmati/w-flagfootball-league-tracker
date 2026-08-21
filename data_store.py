"""
data_store.py
--------------
All database access lives here. Every other file in this app talks to the
database ONLY through these functions. That means if you outgrow SQLite later
(e.g. deploying to Streamlit Cloud for the season and you want data that
survives redeploys), you rewrite the guts of these functions to hit Google
Sheets / Supabase / whatever instead, and nothing in the UI pages has to change.

Rules this schema is built to answer, straight from the league rule sheet:
  - "Every player must play an equal amount of time" -> we track plays per
    player per game, so you can see imbalance as it happens, live.
    (W League has NO CENTER SNAP -- the QB starts the play already holding
    the ball -- so field time is counted in "plays", never "snaps".)
  - "Every player must either run the ball or play quarterback for at least
    one snap each game" -> every logged touch records the role, so the app can
    flag anyone who still needs their mandatory QB/Runner play.
  - "Two timeouts per half" -> tracked per half in game_state, so switching to
    the 2nd half resets the count automatically.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
import pandas as pd

DB_PATH = Path(__file__).parent / "flagfootball.db"

# ---------------------------------------------------------------------------
# League constants, straight from the Mt. Bethel W League (1st & 2nd) rule
# sheet. Anything the app enforces or displays traces back to a line in there.
# ---------------------------------------------------------------------------
TEAM_NAME = "Silver Dogs"
TEAM_CODE = "W-5"

PLAYERS_ON_FIELD = 7          # "two teams of seven players each"
HALVES = 2
HALF_LENGTH_MINUTES = 20      # "two, 20 minute halves"
HALFTIME_BREAK_MINUTES = 5
TIMEOUTS_PER_HALF = 2         # "two time outs per half"
TIMEOUT_SECONDS = 30          # "thirty (30) seconds in length"
PLAY_CLOCK_SECONDS = 35       # "Thirty-Five Second Clock: (Rule Change)"
DOWNS_PER_SERIES = 4          # "four consecutive downs" to reach the next zone
ZONE_YARDS = 9                # "four 9 yard zones"
END_ZONE_YARDS = 5
FIELD_WIDTH_YARDS = 27
FIELD_LENGTH_YARDS = 47
START_YARD_LINE = 7           # no kick-off; receiving team starts on its own 7
MERCY_RULE_TD_MARGIN = 3      # 3+ TDs ahead at the 2nd-half one-minute warning

# Scoring, and what each play is worth.
SCORING_PLAYS = {
    "Touchdown": 6,
    "Try — 1 pt (3 yd line)": 1,
    "Try — 2 pt (7 yd line)": 2,
    "Safety": 2,
}

# Penalties, split by the yardage the rule sheet assigns them.
PENALTIES_3YD = [
    "Off-side / Illegal Procedure",
    "False Start",
    "Delay of Game",
    "Flag Guarding / Stiff Arming",
    "Illegal Forward Pass",
]
PENALTIES_6YD = [
    "Tackling / Tripping / Holding",
    "Obstruction of Runner",
    "Illegal Screen Blocking",
    "Running Over a Player / Charging",
    "Roughing the Passer",
    "Personal Foul",
    "Pass Interference",
]

# The roster and schedule the season starts with. Seeding is idempotent: a
# player is matched on name, a game on (date, opponent), so re-running this
# never creates duplicates and never clobbers stats you've already logged.
SEED_PLAYERS = [
    "Ryan", "Aidin", "Rhett", "Jacob", "Patrick",
    "Walker", "Marshall", "Lincoln", "Julian",
]

# (date, kickoff time, opponent)
SEED_GAMES = [
    ("2026-08-29", "11:00 AM", "W2"),
    ("2026-09-12", "11:00 AM", "W3"),
    ("2026-09-17", "5:15 PM",  "W6"),
    ("2026-10-03", "9:00 AM",  "W1"),
    ("2026-10-10", "9:00 AM",  "W4"),
    ("2026-10-17", "11:00 AM", "W2"),
    ("2026-10-24", "9:00 AM",  "W1"),
    ("2026-10-31", "11:00 AM", "W4"),
]


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _columns(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_date TEXT NOT NULL,
                game_time TEXT,
                opponent TEXT,
                our_score INTEGER,
                their_score INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snaps (
                snap_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                half INTEGER NOT NULL,
                play_number INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                side TEXT NOT NULL DEFAULT 'offense',
                role TEXT,
                event TEXT,
                FOREIGN KEY (game_id) REFERENCES games(game_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        """)
        # One row per game holding the sideline state: which half you're in and
        # how many timeouts you've burned in each half.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_state (
                game_id INTEGER PRIMARY KEY,
                current_half INTEGER NOT NULL DEFAULT 1,
                timeouts_used_h1 INTEGER NOT NULL DEFAULT 0,
                timeouts_used_h2 INTEGER NOT NULL DEFAULT 0,
                current_down INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (game_id) REFERENCES games(game_id)
            )
        """)

        # Every score, so the running total is built from the rule book's
        # point values instead of being typed in by hand.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scoring_plays (
                score_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                half INTEGER NOT NULL,
                team TEXT NOT NULL,            -- 'us' or 'them'
                play_type TEXT NOT NULL,
                points INTEGER NOT NULL,
                player_id INTEGER,
                FOREIGN KEY (game_id) REFERENCES games(game_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS penalties (
                penalty_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                half INTEGER NOT NULL,
                team TEXT NOT NULL,            -- 'us' or 'them'
                name TEXT NOT NULL,
                yards INTEGER NOT NULL,
                FOREIGN KEY (game_id) REFERENCES games(game_id)
            )
        """)

        # --- migrations for databases created by an earlier version ---
        if "game_time" not in _columns(conn, "games"):
            conn.execute("ALTER TABLE games ADD COLUMN game_time TEXT")
        if "jersey_number" in _columns(conn, "players"):
            conn.execute("ALTER TABLE players DROP COLUMN jersey_number")
        if "current_down" not in _columns(conn, "game_state"):
            conn.execute(
                "ALTER TABLE game_state ADD COLUMN current_down INTEGER NOT NULL DEFAULT 1"
            )

    _seed()


def _seed():
    """Insert the starting roster and schedule if they aren't already there."""
    with get_conn() as conn:
        existing_players = {
            r[0].lower() for r in conn.execute("SELECT name FROM players")
        }
        for name in SEED_PLAYERS:
            if name.lower() not in existing_players:
                conn.execute(
                    "INSERT INTO players (name, active) VALUES (?, 1)", (name,)
                )

        existing_games = {
            (r[0], r[1]): r[2]
            for r in conn.execute("SELECT game_date, opponent, game_time FROM games")
        }
        for game_date, game_time, opponent in SEED_GAMES:
            key = (game_date, opponent)
            if key not in existing_games:
                conn.execute(
                    "INSERT INTO games (game_date, game_time, opponent) VALUES (?, ?, ?)",
                    (game_date, game_time, opponent),
                )
            elif not existing_games[key]:
                # Game row predates the schedule (or the game_time column) --
                # fill the kickoff time in without touching anything else.
                conn.execute(
                    "UPDATE games SET game_time = ? WHERE game_date = ? AND opponent = ?",
                    (game_time, game_date, opponent),
                )


# ---------- Players ----------
# Note: there is deliberately no delete_player(). Snap history references
# players, so removing one would silently orphan a season's worth of stats.

def add_player(name):
    name = name.strip()
    if not name:
        raise ValueError("Player name cannot be blank.")
    with get_conn() as conn:
        clash = conn.execute(
            "SELECT 1 FROM players WHERE lower(name) = lower(?)", (name,)
        ).fetchone()
        if clash:
            raise ValueError(f"{name} is already on the roster.")
        conn.execute("INSERT INTO players (name, active) VALUES (?, 1)", (name,))


def get_players(active_only=True):
    with get_conn() as conn:
        query = "SELECT player_id, name, active FROM players"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY player_id"
        return pd.read_sql_query(query, conn)


# ---------- Games ----------

def create_game(game_date, opponent, game_time=""):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO games (game_date, game_time, opponent) VALUES (?, ?, ?)",
            (str(game_date), (game_time or "").strip(), (opponent or "").strip()),
        )
        return cur.lastrowid


def get_games(ascending=True):
    order = "ASC" if ascending else "DESC"
    with get_conn() as conn:
        return pd.read_sql_query(
            f"SELECT * FROM games ORDER BY game_date {order}, game_id {order}", conn
        )


def update_game_score(game_id, our_score, their_score):
    with get_conn() as conn:
        conn.execute(
            "UPDATE games SET our_score = ?, their_score = ? WHERE game_id = ?",
            (our_score, their_score, game_id),
        )


# ---------- Live game state (half + timeouts) ----------

def get_game_state(game_id):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT current_half, timeouts_used_h1, timeouts_used_h2, current_down
               FROM game_state WHERE game_id = ?""",
            (game_id,),
        ).fetchone()
        if row is None:
            conn.execute("INSERT INTO game_state (game_id) VALUES (?)", (game_id,))
            row = (1, 0, 0, 1)
    return {
        "current_half": row[0],
        "timeouts_used_h1": row[1],
        "timeouts_used_h2": row[2],
        "current_down": row[3],
    }


def set_half(game_id, half):
    """
    Switch halves. Each half has its own timeout counter, so moving to the 2nd
    half shows a fresh 2 automatically -- and bouncing back to the 1st half
    still shows what you actually spent there, instead of wiping it.
    """
    get_game_state(game_id)  # make sure the row exists
    with get_conn() as conn:
        conn.execute(
            "UPDATE game_state SET current_half = ? WHERE game_id = ?",
            (half, game_id),
        )


def use_timeout(game_id, half):
    state = get_game_state(game_id)
    column = "timeouts_used_h1" if half == 1 else "timeouts_used_h2"
    if state[column] >= TIMEOUTS_PER_HALF:
        return False
    with get_conn() as conn:
        conn.execute(
            f"UPDATE game_state SET {column} = {column} + 1 WHERE game_id = ?",
            (game_id,),
        )
    return True


def reset_timeouts(game_id, half):
    get_game_state(game_id)
    column = "timeouts_used_h1" if half == 1 else "timeouts_used_h2"
    with get_conn() as conn:
        conn.execute(
            f"UPDATE game_state SET {column} = 0 WHERE game_id = ?", (game_id,)
        )


def timeouts_left(game_id, half):
    state = get_game_state(game_id)
    used = state["timeouts_used_h1"] if half == 1 else state["timeouts_used_h2"]
    return max(0, TIMEOUTS_PER_HALF - used)


# ---------- Snaps (the core "log a play" action) ----------

def get_next_play_number(game_id, half):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(play_number) FROM snaps WHERE game_id = ? AND half = ?",
            (game_id, half),
        ).fetchone()
        return (row[0] or 0) + 1


def log_touch(game_id, half, player_id, role, side="offense", event=None):
    """
    One tap on the sideline = one row. `role` is 'QB', 'Runner', or None for a
    plain snap where the kid was on the field but didn't handle the ball.
    """
    play_number = get_next_play_number(game_id, half)
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO snaps
               (game_id, half, play_number, player_id, side, role, event)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (game_id, half, play_number, player_id, side, role, event),
        )


def log_play(game_id, half, on_field_player_ids, qb_id=None, runner_id=None,
             side="offense", event=None, event_player_id=None):
    """
    Logs one play for a whole group. Every player on the field gets a snap row;
    qb_id / runner_id get role='QB' / role='Runner' on theirs.
    """
    play_number = get_next_play_number(game_id, half)
    with get_conn() as conn:
        for pid in on_field_player_ids:
            role = None
            if pid == qb_id:
                role = "QB"
            elif pid == runner_id:
                role = "Runner"
            row_event = event if (event and pid == event_player_id) else None
            conn.execute(
                """INSERT INTO snaps
                   (game_id, half, play_number, player_id, side, role, event)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (game_id, half, play_number, pid, side, role, row_event),
            )


def undo_last_snap(game_id):
    """Fat-finger insurance: drop the most recent row logged for this game."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT snap_id FROM snaps WHERE game_id = ? ORDER BY snap_id DESC LIMIT 1",
            (game_id,),
        ).fetchone()
        if row is None:
            return False
        conn.execute("DELETE FROM snaps WHERE snap_id = ?", (row[0],))
    return True


def get_game_snaps(game_id):
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT * FROM snaps WHERE game_id = ?", conn, params=(game_id,)
        )


# ---------- Compliance + summaries ----------

def get_game_summary(game_id):
    """
    Per-player snap counts and Equal Play Rule status for one game.

    'Needs Touch' is the league's mandatory-play rule: a player who has not
    played QB and has not carried the ball yet in this game. Those are the kids
    the Game Day grid paints red.
    """
    players = get_players(active_only=True)
    snaps = get_game_snaps(game_id)

    if players.empty:
        return pd.DataFrame()

    rows = []
    for _, p in players.iterrows():
        pid = int(p["player_id"])
        p_snaps = snaps[snaps["player_id"] == pid]
        qb = int((p_snaps["role"] == "QB").sum()) if not p_snaps.empty else 0
        run = int((p_snaps["role"] == "Runner").sum()) if not p_snaps.empty else 0
        rows.append({
            "player_id": pid,
            "Player": p["name"],
            "Plays": len(p_snaps),
            "QB Plays": qb,
            "Runner Plays": run,
            "Touches": qb + run,
            "Touchdowns": int((p_snaps["event"] == "Touchdown").sum()) if not p_snaps.empty else 0,
        })
    df = pd.DataFrame(rows)

    df["Met QB/Runner Rule"] = df["Touches"] > 0
    df["Needs Touch"] = ~df["Met QB/Runner Rule"]

    # Equal playing time: flag anyone more than one snap below the team average,
    # so you can even it out while there's still game left to do it in.
    avg_plays = df["Plays"].mean()
    df["Below Avg Plays"] = df["Plays"] < (avg_plays - 1)
    return df


def is_game_compliant(game_id):
    """True when every active player has their mandatory QB or Runner play."""
    summary = get_game_summary(game_id)
    if summary.empty:
        return False
    return bool(summary["Met QB/Runner Rule"].all())


def get_compliance_overview():
    """One row per game: how many players still need their mandatory touch."""
    games = get_games(ascending=True)
    rows = []
    for g in games.itertuples():
        summary = get_game_summary(g.game_id)
        if summary.empty or summary["Plays"].sum() == 0:
            status, needs = "Not started", []
        else:
            needs = summary[summary["Needs Touch"]]["Player"].tolist()
            status = "Compliant" if not needs else "Needs touches"
        rows.append({
            "Date": g.game_date,
            "Time": getattr(g, "game_time", "") or "",
            "Opponent": g.opponent,
            "Status": status,
            "Still Needs Touch": ", ".join(needs),
        })
    return pd.DataFrame(rows)


# ---------- Season-wide aggregation ----------

def get_season_summary():
    players = get_players(active_only=True)
    with get_conn() as conn:
        snaps = pd.read_sql_query("SELECT * FROM snaps", conn)

    if players.empty:
        return pd.DataFrame()

    rows = []
    for _, p in players.iterrows():
        pid = int(p["player_id"])
        p_snaps = snaps[snaps["player_id"] == pid] if not snaps.empty else snaps
        games_played = p_snaps["game_id"].nunique() if not p_snaps.empty else 0
        qb = int((p_snaps["role"] == "QB").sum()) if not p_snaps.empty else 0
        run = int((p_snaps["role"] == "Runner").sum()) if not p_snaps.empty else 0
        rows.append({
            "Player": p["name"],
            "Games Played": games_played,
            "Total Plays": len(p_snaps),
            "Avg Plays/Game": round(len(p_snaps) / games_played, 1) if games_played else 0,
            "QB Plays": qb,
            "Runner Plays": run,
            "Total Touches": qb + run,
            "Touchdowns": int((p_snaps["event"] == "Touchdown").sum()) if not p_snaps.empty else 0,
        })
    df = pd.DataFrame(rows)
    return df.sort_values("Total Plays", ascending=False)


# ---------- Export ----------

def get_game_export(game_id):
    """
    The per-game CSV: one row per player with their touches and snaps, plus the
    Equal Play Rule verdict. This is the 'tap once at the end of the game'
    download, and it's readable by anyone who opens it in a spreadsheet.
    """
    summary = get_game_summary(game_id)
    if summary.empty:
        return pd.DataFrame()

    games = get_games()
    game = games[games["game_id"] == game_id]
    game_date = game.iloc[0]["game_date"] if not game.empty else ""
    game_time = game.iloc[0].get("game_time", "") if not game.empty else ""
    if pd.isna(game_time):
        game_time = ""
    opponent = game.iloc[0]["opponent"] if not game.empty else ""

    out = summary[["Player", "Plays", "QB Plays", "Runner Plays",
                   "Touches", "Touchdowns"]].copy()
    out.insert(0, "Opponent", opponent)
    out.insert(0, "Time", game_time or "")
    out.insert(0, "Date", game_date)
    out["Equal Play Rule"] = summary["Met QB/Runner Rule"].map(
        {True: "Met", False: "NOT MET"}
    )
    return out.sort_values("Player")


def get_export_dataframes():
    with get_conn() as conn:
        players = pd.read_sql_query("SELECT * FROM players", conn)
        games = pd.read_sql_query("SELECT * FROM games", conn)
        snaps = pd.read_sql_query("SELECT * FROM snaps", conn)
    return players, games, snaps


def set_down(game_id, down):
    """Current down, 1 through 4 ('four consecutive downs' to the next zone)."""
    get_game_state(game_id)
    down = max(1, min(DOWNS_PER_SERIES, int(down)))
    with get_conn() as conn:
        conn.execute(
            "UPDATE game_state SET current_down = ? WHERE game_id = ?",
            (down, game_id),
        )


def next_down(game_id):
    """Advance a down; past 4th it wraps to 1st (turnover on downs / new series)."""
    state = get_game_state(game_id)
    nxt = state["current_down"] + 1
    set_down(game_id, 1 if nxt > DOWNS_PER_SERIES else nxt)


# ---------- Scoring ----------

def add_score(game_id, half, team, play_type, player_id=None):
    """Record a scoring play using the rule book's point value."""
    if play_type not in SCORING_PLAYS:
        raise ValueError(f"Unknown scoring play: {play_type}")
    points = SCORING_PLAYS[play_type]
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO scoring_plays
               (game_id, half, team, play_type, points, player_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (game_id, half, team, play_type, points, player_id),
        )
    _recompute_score(game_id)


def _recompute_score(game_id):
    """Keep games.our_score / their_score in step with the scoring plays."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT team, SUM(points) FROM scoring_plays WHERE game_id = ? GROUP BY team",
            (game_id,),
        ).fetchall()
        totals = {team: total for team, total in rows}
        conn.execute(
            "UPDATE games SET our_score = ?, their_score = ? WHERE game_id = ?",
            (totals.get("us", 0), totals.get("them", 0), game_id),
        )


def get_scoring_plays(game_id):
    with get_conn() as conn:
        return pd.read_sql_query(
            """SELECT s.score_id, s.half, s.team, s.play_type, s.points, p.name AS player
               FROM scoring_plays s LEFT JOIN players p ON p.player_id = s.player_id
               WHERE s.game_id = ? ORDER BY s.score_id""",
            conn, params=(game_id,),
        )


def get_score(game_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT team, SUM(points) FROM scoring_plays WHERE game_id = ? GROUP BY team",
            (game_id,),
        ).fetchall()
    totals = {team: total for team, total in rows}
    return int(totals.get("us", 0)), int(totals.get("them", 0))


def undo_last_score(game_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT score_id FROM scoring_plays WHERE game_id = ? ORDER BY score_id DESC LIMIT 1",
            (game_id,),
        ).fetchone()
        if row is None:
            return False
        conn.execute("DELETE FROM scoring_plays WHERE score_id = ?", (row[0],))
    _recompute_score(game_id)
    return True


def mercy_rule_in_effect(game_id):
    """
    True once either team leads by 3+ touchdowns. The rule only bites at the
    second-half one-minute warning, so this is an early heads-up, not a verdict.
    """
    us, them = get_score(game_id)
    return abs(us - them) >= MERCY_RULE_TD_MARGIN * SCORING_PLAYS["Touchdown"]


# ---------- Penalties ----------

def log_penalty(game_id, half, team, name):
    yards = 3 if name in PENALTIES_3YD else 6
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO penalties (game_id, half, team, name, yards)
               VALUES (?, ?, ?, ?, ?)""",
            (game_id, half, team, name, yards),
        )


def get_penalties(game_id):
    with get_conn() as conn:
        return pd.read_sql_query(
            """SELECT penalty_id, half, team, name, yards FROM penalties
               WHERE game_id = ? ORDER BY penalty_id""",
            conn, params=(game_id,),
        )


def undo_last_penalty(game_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT penalty_id FROM penalties WHERE game_id = ? ORDER BY penalty_id DESC LIMIT 1",
            (game_id,),
        ).fetchone()
        if row is None:
            return False
        conn.execute("DELETE FROM penalties WHERE penalty_id = ?", (row[0],))
    return True


def undo_last_play_for_player(game_id, player_id):
    """
    Remove the most recent play logged for one player. This is the fix for the
    common sideline mistake -- tapping the kid standing next to the right one.
    """
    with get_conn() as conn:
        row = conn.execute(
            """SELECT snap_id FROM snaps WHERE game_id = ? AND player_id = ?
               ORDER BY snap_id DESC LIMIT 1""",
            (game_id, player_id),
        ).fetchone()
        if row is None:
            return False
        conn.execute("DELETE FROM snaps WHERE snap_id = ?", (row[0],))
    return True


def game_log_counts(game_id):
    """What a reset would throw away, so the confirmation can spell it out."""
    with get_conn() as conn:
        plays = conn.execute(
            "SELECT COUNT(*) FROM snaps WHERE game_id = ?", (game_id,)
        ).fetchone()[0]
        scores = conn.execute(
            "SELECT COUNT(*) FROM scoring_plays WHERE game_id = ?", (game_id,)
        ).fetchone()[0]
        pens = conn.execute(
            "SELECT COUNT(*) FROM penalties WHERE game_id = ?", (game_id,)
        ).fetchone()[0]
    return {"plays": plays, "scores": scores, "penalties": pens}


def reset_game(game_id, plays=True, scores=True, penalties=True, state=True):
    """
    Wipe this game back to a clean slate. Scoped so you can clear a botched
    play log without losing a correct scoreboard. Only ever affects one game.
    """
    with get_conn() as conn:
        if plays:
            conn.execute("DELETE FROM snaps WHERE game_id = ?", (game_id,))
        if scores:
            conn.execute("DELETE FROM scoring_plays WHERE game_id = ?", (game_id,))
        if penalties:
            conn.execute("DELETE FROM penalties WHERE game_id = ?", (game_id,))
        if state:
            conn.execute(
                """UPDATE game_state SET current_half = 1, timeouts_used_h1 = 0,
                   timeouts_used_h2 = 0, current_down = 1 WHERE game_id = ?""",
                (game_id,),
            )
    if scores:
        _recompute_score(game_id)
