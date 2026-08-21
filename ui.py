"""
ui.py
------
Shared presentation helpers: the mobile-friendly CSS, the sideline play clock,
and the small formatting bits used by more than one page.

The play clock deliberately lives in a self-contained HTML/JS component rather
than in Python. Streamlit reruns the whole script on every tap, so a countdown
driven from the server would reset itself every time you logged a snap. This
one runs in the browser and stores its deadline in sessionStorage, so it keeps
ticking straight through Streamlit reruns.
"""

import pandas as pd
import streamlit as st

import data_store as ds

# Streamlit resolves switch_page targets relative to the project root.
GAME_DAY_PAGE = "pages/1_🏈_Game_Day.py"
RULES_PAGE = "pages/4_📖_Rules.py"


def inject_mobile_css():
    """Bigger tap targets and the card styles used by the Equal Play grid."""
    st.markdown(
        """
        <style>
        /* Sideline use means gloves-off, one-handed, in the sun: make every
           button a genuinely large tap target. */
        div.stButton > button {
            min-height: 3rem;
            font-size: 1.05rem;
            font-weight: 600;
            border-radius: 0.6rem;
        }
        div.stButton > button p { font-size: 1.05rem; }

        .roster-card {
            background: rgba(128, 128, 128, 0.12);
            border: 1px solid rgba(128, 128, 128, 0.28);
            border-radius: 0.6rem;
            padding: 0.7rem 0.9rem;
            margin-bottom: 0.5rem;
            font-weight: 600;
            font-size: 1.05rem;
        }

        /* Equal Play Rule status cards */
        .player-card {
            border-radius: 0.6rem;
            padding: 0.6rem 0.75rem;
            margin-bottom: 0.35rem;
            border: 2px solid transparent;
            line-height: 1.35;
        }
        .player-card .pc-name {
            font-weight: 700;
            font-size: 1.1rem;
        }
        .player-card .pc-status {
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }
        .player-card .pc-meta {
            font-size: 0.8rem;
            opacity: 0.85;
        }
        /* Red = still owes a mandatory QB or Runner play. */
        .needs-touch {
            background: rgba(220, 38, 38, 0.18);
            border-color: #dc2626;
            color: #dc2626;
        }
        .needs-touch .pc-name, .needs-touch .pc-meta { color: inherit; }
        /* Green = mandatory play satisfied. */
        .has-touch {
            background: rgba(22, 163, 74, 0.15);
            border-color: #16a34a;
            color: #16a34a;
        }
        .has-touch .pc-name, .has-touch .pc-meta { color: inherit; }

        .sched-badge {
            padding: 0.55rem 0.2rem;
            font-weight: 600;
            font-size: 0.95rem;
            white-space: nowrap;
        }
        .down-pill {
            display: inline-block;
            background: rgba(128, 128, 128, 0.15);
            border: 2px solid rgba(128, 128, 128, 0.35);
            border-radius: 0.5rem;
            padding: 0.35rem 0.8rem;
            margin-right: 0.3rem;
            font-weight: 700;
        }
        .down-pill.active {
            background: rgba(37, 99, 235, 0.2);
            border-color: #2563eb;
            color: #2563eb;
        }
        .timeout-pill {
            display: inline-block;
            font-size: 1.6rem;
            letter-spacing: 0.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_game_label(row):
    """'Sat Aug 29 · 11:00 AM vs W2' — what the game picker shows."""
    try:
        pretty = pd.to_datetime(row["game_date"]).strftime("%a %b %-d")
    except (ValueError, TypeError):
        pretty = str(row["game_date"])
    time = row.get("game_time") or ""
    if pd.isna(time):
        time = ""
    time = f" · {time}" if time else ""
    return f"{pretty}{time} vs {row['opponent']}"


def countdown(seconds, label, storage_key, danger_msg, expired_msg,
              danger_at=5, warn_at=10, height=320):
    """
    A self-contained countdown clock. Used for both the 35-second play clock
    and the 30-second timeout, which is why the label, storage key, and
    messages are all parameters -- two clocks on one page must not share state.
    """
    html = r"""
<!-- self-contained: no external assets, so it works offline on the sideline -->
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
         Roboto, Helvetica, Arial, sans-serif; }
  .wrap {
    background: #0f172a; border-radius: 14px; padding: 14px 14px 16px;
    text-align: center; user-select: none; -webkit-user-select: none;
  }
  .label {
    color: #94a3b8; font-size: 12px; font-weight: 700; letter-spacing: .14em;
    text-transform: uppercase; margin-bottom: 2px;
  }
  .digits {
    font-size: 88px; line-height: 1.02; font-weight: 800; color: #f8fafc;
    font-variant-numeric: tabular-nums;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
  .digits.warn { color: #facc15; }
  .digits.danger { color: #f87171; animation: flash .5s steps(1) infinite; }
  .digits.expired { color: #ef4444; }
  @keyframes flash { 50% { opacity: .35; } }
  .msg { height: 20px; font-size: 13px; font-weight: 700; color: #f87171; }
  .btns { display: flex; gap: 8px; margin-top: 10px; }
  button {
    flex: 1; min-height: 54px; border: 0; border-radius: 10px;
    font-size: 15px; font-weight: 700; cursor: pointer; color: #0f172a;
    background: #e2e8f0; touch-action: manipulation;
  }
  button.go { background: #22c55e; color: #04220f; }
  button:active { transform: translateY(1px); }
</style>
<div class="wrap">
  <div class="label">__LABEL__</div>
  <div id="digits" class="digits">__TOTAL__</div>
  <div id="msg" class="msg"></div>
  <div class="btns">
    <button class="go" id="startBtn">▶ START</button>
    <button id="pauseBtn">⏸ PAUSE</button>
    <button id="resetBtn">↺ RESET</button>
  </div>
</div>
<script>
(function () {
  var TOTAL = __TOTAL__ * 1000;
  var DANGER = __DANGER__ * 1000;
  var WARN = __WARN__ * 1000;
  var KEY_DEADLINE = "__KEY___deadline";
  var KEY_PAUSED = "__KEY___paused";

  // sessionStorage lets the clock survive a Streamlit rerun (every tap on the
  // page re-renders this component). Fall back to memory if it's unavailable.
  var mem = {};
  function store(k, v) {
    try { v === null ? sessionStorage.removeItem(k) : sessionStorage.setItem(k, v); }
    catch (e) { v === null ? delete mem[k] : (mem[k] = v); }
  }
  function load(k) {
    try { return sessionStorage.getItem(k); } catch (e) { return mem[k] || null; }
  }

  var digits = document.getElementById("digits");
  var msg = document.getElementById("msg");

  function remaining() {
    var paused = load(KEY_PAUSED);
    if (paused !== null) return Math.max(0, parseInt(paused, 10));
    var dl = load(KEY_DEADLINE);
    if (dl === null) return TOTAL;
    return Math.max(0, parseInt(dl, 10) - Date.now());
  }

  function render() {
    var ms = remaining();
    var running = load(KEY_DEADLINE) !== null && load(KEY_PAUSED) === null;
    // Tenths under 10s: that last stretch is where the penalty happens.
    digits.textContent = ms >= 10000
      ? String(Math.ceil(ms / 1000))
      : (ms / 1000).toFixed(1);

    digits.className = "digits";
    msg.textContent = "";
    if (ms <= 0) {
      digits.className = "digits expired";
      digits.textContent = "0.0";
      msg.textContent = "__EXPIRED__";
    } else if (ms <= DANGER) {
      digits.className = "digits danger";
      if (running) msg.textContent = "__DANGER__MSG__";
    } else if (ms <= WARN) {
      digits.className = "digits warn";
    }
  }

  document.getElementById("startBtn").onclick = function () {
    store(KEY_PAUSED, null);
    store(KEY_DEADLINE, String(Date.now() + TOTAL));
    render();
  };
  document.getElementById("pauseBtn").onclick = function () {
    if (load(KEY_PAUSED) !== null) {           // resume
      var left = parseInt(load(KEY_PAUSED), 10);
      store(KEY_PAUSED, null);
      store(KEY_DEADLINE, String(Date.now() + left));
    } else if (load(KEY_DEADLINE) !== null) {  // pause
      store(KEY_PAUSED, String(remaining()));
    }
    render();
  };
  document.getElementById("resetBtn").onclick = function () {
    store(KEY_DEADLINE, null);
    store(KEY_PAUSED, null);
    render();
  };

  render();
  setInterval(render, 100);
})();
</script>
"""
    markup = (html
              .replace("__DANGER__MSG__", danger_msg)
              .replace("__EXPIRED__", expired_msg)
              .replace("__LABEL__", label)
              .replace("__KEY__", storage_key)
              .replace("__TOTAL__", str(seconds))
              .replace("__DANGER__", str(danger_at))
              .replace("__WARN__", str(warn_at)))
    # st.iframe superseded st.components.v1.html; requirements.txt still allows
    # older Streamlit, so fall back when it isn't there.
    if hasattr(st, "iframe"):
        st.iframe(markup, height=height)
    else:  # pragma: no cover - older Streamlit
        import streamlit.components.v1 as components
        components.html(markup, height=height)


def play_clock(seconds=None, height=320):
    """
    The 35-second play clock. Big enough to read at arm's length, turns red
    under 5 seconds so you can get the ball snapped before the 3-yard delay of
    game penalty. The referee starts it on the ready-for-play signal.
    """
    # Resolved when called, not in the signature. As a default argument this
    # would read data_store while ui.py is still being imported, so a stale or
    # half-loaded data_store took the entire app down at import instead of
    # failing somewhere recoverable.
    if seconds is None:
        seconds = getattr(ds, "PLAY_CLOCK_SECONDS", 35)
    countdown(
        seconds=seconds, label="Play Clock", storage_key="ffb_pc",
        danger_msg="SNAP IT NOW", expired_msg="⚠ DELAY OF GAME — 3 YARDS",
        height=height,
    )


def timeout_clock(seconds=None, height=320):
    """The 30-second timeout the rule sheet allots — two of them per half."""
    if seconds is None:
        seconds = getattr(ds, "TIMEOUT_SECONDS", 30)
    countdown(
        seconds=seconds, label="Timeout (30s)", storage_key="ffb_to",
        danger_msg="BREAK THE HUDDLE", expired_msg="⏱ TIMEOUT OVER",
        height=height,
    )


# Everything the pages need from data_store. Checked up front so a stale
# deployment (Streamlit Cloud serving an old data_store.py) produces a clear
# instruction instead of an AttributeError halfway down a page.
REQUIRED_DATA_STORE_API = [
    "PLAY_CLOCK_SECONDS", "TIMEOUTS_PER_HALF", "log_touch", "get_game_state",
    "timeouts_left", "use_timeout", "set_half", "get_game_summary",
    "get_game_export", "get_compliance_overview", "undo_last_snap",
]


def check_data_store():
    """Stop with a readable message if data_store is older than these pages."""
    missing = [n for n in REQUIRED_DATA_STORE_API if not hasattr(ds, n)]
    if missing:
        st.error(
            "**This deployment is out of date.** The app pages are newer than "
            f"`data_store.py`, which is missing: `{'`, `'.join(missing)}`.\n\n"
            "On Streamlit Community Cloud: open **Manage app → ⋮ → Reboot app** "
            "(or *Clear cache*, then reboot) to force a fresh checkout. "
            "Running locally, `git pull` and restart Streamlit."
        )
        st.stop()


def rules_sidebar():
    """The in-game quick reference. Full text lives on the Rules page."""
    with st.sidebar:
        st.header("📋 League Rules Quick Ref")
        st.error(
            "⚠️ **EQUAL PLAY RULE:** Every player must play an equal amount of "
            "time, and **must** run the ball or play quarterback for at least "
            "one snap each game."
        )
        st.info(
            f"⏱️ **TIMING:** Two {ds.HALF_LENGTH_MINUTES}-minute halves, "
            f"{ds.HALFTIME_BREAK_MINUTES}-minute break. Clock runs continuously "
            "for the first 19 minutes of each half. One-minute warning, then "
            "the clock stops per high school rules. **No overtime.**"
        )
        st.success(
            "🔄 **NO CENTER SNAP:** The QB lines up behind the center and "
            "**already has the ball** to start play. **All players are "
            "eligible receivers. NO motion.**"
        )
        st.warning(
            "🛑 **PENALTIES:** 3-yard (off-side, false start, delay of game, "
            "flag guarding, illegal forward pass) · 6-yard (tackling, "
            "obstruction, illegal screen, charging, roughing the passer, "
            "personal foul, pass interference)."
        )
        st.caption(
            f"**Timeouts:** {ds.TIMEOUTS_PER_HALF} per half, "
            f"{ds.TIMEOUT_SECONDS} seconds each · "
            f"**Play clock:** {ds.PLAY_CLOCK_SECONDS} sec · "
            f"**{ds.PLAYERS_ON_FIELD} players** a side · "
            f"**Scoring:** TD 6, try 1 (3 yd) or 2 (7 yd), safety 2 · "
            f"**Mercy rule:** {ds.MERCY_RULE_TD_MARGIN}+ TDs ahead at the "
            "second-half one-minute warning."
        )
        # No st.page_link here: Streamlit's own sidebar nav already lists the
        # Rules page, and page_link needs the multipage registry, which isn't
        # there when a page is opened on its own.
