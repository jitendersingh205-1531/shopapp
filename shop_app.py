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
    date DATE
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

    today = datetime.today().date()

    # -------- Calculations --------

    if not sales_df.empty:
        sales_df["date"] = pd.to_datetime(sales_df["date"])
        today_sales = sales_df[sales_df["date"].dt.date == today]
        today_profit = today_sales["profit"].sum()
    else:
        today_sales = pd.DataFrame()
        today_profit = 0

    if not stock_df.empty:
        low_stock_df = stock_df[stock_df["qty"] <= 5]
    else:
        low_stock_df = pd.DataFrame()

    if not stock_df.empty:
        stock_df["expiry"] = pd.to_datetime(stock_df["expiry"])
        expiring_df = stock_df[
            stock_df["expiry"] <= (datetime.today() + timedelta(days=7))
        ]
    else:
        expiring_df = pd.DataFrame()

    # -------- DETAILS SCREENS --------

    # Profit Details
    if st.session_state.detail_view == "profit":

        st.subheader("💰 Profit Details (Today)")
        back_button()

        if today_sales.empty:
            st.info("No sales today")
        else:
            df = today_sales[["item_name", "profit"]]
            df.columns = ["Item", "Profit (₹)"]
            st.dataframe(df, use_container_width=True)

        return

    # Low Stock Details
    if st.session_state.detail_view == "low_stock":

        st.subheader("⚠ Low Stock Details")
        back_button()

        if low_stock_df.empty:
            st.info("No low stock items")
        else:
            df = low_stock_df[["name", "qty"]]
            df.columns = ["Item", "Quantity"]
            st.dataframe(df, use_container_width=True)

        return

    # Expiry Details
    if st.session_state.detail_view == "expiring":

        st.subheader("⏰ Expiring Soon Details")
        back_button()

        if expiring_df.empty:
            st.info("No expiring items")
        else:
            df = expiring_df[["name", "qty", "expiry"]]
            df.columns = ["Item", "Qty", "Expiry"]
            st.dataframe(df, use_container_width=True)

        return

    # -------- MAIN DASHBOARD --------

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

    with st.expander("➕ Add New Item"):

        name = st.text_input("Item Name")
        qty = st.number_input("Quantity", min_value=1)
        expiry = st.date_input("Expiry Date")
        buy = st.number_input("Purchase Price", min_value=0.0)
        sell = st.number_input("Selling Price", min_value=0.0)

        if st.button("Save Stock"):

            if name == "":
                st.warning("Enter item name")

            else:
                c.execute("""
                INSERT INTO stock(name,qty,expiry,buy_price,sell_price)
                VALUES(?,?,?,?,?)
                """, (name, qty, expiry, buy, sell))

                conn.commit()
                st.success("Stock Added")

    st.subheader("📋 Current Stock")

    df = pd.read_sql("SELECT * FROM stock", conn)

    if df.empty:
        st.info("No stock available")
    else:
        st.dataframe(df, use_container_width=True)


# ---------------- SALES PAGE ----------------
def sales_page():

    st.subheader("💰 Sales Entry")

    stock_df = pd.read_sql("SELECT * FROM stock", conn)

    if stock_df.empty:
        st.info("No stock available")
        return

    item = st.selectbox("Select Item", stock_df["name"])

    max_qty = stock_df[stock_df["name"] == item]["qty"].values[0]

    qty = st.number_input("Quantity Sold", 1, max_qty)

    if st.button("Confirm Sale"):

        row = stock_df[stock_df["name"] == item].iloc[0]

        sell_price = row["sell_price"]
        buy_price = row["buy_price"]

        profit = (sell_price - buy_price) * qty
        today = datetime.today().date()

        # Save sale
        c.execute("""
        INSERT INTO sales(item_name,qty,sell_price,profit,date)
        VALUES(?,?,?,?,?)
        """, (item, qty, sell_price, profit, today))

        # Update stock
        c.execute("""
        UPDATE stock SET qty = qty - ?
        WHERE name = ?
        """, (qty, item))

        conn.commit()

        st.success("Sale Recorded")


# ---------------- REPORTS PAGE ----------------
def reports_page():

    st.subheader("📊 Reports")

    sales_df = pd.read_sql("SELECT * FROM sales", conn)
    stock_df = pd.read_sql("SELECT * FROM stock", conn)

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
