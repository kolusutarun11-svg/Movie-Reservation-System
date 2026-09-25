
import sqlite3
from pathlib import Path
from datetime import date

DB = Path(__file__).parent / "data" / "movie.db"

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    DB.parent.mkdir(exist_ok=True)
    c = conn()
    cur = c.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS movies(
        movie_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, genre TEXT, language TEXT,
        duration INTEGER, rating REAL
    );
    CREATE TABLE IF NOT EXISTS shows(
        show_id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER, theatre TEXT, show_date TEXT, show_time TEXT,
        FOREIGN KEY(movie_id) REFERENCES movies(movie_id)
    );
    CREATE TABLE IF NOT EXISTS seats(
        seat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        show_id INTEGER, seat_number TEXT, status TEXT DEFAULT 'Available',
        price REAL, FOREIGN KEY(show_id) REFERENCES shows(show_id)
    );
    CREATE TABLE IF NOT EXISTS bookings(
        booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, show_id INTEGER, booking_date TEXT,
        total_amount REAL, status TEXT DEFAULT 'Confirmed'
    );
    CREATE TABLE IF NOT EXISTS booking_seats(
        booking_id INTEGER, seat_id INTEGER,
        FOREIGN KEY(booking_id) REFERENCES bookings(booking_id),
        FOREIGN KEY(seat_id) REFERENCES seats(seat_id)
    );
    """)
    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        cur.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                    ("Demo User","demo@example.com","1234"))
    if cur.execute("SELECT COUNT(*) FROM movies").fetchone()[0] == 0:
        movies = [
            ("Interstellar","Sci-Fi","English",169,8.7),
            ("RRR","Action","Telugu",187,8.0),
            ("Inception","Sci-Fi","English",148,8.8),
            ("Baahubali 2","Action","Telugu",167,8.2),
            ("3 Idiots","Comedy","Hindi",170,8.4)
        ]
        cur.executemany("INSERT INTO movies(title,genre,language,duration,rating) VALUES(?,?,?,?,?)", movies)
    if cur.execute("SELECT COUNT(*) FROM shows").fetchone()[0] == 0:
        shows = []
        for movie_id in range(1,6):
            shows += [(movie_id,"Screen 1","2026-09-26","10:00 AM"),
                      (movie_id,"Screen 2","2026-09-26","02:00 PM"),
                      (movie_id,"Screen 3","2026-09-26","07:30 PM")]
        cur.executemany("INSERT INTO shows(movie_id,theatre,show_date,show_time) VALUES(?,?,?,?)", shows)
        for show_id in range(1,16):
            for r in "ABCDE":
                for n in range(1,7):
                    cur.execute("INSERT INTO seats(show_id,seat_number,status,price) VALUES(?,?,?,?)",
                                (show_id,f"{r}{n}","Available",180 if r in "AB" else 150))
    c.commit()
    c.close()

def get_movies():
    c=conn(); rows=c.execute("SELECT * FROM movies").fetchall(); c.close(); return rows

def get_shows(movie_id):
    c=conn(); rows=c.execute("SELECT * FROM shows WHERE movie_id=? ORDER BY show_time",(movie_id,)).fetchall(); c.close(); return rows

def get_available_seats(show_id):
    c=conn(); rows=c.execute("SELECT * FROM seats WHERE show_id=? AND status='Available' ORDER BY seat_number",(show_id,)).fetchall(); c.close(); return rows

def book_tickets(user_id, show_id, seat_numbers):
    c=conn(); cur=c.cursor()
    qmarks=",".join("?"*len(seat_numbers))
    rows=cur.execute(f"SELECT * FROM seats WHERE show_id=? AND seat_number IN ({qmarks}) AND status='Available'",
                     [show_id]+seat_numbers).fetchall()
    if len(rows)!=len(seat_numbers):
        c.close(); raise ValueError("One or more seats are no longer available.")
    total=sum(r["price"] for r in rows)
    cur.execute("INSERT INTO bookings(user_id,show_id,booking_date,total_amount,status) VALUES(?,?,?,?,?)",
                (user_id,show_id,str(date.today()),total,"Confirmed"))
    booking_id=cur.lastrowid
    for r in rows:
        cur.execute("INSERT INTO booking_seats(booking_id,seat_id) VALUES(?,?)",(booking_id,r["seat_id"]))
        cur.execute("UPDATE seats SET status='Booked' WHERE seat_id=?",(r["seat_id"],))
    c.commit(); c.close(); return booking_id

def get_user_bookings(user_id):
    c=conn()
    rows=c.execute("""
    SELECT b.*, m.title, s.theatre, s.show_date, s.show_time,
           GROUP_CONCAT(se.seat_number, ', ') AS seat_numbers
    FROM bookings b
    JOIN shows s ON b.show_id=s.show_id
    JOIN movies m ON s.movie_id=m.movie_id
    LEFT JOIN booking_seats bs ON b.booking_id=bs.booking_id
    LEFT JOIN seats se ON bs.seat_id=se.seat_id
    WHERE b.user_id=?
    GROUP BY b.booking_id ORDER BY b.booking_id DESC
    """,(user_id,)).fetchall()
    c.close(); return rows

def cancel_booking(booking_id):
    c=conn(); cur=c.cursor()
    cur.execute("UPDATE bookings SET status='Cancelled' WHERE booking_id=?",(booking_id,))
    cur.execute("""UPDATE seats SET status='Available'
                   WHERE seat_id IN (SELECT seat_id FROM booking_seats WHERE booking_id=?)""",(booking_id,))
    c.commit(); c.close()

def get_stats():
    c=conn()
    movies=c.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    bookings=c.execute("SELECT COUNT(*) FROM bookings WHERE status='Confirmed'").fetchone()[0]
    tickets=c.execute("""SELECT COUNT(*) FROM booking_seats bs JOIN bookings b ON bs.booking_id=b.booking_id
                         WHERE b.status='Confirmed'""").fetchone()[0]
    revenue=c.execute("SELECT COALESCE(SUM(total_amount),0) FROM bookings WHERE status='Confirmed'").fetchone()[0]
    c.close()
    return {"movies":movies,"bookings":bookings,"tickets":tickets,"revenue":revenue}

def get_booking_dataframe():
    import pandas as pd
    c=conn()
    df=pd.read_sql_query("""
    SELECT b.booking_id, m.title, m.genre, m.language, s.theatre,
           s.show_date, s.show_time, b.booking_date, b.total_amount, b.status
    FROM bookings b
    JOIN shows s ON b.show_id=s.show_id
    JOIN movies m ON s.movie_id=m.movie_id
    ORDER BY b.booking_id DESC
    """,c)
    c.close(); return df
