import streamlit as st

import data_store as ds
from ui import inject_mobile_css, format_game_label

st.set_page_config(page_title="Export", page_icon="📋", layout="wide")
ds.init_db()
inject_mobile_css()

st.title("📋 Export Game Data")
st.caption(
    "One tap gets you a clean CSV of player touches and snaps — at the end of "
    "a game or any time. Worth doing after every game: if this app is ever "
    "redeployed on Streamlit Cloud, the local database file can reset, and "
    "these downloads are your season's safety net."
)

# ------------------------------------------------------- Per-game export ----
st.subheader("Single game")

games = ds.get_games(ascending=False)
if games.empty:
    st.info("No games scheduled yet.")
else:
    labels = [format_game_label(row) for _, row in games.iterrows()]
    choice = st.selectbox(
        "Game", options=list(range(len(games))), format_func=lambda i: labels[i]
    )
    game_row = games.iloc[choice]
    game_id = int(game_row["game_id"])

    export_df = ds.get_game_export(game_id)
    if export_df.empty:
        st.info("Nothing logged for this game yet.")
    else:
        not_met = int((export_df["Equal Play Rule"] == "NOT MET").sum())
        if not_met:
            st.warning(
                f"⚠️ {not_met} player(s) did not get their mandatory QB or "
                "Runner play in this game."
            )
        else:
            st.success("✅ Equal Play Rule met by every player in this game.")

        st.download_button(
            "⬇️ Download This Game's CSV",
            export_df.to_csv(index=False),
            file_name=f"game_{game_row['game_date']}_vs_{game_row['opponent']}.csv",
            mime="text/csv", width="stretch", type="primary",
        )
        st.dataframe(export_df, width="stretch", hide_index=True)

st.divider()

# ---------------------------------------------------------- Season export ----
st.subheader("Whole season")

season = ds.get_season_summary()
if not season.empty:
    st.download_button(
        "⬇️ Download Season Summary CSV",
        season.to_csv(index=False),
        file_name="season_summary.csv", mime="text/csv",
        width="stretch", type="primary",
    )
    st.dataframe(season, width="stretch", hide_index=True)

overview = ds.get_compliance_overview()
if not overview.empty:
    st.download_button(
        "⬇️ Download Equal Play Compliance CSV",
        overview.to_csv(index=False),
        file_name="equal_play_compliance.csv", mime="text/csv",
        width="stretch",
    )

st.divider()

# ------------------------------------------------------------- Raw backup ----
with st.expander("Raw table backup (players / games / every logged snap)"):
    players, all_games, snaps = ds.get_export_dataframes()
    c1, c2, c3 = st.columns(3)
    c1.download_button(
        "⬇️ Players CSV", players.to_csv(index=False),
        file_name="players.csv", mime="text/csv", width="stretch",
    )
    c2.download_button(
        "⬇️ Games CSV", all_games.to_csv(index=False),
        file_name="games.csv", mime="text/csv", width="stretch",
    )
    c3.download_button(
        "⬇️ Raw Snap Log CSV", snaps.to_csv(index=False),
        file_name="snaps.csv", mime="text/csv", width="stretch",
    )
