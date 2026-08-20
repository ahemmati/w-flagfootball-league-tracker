"""
data_store.py
--------------
All database access lives here. Every other file in this app talks to the
database ONLY through these functions. That means if you outgrow SQLite later
(e.g. deploying to Streamlit Cloud for the season and you want data that
survives redeploys), you rewrite the guts of these functions to hit Google
Sheets / Supabase / whatever instead, and nothing in the UI pages has to change.

Rules this schema is built to answer, straight from the league rule sheet:
  - "Every player must play an equal amount of time" -> we track snaps per
    player per game, so you can see imbalance as it happens, live.
  - "Every player must either run the ball or play quarterback for at least
    one snap each game" -> every logged play captures who was QB and who was
    the runner, so you can see at a glance who still needs a turn.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
import pandas as pd

DB_PATH = Path(__file__).parent / "flagfootball.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                jersey_number TEXT,
                active INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_date TEXT NOT NULL,
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


# ---------- Players ----------

def add_player(name, jersey_number=""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO players (name, jersey_number, active) VALUES (?, ?, 1)",
            (name.strip(), jersey_number.strip()),
        )


def set_player_active(player_id, active: bool):
    with get_conn() as conn:
        conn.execute(
            "UPDATE players SET active = ? WHERE player_id = ?",
            (1 if active else 0, player_id),
        )


def get_players(active_only=True):
    with get_conn() as conn:
        query = "SELECT * FROM players"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY name"
        return pd.read_sql_query(query, conn)


# ---------- Games ----------

def create_game(game_date, opponent):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO games (game_date, opponent) VALUES (?, ?)",
            (str(game_date), opponent.strip()),
        )
        return cur.lastrowid


def get_games():
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT * FROM games ORDER BY game_date DESC, game_id DESC", conn
        )


def update_game_score(game_id, our_score, their_score):
    with get_conn() as conn:
        conn.execute(
            "UPDATE games SET our_score = ?, their_score = ? WHERE game_id = ?",
            (our_score, their_score, game_id),
        )


def get_next_play_number(game_id, half):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(play_number) FROM snaps WHERE game_id = ? AND half = ?",
            (game_id, half),
        ).fetchone()
        return (row[0] or 0) + 1


# ---------- Snaps (the core "log a play" action) ----------

def log_play(game_id, half, on_field_player_ids, qb_id=None, runner_id=None,
             side="offense", event=None, event_player_id=None):
    """
    Logs one play. Every player who was on the field gets a snap row.
    qb_id / runner_id (if set) get role='QB' / role='Runner' on their row.
    event (e.g. 'Touchdown', 'Flag Pulled (Us)', 'Interception') attaches to
    event_player_id if given, otherwise it's just recorded at the game level
    on the first player's row for reference.
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


def get_game_snaps(game_id):
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT * FROM snaps WHERE game_id = ?", conn, params=(game_id,)
        )


def get_game_summary(game_id):
    """Per-player snap counts + rule compliance for one game."""
    players = get_players(active_only=False)
    snaps = get_game_snaps(game_id)

    if players.empty:
        return pd.DataFrame()

    rows = []
    for _, p in players.iterrows():
        pid = p["player_id"]
        p_snaps = snaps[snaps["player_id"] == pid]
        rows.append({
            "player_id": pid,
            "Player": p["name"],
            "Jersey": p["jersey_number"],
            "Snaps": len(p_snaps),
            "QB Snaps": (p_snaps["role"] == "QB").sum(),
            "Runner Snaps": (p_snaps["role"] == "Runner").sum(),
            "Touchdowns": (p_snaps["event"] == "Touchdown").sum(),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["Met QB/Runner Rule"] = (df["QB Snaps"] + df["Runner Snaps"]) > 0
    avg_snaps = df["Snaps"].mean()
    df["Below Avg Snaps"] = df["Snaps"] < (avg_snaps - 1)  # 1-snap tolerance
    return df.sort_values("Snaps")


# ---------- Season-wide aggregation ----------

def get_season_summary():
    players = get_players(active_only=False)
    with get_conn() as conn:
        snaps = pd.read_sql_query("SELECT * FROM snaps", conn)
        games = pd.read_sql_query("SELECT * FROM games", conn)

    if players.empty:
        return pd.DataFrame()

    rows = []
    for _, p in players.iterrows():
        pid = p["player_id"]
        p_snaps = snaps[snaps["player_id"] == pid]
        games_played = p_snaps["game_id"].nunique()
        rows.append({
            "Player": p["name"],
            "Jersey": p["jersey_number"],
            "Games Played": games_played,
            "Total Snaps": len(p_snaps),
            "Avg Snaps/Game": round(len(p_snaps) / games_played, 1) if games_played else 0,
            "QB Snaps": (p_snaps["role"] == "QB").sum(),
            "Runner Snaps": (p_snaps["role"] == "Runner").sum(),
            "Touchdowns": (p_snaps["event"] == "Touchdown").sum(),
        })
    df = pd.DataFrame(rows)
    return df.sort_values("Total Snaps", ascending=False)


def get_export_dataframes():
    with get_conn() as conn:
        players = pd.read_sql_query("SELECT * FROM players", conn)
        games = pd.read_sql_query("SELECT * FROM games", conn)
        snaps = pd.read_sql_query("SELECT * FROM snaps", conn)
    return players, games, snaps
