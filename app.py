
import streamlit as st
from database import init_db, get_movies, get_shows, get_available_seats, book_tickets, get_user_bookings, cancel_booking, get_stats

st.set_page_config(page_title="Movie Reservation System", page_icon="🎬", layout="wide")
init_db()

st.title("🎬 Movie Reservation System")
st.caption("Python + Streamlit + SQLite + Pandas + Machine Learning")

if "user_id" not in st.session_state:
    st.session_state.user_id = 1

menu = st.sidebar.radio("Menu", ["Home", "Movies & Booking", "My Bookings", "Analytics", "Admin"])

if menu == "Home":
    st.header("Welcome")
    c1,c2,c3 = st.columns(3)
    stats = get_stats()
    c1.metric("Movies", stats["movies"])
    c2.metric("Bookings", stats["bookings"])
    c3.metric("Revenue", f"₹{stats['revenue']:,.0f}")
    st.info("Demo login: customer is automatically selected. Use Admin to view management and analytics.")

elif menu == "Movies & Booking":
    st.header("🎟️ Book Movie Tickets")
    movies = get_movies()
    movie_names = [m["title"] for m in movies]
    selected_title = st.selectbox("Select Movie", movie_names)
    movie = next(m for m in movies if m["title"] == selected_title)
    st.write(f"**Genre:** {movie['genre']}  | **Language:** {movie['language']}  | **Duration:** {movie['duration']} min  | **Rating:** ⭐ {movie['rating']}")

    shows = get_shows(movie["movie_id"])
    show_labels = [f"{s['show_id']} | {s['theatre']} | {s['show_date']} | {s['show_time']}" for s in shows]
    selected_show_label = st.selectbox("Select Theatre & Show", show_labels)
    show_id = int(selected_show_label.split("|")[0].strip())

    seats = get_available_seats(show_id)
    seat_numbers = [s["seat_number"] for s in seats]
    selected_seats = st.multiselect("Select Seats", seat_numbers)

    if selected_seats:
        price = next(s["price"] for s in seats if s["seat_number"] == selected_seats[0])
        total = price * len(selected_seats)
        st.success(f"Selected: {', '.join(selected_seats)} | Total: ₹{total:,.0f}")

    if st.button("Confirm Booking", type="primary"):
        if not selected_seats:
            st.warning("Please select at least one seat.")
        else:
            booking_id = book_tickets(st.session_state.user_id, show_id, selected_seats)
            st.success(f"Booking confirmed! Booking ID: BK{booking_id:05d}")
            st.balloons()

elif menu == "My Bookings":
    st.header("📋 My Bookings")
    bookings = get_user_bookings(st.session_state.user_id)
    if not bookings:
        st.info("No bookings found.")
    for b in bookings:
        with st.expander(f"BK{b['booking_id']:05d} — {b['title']} — ₹{b['total_amount']:,.0f}"):
            st.write(f"Theatre: {b['theatre']}")
            st.write(f"Date/Time: {b['show_date']} {b['show_time']}")
            st.write(f"Seats: {b['seat_numbers']}")
            st.write(f"Status: **{b['status']}**")
            if b["status"] == "Confirmed":
                if st.button("Cancel Booking", key=f"cancel_{b['booking_id']}"):
                    cancel_booking(b["booking_id"])
                    st.success("Booking cancelled and seats released.")
                    st.rerun()

elif menu == "Analytics":
    st.header("📊 Data Science & Analytics")
    stats = get_stats()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Movies", stats["movies"])
    c2.metric("Confirmed Bookings", stats["bookings"])
    c3.metric("Tickets Sold", stats["tickets"])
    c4.metric("Revenue", f"₹{stats['revenue']:,.0f}")

    import pandas as pd
    from database import get_booking_dataframe
    df = get_booking_dataframe()
    if df.empty:
        st.info("Make a few bookings to see analytics.")
    else:
        st.subheader("Bookings by Movie")
        movie_counts = df[df["status"]=="Confirmed"].groupby("title").size().sort_values(ascending=False)
        st.bar_chart(movie_counts)
        st.subheader("Revenue by Movie")
        revenue = df[df["status"]=="Confirmed"].groupby("title")["total_amount"].sum().sort_values(ascending=False)
        st.bar_chart(revenue)
        st.subheader("Booking Dataset")
        st.dataframe(df, use_container_width=True)

elif menu == "Admin":
    st.header("⚙️ Admin Dashboard")
    st.warning("Demo admin panel — add authentication before deploying publicly.")
    stats = get_stats()
    st.write("### System Summary")
    st.write(f"- Movies: {stats['movies']}")
    st.write(f"- Confirmed bookings: {stats['bookings']}")
    st.write(f"- Tickets sold: {stats['tickets']}")
    st.write(f"- Revenue: ₹{stats['revenue']:,.0f}")
    st.write("### Available Movies")
    for m in get_movies():
        st.write(f"🎬 {m['title']} — {m['genre']} — {m['language']} — ⭐ {m['rating']}")
