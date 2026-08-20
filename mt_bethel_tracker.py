import streamlit as st
import pandas as pd
import time

# --- STYLES & SETUP ---
st.set_page_config(
    page_title="Mt. Bethel W-League Sideline Tracker",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App Title & Description
st.title("🏈 Mt. Bethel W-League Sideline Tracker")
st.markdown("""
This app is designed for **1st and 2nd Grade Flag Football Coaches** to manage rosters and track league-mandated touches in real-time on the sideline.
""")

# --- MANDATORY RULES REFERENCE PANEL ---
with st.sidebar:
    st.header("📋 League Rules Quick Ref")
    st.error("⚠️ **EQUAL PLAY RULE:** Every player must play an equal amount of time. Every player **must** either run the ball or play quarterback for at least one snap each game.")
    st.info("⏱️ **TIMING:** Two 20-minute halves. Continuous clock until the final 1 minute of each half. 35-second play clock.")
    st.success("🔄 **NO CENTER SNAP:** QB starts with the ball already in possession (no snap). Center is immediately eligible to run a route.")
    st.warning("🛑 **PENALTIES:** 3-Yard (Dead Ball / Technical) or 6-Yard (Live Ball / Contact / Physical).")

# --- SESSION STATE INITIALIZATION ---
if 'roster' not in st.session_state:
    # Default placeholder roster for quick start
    st.session_state.roster = [
        {"name": "Alex", "qb_snaps": 0, "run_snaps": 0, "total_snaps": 0},
        {"name": "Benny", "qb_snaps": 0, "run_snaps": 0, "total_snaps": 0},
        {"name": "Charlie", "qb_snaps": 0, "run_snaps": 0, "total_snaps": 0},
        {"name": "Danny", "qb_snaps": 0, "run_snaps": 0, "total_snaps": 0},
        {"name": "Eli", "qb_snaps": 0, "run_snaps": 0, "total_snaps": 0},
        {"name": "Finley", "qb_snaps": 0, "run_snaps": 0, "total_snaps": 0},
        {"name": "Gavin", "qb_snaps": 0, "run_snaps": 0, "total_snaps": 0}
    ]

if 'half' not in st.session_state:
    st.session_state.half = 1

if 'timeouts' not in st.session_state:
    st.session_state.timeouts = 2

# --- ROSTER MANAGEMENT SECTION ---
st.header("👥 Team Roster")
new_player = st.text_input("Add New Player to Roster:", placeholder="Enter player name...")
if st.button("Add Player") and new_player.strip() != "":
    # Check if duplicate
    if any(p['name'].lower() == new_player.strip().lower() for p in st.session_state.roster):
        st.warning("Player already on the roster!")
    else:
        st.session_state.roster.append({
            "name": new_player.strip(),
            "qb_snaps": 0,
            "run_snaps": 0,
            "total_snaps": 0
        })
        st.success(f"Added {new_player.strip()}!")
        st.rerun()

# --- GAME CONTROLS & TIMING ---
st.header("⏱️ Sideline Game Clock & Timeouts")
col_t1, col_t2, col_t3 = st.columns(3)

with col_t1:
    st.metric("Current Period", f"Half {st.session_state.half}")
    if st.button("Switch to 2nd Half"):
        st.session_state.half = 2
        st.session_state.timeouts = 2  # Reset timeouts for 2nd half
        st.success("Switched to Half 2! Timeouts reset to 2.")
        st.rerun()

with col_t2:
    st.metric("Timeouts Remaining", f"{st.session_state.timeouts} / 2")
    if st.button("Use Timeout") and st.session_state.timeouts > 0:
        st.session_state.timeouts -= 1
        st.success("Timeout called! (30 seconds starts now)")
        st.rerun()

with col_t3:
    st.subheader("⏱️ 35s Play Clock")
    # Quick client-side HTML play-clock button to avoid server refresh latency on a phone
    play_clock_html = """
    <div style="text-align: center;">
        <button id="timer-btn" onclick="startTimer()" style="
            background-color: #ff4b4b; 
            color: white; 
            border: none; 
            padding: 10px 20px; 
            font-size: 16px; 
            border-radius: 5px; 
            cursor: pointer;
            width: 100%;
            font-weight: bold;
        ">⏱️ Start 35s Play Clock</button>
        <h1 id="countdown" style="font-size: 48px; margin: 10px 0; color: #31333F;">35</h1>
    </div>

    <script>
        var timer;
        function startTimer() {
            clearInterval(timer);
            var timeLeft = 35;
            var countdownEl = document.getElementById("countdown");
            var btn = document.getElementById("timer-btn");
            countdownEl.style.color = "#31333F";
            btn.disabled = true;
            btn.style.backgroundColor = "#cccccc";
            
            timer = setInterval(function() {
                timeLeft--;
                countdownEl.innerHTML = timeLeft;
                
                if (timeLeft <= 5) {
                    countdownEl.style.color = "red";
                }
                
                if (timeLeft <= 0) {
                    clearInterval(timer);
                    countdownEl.innerHTML = "DELAY!";
                    btn.disabled = false;
                    btn.style.backgroundColor = "#ff4b4b";
                }
            }, 1000);
        }
    </script>
    """
    st.components.v1.html(play_clock_html, height=130)

# --- TRACKING TABLE ---
st.header("📊 Equal Play & Ball Carrier Tracker")
st.markdown("Track snaps and verify that **every kid** has played and gotten either a **QB snap** or a **Run snap** (W-League mandate).")

# Calculate compliance stats
total_players = len(st.session_state.roster)
compliant_players = sum(1 for p in st.session_state.roster if p['qb_snaps'] > 0 or p['run_snaps'] > 0)
compliance_percentage = (compliant_players / total_players * 100) if total_players > 0 else 100

st.progress(compliance_percentage / 100, text=f"**League Rule Compliance: {compliant_players} / {total_players} players tracked ({compliance_percentage:.0f}%)**")

# Grid layout for sideline tap-friendliness
st.markdown("---")
for idx, player in enumerate(st.session_state.roster):
    # Rule check: Has the player received at least one running or QB play?
    is_compliant = player['qb_snaps'] > 0 or player['run_snaps'] > 0
    bg_color = "#d4edda" if is_compliant else "#f8d7da"
    text_color = "#155724" if is_compliant else "#721c24"
    status_label = "✅ COMPLIANT" if is_compliant else "❌ NEEDS TOUCH"

    # Container with visual color status
    st.markdown(
        f'<div style="background-color: {bg_color}; padding: 10px; border-radius: 5px; margin-bottom: 5px; border-left: 5px solid {text_color};">'
        f'<span style="color: {text_color}; font-weight: bold; font-size: 16px;">{player["name"]}</span> — '
        f'<span style="color: {text_color}; font-size: 14px;">{status_label} | Total Snaps: {player["total_snaps"]}</span>'
        f'</div>', 
        unsafe_allow_name=True
    )

    col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 1.5, 1.5, 1])
    
    with col1:
        st.write(f"**QB Plays:** {player['qb_snaps']}")
        if st.button("➕ QB Play", key=f"qb_plus_{idx}"):
            st.session_state.roster[idx]['qb_snaps'] += 1
            st.session_state.roster[idx]['total_snaps'] += 1
            st.rerun()
            
    with col2:
        st.write(f"**Run Plays:** {player['run_snaps']}")
        if st.button("➕ Run Play", key=f"run_plus_{idx}"):
            st.session_state.roster[idx]['run_snaps'] += 1
            st.session_state.roster[idx]['total_snaps'] += 1
            st.rerun()

    with col3:
        st.write(f"**Other Snap:** (Defense/Block)")
        if st.button("➕ Other Snap", key=f"other_plus_{idx}"):
            st.session_state.roster[idx]['total_snaps'] += 1
            st.rerun()

    with col4:
        st.write("**Correction:**")
        if st.button("➖ Subtract Snap", key=f"sub_{idx}"):
            if st.session_state.roster[idx]['total_snaps'] > 0:
                st.session_state.roster[idx]['total_snaps'] -= 1
                # Subtract from runs first, then QBs if possible
                if st.session_state.roster[idx]['run_snaps'] > 0:
                    st.session_state.roster[idx]['run_snaps'] -= 1
                elif st.session_state.roster[idx]['qb_snaps'] > 0:
                    st.session_state.roster[idx]['qb_snaps'] -= 1
                st.rerun()

    with col5:
        st.write("**Remove:**")
        if st.button("🗑️ Remove", key=f"del_{idx}"):
            st.session_state.roster.pop(idx)
            st.rerun()
            
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

# --- EXPORT & RESET CONTROLS ---
st.header("⚙️ Game Actions")
col_b1, col_b2 = st.columns(2)

with col_b1:
    # Convert session state to DataFrame for CSV download
    df = pd.DataFrame(st.session_state.roster)
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Roster & Stats (CSV)",
            data=csv,
            file_name="mt_bethel_game_stats.csv",
            mime="text/csv"
        )

with col_b2:
    if st.button("⚠️ Reset All Stats & Game"):
        for p in st.session_state.roster:
            p['qb_snaps'] = 0
            p['run_snaps'] = 0
            p['total_snaps'] = 0
        st.session_state.half = 1
        st.session_state.timeouts = 2
        st.success("All game stats reset!")
        st.rerun()
