import streamlit as st
import data_store as ds

st.set_page_config(page_title="Season Dashboard", page_icon="📊", layout="wide")
ds.init_db()

st.title("📊 Season Dashboard")

season = ds.get_season_summary()
if season.empty:
    st.info("No data yet — log some plays on the Game Day page first.")
    st.stop()

st.subheader("Total snaps per player this season")
st.caption("A quick visual gut-check on whether playing time is staying balanced across the season.")
chart_df = season.set_index("Player")["Total Snaps"]
st.bar_chart(chart_df)

st.subheader("Full season stats")
st.dataframe(season, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Per-game rule compliance")
st.caption("Which games had a player miss the 'must QB or run at least once' rule.")

games = ds.get_games()
for row in games.itertuples():
    summary = ds.get_game_summary(row.game_id)
    if summary.empty:
        continue
    missed = summary[~summary["Met QB/Runner Rule"]]["Player"].tolist()
    if missed:
        st.write(f"**{row.game_date} vs {row.opponent}:** {', '.join(missed)} didn't get a QB/Runner snap.")

st.divider()
st.subheader("End-of-season notes")
st.caption("Auto-drafted one-liners per player — edit freely before you use them.")

for _, p in season.iterrows():
    blurb = (
        f"**{p['Player']}** — played {int(p['Games Played'])} game(s), "
        f"{int(p['Total Snaps'])} total snaps"
    )
    extras = []
    if p["QB Snaps"] > 0:
        extras.append(f"took {int(p['QB Snaps'])} snap(s) at QB")
    if p["Runner Snaps"] > 0:
        extras.append(f"carried the ball {int(p['Runner Snaps'])} time(s)")
    if p["Touchdowns"] > 0:
        extras.append(f"scored {int(p['Touchdowns'])} touchdown(s)")
    if extras:
        blurb += ", " + ", ".join(extras)
    blurb += "."
    st.write(blurb)
