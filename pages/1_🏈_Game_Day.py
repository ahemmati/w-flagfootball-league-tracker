import streamlit as st
import data_store as ds

st.set_page_config(page_title="Game Day", page_icon="🏈", layout="wide")
ds.init_db()

st.title("🏈 Game Day Tracker")

games = ds.get_games()
if games.empty:
    st.warning("No games yet. Add one on the Roster page first.")
    st.stop()

players = ds.get_players(active_only=True)
if players.empty:
    st.warning("No active players yet. Add your roster on the Roster page first.")
    st.stop()

game_labels = [f"{row.game_date} vs {row.opponent}" for row in games.itertuples()]
game_choice = st.selectbox("Game", options=range(len(games)), format_func=lambda i: game_labels[i])
game_row = games.iloc[game_choice]
game_id = int(game_row["game_id"])

col_half, col_side = st.columns(2)
half = col_half.radio("Half", [1, 2], horizontal=True)
side = col_side.radio("Side of ball", ["offense", "defense"], horizontal=True)

st.divider()

# Keep the last "on field" group in session_state so re-logging the next play
# for the same group of kids is one tap, not seven.
state_key = f"on_field_{game_id}_{side}"
if state_key not in st.session_state:
    st.session_state[state_key] = set()

st.subheader("Who's on the field this play?")
cols = st.columns(4)
on_field_ids = []
for i, p in enumerate(players.itertuples()):
    with cols[i % 4]:
        checked = st.checkbox(
            f"{p.name} (#{p.jersey_number or '—'})",
            value=p.player_id in st.session_state[state_key],
            key=f"chk_{game_id}_{side}_{p.player_id}",
        )
        if checked:
            on_field_ids.append(p.player_id)

st.session_state[state_key] = set(on_field_ids)

on_field_players = players[players["player_id"].isin(on_field_ids)]

col_qb, col_run, col_event = st.columns(3)
qb_choice = col_qb.selectbox(
    "QB this play (offense only)",
    options=[None] + on_field_players["player_id"].tolist(),
    format_func=lambda pid: "—" if pid is None else players.set_index("player_id").loc[pid, "name"],
)
runner_choice = col_run.selectbox(
    "Runner this play (offense only)",
    options=[None] + on_field_players["player_id"].tolist(),
    format_func=lambda pid: "—" if pid is None else players.set_index("player_id").loc[pid, "name"],
)
event_choice = col_event.selectbox(
    "Event (optional)",
    options=[None, "Touchdown", "Flag Pulled (Us)", "Flag Pulled (Them)",
             "Interception", "Incomplete Pass", "Penalty"],
)

event_player_choice = None
if event_choice:
    event_player_choice = st.selectbox(
        "Who does that event belong to?",
        options=on_field_players["player_id"].tolist(),
        format_func=lambda pid: players.set_index("player_id").loc[pid, "name"],
    )

if st.button("✅ Log Play", type="primary", use_container_width=True, disabled=len(on_field_ids) == 0):
    ds.log_play(
        game_id=game_id, half=half, on_field_player_ids=on_field_ids,
        qb_id=qb_choice, runner_id=runner_choice, side=side,
        event=event_choice, event_player_id=event_player_choice,
    )
    st.success(f"Play logged for {len(on_field_ids)} players.")

st.divider()

st.subheader("Live status — this game")
summary = ds.get_game_summary(game_id)
if summary.empty:
    st.info("No plays logged yet.")
else:
    needs_qb_run = summary[~summary["Met QB/Runner Rule"]]["Player"].tolist()
    low_snaps = summary[summary["Below Avg Snaps"]]["Player"].tolist()

    if needs_qb_run:
        st.warning(f"⚠️ Still need a QB or Runner snap: {', '.join(needs_qb_run)}")
    if low_snaps:
        st.warning(f"⚠️ Below average snap count: {', '.join(low_snaps)}")
    if not needs_qb_run and not low_snaps:
        st.success("Playing time and QB/Runner rule are on track for everyone.")

    display = summary[["Player", "Jersey", "Snaps", "QB Snaps", "Runner Snaps",
                        "Touchdowns", "Met QB/Runner Rule"]]
    st.dataframe(display, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Final score")
c1, c2, c3 = st.columns([1, 1, 1])
our_score = c1.number_input("Us", min_value=0, value=int(game_row["our_score"] or 0))
their_score = c2.number_input("Them", min_value=0, value=int(game_row["their_score"] or 0))
if c3.button("Save score", use_container_width=True):
    ds.update_game_score(game_id, our_score, their_score)
    st.success("Score saved.")
