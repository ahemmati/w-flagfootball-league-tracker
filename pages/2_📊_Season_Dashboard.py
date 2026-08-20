import streamlit as st

import data_store as ds
from ui import inject_mobile_css

st.set_page_config(page_title="Season Dashboard", page_icon="📊", layout="wide")
ds.init_db()
inject_mobile_css()

st.title("📊 Season Dashboard")

season = ds.get_season_summary()
played = season[season["Total Snaps"] > 0] if not season.empty else season

# ------------------------------------------------- Compliance at a glance ----
st.subheader("⚖️ Equal Play Rule — every game")
st.caption(
    "A game is Compliant once every player has taken a snap at QB or carried "
    "the ball at least once."
)

overview = ds.get_compliance_overview()
if overview.empty:
    st.info("No games scheduled yet.")
else:
    tracked = overview[overview["Status"] != "Not started"]
    if not tracked.empty:
        compliant = int((tracked["Status"] == "Compliant").sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Games tracked", len(tracked))
        c2.metric("Compliant", compliant)
        c3.metric("Need touches", len(tracked) - compliant)

    st.dataframe(
        overview.rename(columns={"Still Needs Touch": "Still Needs a Touch"}),
        width="stretch", hide_index=True,
    )

st.divider()

if played.empty:
    st.info("No plays logged yet — track a game on the Game Day page first.")
    st.stop()

# ------------------------------------------------------- Playing time ----
st.subheader("Total snaps per player")
st.caption("A gut-check on whether playing time is staying balanced season-long.")
st.bar_chart(played.set_index("Player")["Total Snaps"])

st.subheader("Ball touches per player (QB + Runner)")
st.caption("The other half of the rule: who is actually getting the ball.")
st.bar_chart(played.set_index("Player")["Total Touches"])

st.subheader("Full season stats")
st.dataframe(season, width="stretch", hide_index=True)

st.divider()

# -------------------------------------------------- End-of-season notes ----
st.subheader("End-of-season notes")
st.caption("Auto-drafted one-liners per player — edit freely before you use them.")

for _, p in played.iterrows():
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
    st.write(blurb + ".")
