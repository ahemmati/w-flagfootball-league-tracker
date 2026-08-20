import streamlit as st
import data_store as ds

st.set_page_config(page_title="Flag Football Tracker", page_icon="🏈", layout="wide")
ds.init_db()

st.title("🏈 Flag Football Tracker")
st.caption("Roster · use the sidebar to jump to Game Day tracking, the Season Dashboard, or Export.")

st.header("Roster")

with st.form("add_player_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([3, 1, 1])
    name = col1.text_input("Player name")
    jersey = col2.text_input("Jersey #")
    submitted = col3.form_submit_button("Add Player", use_container_width=True)
    if submitted:
        if name.strip():
            ds.add_player(name, jersey)
            st.success(f"Added {name}")
            st.rerun()
        else:
            st.warning("Enter a name first.")

st.divider()

players = ds.get_players(active_only=False)

if players.empty:
    st.info("No players yet — add your roster above to get started.")
else:
    active = players[players["active"] == 1]
    inactive = players[players["active"] == 0]

    st.subheader(f"Active roster ({len(active)})")
    for _, p in active.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{p['name']}**  ·  #{p['jersey_number'] or '—'}")
        if c3.button("Mark inactive", key=f"deact_{p['player_id']}"):
            ds.set_player_active(p["player_id"], False)
            st.rerun()

    if not inactive.empty:
        with st.expander(f"Inactive players ({len(inactive)})"):
            for _, p in inactive.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"{p['name']}  ·  #{p['jersey_number'] or '—'}")
                if c2.button("Reactivate", key=f"react_{p['player_id']}"):
                    ds.set_player_active(p["player_id"], True)
                    st.rerun()

st.divider()
st.subheader("Games")

with st.form("add_game_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([1, 2, 1])
    game_date = col1.date_input("Date")
    opponent = col2.text_input("Opponent")
    add_game = col3.form_submit_button("Add Game", use_container_width=True)
    if add_game:
        ds.create_game(game_date, opponent)
        st.success(f"Game vs {opponent} added — go to Game Day to track it.")
        st.rerun()

games = ds.get_games()
if not games.empty:
    st.dataframe(
        games[["game_date", "opponent", "our_score", "their_score"]]
        .rename(columns={"game_date": "Date", "opponent": "Opponent",
                          "our_score": "Us", "their_score": "Them"}),
        use_container_width=True, hide_index=True,
    )
