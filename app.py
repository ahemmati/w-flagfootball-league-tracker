import pandas as pd
import streamlit as st

import data_store as ds
from ui import (inject_mobile_css, format_game_label, check_data_store,
                rules_sidebar, GAME_DAY_PAGE)

st.set_page_config(
    page_title=f"{ds.TEAM_NAME} Tracker",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)
check_data_store()
ds.init_db()
inject_mobile_css()

st.title(f"🏈 {ds.TEAM_NAME}")
st.caption(
    f"Mt. Bethel W League (1st & 2nd Grade) · Team {ds.TEAM_CODE} · "
    "Use the sidebar for Game Day, the Season Dashboard, Export, and the full Rules."
)

rules_sidebar()

# -------------------------------------------------------------- Schedule ----
st.header("Schedule")
st.caption("Tap a game to open it on the Game Day tracker.")

games = ds.get_games(ascending=True)
if games.empty:
    st.info("No games scheduled.")
else:
    overview = ds.get_compliance_overview()
    today = pd.Timestamp.today().normalize()

    for i, (_, g) in enumerate(games.iterrows()):
        game_id = int(g["game_id"])
        date = pd.to_datetime(g["game_date"])
        us, them = ds.get_score(game_id)
        status = overview.iloc[i]["Status"]

        # Result badge once a game has been played, schedule info before that.
        if status == "Not started":
            badge = "🔜 Upcoming" if date >= today else "— Not tracked"
        elif us > them:
            badge = f"✅ W {us}–{them}"
        elif us < them:
            badge = f"❌ L {us}–{them}"
        else:
            badge = f"➖ T {us}–{them}"

        rule_badge = {
            "Compliant": "⚖️ Equal Play met",
            "Needs touches": "⚠️ Touches still owed",
            "Not started": "",
        }[status]

        c1, c2, c3 = st.columns([4, 2, 2])
        with c1:
            if st.button(
                f"🏈 {date.strftime('%a %b %-d, %Y')} · {g['game_time']} "
                f"vs {g['opponent']}",
                key=f"open_game_{game_id}", width="stretch",
            ):
                # Hand the choice to Game Day, then jump straight there.
                st.session_state["selected_game_id"] = game_id
                st.switch_page(GAME_DAY_PAGE)
        c2.markdown(f"<div class='sched-badge'>{badge}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='sched-badge'>{rule_badge}</div>", unsafe_allow_html=True)

with st.expander("Add another game"):
    with st.form("add_game_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        game_date = col1.date_input("Date")
        game_time = col2.text_input("Time", placeholder="9:00 AM")
        opponent = col3.text_input("Opponent", placeholder="W3")
        add_game = col4.form_submit_button("Add Game", width="stretch")
        if add_game:
            if opponent.strip():
                ds.create_game(game_date, opponent, game_time)
                st.success(f"Game vs {opponent.strip()} added.")
                st.rerun()
            else:
                st.warning("Enter an opponent first.")

st.divider()

# ---------------------------------------------------------------- Roster ----
st.header("Roster")

players = ds.get_players()
if players.empty:
    st.info("No players yet — add your roster below.")
else:
    st.caption(
        f"{len(players)} players · {ds.PLAYERS_ON_FIELD} on the field at a time."
    )
    cols = st.columns(3)
    for i, p in enumerate(players.itertuples()):
        with cols[i % 3]:
            st.markdown(
                f"<div class='roster-card'>{p.name}</div>", unsafe_allow_html=True
            )

st.markdown("")
with st.form("add_player_form", clear_on_submit=True):
    st.markdown("**Add a player**")
    col1, col2 = st.columns([3, 1])
    name = col1.text_input(
        "Player name", label_visibility="collapsed", placeholder="Player name"
    )
    submitted = col2.form_submit_button("➕ Add Player", width="stretch")
    if submitted:
        try:
            ds.add_player(name)
            st.success(f"Added {name.strip()} to the roster.")
            st.rerun()
        except ValueError as err:
            st.warning(str(err))

st.caption(
    "Players can be added at any time. Removing a player isn't supported on "
    "purpose — snap history points at the roster, so deleting someone would "
    "take their season stats with them."
)
