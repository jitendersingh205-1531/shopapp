import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
st.set_page_config("Shop Manager", layout="centered")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("shop.db", check_same_thread=False)
c = conn.cursor()

# Tables
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


# ---------------- NAV ----------------
c1, c2, c3 = st.columns(3)

with c1:
    if st.button("📦 Stock"):
        st.session_state.page = "Stock"
        st.session_state.detail_view = None
        st.rerun()

with c2:
    if st.button("💰 Sales"):
        st.session_state.page = "Sales"
        st.session_state.detail_view = None
        st.rerun()

with c3:
    if st.button("📊 Reports"):
        st.session_state.page = "Reports"
        st.session_state.detail_view = None
        st.rerun()

st.divider()


# ---------------- BACK ----------------
def back_button():
    if st.button("⬅ Back"):
        st.session_state.detail_view = None
        st.rerun()


# ---------------- DASHBOARD ----------------
def show_dashboard():

    today = datetime.today().strftime("%Y-%m-%d")

    st.subheader("📈 Today Overview")

    # -------- PROFIT --------
    sales_df = pd.read_sql("SELECT * FROM sales", conn)

    if not sales_df.empty:
        today_sales = sales_df[sales_df["date"] == today]
        profit = today_sales["profit"].sum()
    else:
        today_sales = pd.DataFrame()
        profit = 0

    # -------- LOW STOCK (fresh query) --------
    grouped = pd.read_sql("""
        SELECT name, SUM(qty) as qty
        FROM stock
        GROUP BY name
    """, conn)

    low_stock = grouped[grouped["qty"] <= 5]

    # -------- EXPIRY (fresh query) --------
    expiry_df = pd.read_sql("""
        SELECT name, qty, expiry
        FROM stock
    """, conn)

    if not expiry_df.empty:
        expiry_df["expiry"] = pd.to_datetime(expiry_df["expiry"])
        expiring = expiry_df[
            expiry_df["expiry"] <= (datetime.today() + timedelta(days=7))
        ]
    else:
        expiring = pd.DataFrame()

    # ---------------- DETAILS ----------------

    if st.session_state.detail_view == "profit":
        st.subheader("💰 Profit Details")
        back_button()

        if today_sales.empty:
            st.info("No sales today")
        else:
            st.dataframe(today_sales[["item_name", "profit"]], width="stretch")
        return

    if st.session_state.detail_view == "low":
        st.subheader("⚠ Low Stock Details")
        back_button()

        fresh = pd.read_sql("""
            SELECT name, SUM(qty) as qty
            FROM stock
            GROUP BY name
        """, conn)

        low_stock = fresh[fresh["qty"] <= 5]

        if low_stock.empty:
            st.info("No low stock")
        else:
            st.dataframe(low_stock, width="stretch")
        return

    if st.session_state.detail_view == "exp":
        st.subheader("⏰ Expiring Soon")
        back_button()

        fresh = pd.read_sql("""
            SELECT name, qty, expiry
            FROM stock
        """, conn)

        if not fresh.empty:
            fresh["expiry"] = pd.to_datetime(fresh["expiry"])
            expiring = fresh[
                fresh["expiry"] <= (datetime.today() + timedelta(days=7))
            ]
        else:
            expiring = pd.DataFrame()

        if expiring.empty:
            st.info("No expiring")
        else:
            st.dataframe(expiring, width="stretch")
        return

    # ---------------- MAIN CARDS ----------------
    d1, d2, d3 = st.columns(3)

    with d1:
        st.metric("💰 Today Profit", round(profit, 2))
        if st.button("Details", key="dp"):
            st.session_state.detail_view = "profit"
            st.rerun()

    with d2:
        st.metric("⚠ Low Stock", len(low_stock))
        if st.button("Details", key="dl"):
            st.session_state.detail_view = "low"
            st.rerun()

    with d3:
        st.metric("⏰ Expiring", len(expiring))
        if st.button("Details", key="de"):
            st.session_state.detail_view = "exp"
            st.rerun()


# ---------------- STOCK PAGE ----------------
def stock_page():

    st.subheader("📦 Stock Management")

    names = pd.read_sql("SELECT DISTINCT name FROM stock", conn)["name"].tolist()

    search = st.text_input("🔍 Search Item")

    if search:
        names = [n for n in names if search.lower() in n.lower()]

    options = ["New Item"] + names

    selected = st.selectbox("Select Item", options)

    if selected == "New Item":
        name = st.text_input("Item Name")
    else:
        name = selected

    qty = st.number_input("Quantity", min_value=1)
    expiry = st.date_input("Expiry Date")
    buy = st.number_input("Buy Price", min_value=0.0)
    sell = st.number_input("Sell Price", min_value=0.0)

    if st.button("Save Stock"):

        if name == "":
            st.warning("Enter name")
            return

        c.execute("""
        INSERT INTO stock(name,qty,expiry,buy_price,sell_price)
        VALUES(?,?,?,?,?)
        """, (name, qty, expiry, buy, sell))

        conn.commit()

        st.success("Stock Added")
        st.rerun()

    df = pd.read_sql("""
        SELECT name, SUM(qty) as qty, MIN(expiry) as expiry
        FROM stock
        GROUP BY name
    """, conn)

    st.subheader("📋 Current Stock")

    if df.empty:
        st.info("No stock")
    else:
        st.dataframe(df, width="stretch")


# ---------------- SALES PAGE ----------------
def sales_page():

    st.subheader("💰 Sales Entry")

    stock_df = pd.read_sql("""
        SELECT name,
               SUM(qty) as qty,
               AVG(buy_price) as buy,
               AVG(sell_price) as sell
        FROM stock
        GROUP BY name
    """, conn)

    if stock_df.empty:
        st.info("No stock")
        return

    search = st.text_input("🔍 Search Item")

    if search:
        stock_df = stock_df[
            stock_df["name"].str.lower().str.contains(search.lower())
        ]

    if stock_df.empty:
        st.warning("No match")
        return

    item = st.selectbox("Select Item", stock_df["name"].tolist())

    row = stock_df[stock_df["name"] == item].iloc[0]

    max_qty = int(row["qty"])

    qty = st.number_input("Quantity", 1, max_qty, 1, 1)

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

            if r["qty"] <= remaining:
                c.execute("DELETE FROM stock WHERE id=?", (r["id"],))
                remaining -= r["qty"]
            else:
                c.execute("""
                UPDATE stock SET qty=qty-?
                WHERE id=?
                """, (remaining, r["id"]))
                remaining = 0

        profit = (row["sell"] - row["buy"]) * qty
        today = datetime.today().strftime("%Y-%m-%d")

        c.execute("""
        INSERT INTO sales(item_name,qty,sell_price,profit,date)
        VALUES(?,?,?,?,?)
        """, (item, qty, row["sell"], profit, today))

        conn.commit()

        st.success("Sale Recorded")
        st.rerun()


# ---------------- REPORTS ----------------
def reports_page():

    st.subheader("📊 Reports")

    sales_df = pd.read_sql("SELECT * FROM sales", conn)

    stock_df = pd.read_sql("""
        SELECT name, SUM(qty) as qty, MIN(expiry) as expiry
        FROM stock
        GROUP BY name
    """, conn)

    st.write("### 💰 Sales")

    if sales_df.empty:
        st.info("No sales")
    else:
        st.dataframe(sales_df, width="stretch")

    st.write("### 📦 Stock")

    if stock_df.empty:
        st.info("No stock")
    else:
        st.dataframe(stock_df, width="stretch")


# ---------------- MAIN ----------------
show_dashboard()

if st.session_state.page == "Stock":
    stock_page()

elif st.session_state.page == "Sales":
    sales_page()

elif st.session_state.page == "Reports":
    reports_page()


# ---------------- DEBUG ----------------
st.divider()
st.subheader("🛠 Debug Tools")

with open("shop.db", "rb") as f:
    st.download_button("📥 Download Database", f, file_name="shop.db")


# ---------------- RESET ----------------
st.divider()
st.subheader("⚠ Reset Database")

if st.button("🔴 Reset All Data"):
    c.execute("DELETE FROM stock")
    c.execute("DELETE FROM sales")
    conn.commit()
    st.success("All data cleared!")
    st.rerun()
