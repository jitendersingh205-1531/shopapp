import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
st.set_page_config("Shop Manager", layout="centered")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("shop.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS stock(
    id INTEGER PRIMARY KEY,
    name TEXT,
    qty INTEGER,
    expiry DATE,
    buy_price REAL,
    sell_price REAL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS sales(
    id INTEGER PRIMARY KEY,
    item_name TEXT,
    qty INTEGER,
    sell_price REAL,
    profit REAL,
    date TEXT
)
""")

conn.commit()

# ---------------- SESSION ----------------
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "detail_view" not in st.session_state:
    st.session_state.detail_view = None

# ---------------- HEADER ----------------
st.markdown("<h2 style='text-align:center'>🛒 Simple Shop Manager</h2>",
            unsafe_allow_html=True)
st.write("")

# ---------------- TOP BUTTONS ----------------
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📦 Stock", use_container_width=True):
        st.session_state.page = "Stock"
        st.session_state.detail_view = None

with col2:
    if st.button("💰 Sales", use_container_width=True):
        st.session_state.page = "Sales"
        st.session_state.detail_view = None

with col3:
    if st.button("📊 Reports", use_container_width=True):
        st.session_state.page = "Reports"
        st.session_state.detail_view = None

st.divider()

# ---------------- BACK BUTTON ----------------
def back_button():
    if st.button("⬅ Back"):
        st.session_state.detail_view = None
        st.experimental_rerun()

# ---------------- DASHBOARD ----------------
def show_dashboard():

    st.subheader("📈 Today Overview")

    stock_df = pd.read_sql("SELECT * FROM stock", conn)
    sales_df = pd.read_sql("SELECT * FROM sales", conn)

    today = datetime.today().strftime("%Y-%m-%d")

    # PROFIT
    if not sales_df.empty:
        today_sales = sales_df[sales_df["date"] == today]
        today_profit = today_sales["profit"].sum()
    else:
        today_sales = pd.DataFrame()
        today_profit = 0

    # LOW STOCK
    if not stock_df.empty:
        grouped = stock_df.groupby("name")["qty"].sum().reset_index()
        low_stock_df = grouped[grouped["qty"] <= 5]
    else:
        low_stock_df = pd.DataFrame()

    # EXPIRY
    if not stock_df.empty:
        stock_df["expiry"] = pd.to_datetime(stock_df["expiry"])
        expiring_df = stock_df[
            stock_df["expiry"] <= (datetime.today() + timedelta(days=7))
        ]
    else:
        expiring_df = pd.DataFrame()

    # DETAILS
    if st.session_state.detail_view == "profit":
        st.subheader("💰 Profit Details (Today)")
        back_button()
        if today_sales.empty:
            st.info("No sales today")
        else:
            st.dataframe(
                today_sales[["item_name", "profit"]],
                use_container_width=True
            )
        return

    if st.session_state.detail_view == "low_stock":
        st.subheader("⚠ Low Stock Details")
        back_button()
        if low_stock_df.empty:
            st.info("No low stock items")
        else:
            st.dataframe(low_stock_df, use_container_width=True)
        return

    if st.session_state.detail_view == "expiring":
        st.subheader("⏰ Expiring Soon Details")
        back_button()
        if expiring_df.empty:
            st.info("No expiring items")
        else:
            st.dataframe(
                expiring_df[["name", "qty", "expiry"]],
                use_container_width=True
            )
        return

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("💰 Profit Today (₹)", round(today_profit, 2))
        if st.button("Details", key="p"):
            st.session_state.detail_view = "profit"
            st.experimental_rerun()

    with c2:
        st.metric("⚠ Low Stock", len(low_stock_df))
        if st.button("Details", key="l"):
            st.session_state.detail_view = "low_stock"
            st.experimental_rerun()

    with c3:
        st.metric("⏰ Expiring Soon", len(expiring_df))
        if st.button("Details", key="e"):
            st.session_state.detail_view = "expiring"
            st.experimental_rerun()

    st.divider()

# ---------------- STOCK PAGE ----------------
def stock_page():

    st.subheader("📦 Stock Management")

    names_df = pd.read_sql("SELECT DISTINCT name FROM stock", conn)
    existing_names = names_df["name"].tolist()

    search_name = st.text_input("🔍 Search Existing Item")

    filtered = [
        n for n in existing_names
        if search_name.lower() in n.lower()
    ]

    select_options = ["New Item"] + filtered

    selected = st.selectbox("Select Item", select_options)

    if selected == "New Item":
        name = st.text_input("Item Name")
    else:
        name = selected

    qty = st.number_input("Quantity", min_value=1)
    expiry = st.date_input("Expiry Date")
    buy = st.number_input("Purchase Price", min_value=0.0)
    sell = st.number_input("Selling Price", min_value=0.0)

    if st.button("Save Stock"):

        if name == "":
            st.warning("Enter item name")
            return

        c.execute("""
        INSERT INTO stock(name,qty,expiry,buy_price,sell_price)
        VALUES(?,?,?,?,?)
        """, (name, qty, expiry, buy, sell))

        conn.commit()
        st.success("Stock Added")
        st.experimental_rerun()

    st.subheader("📋 Current Stock (Total)")

    stock_df = pd.read_sql("""
        SELECT name,
               SUM(qty) as qty,
               MIN(expiry) as nearest_expiry
        FROM stock
        GROUP BY name
    """, conn)

    if stock_df.empty:
        st.info("No stock available")
    else:
        st.dataframe(stock_df, use_container_width=True)

# ---------------- SALES PAGE ----------------
def sales_page():

    st.subheader("💰 Sales Entry")

    stock_df = pd.read_sql("""
        SELECT name,
               SUM(qty) as total_qty,
               AVG(buy_price) as buy_price,
               AVG(sell_price) as sell_price
        FROM stock
        GROUP BY name
    """, conn)

    if stock_df.empty:
        st.info("No stock available")
        return

    search = st.text_input("🔍 Search Item")

    filtered = stock_df[
        stock_df["name"].str.lower().str.contains(search.lower())
    ]

    if filtered.empty:
        st.warning("No matching item")
        return

    item = st.selectbox("Select Item", filtered["name"].tolist())

    row = stock_df[stock_df["name"] == item].iloc[0]
    max_qty = int(row["total_qty"])

    if max_qty <= 0:
        st.error("Out of stock")
        return

    qty = st.number_input(
        "Quantity Sold",
        min_value=1,
        max_value=max_qty,
        value=1,
        step=1
    )

    if st.button("Confirm Sale"):

        remaining = qty

        batches = pd.read_sql("""
            SELECT id, qty FROM stock
            WHERE name=?
            ORDER BY expiry
        """, conn, params=(item,))

        for _, r in batches.iterrows():
            if remaining <= 0:
                break

            batch_qty = r["qty"]
            batch_id = r["id"]

            if batch_qty <= remaining:
                c.execute("DELETE FROM stock WHERE id=?", (batch_id,))
                remaining -= batch_qty
            else:
                c.execute(
                    "UPDATE stock SET qty = qty - ? WHERE id=?",
                    (remaining, batch_id)
                )
                remaining = 0

        profit = (row["sell_price"] - row["buy_price"]) * qty
        today = datetime.today().strftime("%Y-%m-%d")

        c.execute("""
        INSERT INTO sales(item_name,qty,sell_price,profit,date)
        VALUES(?,?,?,?,?)
        """, (item, qty, row["sell_price"], profit, today))

        conn.commit()

        st.success("Sale Recorded")
        st.experimental_rerun()

# ---------------- REPORTS PAGE ----------------
def reports_page():

    st.subheader("📊 Reports")

    sales_df = pd.read_sql("SELECT * FROM sales", conn)

    stock_df = pd.read_sql("""
        SELECT name,
               SUM(qty) as qty,
               MIN(expiry) as expiry
        FROM stock
        GROUP BY name
    """, conn)

    st.write("### 💰 Sales History")

    if sales_df.empty:
        st.info("No sales yet")
    else:
        st.dataframe(sales_df, use_container_width=True)

    st.write("### 📦 Stock Status")

    if stock_df.empty:
        st.info("No stock")
    else:
        st.dataframe(stock_df, use_container_width=True)

# ---------------- MAIN ----------------
show_dashboard()

if st.session_state.page == "Stock":
    stock_page()

elif st.session_state.page == "Sales":
    sales_page()

elif st.session_state.page == "Reports":
    reports_page()
