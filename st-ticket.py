import time
import requests

import requests
import streamlit as st
from collections import defaultdict
from datetime import datetime, timedelta

st.set_page_config(page_title="Ticket Users Visualizer", page_icon="🎫")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

:root {
    --kz-navy:  #1e4385;
    --kz-gold:  #ffc727;
    --kz-dark:  #1e0a3c;
    --kz-gray:  #6f7287;
    --kz-border: #cbd5e0;
    --kz-bg:    #f8f7fa;
    --kz-shadow: 0 5px 10px rgba(154,160,185,.06), 0 15px 40px rgba(166,173,201,.18);
}

/* ── Global font ─────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ── App background ──────────────────────────────── */
.stApp { background-color: var(--kz-bg) !important; }

/* ── Sidebar ─────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: var(--kz-dark) !important;
    background-image: url('https://kidzania-sg.thecoolmelon.com/static/media/brick-bg.2e8ac85639cab660df03.png');
    background-size: 220px;
    background-blend-mode: soft-light;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p {
    color: rgba(255,255,255,.85) !important;
}
section[data-testid="stSidebar"] input[type="number"] {
    background: rgba(255,255,255,.1) !important;
    border-color: rgba(255,255,255,.25) !important;
    color: white !important;
    border-radius: 8px !important;
}

/* ── Headings ────────────────────────────────────── */
h1 { color: var(--kz-navy) !important; font-weight: 700 !important; }
h2, h3 { color: var(--kz-navy) !important; }

/* ── Bordered containers (ticket cards) ──────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
    border: 1.5px solid var(--kz-border) !important;
    box-shadow: var(--kz-shadow) !important;
    background: white !important;
}

/* ── Expanders ───────────────────────────────────── */
[data-testid="stExpander"] {
    border-radius: 10px !important;
    border: 1px solid var(--kz-border) !important;
    background: white !important;
}

/* ── Subheader accent line ───────────────────────── */
[data-testid="stHeadingWithActionElements"] h2,
[data-testid="stHeadingWithActionElements"] h3 {
    border-left: 4px solid var(--kz-gold);
    padding-left: 10px;
}

/* ── Warning / info / error boxes ───────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
}

/* ── Hide sidebar & header ───────────────────────── */
section[data-testid="stSidebar"] { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }

/* ── Sticky ticket ID bar ────────────────────────── */
div:has(> div[data-testid="stNumberInput"]) {
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--kz-bg);
    padding: 1.6rem;
    border-bottom: 2px solid var(--kz-gold);
    box-shadow: 0 3px 14px rgba(30,10,60,0.07);
}
</style>
""", unsafe_allow_html=True)

def createbutton(text,link):
    st.markdown(f"""
    <style>
    .modern-button {{
        display: inline-block;
        padding: 0.6em 1.4em;
        font-size: 15px;
        font-weight: 600;
        color: white !important;
        background: #1e4385;
        border-radius: 10px;
        text-decoration: none !important;
        transition: all 0.22s ease;
        box-shadow: 0 4px 14px rgba(30,67,133,0.25);
    }}

    .modern-button:hover {{
        color: white !important;
        text-decoration: none !important;
        background: #163269;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(30,67,133,0.35);
    }}

    .modern-button:visited {{
        color: white !important;
    }}
    </style>

    <a href="{link}" target="_blank" class="modern-button">
        🎫 {text}
    </a>
""", unsafe_allow_html=True)
try:
    startValue = int(open('lastknown.txt').read().strip())
except Exception:
    startValue = 412300
# Create a session
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "accept": "application/json, text/plain, */*",
    "origin": "https://kidzania-sg.thecoolmelon.com",
})

# Send GET request



# =========================================================
# CONFIG
# =========================================================
TIMEOUT = 5
GAP_SCAN = 20  # linear scan forward at end to catch small gaps


# =========================================================
# CHECK FUNCTION
# =========================================================
def check(ticket_id: int) -> bool:
    url = f"https://backend.thecoolmelon.com/ticket/user/get?ticket_id={ticket_id}"
    try:
        resp = session.get(url, timeout=TIMEOUT)
        if resp.status_code == 201 and resp.text.strip() != '{"message":"Get Ticket Users","ticket_users":{"count":0,"rows":[]},"ticket":null}':
            return True
        return False
    except requests.RequestException:
        return False


# =========================================================
# FIND LATEST TICKET — exponential search + binary search
# O(log n) API calls vs the old O(n) linear scan
# =========================================================
def find_latest_ticket(check_fn, start, status_fn=None):
    """
    Phase 1 — scan backward from start to find a valid anchor (in case
               startValue is stale).
    Phase 2 — exponential jumps forward to bracket the upper bound.
    Phase 3 — binary search within the bracket to find the exact boundary.
    Phase 4 — short linear scan forward to handle small gaps at the tail.
    """
    def log(msg):
        print(msg)
        if status_fn:
            status_fn(msg)

    # Phase 1: anchor
    log(f"Checking start point {start}...")
    if not check_fn(start):
        log("Start invalid, scanning backward...")
        for back in range(start - 1, max(0, start - 500), -1):
            if check_fn(back):
                start = back
                log(f"Anchor found at {start}")
                break
        else:
            log("No valid anchor found.")
            return None

    # Phase 2: exponential jump
    log("Jumping forward exponentially...")
    lo = start
    step = 64
    hi = lo + step
    while check_fn(hi):
        lo = hi
        step = min(step * 2, 10_000)
        hi = lo + step
        log(f"Jumped to {hi}...")

    # Phase 3: binary search in [lo, hi]
    log(f"Binary searching in [{lo}, {hi}]...")
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if check_fn(mid):
            lo = mid
        else:
            hi = mid
        log(f"  Range narrowed to [{lo}, {hi}]")

    # Phase 4: short forward scan for gap tolerance
    result = lo
    for n in range(lo + 1, lo + GAP_SCAN + 1):
        if check_fn(n):
            result = n
    log(f"Latest ticket: {result}")
    return result


# =========================================================
# MAIN
# =========================================================
def run_search(start):
    msg = st.empty()
    msg.info("🔍 Finding latest ticket...")
    latest = find_latest_ticket(check, start, status_fn=lambda m: msg.info(m))
    msg.empty()
    if latest is not None:
        with open('lastknown.txt', 'w') as f:
            f.write(str(latest))
        return latest
    else:
        return start

# Auto-search on first load
if 'auto_searched' not in st.session_state:
    st.session_state.auto_searched = True
    startValue = run_search(startValue)

# --- Ticket ID input (sticky) ---
ticket_id = st.number_input(
    "Ticket ID",
    min_value=1,
    step=1,
    value=startValue
)


def format_text(text: str) -> str:
    """Convert underscores to spaces and apply title case."""
    return text.replace("_", " ").title()

# --- Fetch Data ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "accept": "application/json, text/plain, */*",
    "origin": "https://kidzania-sg.thecoolmelon.com",
})

url = f"https://backend.thecoolmelon.com/ticket/user/get?ticket_id={ticket_id}"
response = session.get(url)
data = response.json()


# --- Show ticket info in 3 columns ---
st.subheader("Ticket Info")
with st.container(border=True):
    ticket = data.get('ticket', {})

    col1, col2, col3 = st.columns(3)
    important_keys_ticket = ['agents','contact_no','payment_date','visit_date','cancel_remark','ticket_id','running_number','unique_no','payment_status_id','created_at','expired_date','is_open_date','remarks','name', 'email', 'actual_price', 'tax_amount', 'payment_amount']

    count = 0
    if not hasattr(ticket, 'items'):
        st.error("Ticket data is not in the expected format/ Ticket have not been sold")
        st.stop()
    for k, v in ticket.items():
        if k in important_keys_ticket:
            text = f"**{format_text(k)}:**<br>{v}"
            count += 1
            if isinstance(v, str) and 'T' in v and 'Z' in v:
                try:
                    dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                    dt = dt + timedelta(hours=8)
                    v = dt.strftime('%Y-%m-%d %H:%M:%S')
                    text = f"**{format_text(k)}:**<br>{v}"
                except:
                    pass
        else:
            continue
        # Distribute into 3 columns
        if count % 3 == 0:
            col1.markdown(text, unsafe_allow_html=True)
        elif count % 3 == 1:
            col2.markdown(text, unsafe_allow_html=True)
        else:
            col3.markdown(text, unsafe_allow_html=True  )
    with st.expander("Show All Ticket Info", expanded=False):
        st.write(ticket)
    # --- Show face link if running_number starts with KZS ---
    running_number = ticket.get('running_number', '')
    payment_date = ticket.get('payment_date', '')
    token = ticket.get('token', '')
    if running_number.startswith("KZS") and token:
        createbutton("Open Ticket Page", f"https://kidzania-sg.thecoolmelon.com/ticket/face/{token}?page=1&c=1")
        st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(to bottom, #ffffff, #ffe6e6);
            }

            </style>
        """, unsafe_allow_html=True)
    if running_number.startswith("KZK") and token:
        createbutton("Open Ticket Page", f"https://kidzania-kl.thecoolmelon.com/ticket/face/{token}?page=1&c=1")
        st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(to bottom, #ffffff, #d4f5dd);
            }

       
            </style>
        """, unsafe_allow_html=True)

    if payment_date is None or payment_date == "":
        st.warning("⚠️ Ticket not yet paid. Ticket may not be available.")



# --- Ticket users ---
ticket_users = data.get('ticket_users', {}).get('rows', [])
grouped_users = defaultdict(list)

for user in ticket_users:
    ticket_no = user['ticket']['unique_no']
    grouped_users[ticket_no].append(user)

# --- Display users in 3 columns ---
for ticket_no, users in grouped_users.items():
    st.markdown(f"### Ticket No: {ticket_no} ({len(users)} Tickets)")
    for idx, user in enumerate(users, 1):
        with st.container(border=True):
            if running_number.startswith("KZS") and token:
                            
                createbutton("Open Face Page", f"https://kidzania-sg.thecoolmelon.com/ticket/user/{user['ticket_user_no']}?page=1&c=1")

                        
            st.markdown(f"**User {idx}: {user.get('ticket_user_no')}**")

            # Display image if available
            if user.get('image_url'):
                st.image(user['image_url'], width=150)

            # Three columns layout
            col1, col2, col3 = st.columns(3)
            important_keys_user = ['gender','ticket_user_no','price','age','open_date','name', 'email', 'actual_price', 'tax_amount', 'payment_amount']
            count = 0
            for k, v in user.items():
                if k == 'image_url':
                    continue
                # Highlight important fields
                if k in important_keys_user:
                    count += 1
                    text = f"**{format_text(k)}:**<br>{v}"
                else:
                    continue

                # Distribute into 3 columns
                if count % 3 == 0:
                    col1.markdown(text, unsafe_allow_html=True)
                elif count % 3 == 1:
                    col2.markdown(text, unsafe_allow_html=True)
                else:
                    col3.markdown(text, unsafe_allow_html=True)

            # Show nested dicts in expanders
            for k, v in user.items():
                if isinstance(v, dict):
                    with st.expander(k):
                        for sub_k, sub_v in v.items():
                            st.write(f"{sub_k}: {sub_v}")
