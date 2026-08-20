import streamlit as st
import pandas as pd
import data_store as ds
from ui import inject_mobile_css, format_game_label

st.set_page_config(
    page_title="Flag Football Tracker",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)
ds.init_db()
inject_mobile_css()

st.title("🏈 Flag Football Tracker")
st.caption(
    "Mt. Bethel W League · Use the sidebar for Game Day tracking, "
    "the Season Dashboard, and Export."
)

with st.sidebar:
    st.header("📋 League Rules Quick Ref")
    st.error(
        "⚠️ **EQUAL PLAY RULE:** Every player must play an equal amount of time, "
        "and **must** run the ball or play quarterback for at least one snap "
        "each game."
    )
    st.info(
        "⏱️ **TIMING:** Two 20-minute halves. Continuous clock until the final "
        "minute of each half. **35-second play clock.**"
    )
    st.success(
        "🔄 **NO CENTER SNAP:** QB starts with the ball in possession. The "
        "center is immediately eligible to run a route."
    )
    st.warning(
        "🛑 **PENALTIES:** 3-Yard (dead ball / technical) or 6-Yard "
        "(live ball / contact)."
    )
    st.caption(f"**Timeouts:** {ds.TIMEOUTS_PER_HALF} per half.")

# ---------------------------------------------------------------- Roster ----
st.header("Roster")

players = ds.get_players()

if players.empty:
    st.info("No players yet — add your roster below.")
else:
    st.caption(f"{len(players)} players on the roster.")
    cols = st.columns(3)
    for i, p in enumerate(players.itertuples()):
        with cols[i % 3]:
            st.markdown(
                f"<div class='roster-card'>{p.name}</div>",
                unsafe_allow_html=True,
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

st.divider()

# -------------------------------------------------------------- Schedule ----
st.header("Schedule")

games = ds.get_games(ascending=True)
if games.empty:
    st.info("No games scheduled.")
else:
    overview = ds.get_compliance_overview()
    display = games.copy()
    display["Date"] = pd.to_datetime(display["game_date"]).dt.strftime("%a %b %-d, %Y")
    display["Time"] = display["game_time"].fillna("")
    display["Opponent"] = display["opponent"]
    display["Us"] = display["our_score"]
    display["Them"] = display["their_score"]
    display["Equal Play"] = overview["Status"].values

    st.dataframe(
        display[["Date", "Time", "Opponent", "Us", "Them", "Equal Play"]],
        width="stretch",
        hide_index=True,
    )

with st.expander("Add another game"):
    with st.form("add_game_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        game_date = col1.date_input("Date")
        game_time = col2.text_input("Time", placeholder="9:00 AM")
        opponent = col3.text_input("Opponent", placeholder="W5")
        add_game = col4.form_submit_button("Add Game", width="stretch")
        if add_game:
            if opponent.strip():
                ds.create_game(game_date, opponent, game_time)
                st.success(f"Game vs {opponent.strip()} added.")
                st.rerun()
            else:
                st.warning("Enter an opponent first.")
