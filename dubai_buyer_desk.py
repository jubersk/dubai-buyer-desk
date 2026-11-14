import sqlite3
from contextlib import closing
from pathlib import Path
from time import perf_counter

import streamlit as st

from buyer_qualification import extract_buyer_requirements, qualify_buyer


DB_PATH = Path(__file__).with_name("buyer_demo.sqlite3")
SAMPLE = (
    "I saw DM-S01 listed at AED 2.7M. I want to buy a 2br in Dubai Marina "
    "and my maximum budget is AED 3M."
)

INVENTORY = (
    {"id": "DM-S01", "area": "Dubai Marina", "bedrooms": 2, "asking_price": 2_850_000},
    {"id": "DM-S02", "area": "Dubai Marina", "bedrooms": 2, "asking_price": 2_950_000},
    {"id": "DM-S03", "area": "Dubai Marina", "bedrooms": 2, "asking_price": 3_200_000},
)


def find_listings(area, bedrooms, budget, unavailable):
    matches = []
    trace = []

    for listing in INVENTORY:
        listing_id = listing["id"]
        if listing["area"] != area or listing["bedrooms"] != bedrooms:
            decision = "Requirements mismatch"
        elif listing_id in unavailable:
            decision = "Unavailable"
        elif listing["asking_price"] > budget:
            decision = "Over budget"
        else:
            decision = "Matched"
            matches.append(listing)

        trace.append({
            "Listing": listing_id,
            "Asking price from inventory": f"AED {listing['asking_price']:,}",
            "Decision": decision,
        })

    return sorted(matches, key=lambda listing: listing["asking_price"]), trace


def load_queue(qualified_lead=None):
    with closing(sqlite3.connect(DB_PATH)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS sales_queue (
                    id INTEGER PRIMARY KEY,
                    inquiry TEXT NOT NULL UNIQUE,
                    area TEXT NOT NULL,
                    bedrooms INTEGER NOT NULL,
                    budget_aed INTEGER NOT NULL
                )
            """)
            added = False
            if qualified_lead is not None:
                result = connection.execute("""
                    INSERT INTO sales_queue (inquiry, area, bedrooms, budget_aed)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(inquiry) DO NOTHING
                """, qualified_lead)
                added = result.rowcount == 1

            connection.row_factory = sqlite3.Row
            rows = connection.execute("""
                SELECT id, area, bedrooms, budget_aed
                FROM sales_queue
                ORDER BY id DESC
            """).fetchall()
            return added, [dict(row) for row in rows]
def load_demo_queue(qualified_lead=None):
    queue = st.session_state.setdefault("demo_sales_queue", {})
    added = False

    if qualified_lead is not None:
        inquiry, area, bedrooms, budget = qualified_lead
        if inquiry not in queue:
            queue[inquiry] = {
                "id": len(queue) + 1,
                "area": area,
                "bedrooms": bedrooms,
                "budget_aed": budget,
            }
            added = True

    return added, list(reversed(list(queue.values())))


st.set_page_config(page_title="Dubai Buyer Desk", layout="wide")
st.title("Dubai Buyer Desk")
st.caption("Portfolio demo. Use fictional buyer inquiries.")

unavailable = set(st.sidebar.multiselect(
    "Mark sample listings unavailable",
    [listing["id"] for listing in INVENTORY],
))

with st.form("buyer_inquiry"):
    inquiry = st.text_area("Buyer inquiry", value=SAMPLE, max_chars=2000)
    submitted = st.form_submit_button("Qualify buyer", type="primary")

qualified_lead = None
if submitted:
    started = perf_counter()
    inquiry = inquiry.strip()

    if not inquiry:
        st.warning("Enter a buyer inquiry.")
    else:
        area, bedrooms, budget = extract_buyer_requirements(inquiry)
        decision, message = qualify_buyer(inquiry)
        st.write(
            f"**Area:** {area or 'Unknown'} · "
            f"**Bedrooms:** {bedrooms or 'Unknown'} · "
            f"**Maximum budget:** {f'AED {budget:,}' if budget else 'Unknown'}"
        )

        if decision == "Sales queue":
            qualified_lead = (inquiry, area, bedrooms, budget)
        else:
            st.warning(message)

public_demo = st.sidebar.toggle("Public demo mode", value=True)

if public_demo:
    added, queue = load_demo_queue(qualified_lead)
else:
    added, queue = load_queue(qualified_lead)

added, queue = load_queue(qualified_lead)

if qualified_lead is not None:
    matches, trace = find_listings(area, bedrooms, budget, unavailable)
    elapsed_ms = (perf_counter() - started) * 1000

    st.success(
        "Added to the sales queue." if added
        else "This inquiry is already in the queue."
    )
    st.subheader("Draft for broker review")
    if matches:
        best = matches[0]
        st.write(
            f"I found a {best['bedrooms']}-bedroom apartment in {best['area']}, "
            f"reference {best['id']}, with an asking price of "
            f"AED {best['asking_price']:,}. Would you like to arrange a viewing?"
        )
    else:
        st.write(
            "Thanks for sharing your requirements. A broker will follow up "
            "to check for suitable properties within your budget."
        )

    with st.expander("Decision trace"):
        st.write(f"**Routing:** Sales queue · {'New lead' if added else 'Already queued'}")
        st.write(f"**Processing time:** {elapsed_ms:.1f} ms")
        st.dataframe(trace, hide_index=True)

st.subheader("Sales queue")
if queue:
    st.dataframe(queue, hide_index=True, use_container_width=True)
else:
    st.info("Qualified buyers will appear here.")