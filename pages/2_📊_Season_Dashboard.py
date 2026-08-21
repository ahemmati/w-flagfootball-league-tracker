import streamlit as st

import pandas as pd

import data_store as ds
from ui import inject_mobile_css, check_data_store, rules_sidebar

st.set_page_config(page_title="Season Dashboard", page_icon="📊", layout="wide")
check_data_store()
ds.init_db()
inject_mobile_css()

st.title("📊 Season Dashboard")
st.caption(f"{ds.TEAM_NAME} · Team {ds.TEAM_CODE} · Mt. Bethel W League")

rules_sidebar()

# ------------------------------------------------------------- Record ----
games = ds.get_games(ascending=True)
results = []
for g in games.itertuples():
    us, them = ds.get_score(g.game_id)
    if us == 0 and them == 0:
        continue
    results.append({
        "Date": g.game_date, "Opponent": g.opponent,
        f"{ds.TEAM_NAME}": us, "Them": them,
        "Result": "W" if us > them else ("L" if us < them else "T"),
    })

if results:
    rec = pd.DataFrame(results)
    w = int((rec["Result"] == "W").sum())
    l = int((rec["Result"] == "L").sum())
    t = int((rec["Result"] == "T").sum())
    m1, m2, m3 = st.columns(3)
    m1.metric("Record", f"{w}-{l}" + (f"-{t}" if t else ""))
    m2.metric("Points for", int(rec[ds.TEAM_NAME].sum()))
    m3.metric("Points against", int(rec["Them"].sum()))
    st.dataframe(rec, width="stretch", hide_index=True)
    st.divider()

season = ds.get_season_summary()
played = season[season["Total Plays"] > 0] if not season.empty else season

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
st.subheader("Total plays per player")
st.caption("A gut-check on whether playing time is staying balanced season-long.")
st.bar_chart(played.set_index("Player")["Total Plays"])

st.subheader("Ball touches per player (QB + Runner)")
st.caption("The other half of the rule: who is actually getting the ball.")
st.bar_chart(played.set_index("Player")["Total Touches"])

st.subheader("Full season stats")
st.dataframe(season, width="stretch", hide_index=True)

st.divider()

# ------------------------------------------------------------ Penalties ----
all_pens = []
for g in ds.get_games(ascending=True).itertuples():
    pens = ds.get_penalties(g.game_id)
    if pens.empty:
        continue
    ours = pens[pens["team"] == "us"]
    all_pens.append({
        "Date": g.game_date, "Opponent": g.opponent,
        "Our penalties": len(ours), "Our yards": int(ours["yards"].sum()),
    })
if all_pens:
    st.subheader("🛑 Penalties")
    pen_df = pd.DataFrame(all_pens)
    st.dataframe(pen_df, width="stretch", hide_index=True)
    st.caption(
        f"{int(pen_df['Our penalties'].sum())} penalties against us this season, "
        f"{int(pen_df['Our yards'].sum())} yards."
    )
    st.divider()

# -------------------------------------------------- End-of-season notes ----
st.subheader("End-of-season notes")
st.caption("Auto-drafted one-liners per player — edit freely before you use them.")

for _, p in played.iterrows():
    blurb = (
        f"**{p['Player']}** — played {int(p['Games Played'])} game(s), "
        f"{int(p['Total Plays'])} total plays"
    )
    extras = []
    if p["QB Plays"] > 0:
        extras.append(f"played {int(p['QB Plays'])} play(s) at QB")
    if p["Runner Plays"] > 0:
        extras.append(f"carried the ball {int(p['Runner Plays'])} time(s)")
    if p["Touchdowns"] > 0:
        extras.append(f"scored {int(p['Touchdowns'])} touchdown(s)")
    if extras:
        blurb += ", " + ", ".join(extras)
    st.write(blurb + ".")
