import time
import requests

import requests
import streamlit as st
from collections import defaultdict
from datetime import datetime, timedelta

st.set_page_config(page_title="Ticket Users Visualizer",page_icon="🎫")
# st.markdown("""
#     <style>
#     header.stAppHeader {
#         display: none;
#     }
#     </style>
# """, unsafe_allow_html=True)
def createbutton(text,link):
    st.markdown(f"""
    <style>
    .modern-button {{
        display: inline-block;
        padding: 0.6em 1.4em;
        font-size: 15px;
        font-weight: 600;
        color: white !important;
        background: linear-gradient(135deg, #6b7280, #4b5563);
        border-radius: 10px;
        text-decoration: none !important;
        transition: all 0.25s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }}

    .modern-button:hover {{
        color: white !important;
        text-decoration: none !important;
        background: linear-gradient(135deg, #4b5563, #374151);
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.18);
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
MISS_LIMIT = 10
INITIAL_STEP = 1
MAX_STEP = 2_000
TIMEOUT = 5


# =========================================================
# CHECK FUNCTION (replace this with your real logic)
# =========================================================
def check(running_number: int) -> bool:
    """
    Return True if this running_number has a response. 
    Return False if it does not.
    """

    # ===== EXAMPLE: HTTP request =====
    # Replace URL and logic as needed

    url = f"https://backend.thecoolmelon.com/ticket/user/get?ticket_id={running_number}"
    
    try:
        resp = session.get(url, timeout=TIMEOUT)
        # Define what "response" means to you
        if resp.status_code == 201 and resp.text.strip() != '{"message":"Get Ticket Users","ticket_users":{"count":0,"rows":[]},"ticket":null}':
            return True

        return False

    except requests.RequestException:
        return False


# =========================================================
# ADAPTIVE BRUTE FORCE SEARCH
# =========================================================
def find_max_running_number(
    check_fn,
    start=startValue,
    initial_step=INITIAL_STEP,
    max_step=MAX_STEP,
    miss_limit=MISS_LIMIT,
):
    n = start
    step = initial_step

    last_success = None
    consecutive_miss = 0

    print("Starting adaptive scan...")

    while consecutive_miss < miss_limit:
        ok = check_fn(n)
        print(f"Testing {n} | step={step} | ok={ok}")

        if ok:
            last_success = n
            consecutive_miss = 0

            # speed up
            step = min(step * 2, max_step)
            n += step
        else:
            consecutive_miss += 1

            # slow down
            step = max(1, step // 2)
            n += step

        time.sleep(0.05)  # prevent hammering API

    print("Boundary detected.")
    return last_success


# =========================================================
# FINAL LINEAR REFINEMENT (PRECISE)
# =========================================================
def refine_linear(check_fn, start, miss_limit=MISS_LIMIT):
    print("Refining with linear scan...")

    last_success = None
    consecutive_miss = 0
    n = start

    while consecutive_miss < miss_limit:
        ok = check_fn(n)
        print(f"Refine {n} | ok={ok}")

        if ok:
            last_success = n
            consecutive_miss = 0
        else:
            consecutive_miss += 1

        n += 1
        time.sleep(0.05)

    return last_success


# =========================================================
# MAIN
# =========================================================
if st.sidebar.button("Find the latest Ticket"):
    rough_max = find_max_running_number(check)
    print(f"Rough max candidate: {rough_max}")

    if rough_max is not None:
        exact_max = refine_linear(check, rough_max - 20)
        startValue = exact_max
        st.sidebar.info(f"✅ The latest ticket found.")
        with open('lastknown.txt', 'w') as f:
            f.write(str(exact_max))
    else:
        st.sidebar.error("❌ No valid running number found.")



st.title("Ticket Users Visualizer")

# --- Ticket ID input ---
ticket_id = st.sidebar.number_input(
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
                background: linear-gradient(135deg, #fff5f5, #ffe6e6);
            }

            section[data-testid="stSidebar"] {
                background-color: #ffffff;
            }
            </style>
        """, unsafe_allow_html=True)
    if running_number.startswith("KZK") and token:
        createbutton("Open Ticket Page", f"https://kidzania-kl.thecoolmelon.com/ticket/face/{token}?page=1&c=1")
        st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(135deg, #f0fff4, #d4f5dd);
            }

            section[data-testid="stSidebar"] {
                background-color: #ffffff;
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
