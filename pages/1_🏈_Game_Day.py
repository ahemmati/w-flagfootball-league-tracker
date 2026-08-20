import datetime

import pandas as pd
import streamlit as st

import data_store as ds
from ui import inject_mobile_css, format_game_label, play_clock

st.set_page_config(
    page_title="Game Day", page_icon="🏈", layout="wide",
    initial_sidebar_state="collapsed",   # sideline mode: maximum screen space
)
ds.init_db()
inject_mobile_css()

st.title("🏈 Game Day")

games = ds.get_games(ascending=True)
if games.empty:
    st.warning("No games scheduled. Add one on the Roster page first.")
    st.stop()

players = ds.get_players()
if players.empty:
    st.warning("No players on the roster. Add them on the Roster page first.")
    st.stop()


def default_game_index():
    """Open on today's game, else the next one coming up, else the last one."""
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

# ------------------------------------------------------------ Play clock ----
clock_col, state_col = st.columns([1, 1])

with clock_col:
    play_clock()
    st.caption(
        "Runs in your browser, so it keeps ticking while you log plays. "
        "Turns red under 5 seconds — snap it before the 3-yard delay of game."
    )

# ------------------------------------------------- Game state & timeouts ----
with state_col:
    state = ds.get_game_state(game_id)

    st.subheader("Game State")
    half = st.radio(
        "Half", [1, 2],
        index=0 if state["current_half"] == 1 else 1,
        horizontal=True,
        format_func=lambda h: f"{h}st Half" if h == 1 else f"{h}nd Half",
    )
    # Only write when it actually changed, otherwise every rerun is a write.
    if half != state["current_half"]:
        ds.set_half(game_id, half)
        st.rerun()

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
        "⏱️ Use Timeout", width="stretch", disabled=left == 0,
        key="use_timeout",
    ):
        if ds.use_timeout(game_id, half):
            st.rerun()
    if t2.button("↺ Reset Half's Timeouts", width="stretch", key="reset_to"):
        ds.reset_timeouts(game_id, half)
        st.rerun()

    st.caption(
        f"{ds.TIMEOUTS_PER_HALF} timeouts per half. Each half keeps its own "
        "count, so the 2nd half starts fresh on its own."
    )

st.divider()

# -------------------------------------------- Equal Play Rule Check grid ----
summary = ds.get_game_summary(game_id)
needs = summary[summary["Needs Touch"]]["Player"].tolist()

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
    "Tap **QB** or **RUN** the moment a kid takes their mandatory play. "
    "**SNAP** logs field time only — it counts toward equal playing time but "
    "does not satisfy the rule."
)

cols = st.columns(3)
# Roster order, not sorted by status: the tiles need to stay put between taps
# so you build muscle memory for where each kid's buttons are.
for i, (_, row) in enumerate(summary.iterrows()):
    with cols[i % 3]:
        needs_touch = bool(row["Needs Touch"])
        css = "needs-touch" if needs_touch else "has-touch"
        status = "⚠ NEEDS TOUCH" if needs_touch else "✓ RULE MET"
        st.markdown(
            f"""
            <div class='player-card {css}'>
              <div class='pc-name'>{row["Player"]}</div>
              <div class='pc-status'>{status}</div>
              <div class='pc-meta'>{row["Snaps"]} snaps · QB {row["QB Snaps"]} · Run {row["Runner Snaps"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        b1, b2, b3 = st.columns(3)
        pid = int(row["player_id"])
        if b1.button("QB", key=f"qb_{game_id}_{pid}", width="stretch"):
            ds.log_touch(game_id, half, pid, "QB")
            st.rerun()
        if b2.button("RUN", key=f"run_{game_id}_{pid}", width="stretch"):
            ds.log_touch(game_id, half, pid, "Runner")
            st.rerun()
        if b3.button("SNAP", key=f"snap_{game_id}_{pid}", width="stretch"):
            ds.log_touch(game_id, half, pid, None)
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
below = summary[summary["Below Avg Snaps"]]["Player"].tolist()
if below:
    u2.warning(f"⚠️ Below average playing time: {', '.join(below)}")

st.divider()

# ---------------------------------------------------- Live stats + score ----
st.subheader("Live Stats")
st.dataframe(
    summary[["Player", "Snaps", "QB Snaps", "Runner Snaps", "Touches",
             "Touchdowns", "Met QB/Runner Rule"]],
    width="stretch", hide_index=True,
)

sc1, sc2, sc3 = st.columns([1, 1, 2])
our_score = sc1.number_input(
    "Us", min_value=0,
    value=int(game_row["our_score"]) if pd.notna(game_row["our_score"]) else 0,
)
their_score = sc2.number_input(
    "Them", min_value=0,
    value=int(game_row["their_score"]) if pd.notna(game_row["their_score"]) else 0,
)
if sc3.button("💾 Save Score", width="stretch", key="save_score"):
    ds.update_game_score(game_id, our_score, their_score)
    st.success("Score saved.")

st.divider()

# --------------------------------------------------------- Quick export ----
st.subheader("📋 Export This Game")
export_df = ds.get_game_export(game_id)
if export_df.empty:
    st.info("Log a play first and the CSV will appear here.")
else:
    st.download_button(
        "⬇️ Download This Game's CSV",
        export_df.to_csv(index=False),
        file_name=f"game_{game_row['game_date']}_vs_{game_row['opponent']}.csv",
        mime="text/csv",
        width="stretch",
        type="primary",
    )
