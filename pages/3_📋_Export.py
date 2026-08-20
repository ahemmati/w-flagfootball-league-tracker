import streamlit as st
import data_store as ds

st.set_page_config(page_title="Export", page_icon="📋", layout="wide")
ds.init_db()

st.title("📋 Export / Backup")
st.caption(
    "Download a backup after each game. This matters more than it sounds like: "
    "if this app is ever redeployed on Streamlit Cloud, the local database file "
    "can reset. These downloads are your season's safety net until the app is "
    "wired up to a persistent backend."
)

players, games, snaps = ds.get_export_dataframes()

col1, col2, col3 = st.columns(3)
col1.download_button(
    "⬇️ Download Players CSV", players.to_csv(index=False),
    file_name="players.csv", mime="text/csv", use_container_width=True,
)
col2.download_button(
    "⬇️ Download Games CSV", games.to_csv(index=False),
    file_name="games.csv", mime="text/csv", use_container_width=True,
)
col3.download_button(
    "⬇️ Download Raw Snap Log CSV", snaps.to_csv(index=False),
    file_name="snaps.csv", mime="text/csv", use_container_width=True,
)

season = ds.get_season_summary()
if not season.empty:
    st.divider()
    st.subheader("Season summary (what you'd hand to another coach)")
    st.download_button(
        "⬇️ Download Season Summary CSV", season.to_csv(index=False),
        file_name="season_summary.csv", mime="text/csv",
    )
    st.dataframe(season, use_container_width=True, hide_index=True)
