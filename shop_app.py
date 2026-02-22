import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# ---------------- DATABASE ----------------
conn = sqlite3.connect("shop.db", check_same_thread=False)
c = conn.cursor()

# Create tables
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

# ---------------- UI ----------------
st.set_page_config("Shop Manager", layout="centered")
st.title("🛒 Simple Shop Manager")

menu = ["Add Stock", "Sales", "Reports"]
choice = st.sidebar.selectbox("Menu", menu)

# ---------------- ADD STOCK ----------------
if choice == "Add Stock":

    st.subheader("➕ Add New Stock")

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
            """,(name,qty,expiry,buy,sell))

            conn.commit()

            st.success("Stock Added Successfully")

# ---------------- SALES ----------------
elif choice == "Sales":

    st.subheader("💰 Record Sale")

    stock_df = pd.read_sql("SELECT * FROM stock", conn)

    if stock_df.empty:
        st.info("No stock available")
    else:

        item = st.selectbox("Select Item", stock_df["name"])

        max_qty = stock_df[stock_df["name"]==item]["qty"].values[0]

        qty = st.number_input("Quantity Sold",1,max_qty)

        if st.button("Confirm Sale"):

            row = stock_df[stock_df["name"]==item].iloc[0]

            sell_price = row["sell_price"]
            buy_price = row["buy_price"]

            profit = (sell_price - buy_price) * qty
            today = datetime.today().date()

            # Save sale
            c.execute("""
            INSERT INTO sales(item_name,qty,sell_price,profit,date)
            VALUES(?,?,?,?,?)
            """,(item,qty,sell_price,profit,today))

            # Update stock
            c.execute("""
            UPDATE stock SET qty = qty - ?
            WHERE name = ?
            """,(qty,item))

            conn.commit()

            st.success("Sale Recorded")

# ---------------- REPORTS ----------------
elif choice == "Reports":

    st.subheader("📊 Reports & Alerts")

    # -------- PROFIT --------
    today = datetime.today().date()

    sales_df = pd.read_sql("SELECT * FROM sales", conn)

    if not sales_df.empty:

        sales_df["date"] = pd.to_datetime(sales_df["date"])

        today_profit = sales_df[sales_df["date"].dt.date == today]["profit"].sum()

        st.metric("Today's Profit (₹)", round(today_profit,2))

    else:
        st.info("No sales data")

    # -------- EXPIRY --------
    st.subheader("⚠ Expiring Soon (Next 7 Days)")

    stock_df = pd.read_sql("SELECT * FROM stock", conn)

    if not stock_df.empty:

        stock_df["expiry"] = pd.to_datetime(stock_df["expiry"])

        alert = stock_df[
            stock_df["expiry"] <= (datetime.today()+timedelta(days=7))
        ]

        if alert.empty:
            st.success("No items expiring soon")

        else:
            st.dataframe(alert[["name","qty","expiry"]])

    else:
        st.info("No stock data")

    # -------- FULL DATA --------
    st.subheader("📦 Current Stock")
    st.dataframe(stock_df)