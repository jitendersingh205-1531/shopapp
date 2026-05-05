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

    sales_df = pd.read_sql("SELECT * FROM sales", conn)

    if not sales_df.empty:
        today_sales = sales_df[sales_df["date"] == today]
        profit = today_sales["profit"].sum()
    else:
        today_sales = pd.DataFrame()
        profit = 0

    grouped = pd.read_sql("""
        SELECT name, COALESCE(SUM(qty),0) as qty
        FROM stock
        GROUP BY name
    """, conn)

    low_stock = grouped[grouped["qty"] <= 5]

    expiry_df = pd.read_sql("SELECT name, qty, expiry FROM stock", conn)

    if not expiry_df.empty:
        expiry_df["expiry"] = pd.to_datetime(expiry_df["expiry"])
        expiring = expiry_df[
            expiry_df["expiry"] <= (datetime.today() + timedelta(days=7))
        ]
    else:
        expiring = pd.DataFrame()

    d1, d2, d3 = st.columns(3)

    with d1:
        st.metric("💰 Today Profit", round(profit, 2))

    with d2:
        st.metric("⚠ Low Stock", len(low_stock))

    with d3:
        st.metric("⏰ Expiring", len(expiring))


# ---------------- STOCK PAGE ----------------
def stock_page():

    st.subheader("📦 Stock Management")

    names = pd.read_sql("SELECT DISTINCT name FROM stock", conn)["name"].tolist()

    search = st.text_input("🔍 Search Item")

    if search:
        names = [n for n in names if search.lower() in n.lower()]

    options = ["New Item"] + names

    selected = st.selectbox("Select Item", options)

    name = st.text_input("Item Name") if selected == "New Item" else selected

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
        SELECT name, COALESCE(SUM(qty),0) as qty, MIN(expiry) as expiry
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

    qty = st.number_input("Quantity", 1, max_qty, 1)

    if st.button("Confirm Sale"):

        if qty > max_qty:
            st.error("Not enough stock available")
            return

        try:
            conn.execute("BEGIN")

            remaining = qty

            batches = pd.read_sql("""
                SELECT id, qty FROM stock
                WHERE name=?
                ORDER BY expiry ASC, id ASC
            """, conn, params=(item,))

            for _, r in batches.iterrows():

                if remaining <= 0:
                    break

                batch_id = r["id"]
                batch_qty = int(r["qty"])

                if batch_qty <= remaining:
                    c.execute("DELETE FROM stock WHERE id=?", (batch_id,))
                    remaining -= batch_qty
                else:
                    c.execute("""
                        UPDATE stock 
                        SET qty = qty - ?
                        WHERE id = ?
                    """, (remaining, batch_id))
                    remaining = 0

            if remaining > 0:
                conn.rollback()
                st.error("Stock update failed")
                return

            profit = (row["sell"] - row["buy"]) * qty
            today = datetime.today().strftime("%Y-%m-%d")

            c.execute("""
            INSERT INTO sales(item_name,qty,sell_price,profit,date)
            VALUES(?,?,?,?,?)
            """, (item, qty, row["sell"], profit, today))

            conn.commit()

            st.success("Sale Recorded & Stock Updated ✅")
            st.rerun()

        except Exception as e:
            conn.rollback()
            st.error(f"Error: {e}")


# ---------------- REPORTS ----------------
def reports_page():

    st.subheader("📊 Reports")

    sales_df = pd.read_sql("SELECT * FROM sales", conn)

    stock_df = pd.read_sql("""
        SELECT name, COALESCE(SUM(qty),0) as qty, MIN(expiry) as expiry
        FROM stock
        GROUP BY name
    """, conn)

    st.write("### 💰 Sales")
    st.dataframe(sales_df if not sales_df.empty else pd.DataFrame())

    st.write("### 📦 Stock")
    st.dataframe(stock_df if not stock_df.empty else pd.DataFrame())


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
