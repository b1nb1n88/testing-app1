import streamlit as st
from streamlit_calendar import calendar
from datetime import date, timedelta
import json
import uuid

st.set_page_config(page_title="Office Chores", layout="wide")

# ── Color palette for team members ──────────────────────────────────────
MEMBER_COLORS = [
    "#4A90D9", "#E07B53", "#5BBD72", "#D4A843",
    "#9B6FC3", "#E06B8E", "#4BBFBF", "#7C8EA0",
    "#C75D5D", "#6B8E5D",
]

RECURRENCE_OPTIONS = {
    "none": "One-time",
    "daily": "Daily",
    "weekly": "Weekly",
    "biweekly": "Biweekly",
    "monthly": "Monthly",
}

# ── Session state initialization ────────────────────────────────────────
if "chores" not in st.session_state:
    st.session_state.chores = []  # list of dicts
if "members" not in st.session_state:
    st.session_state.members = []  # list of dicts {id, name, color}
if "completions" not in st.session_state:
    st.session_state.completions = {}  # "choreId:date" -> True


# ── Helper functions ────────────────────────────────────────────────────
def generate_id():
    return str(uuid.uuid4())[:8]


def next_date(d, recurrence):
    if recurrence == "daily":
        return d + timedelta(days=1)
    elif recurrence == "weekly":
        return d + timedelta(weeks=1)
    elif recurrence == "biweekly":
        return d + timedelta(weeks=2)
    elif recurrence == "monthly":
        month = d.month + 1
        year = d.year
        if month > 12:
            month = 1
            year += 1
        day = min(d.day, 28)  # safe for all months
        return date(year, month, day)
    return d


def generate_occurrences(chore, range_start, range_end):
    """Generate all occurrences of a chore within a date range."""
    chore_date = date.fromisoformat(chore["date"])
    if chore["recurrence"] == "none":
        if range_start <= chore_date <= range_end:
            return [(chore, chore["date"])]
        return []

    occurrences = []
    current = chore_date
    # Advance to range start
    while current < range_start:
        current = next_date(current, chore["recurrence"])
    # Collect within range
    while current <= range_end:
        occurrences.append((chore, current.isoformat()))
        current = next_date(current, chore["recurrence"])
    return occurrences


def get_member_map():
    return {m["id"]: m for m in st.session_state.members}


# ── Build calendar events ──────────────────────────────────────────────
def build_calendar_events():
    """Build events list for streamlit-calendar across a wide range."""
    today = date.today()
    range_start = today - timedelta(days=180)
    range_end = today + timedelta(days=365)
    member_map = get_member_map()

    events = []
    for chore in st.session_state.chores:
        for ch, occ_date in generate_occurrences(chore, range_start, range_end):
            comp_key = f"{ch['id']}:{occ_date}"
            done = st.session_state.completions.get(comp_key, False)
            member = member_map.get(ch.get("assigneeId", ""))
            color = member["color"] if member else "#999999"

            title = ch["name"]
            if member:
                title += f" ({member['name']})"
            if done:
                title = f"✓ {title}"

            events.append({
                "title": title,
                "start": occ_date,
                "end": occ_date,
                "allDay": True,
                "backgroundColor": color if not done else "#cccccc",
                "borderColor": color,
                "extendedProps": {
                    "choreId": ch["id"],
                    "occurrenceDate": occ_date,
                    "done": done,
                },
            })
    return events


# ── Layout ──────────────────────────────────────────────────────────────
st.markdown(
    """<h1 style='margin-bottom:0'>Office Chores</h1>
    <p style='color:#888; margin-top:0'>Manage your team's chores</p>""",
    unsafe_allow_html=True,
)

sidebar, main = st.columns([1, 3])

# ── Sidebar ─────────────────────────────────────────────────────────────
with sidebar:

    # — Add Chore —
    st.subheader("Add Chore")
    with st.form("add_chore_form", clear_on_submit=True):
        chore_name = st.text_input("Chore name", placeholder="e.g. Clean kitchen")
        member_options = {m["id"]: m["name"] for m in st.session_state.members}
        assignee = st.selectbox(
            "Assign to",
            options=[""] + list(member_options.keys()),
            format_func=lambda x: member_options.get(x, "Unassigned"),
        )
        chore_date = st.date_input("Date", value=date.today())
        recurrence = st.selectbox(
            "Recurrence",
            options=list(RECURRENCE_OPTIONS.keys()),
            format_func=lambda x: RECURRENCE_OPTIONS[x],
        )
        add_submitted = st.form_submit_button("Add Chore", use_container_width=True, type="primary")
        if add_submitted and chore_name.strip():
            st.session_state.chores.append({
                "id": generate_id(),
                "name": chore_name.strip(),
                "assigneeId": assignee,
                "date": chore_date.isoformat(),
                "recurrence": recurrence,
            })
            st.rerun()

    st.divider()

    # — Team Members —
    st.subheader("Team Members")
    with st.form("add_member_form", clear_on_submit=True):
        member_cols = st.columns([3, 1])
        with member_cols[0]:
            new_member = st.text_input("Name", placeholder="Add member...", label_visibility="collapsed")
        with member_cols[1]:
            member_submitted = st.form_submit_button("+")
        if member_submitted and new_member.strip():
            used_colors = {m["color"] for m in st.session_state.members}
            color = next(
                (c for c in MEMBER_COLORS if c not in used_colors),
                MEMBER_COLORS[len(st.session_state.members) % len(MEMBER_COLORS)],
            )
            st.session_state.members.append({
                "id": generate_id(),
                "name": new_member.strip(),
                "color": color,
            })
            st.rerun()

    for m in st.session_state.members:
        cols = st.columns([0.5, 3, 1])
        with cols[0]:
            st.markdown(
                f'<span style="display:inline-block;width:12px;height:12px;'
                f'border-radius:50%;background:{m["color"]};margin-top:8px"></span>',
                unsafe_allow_html=True,
            )
        with cols[1]:
            st.markdown(f"**{m['name']}**")
        with cols[2]:
            if st.button("✕", key=f"rm_{m['id']}"):
                st.session_state.members = [x for x in st.session_state.members if x["id"] != m["id"]]
                # Unassign from chores
                for ch in st.session_state.chores:
                    if ch["assigneeId"] == m["id"]:
                        ch["assigneeId"] = ""
                st.rerun()

    if not st.session_state.members:
        st.caption("No team members yet")

    st.divider()

    # — Upcoming Chores (next 7 days) —
    st.subheader("Upcoming")
    today = date.today()
    upcoming = []
    member_map = get_member_map()
    for chore in st.session_state.chores:
        for ch, occ_date in generate_occurrences(chore, today, today + timedelta(days=7)):
            comp_key = f"{ch['id']}:{occ_date}"
            done = st.session_state.completions.get(comp_key, False)
            upcoming.append((ch, occ_date, done))
    upcoming.sort(key=lambda x: x[1])

    if upcoming:
        for ch, occ_date, done in upcoming[:10]:
            d = date.fromisoformat(occ_date)
            diff = (d - today).days
            if diff == 0:
                date_label = "Today"
            elif diff == 1:
                date_label = "Tomorrow"
            else:
                date_label = d.strftime("%a, %b %d")
            member = member_map.get(ch.get("assigneeId", ""))
            member_label = f" · {member['name']}" if member else ""

            style = "text-decoration: line-through; opacity: 0.5;" if done else ""
            st.markdown(
                f'<div style="padding:6px 8px;background:#f9f9f9;border-radius:4px;'
                f'border:1px solid #eee;margin-bottom:4px;{style}">'
                f'<div style="font-size:13px;font-weight:500">{ch["name"]}</div>'
                f'<div style="font-size:11px;color:#888">{date_label}{member_label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("No upcoming chores")

# ── Main: Calendar ──────────────────────────────────────────────────────
with main:
    events = build_calendar_events()

    calendar_options = {
        "editable": False,
        "selectable": True,
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "",
        },
        "initialView": "dayGridMonth",
        "fixedWeekCount": False,
        "dayMaxEvents": 4,
        "height": 650,
    }

    custom_css = """
        .fc-event-past { opacity: 0.8; }
        .fc-event { cursor: pointer; font-size: 12px; }
        .fc-daygrid-day-number { font-size: 13px; }
        .fc { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    """

    result = calendar(
        events=events,
        options=calendar_options,
        custom_css=custom_css,
        key="office_chores_calendar",
        callbacks=["eventClick"],
    )

    # — Handle calendar event click: toggle completion —
    if result and result.get("callback") == "eventClick":
        event_data = result.get("eventClick", {}).get("event", {})
        ext = event_data.get("extendedProps", {})
        chore_id = ext.get("choreId")
        occ_date = ext.get("occurrenceDate")
        if chore_id and occ_date:
            comp_key = f"{chore_id}:{occ_date}"
            st.session_state.completions[comp_key] = not st.session_state.completions.get(comp_key, False)
            st.rerun()

    st.divider()

    # — Manage existing chores —
    st.subheader("Manage Chores")
    if st.session_state.chores:
        for i, chore in enumerate(st.session_state.chores):
            member = member_map.get(chore.get("assigneeId", ""))
            member_label = member["name"] if member else "Unassigned"
            rec_label = RECURRENCE_OPTIONS.get(chore["recurrence"], "One-time")
            cols = st.columns([3, 2, 2, 2, 1])
            with cols[0]:
                st.markdown(f"**{chore['name']}**")
            with cols[1]:
                st.caption(member_label)
            with cols[2]:
                st.caption(chore["date"])
            with cols[3]:
                st.caption(rec_label)
            with cols[4]:
                if st.button("Delete", key=f"del_{chore['id']}"):
                    st.session_state.chores = [c for c in st.session_state.chores if c["id"] != chore["id"]]
                    # Clean up completions
                    st.session_state.completions = {
                        k: v for k, v in st.session_state.completions.items()
                        if not k.startswith(f"{chore['id']}:")
                    }
                    st.rerun()
    else:
        st.caption("No chores yet. Add one from the sidebar!")
