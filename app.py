# app.py
import streamlit as st
from datetime import date, timedelta
from database import db
import math
import plotly.express as px
import pandas as pd


st.set_page_config(page_title="Hotel Reservation System", layout="wide", page_icon="🏨")
st.title("🏨 Hotel Reservation System")

def format_currency(v):
    try: return f"${v:,.2f}"
    except: return str(v)

def nights_between(a,b): return (b - a).days

menu = st.sidebar.selectbox("Navigation", ["Dashboard","Data Entry (All Tables)","Reservations","Rooms","Guests","Services","Payments","Reports","Debug"])

# ---------- Dashboard ----------
if menu == "Dashboard":
    st.header("Dashboard")
    total_guests = db.fetch_one("SELECT COUNT(*) as cnt FROM GUEST") or {'cnt':0}
    available_rooms = db.fetch_one("SELECT COUNT(*) as cnt FROM ROOM WHERE Status='Available'") or {'cnt':0}
    today = date.today().isoformat()
    todays_checkins = db.fetch_one("SELECT COUNT(*) as cnt FROM RESERVATION WHERE CheckInDate=%s AND Status='Confirmed'", (today,)) or {'cnt':0}
    total_revenue = db.fetch_one("SELECT COALESCE(SUM(Amount),0) as total FROM PAYMENT WHERE PaymentStatus='Completed'") or {'total':0}
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Guests", total_guests['cnt'])
    c2.metric("Available Rooms", available_rooms['cnt'])
    c3.metric("Today's Check-ins", todays_checkins['cnt'])
    c4.metric("Total Revenue", format_currency(total_revenue['total']))

# ---------- Data Entry (one simple form per table) ----------
elif menu == "Data Entry (All Tables)":
    st.header("Data Entry — Simple forms for each table")
    st.subheader("1) Add Guest")
    with st.form("add_guest"):
        fn = st.text_input("First name")
        ln = st.text_input("Last name")
        em = st.text_input("Email")
        ph = st.text_input("Phone")
        addr = st.text_area("Address")
        if st.form_submit_button("Add Guest"):
            if not (fn and ln and em): st.error("Firstname, Lastname, Email required")
            else:
                r = db.execute("INSERT INTO GUEST (FirstName,LastName,Email,Phone,Address) VALUES (%s,%s,%s,%s,%s)", (fn,ln,em,ph,addr))
                if r is not None: st.success("Guest added")
                else: st.error("Failed to add")

    st.markdown("---")
    st.subheader("2) Add Room Type")
    with st.form("add_roomtype"):
        tname = st.text_input("Type name")
        rate = st.number_input("Rate", min_value=0.0, value=100.0, step=1.0)
        cap = st.number_input("Max capacity", min_value=1, value=2)
        desc = st.text_area("Description")
        if st.form_submit_button("Add Room Type"):
            if not tname: st.error("Type name required")
            else:
                r = db.execute("INSERT INTO ROOM_TYPE (TypeName,Rate,MaxCapacity,Description) VALUES (%s,%s,%s,%s)", (tname,rate,cap,desc))
                if r is not None: st.success("Room type added")
                else: st.error("Failed to add")

    st.markdown("---")
    st.subheader("3) Add Room")
    rtypes = db.fetch_all("SELECT RoomTypeID,TypeName FROM ROOM_TYPE") or []
    rt_map = {r['TypeName']: r['RoomTypeID'] for r in rtypes}
    with st.form("add_room"):
        rn = st.text_input("Room number")
        rtype = st.selectbox("Room type", options=list(rt_map.keys())) if rt_map else st.text_input("Room type id (create types first)")
        floor = st.number_input("Floor", value=1, step=1)
        status = st.selectbox("Status", ['Available','Occupied','Maintenance'])
        if st.form_submit_button("Add Room"):
            if not rn or (not rt_map and not rtype): st.error("Provide room number and room type")
            else:
                rt_id = rt_map.get(rtype) if rt_map else int(rtype)
                r = db.execute("INSERT INTO ROOM (RoomNumber,RoomTypeID,Floor,Status) VALUES (%s,%s,%s,%s)", (rn,rt_id,floor,status))
                if r is not None: st.success("Room added")
                else: st.error("Failed to add")

    st.markdown("---")
    st.subheader("4) Add Service")
    with st.form("add_service"):
        sname = st.text_input("Service name")
        sprice = st.number_input("Service price", min_value=0.0, value=10.0)
        if st.form_submit_button("Add Service"):
            if not sname: st.error("Service name required")
            else:
                r = db.execute("INSERT INTO SERVICE (ServiceName,ServicePrice) VALUES (%s,%s)", (sname,sprice))
                if r is not None: st.success("Service added")
                else: st.error("Failed to add")

    st.markdown("---")
    st.subheader("5) Add Payment (for an existing reservation)")
    res_list = db.fetch_all("SELECT ReservationID FROM RESERVATION ORDER BY ReservationID DESC LIMIT 100") or []
    res_ids = [r['ReservationID'] for r in res_list]
    with st.form("add_payment"):
        rid = st.selectbox("Reservation ID", options=res_ids) if res_ids else st.number_input("Reservation ID", value=0)
        pamt = st.number_input("Amount", min_value=0.0, value=0.0)
        pmethod = st.selectbox("Payment method", ['Credit Card','Cash','Bank Transfer','Debit Card'])
        pstatus = st.selectbox("Payment status", ['Pending','Completed','Failed','Refunded'])
        if st.form_submit_button("Add Payment"):
            r = db.execute("INSERT INTO PAYMENT (ReservationID,Amount,PaymentMethod,PaymentStatus) VALUES (%s,%s,%s,%s)", (rid,pamt,pmethod,pstatus))
            if r is not None: st.success("Payment recorded")
            else: st.error("Failed to add payment")

    st.markdown("---")
    st.subheader("6) Manual: Add Reservation + Allocate Room (useful to seed multi-step data)")
    g_list = db.fetch_all("SELECT GuestID, FirstName, LastName FROM GUEST ORDER BY GuestID DESC LIMIT 100") or []
    guest_opts = {f"{g['FirstName']} {g['LastName']} (ID:{g['GuestID']})": g['GuestID'] for g in g_list}
    rooms = db.fetch_all("SELECT RoomNumber, RoomTypeID FROM ROOM WHERE Status='Available'") or []
    room_opts = [r['RoomNumber'] for r in rooms]

    with st.form("add_reservation"):
        guest_sel = st.selectbox("Guest", options=list(guest_opts.keys())) if guest_opts else st.text_input("Guest ID")
        ci = st.date_input("Check-in", min_value=date.today())
        co = st.date_input("Check-out", min_value=ci + timedelta(days=1))
        room_sel = st.selectbox("Room", options=room_opts) if room_opts else st.text_input("RoomNumber")
        if st.form_submit_button("Create Reservation and Allocate Room"):
            gid = guest_opts.get(guest_sel) if guest_opts else int(guest_sel)
            nights = nights_between(ci,co)
            price = db.fetch_one("SELECT rt.Rate FROM ROOM rm JOIN ROOM_TYPE rt ON rm.RoomTypeID=rt.RoomTypeID WHERE rm.RoomNumber=%s", (room_sel,))
            rate = price['Rate'] if price else 0
            total = rate * nights
            r1 = db.execute("INSERT INTO RESERVATION (GuestID,CheckInDate,CheckOutDate,TotalAmount,Status) VALUES (%s,%s,%s,%s,%s)", (gid,ci.isoformat(),co.isoformat(),total,'Confirmed'))
            if r1 is None:
                st.error("Failed to create reservation")
            else:
                rid = db.fetch_one("SELECT LAST_INSERT_ID() as ReservationID")
                reservation_id = rid['ReservationID'] if rid else None
                if reservation_id:
                    a = db.execute("INSERT INTO ALLOCATED_ROOM (ReservationID,RoomNumber,PricePerNight) VALUES (%s,%s,%s)", (reservation_id, room_sel, rate))
                    u = db.execute("UPDATE ROOM SET Status='Occupied' WHERE RoomNumber=%s", (room_sel,))
                    st.success(f"Reservation #{reservation_id} created. Total: {format_currency(total)}")
                else:
                    st.error("Could not fetch reservation id")

# ---------- Reservations ----------
elif menu == "Reservations":
    st.header("Reservations — View and Search")
    st.subheader("Search by Guest name or Reservation ID")
    q = st.text_input("Search (name or reservation id)")
    if st.button("Search"):
        if q.isdigit():
            rows = db.fetch_all("SELECT r.*, g.FirstName, g.LastName FROM RESERVATION r JOIN GUEST g ON r.GuestID=g.GuestID WHERE r.ReservationID=%s", (int(q),))
        else:
            rows = db.fetch_all("SELECT r.*, g.FirstName, g.LastName FROM RESERVATION r JOIN GUEST g ON r.GuestID=g.GuestID WHERE g.FirstName LIKE %s OR g.LastName LIKE %s", (f"%{q}%", f"%{q}%"))
        st.write(rows or "No results")
    st.markdown("---")
    st.subheader("All reservations (latest 100)")
    rows = db.fetch_all("SELECT r.*, g.FirstName, g.LastName FROM RESERVATION r JOIN GUEST g ON r.GuestID=g.GuestID ORDER BY r.BookingDate DESC LIMIT 100") or []
    for r in rows:
        st.write(f"#{r['ReservationID']} — {r['FirstName']} {r['LastName']} — {r['CheckInDate']}→{r['CheckOutDate']} — {r['Status']} — {format_currency(r['TotalAmount'])}")

# ---------- Rooms ----------
elif menu == "Rooms":
    st.header("Rooms — View & Update Status")
    rooms = db.fetch_all("SELECT rm.RoomNumber, rm.Floor, rm.Status, rt.TypeName, rt.Rate FROM ROOM rm JOIN ROOM_TYPE rt ON rm.RoomTypeID=rt.RoomTypeID ORDER BY rm.Floor, rm.RoomNumber") or []
    for rm in rooms:
        cols = st.columns([1,2,1,1])
        cols[0].write(f"**{rm['RoomNumber']}**")
        cols[1].write(f"{rm['TypeName']} (Floor {rm['Floor']})")
        cols[2].write(rm['Status'])
        cols[3].write(format_currency(rm['Rate']))
        if cols[2].button("Mark Available", key=f"avail_{rm['RoomNumber']}"):
            db.execute("UPDATE ROOM SET Status='Available' WHERE RoomNumber=%s", (rm['RoomNumber'],))
            st.experimental_rerun()
        if cols[2].button("Mark Maintenance", key=f"maint_{rm['RoomNumber']}"):
            db.execute("UPDATE ROOM SET Status='Maintenance' WHERE RoomNumber=%s", (rm['RoomNumber'],))
            st.experimental_rerun()

# ---------- Guests ----------
elif menu == "Guests":
    st.header("Guests — View list")
    guests = db.fetch_all("SELECT * FROM GUEST ORDER BY CreatedDate DESC LIMIT 200") or []
    for g in guests:
        with st.expander(f"{g['FirstName']} {g['LastName']} (ID:{g['GuestID']})"):
            st.write(f"Email: {g['Email']}")
            st.write(f"Phone: {g['Phone']}")
            st.write(f"Address: {g['Address']}")
            if st.button("Show Reservations", key=f"showres_{g['GuestID']}"):
                res = db.fetch_all("SELECT * FROM RESERVATION WHERE GuestID=%s ORDER BY CheckInDate DESC", (g['GuestID'],))
                st.write(res or "No reservations")

# ---------- Services ----------
elif menu == "Services":
    st.header("Services")
    svs = db.fetch_all("SELECT * FROM SERVICE") or []
    st.write(svs)

# ---------- Payments ----------
elif menu == "Payments":
    st.header("Payments (latest 100)")
    pays = db.fetch_all("SELECT p.*, r.CheckInDate, r.CheckOutDate FROM PAYMENT p JOIN RESERVATION r ON p.ReservationID=r.ReservationID ORDER BY p.PaymentDate DESC LIMIT 100") or []
    st.write(pays)


# ---------- Reports (with charts) ----------
elif menu == "Reports":

    st.header("📊 Reports & Visual Analytics")

    report = st.selectbox("Select report", [
        "Revenue Summary by Room Type",
        "Occupancy Rate by Room Type",
        "Daily Check-in Trend",
        "Service Usage Summary",
        "Total Guest Spending"
    ])

    # Helper to convert db results to DataFrame
    def df_query(query, params=None):
        data = db.fetch_all(query, params) or []
        return pd.DataFrame(data)

    # --------------------------------------------------
    # 1) Revenue Summary with Pie Chart
    # --------------------------------------------------
    if report == "Revenue Summary by Room Type":
        st.subheader("Revenue Summary by Room Type")

        query = """
            SELECT rt.TypeName AS RoomType,
                   SUM(ar.PricePerNight) AS Revenue
            FROM ALLOCATED_ROOM ar
            JOIN ROOM rm ON ar.RoomNumber = rm.RoomNumber
            JOIN ROOM_TYPE rt ON rm.RoomTypeID = rt.RoomTypeID
            GROUP BY rt.TypeName;
        """

        df = df_query(query)

        if df.empty:
            st.info("No revenue data found.")
        else:
            st.dataframe(df)

            fig = px.pie(df,
                         names="RoomType",
                         values="Revenue",
                         title="Revenue Distribution by Room Type")
            st.plotly_chart(fig)

    # --------------------------------------------------
    # 2) Occupancy Rate with Bar Chart
    # --------------------------------------------------
    elif report == "Occupancy Rate by Room Type":
        st.subheader("Current Occupancy Rate by Room Type")

        query = """
            SELECT rt.TypeName AS RoomType,
                   COUNT(rm.RoomNumber) AS TotalRooms,
                   SUM(CASE WHEN rm.Status='Occupied' THEN 1 ELSE 0 END) AS OccupiedRooms
            FROM ROOM rm
            JOIN ROOM_TYPE rt ON rm.RoomTypeID = rt.RoomTypeID
            GROUP BY rt.TypeName;
        """

        df = df_query(query)

        if df.empty:
            st.info("No room data found.")
        else:
            df["OccupancyRate"] = (df["OccupiedRooms"] / df["TotalRooms"]) * 100

            st.dataframe(df)

            fig = px.bar(df,
                         x="RoomType",
                         y="OccupancyRate",
                         text="OccupancyRate",
                         title="Occupancy % per Room Type")
            st.plotly_chart(fig)

    # --------------------------------------------------
    # 3) Daily Check-in Trend with Line Graph
    # --------------------------------------------------
    elif report == "Daily Check-in Trend":
        st.subheader("Daily Check-in Trend")

        query = """
            SELECT CheckInDate, COUNT(*) AS NumGuests
            FROM RESERVATION
            GROUP BY CheckInDate
            ORDER BY CheckInDate;
        """

        df = df_query(query)

        if df.empty:
            st.info("No check-ins recorded yet.")
        else:
            st.dataframe(df)

            fig = px.line(df,
                          x="CheckInDate",
                          y="NumGuests",
                          markers=True,
                          title="Daily Check-in Trend")
            st.plotly_chart(fig)

    # --------------------------------------------------
    # 4) Service Usage Summary with Bar Chart
    # --------------------------------------------------
    elif report == "Service Usage Summary":
        st.subheader("Service Usage Summary")

        query = """
            SELECT s.ServiceName,
                   COUNT(rs.ServiceID) AS TimesUsed
            FROM RESERVATION_SERVICE rs
            JOIN SERVICE s ON rs.ServiceID = s.ServiceID
            GROUP BY s.ServiceName;
        """

        df = df_query(query)

        if df.empty:
            st.info("No services used yet.")
        else:
            st.dataframe(df)

            fig = px.bar(df,
                         x="ServiceName",
                         y="TimesUsed",
                         text="TimesUsed",
                         title="Service Usage Count")
            st.plotly_chart(fig)

    # --------------------------------------------------
    # 5) Total Guest Spending with Bar Chart
    # --------------------------------------------------
    elif report == "Total Guest Spending":
        st.subheader("Total Guest Spending")

        query = """
            SELECT g.FirstName, g.LastName,
                   SUM(p.Amount) AS TotalSpent
            FROM PAYMENT p
            JOIN RESERVATION r ON p.ReservationID = r.ReservationID
            JOIN GUEST g ON r.GuestID = g.GuestID
            WHERE p.PaymentStatus='Completed'
            GROUP BY g.GuestID;
        """

        df = df_query(query)

        if df.empty:
            st.info("No payments found.")
        else:
            st.dataframe(df)

            df["Guest"] = df["FirstName"] + " " + df["LastName"]

            fig = px.bar(df,
                         x="Guest",
                         y="TotalSpent",
                         text="TotalSpent",
                         title="Total Spending per Guest")
            st.plotly_chart(fig)


# ---------- Debug ----------
elif menu == "Debug":
    st.header("Debug")
    if st.button("Test DB"):
        r = db.fetch_one("SELECT 1 as ok")
        if r and r.get('ok') == 1: st.success("DB ok")
        else: st.error("DB error or bad response")
