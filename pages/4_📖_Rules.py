import streamlit as st

import data_store as ds
from ui import inject_mobile_css

st.set_page_config(page_title="Rules", page_icon="📖", layout="wide")
ds.init_db()
inject_mobile_css()

st.title("📖 W League Rules")
st.caption(
    "Mt. Bethel Church · W League (1st and 2nd Grade) Flag Football · "
    f"Team {ds.TEAM_CODE} — {ds.TEAM_NAME}. "
    "Full reference; the sidebar on other pages carries the short version."
)

# The two rules this app actively tracks get top billing.
st.error(
    "### ⚠️ Playing Time — the rule this app tracks\n"
    "Every player must play an **equal amount of time**. Every player must "
    "**either run the ball or play quarterback for at least one snap each "
    "game**.\n\n"
    "**Only two actions satisfy it:**\n"
    "1. **Running the ball**\n"
    "2. **Playing quarterback**\n\n"
    "Every player on the roster must do at least one of those, at least once, "
    "every game. Other common offensive actions — **playing center, blocking, "
    "or catching a pass** (including catching a touchdown) — do **not** count "
    "toward this rule, though they do count toward equal playing time.\n\n"
    "→ The Game Day page flags anyone still owed their mandatory play in red."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Players a side", ds.PLAYERS_ON_FIELD)
c2.metric("Halves", f"{ds.HALVES} × {ds.HALF_LENGTH_MINUTES} min")
c3.metric("Timeouts", f"{ds.TIMEOUTS_PER_HALF}/half · {ds.TIMEOUT_SECONDS}s")
c4.metric("Play clock", f"{ds.PLAY_CLOCK_SECONDS} sec")

st.success(
    "### 🔄 No center snap\n"
    "**For W League only, there is no center snap.** The QB lines up behind "
    "the center and **already has possession of the ball to start play**.\n\n"
    "→ That's why this app counts field time in **plays**, not snaps."
)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("The Basics")
    st.markdown(
        f"""
- **Ball size:** Pee Wee.
- **The game:** two teams of **{ds.PLAYERS_ON_FIELD} players** each.
- **Field:** {ds.FIELD_WIDTH_YARDS} yards wide × {ds.FIELD_LENGTH_YARDS} yards
  long — four **{ds.ZONE_YARDS}-yard zones** and two **{ds.END_ZONE_YARDS}-yard
  end zones**.
- **Pants/shorts:** no belts, belt loops, pockets, or exposed draw strings, and
  a different colour than the flags.
- **The opening:** coin toss decides home and away; the home team leads the
  prayer before each game.
- **Captains meeting:** 5 minutes before kickoff, two captains per team. The
  visiting team calls the toss. The winner takes the first-half option or
  defers to the second half — either (1) offense/defense, or (2) which goal to
  defend.
- **Coaches on field:** for all **9 games**, one coach on the field for
  offense and defense, at least **five yards back** from the quarterback once
  the huddle breaks. First violation is a warning, each one after that is a
  3-yard penalty.
"""
    )

    st.subheader("Timing & Clock")
    st.markdown(
        f"""
- Two **{ds.HALF_LENGTH_MINUTES}-minute halves**, with a
  **{ds.HALFTIME_BREAK_MINUTES}-minute break** between them.
- The clock runs continuously for the first **19 minutes** of each half, and
  stops only after: the extra-point attempt (restarts on the next offensive
  snap), a safety (on the snap), a team timeout (on the snap), or a referee's
  timeout (on the ready for play).
- A **one-minute warning** is given to both teams near the end of each half.
  During that final minute the clock stops per high school rules — incomplete
  passes, out of bounds, penalties, first downs.
- **No overtime.**
- **Timeouts:** {ds.TIMEOUTS_PER_HALF} per half, **{ds.TIMEOUT_SECONDS} seconds** each.
- **{ds.PLAY_CLOCK_SECONDS}-second clock:** once the ball is placed for a down,
  the referee's ready-to-play signal starts it.
- **Mercy rule:** if a team is **{ds.MERCY_RULE_TD_MARGIN} or more touchdowns
  ahead** when the referee announces the one-minute warning of the second half,
  the clock runs without stopping.
"""
    )

    st.subheader("Scoring")
    st.markdown(
        """
The rule sheet states exactly two ways to put points on the board:

- **Touchdown — 6 points.** The runner advances from the field of play so the
  ball breaks the vertical plane of the opponent's goal line.
- **The Try / extra point — 1 or 2 points.** After a touchdown the offense
  attempts a try from scrimmage. The referee asks the offense beforehand, and
  the coach must choose **before the play**: from the **3-yard line for 1
  point**, or the **7-yard line for 2 points**. Once chosen it can only be
  changed if either team takes a timeout, and it **cannot** be changed because
  a penalty occurs.
"""
    )
    st.info(
        "**Safety — no point value given.** The sheet mentions a safety only "
        "as something that stops the clock (*\"Safety - starts on the snap\"*) "
        "and never says what it's worth. Under the NIRSA and NFHS rule books "
        "the sheet defers to, a safety is **2 points**, which is what this app "
        "defaults to — but you can change the number when you log one, and it "
        "is worth settling at the captains meeting."
    )

with right:
    st.subheader("Play")
    st.markdown(
        f"""
- **No center snap** (W League only): the QB lines up behind the center and
  **starts the play already holding the ball**.
- **No kick-off:** the receiving team starts on its **own {ds.START_YARD_LINE}-yard line**.
- **Line of scrimmage:** the defense observes a **3-yard neutral zone** (yellow
  disc) once the referee places the ball.
- **First downs:** **{ds.DOWNS_PER_SERIES} consecutive downs** to move the ball
  across the next zone line to gain. The most forward point of the ball when
  declared dead decides it. Losing yardage behind the line to gain doesn't move
  the line — you still have to cross the original one.
- **Downing a runner:** flag belt legally removed; or a one-hand tag between
  shoulders and knees once the belt is gone; or any part of the body other than
  a hand or foot touching the ground.
- **Passing:** every player on the field is an eligible receiver. One forward
  pass per down, thrown from **behind** the line. A player who passes to
  himself makes the ball dead at the spot he threw from.
- **Catches:** one foot in bounds with control, end line included.
- **Ball carrier:** may not leave his feet or jump to avoid a tackle or to lunge
  for the line to gain. Spin moves are the official's judgement.
- **Jumping:** the defense may jump to deflect a pass; receivers may jump to catch one.
- **Fumble / backward pass / lateral:** dead the moment it hits the ground,
  belonging to whoever had it last, spotted where it landed. Fumbled forward,
  it's spotted where the runner last had it.
- **Screen blocking:** obstruct without initiating contact — **hands behind the
  back**.
- **NO motion in W League.**
"""
    )

    st.subheader("Scrimmage Kick (Punt)")
    st.markdown(
        f"""
On fourth down the referee asks the offense whether they'll play or kick, and
announces it to the defense.

- No rushing or blocking of the kick; the **defense may advance** it.
- Once the ball hits the turf it's dead — the offense takes over where it
  **first hit**, not where it stops.
- The punter may kick from the line of scrimmage but may not cross it.
- Alternatively, take the ball placed **25 yards** from the scrimmage line, with
  no defensive advance — but never inside the defense's
  {ds.START_YARD_LINE}-yard line. More than 25 yards inside the
  {ds.START_YARD_LINE} is a touchback.
"""
    )

st.divider()

st.subheader("🛑 Fouls and Penalties")
pen_left, pen_right = st.columns(2)

with pen_left:
    st.markdown("#### 3-Yard Penalties")
    st.markdown(
        """
- **Off-side / Illegal Procedure** — entering the neutral zone after the ready
  for play and before the snap. Dead ball foul.
- **False Start** — offensive movement simulating the snap. Dead ball foul.
- **Delay of Game** — violating the play clock. Dead ball foul.
- **Flag Guarding or Stiff Arming** — using arms, hands, or the ball to protect
  the flags.
- **Illegal Forward Pass** — the passer's foot beyond the line; the passer
  catching his own pass; or more than one forward pass in a down.
"""
    )

with pen_right:
    st.markdown("#### 6-Yard Penalties")
    st.markdown(
        """
- **Tackling / Tripping / Holding.**
- **Obstruction of Runner** — holding, grasping, or obstructing a runner's
  forward progress while removing the flag or making a tag.
- **Illegal Screen Blocking** — any use of hands, arms, elbows, legs, or body to
  initiate contact. A blocker may use a hand or arm to break a fall or keep
  balance.
- **Running Over a Player or Charging** — it's the runner's job to avoid a
  defender who has established and held position.
- **Roughing the Passer** — the defense may bat the ball down but may not touch
  the passer.
- **Personal Fouls** — unsportsmanlike conduct, unnecessary roughness. Flagrant
  fouls bring ejection and possible suspension.
- **Pass Interference** — intentionally obstructing an eligible receiver,
  including holding, tripping, or pulling the arms. Applies to **both** offense
  and defense.
"""
    )

st.divider()

st.caption(
    "**General governance:** any rule not covered here falls under the NIRSA "
    "flag football rule book and the High School National Federation Football "
    "Rule Book."
)

st.warning(
    "**One inconsistency in the rule sheet, worth knowing before you argue it "
    "with an official.** The *Thirty-Five Second Clock (Rule Change)* section "
    f"sets a {ds.PLAY_CLOCK_SECONDS}-second clock, but the *Delay of Game* "
    "penalty still describes “violation of the **25** second clock.” The "
    f"“(Rule Change)” label suggests {ds.PLAY_CLOCK_SECONDS} is the current "
    "number and the penalty text simply wasn't updated, so this app counts "
    f"down from {ds.PLAY_CLOCK_SECONDS}. Worth confirming with your referee at "
    "the captains meeting."
)
