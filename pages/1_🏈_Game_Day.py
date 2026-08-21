import datetime

import pandas as pd
import streamlit as st

import data_store as ds
from ui import (inject_mobile_css, format_game_label, play_clock, timeout_clock,
                check_data_store, rules_sidebar)

st.set_page_config(
    page_title="Game Day", page_icon="🏈", layout="wide",
    initial_sidebar_state="collapsed",   # sideline mode: maximum screen space
)
check_data_store()
ds.init_db()
inject_mobile_css()

games = ds.get_games(ascending=True)
if games.empty:
    st.warning("No games scheduled. Add one on the Roster page first.")
    st.stop()

players = ds.get_players()
if players.empty:
    st.warning("No players on the roster. Add them on the Roster page first.")
    st.stop()


def default_game_index():
    """
    Honour a game tapped on the schedule; otherwise open today's game, else the
    next one coming up, else the last one played.
    """
    picked = st.session_state.get("selected_game_id")
    if picked is not None:
        match = games.index[games["game_id"] == picked].tolist()
        if match:
            return match[0]
    today = datetime.date.today().isoformat()
    upcoming = games.index[games["game_date"] >= today].tolist()
    return upcoming[0] if upcoming else len(games) - 1


labels = [format_game_label(row) for _, row in games.iterrows()]
choice = st.selectbox(
    "Game", options=list(range(len(games))),
    index=int(default_game_index()), format_func=lambda i: labels[i],
)
game_row = games.iloc[choice]
game_id = int(game_row["game_id"])
# Keep the picker and the schedule tap in agreement on later reruns.
st.session_state["selected_game_id"] = game_id

state = ds.get_game_state(game_id)
half = state["current_half"]

us, them = ds.get_score(game_id)
st.title(f"🏈 {ds.TEAM_NAME} {us} — {them} {game_row['opponent']}")
if ds.mercy_rule_in_effect(game_id):
    st.info(
        f"📢 **Mercy rule range** — a {ds.MERCY_RULE_TD_MARGIN}+ touchdown lead "
        "means the clock runs without stopping from the second-half "
        "one-minute warning."
    )

rules_sidebar()

# ------------------------------------------------------------- The clocks ----
clock_col, state_col = st.columns([1, 1])

with clock_col:
    play_clock()
    st.caption(
        f"The referee starts the {ds.PLAY_CLOCK_SECONDS}-second clock on the "
        "ready-for-play signal. Red under 5 seconds — snap it before the "
        "3-yard delay of game."
    )

with state_col:
    st.subheader("Game State")

    picked_half = st.radio(
        "Half", list(range(1, ds.HALVES + 1)),
        index=half - 1, horizontal=True,
        format_func=lambda h: f"{h}st Half" if h == 1 else f"{h}nd Half",
    )
    if picked_half != half:
        ds.set_half(game_id, picked_half)
        st.rerun()

    # --- down and distance -------------------------------------------------
    down = state["current_down"]
    st.markdown(
        "".join(
            f"<span class='down-pill{' active' if d == down else ''}'>{d}</span>"
            for d in range(1, ds.DOWNS_PER_SERIES + 1)
        ),
        unsafe_allow_html=True,
    )
    st.caption(
        f"**Down {down} of {ds.DOWNS_PER_SERIES}** — four downs to cross the "
        f"next {ds.ZONE_YARDS}-yard zone line for a first down."
    )
    d1, d2 = st.columns(2)
    if d1.button("▶ Next Down", width="stretch", key="next_down"):
        ds.next_down(game_id)
        st.rerun()
    if d2.button("🔄 First Down", width="stretch", key="first_down"):
        ds.set_down(game_id, 1)
        st.rerun()

    # --- timeouts ----------------------------------------------------------
    left = ds.timeouts_left(game_id, half)
    used = ds.TIMEOUTS_PER_HALF - left
    st.markdown(
        f"<div class='timeout-pill'>{'🟢' * left}{'⚪' * used}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"**{left} of {ds.TIMEOUTS_PER_HALF} timeouts left** "
        f"— {'1st' if half == 1 else '2nd'} half"
    )
    t1, t2 = st.columns(2)
    if t1.button(
        "⏱️ Use Timeout", width="stretch", disabled=left == 0, key="use_timeout"
    ):
        if ds.use_timeout(game_id, half):
            st.rerun()
    if t2.button("↺ Reset Half's Timeouts", width="stretch", key="reset_to"):
        ds.reset_timeouts(game_id, half)
        st.rerun()

    with st.expander(f"⏱️ {ds.TIMEOUT_SECONDS}-second timeout clock"):
        timeout_clock()
        st.caption(
            f"Each timeout is {ds.TIMEOUT_SECONDS} seconds long. "
            f"{ds.TIMEOUTS_PER_HALF} per half; each half keeps its own count."
        )

st.divider()

# -------------------------------------------- Equal Play Rule Check grid ----
summary = ds.get_game_summary(game_id)
needs = summary[summary["Needs QB/Run"]]["Player"].tolist()

st.subheader("⚖️ Equal Play Rule Check")

if needs:
    st.error(
        f"**{len(needs)} still need a mandatory QB or Runner play:** "
        f"{', '.join(needs)}"
    )
else:
    st.success(
        "✅ **COMPLIANT** — every player has taken a snap at QB or carried the ball."
    )

st.caption(
    "**Only two things satisfy this rule: running the ball, or playing "
    "quarterback.** Tap **QB** or **RUN** the moment a kid does one of them.\n\n"
    "**PLAY** logs field time only. Playing center, blocking, and catching a "
    "pass — including catching a touchdown — all count toward equal playing "
    "time but do **not** satisfy the mandatory-involvement rule, so they leave "
    "a player red.\n\n"
    "**🏈 TD +6** credits a touchdown to that player and adds 6 to the score. "
    "It's scoring only — if he ran it in, tap **RUN** as well.\n\n"
    "Tap **↩** on a card to take back that player's last entry if you tapped "
    "the wrong name. There is no center snap in W League — the QB starts the "
    "play already holding the ball — so field time is counted in plays."
)

cols = st.columns(3)
# Roster order, not sorted by status: the tiles need to stay put between taps
# so you build muscle memory for where each kid's buttons are.
for i, (_, row) in enumerate(summary.iterrows()):
    with cols[i % 3]:
        pid = int(row["player_id"])
        needs_touch = bool(row["Needs QB/Run"])
        css = "needs-touch" if needs_touch else "has-touch"
        status = "⚠ NEEDS QB / RUN" if needs_touch else "✓ RULE MET"
        tds = int(row["Touchdowns"])
        td_meta = f" · 🏈 {tds} TD" if tds else ""
        st.markdown(
            f"""
            <div class='player-card {css}'>
              <div class='pc-name'>{row["Player"]}</div>
              <div class='pc-status'>{status}</div>
              <div class='pc-meta'>{row["Plays"]} plays · QB {row["QB Plays"]} · Run {row["Runner Plays"]}{td_meta}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        b1, b2, b3 = st.columns(3)
        if b1.button("QB", key=f"qb_{game_id}_{pid}", width="stretch"):
            ds.log_touch(game_id, half, pid, "QB")
            st.rerun()
        if b2.button("RUN", key=f"run_{game_id}_{pid}", width="stretch"):
            ds.log_touch(game_id, half, pid, "Runner")
            st.rerun()
        if b3.button("PLAY", key=f"play_{game_id}_{pid}", width="stretch"):
            ds.log_touch(game_id, half, pid, None)
            st.rerun()

        b4, b5 = st.columns([2, 1])
        # Scores 6 for the team and credits this player. Scoring only -- if he
        # ran it in, tap RUN too; a receiving TD never satisfies the rule.
        if b4.button(
            "🏈 TD +6", key=f"td_{game_id}_{pid}", width="stretch",
            help=f"Touchdown scored by {row['Player']} (+6)",
        ):
            ds.add_score(game_id, half, "us", "Touchdown", player_id=pid)
            st.toast(f"Touchdown — {row['Player']}!")
            st.rerun()
        # Undo just this player -- for the mis-tap, not the whole log.
        if b5.button(
            "↩", key=f"undop_{game_id}_{pid}", width="stretch",
            help=f"Undo {row['Player']}'s last entry",
            disabled=int(row["Plays"]) == 0 and int(row["Touchdowns"]) == 0,
        ):
            ds.undo_last_entry_for_player(game_id, pid)
            st.rerun()

st.markdown("")
u1, u2 = st.columns([1, 3])
if u1.button("↩️ Undo Last", width="stretch", key="undo"):
    if ds.undo_last_snap(game_id):
        st.toast("Removed the last logged play.")
        st.rerun()
    else:
        st.warning("Nothing logged for this game yet.")

# Equal playing time is the other half of the rule — surface it separately.
below = summary[summary["Below Avg Plays"]]["Player"].tolist()
if below:
    u2.warning(f"⚠️ Below average playing time: {', '.join(below)}")

# ---------------------------------------- Log a whole play (7 on the field) --
with st.expander(f"Log a full play — {ds.PLAYERS_ON_FIELD} on the field"):
    st.caption(
        f"The rule sheet puts {ds.PLAYERS_ON_FIELD} players a side. Tick who "
        "was out there and log the snap for all of them at once — the fastest "
        "way to keep playing time honest."
    )
    on_field = st.multiselect(
        "On the field", options=summary["player_id"].tolist(),
        format_func=lambda pid: summary.set_index("player_id").loc[pid, "Player"],
        key=f"onfield_{game_id}",
    )
    if len(on_field) and len(on_field) != ds.PLAYERS_ON_FIELD:
        st.warning(
            f"{len(on_field)} selected — the league plays "
            f"{ds.PLAYERS_ON_FIELD} a side."
        )
    f1, f2 = st.columns(2)
    qb = f1.selectbox(
        "QB this play", options=[None] + on_field,
        format_func=lambda pid: "—" if pid is None
        else summary.set_index("player_id").loc[pid, "Player"],
        key=f"qb_sel_{game_id}",
    )
    runner = f2.selectbox(
        "Ball carrier this play", options=[None] + on_field,
        format_func=lambda pid: "—" if pid is None
        else summary.set_index("player_id").loc[pid, "Player"],
        key=f"run_sel_{game_id}",
    )
    if st.button(
        "✅ Log Play", type="primary", width="stretch",
        disabled=not on_field, key="log_full_play",
    ):
        ds.log_play(game_id, half, on_field, qb_id=qb, runner_id=runner)
        ds.next_down(game_id)
        st.success(f"Play logged for {len(on_field)} players.")
        st.rerun()

st.divider()

# --------------------------------------------------------------- Scoring ----
st.subheader("🏆 Scoring")
st.caption(
    "Touchdown 6 · try 1 point from the 3-yard line or 2 from the 7 · safety 2."
)

st.caption(
    f"Touchdowns are credited to a player with the **🏈 TD +6** button on their "
    f"card above. The buttons here are for {ds.TEAM_NAME} scores you don't need "
    "credited to anyone, and for the opponent."
)

for team, team_label in (("us", ds.TEAM_NAME), ("them", str(game_row["opponent"]))):
    st.markdown(f"**{team_label}**")
    score_cols = st.columns(len(ds.SCORING_PLAYS))
    for col, (play_type, points) in zip(score_cols, ds.SCORING_PLAYS.items()):
        if col.button(
            f"{play_type.replace('Try — ', 'Try ')} (+{points})",
            key=f"score_{team}_{play_type}_{game_id}", width="stretch",
        ):
            ds.add_score(game_id, half, team, play_type)
            st.rerun()

sc1, sc2 = st.columns([1, 3])
if sc1.button("↩️ Undo Last Score", width="stretch", key="undo_score"):
    if ds.undo_last_score(game_id):
        st.rerun()
    else:
        st.warning("No scoring plays logged yet.")

scoring = ds.get_scoring_plays(game_id)
if not scoring.empty:
    with st.expander(f"Scoring plays ({len(scoring)})"):
        st.dataframe(scoring, width="stretch", hide_index=True)

st.divider()

# -------------------------------------------------------------- Penalties ----
st.subheader("🛑 Penalties")

pen_team = st.radio(
    "Penalty on", ["us", "them"], horizontal=True,
    format_func=lambda t: ds.TEAM_NAME if t == "us" else str(game_row["opponent"]),
    key="pen_team",
)

st.markdown("**3-yard penalties** — dead ball / technical")
p3 = st.columns(len(ds.PENALTIES_3YD))
for col, name in zip(p3, ds.PENALTIES_3YD):
    if col.button(name, key=f"p3_{name}_{game_id}", width="stretch"):
        ds.log_penalty(game_id, half, pen_team, name)
        st.rerun()

st.markdown("**6-yard penalties** — live ball / contact")
p6 = st.columns(4)
for i, name in enumerate(ds.PENALTIES_6YD):
    if p6[i % 4].button(name, key=f"p6_{name}_{game_id}", width="stretch"):
        ds.log_penalty(game_id, half, pen_team, name)
        st.rerun()

penalties = ds.get_penalties(game_id)
if not penalties.empty:
    pc1, pc2 = st.columns([1, 3])
    if pc1.button("↩️ Undo Last Penalty", width="stretch", key="undo_pen"):
        ds.undo_last_penalty(game_id)
        st.rerun()
    pc2.caption(
        f"{len(penalties)} logged · "
        f"{int(penalties['yards'].sum())} penalty yards total"
    )
    with st.expander(f"Penalties ({len(penalties)})"):
        st.dataframe(penalties, width="stretch", hide_index=True)

st.divider()

# ------------------------------------------------------------- Live stats ----
st.subheader("Live Stats")
st.dataframe(
    summary[["Player", "Plays", "QB Plays", "Runner Plays", "QB/Run Plays",
             "Touchdowns", "Met QB/Runner Rule"]],
    width="stretch", hide_index=True,
)

# --------------------------------------------------------- Quick export ----
st.subheader("📋 Export This Game")
export_df = ds.get_game_export(game_id)
if export_df.empty:
    st.info("Log a play first and the CSV will appear here.")
else:
    st.download_button(
        "⬇️ Download This Game's CSV",
        export_df.to_csv(index=False),
        file_name=f"{ds.TEAM_CODE}_{game_row['game_date']}_vs_{game_row['opponent']}.csv",
        mime="text/csv", width="stretch", type="primary",
    )

st.divider()

# ------------------------------------------------------------------ Reset ----
with st.expander("🗑️ Reset this game's log"):
    counts = ds.game_log_counts(game_id)
    st.caption(
        "Clears this game only — every other game keeps its data. Use the "
        "**↩** button on a player card first if you only need to take back one "
        "mistaken entry."
    )
    st.markdown(
        f"Currently logged: **{counts['plays']} plays**, "
        f"**{counts['scores']} scoring plays**, **{counts['penalties']} penalties**."
    )
    what = st.multiselect(
        "What to clear",
        ["Player plays & touches", "Scoring", "Penalties", "Down & timeouts"],
        default=["Player plays & touches"],
        key="reset_scope",
    )
    confirm = st.checkbox(
        f"Yes, permanently clear this for {game_row['game_date']} vs "
        f"{game_row['opponent']}",
        key="reset_confirm",
    )
    if st.button(
        "🗑️ Reset", type="primary", width="stretch",
        disabled=not (what and confirm), key="reset_game",
    ):
        ds.reset_game(
            game_id,
            plays="Player plays & touches" in what,
            scores="Scoring" in what,
            penalties="Penalties" in what,
            state="Down & timeouts" in what,
        )
        st.success("Game log reset.")
        st.rerun()
