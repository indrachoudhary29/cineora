from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'cineora_ultra_secret_key'

# --- DATABASE CONNECTION ---
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Indracrv",  # Your confirmed password
        database="cineora_local"
    )

# --- AUTHENTICATION (USER & ADMIN) ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('fullname')
        email = request.form.get('email')
        pwd = request.form.get('password')
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Users can register with ANY random email/password
            cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES (%s, %s, %s, 'user')", (name, email, pwd))
            conn.commit()
            return redirect(url_for('login'))
        except Exception as e:
            flash("Registration Failed: Email might already exist!")
            return redirect(url_for('register'))
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()
        role = request.form.get('role')

        # 1. SPECIFIC ADMIN GATE (Hardcoded for Security)
        if role == 'admin':
            if email == "admin@cineora.com" and password == "master2026":
                session['role'] = 'admin'
                session['fullname'] = "System Admin"
                return redirect(url_for('admin_dashboard'))
            else:
                flash("Invalid Admin Credentials")
                return redirect(url_for('login'))

        # 2. RANDOM USER GATE (Database Check)
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            # Checks the database for the email/password the user just registered
            cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
            user = cursor.fetchone()
            conn.close()

            if user:
                session['user_id'] = user['id']
                session['role'] = 'user'
                session['fullname'] = user['fullname']
                return redirect(url_for('home'))
            
            flash("Invalid User Credentials. Please check your email and password.")
        except Exception as e:
            flash(f"Database Error: {str(e)}")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- USER SIDE FUNCTIONALITY ---

@app.route('/')
def home():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM movies")
    movies = cursor.fetchall()
    conn.close()
    return render_template('cineora.html', movies=movies, user_name=session.get('fullname', 'Guest'))

@app.route('/book/<int:movie_id>')
def book_movie(movie_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
    movie = cursor.fetchone()
    conn.close()
    return render_template('book.html', movie=movie)

@app.route('/api/reserve', methods=['POST'])
def reserve():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})
    
    data = request.json
    u_id = session['user_id']
    m_id = data['movie_id']
    time = data['show_time']
    new_seats = data['seats']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # RDBMS CHECK: Prevent Double Booking
    cursor.execute("SELECT seats_selected FROM bookings WHERE movie_id = %s AND show_time = %s", (m_id, time))
    booked_rows = cursor.fetchall()
    occupied = []
    for row in booked_rows: 
        occupied.extend(row['seats_selected'].split(','))
    
    for seat in new_seats:
        if seat in occupied: 
            return jsonify({'status': 'error', 'message': f'Seat {seat} already taken!'})

    cursor.execute("INSERT INTO bookings (user_id, movie_id, show_time, seats_selected, total_price) VALUES (%s,%s,%s,%s,%s)",
                   (u_id, m_id, time, ",".join(new_seats), data['total_price']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/my-bookings')
def my_bookings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT b.id, m.title, b.seats_selected, b.total_price, b.booking_date, b.movie_id
        FROM bookings b 
        JOIN movies m ON b.movie_id = m.id 
        WHERE b.user_id = %s
        ORDER BY b.booking_date DESC
    """
    
    image_map = {
        1: 'majili.jpg', 2: 'dune.jpg', 3: 'batman.jpg', 
        4: 'oppenheimer.jpg', 5: 'spider.jpg', 6: 'avatar.jpg', 
        7: 'inception.jpg', 8: 'metro.jpg'
    }

    try:
        cursor.execute(query, (session['user_id'],))
        bookings_data = cursor.fetchall()
        for b in bookings_data:
            b['image_url'] = image_map.get(b['movie_id'], 'placeholder.jpg')
    except Exception as e:
        bookings_data = []
    finally:
        conn.close()
        
    return render_template('my_bookings.html', bookings=bookings_data)

# --- ADMIN SIDE (DATABASE CONNECTIVITY & CREATIVITY) ---

@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin': 
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Real-time Movie Inventory
    cursor.execute("SELECT * FROM movies")
    movies_list = cursor.fetchall()
    
    # 2. Recent Transactions (Relational JOIN Creativity)
    cursor.execute("""
        SELECT b.id, b.user_id, u.fullname, m.title, b.show_time, b.seats_selected, b.total_price 
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN movies m ON b.movie_id = m.id
        ORDER BY b.id DESC
    """)
    bookings_list = cursor.fetchall()
    
    # 3. Global Stats from Database
    cursor.execute("SELECT SUM(total_price) AS total FROM bookings")
    revenue_res = cursor.fetchone()
    total_revenue = float(revenue_res['total']) if revenue_res and revenue_res['total'] else 0
    
    cursor.execute("SELECT COUNT(id) AS count FROM users WHERE role = 'user'")
    total_users_res = cursor.fetchone()
    total_users = total_users_res['count'] if total_users_res else 0

    # 4. NEXT LEVEL: 7-Day Revenue Intelligence 📈
    revenue_trends = []
    date_labels = []

    for i in range(6, -1, -1):
        target_date = (datetime.now() - timedelta(days=i)).date()
        date_labels.append(target_date.strftime('%d %b'))

        cursor.execute("""
            SELECT SUM(total_price) AS daily_total 
            FROM bookings 
            WHERE DATE(booking_date) = %s
        """, (target_date,))
        
        day_res = cursor.fetchone()
        revenue_trends.append(float(day_res['daily_total']) if day_res and day_res['daily_total'] else 0)

    conn.close()
    
    return render_template('admin_dashboard.html', 
                            bookings=bookings_list, 
                            movies=movies_list, 
                            revenue=total_revenue, 
                            users_count=total_users, 
                            bookings_count=len(bookings_list), 
                            revenue_trends=revenue_trends, 
                            date_labels=date_labels)

@app.route('/admin/add_movie', methods=['POST'])
def add_movie():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    title = request.form.get('title')
    genre = request.form.get('genre')
    price = request.form.get('price')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO movies (title, genre, price) VALUES (%s, %s, %s)", (title, genre, price))
    conn.commit()
    conn.close()
    flash("New Movie Added Successfully!")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_movie/<int:movie_id>')
def delete_movie(movie_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    # RDBMS Feature: Deleting a movie will remove it from the dashboard inventory
    cursor.execute("DELETE FROM movies WHERE id = %s", (movie_id,))
    conn.commit()
    conn.close()
    flash("Movie removed successfully!")
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)