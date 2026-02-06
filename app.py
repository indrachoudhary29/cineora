from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = 'cineora_secret_key'

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Indracrv", # Change this to your MySQL password
        database="cineora_local"
    )

# --- AUTHENTICATION ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name, email, pwd = request.form.get('fullname'), request.form.get('email'), request.form.get('password')
        conn = get_db_connection(); cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (fullname, email, password) VALUES (%s, %s, %s)", (name, email, pwd))
            conn.commit()
            return redirect(url_for('login'))
        except: flash("Email already exists!"); return redirect(url_for('register'))
        finally: conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, pwd = request.form.get('email'), request.form.get('password')
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, pwd))
        user = cursor.fetchone()
        if user:
            session['user_id'], session['name'], session['role'] = user['id'], user['fullname'], user['role']
            return redirect(url_for('admin_dashboard' if user['role'] == 'admin' else 'home'))
        flash("Invalid Credentials"); conn.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# --- USER SIDE ---
@app.route('/')
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM movies")
    movies = cursor.fetchall()
    conn.close()
    return render_template('cineora.html', movies=movies, user_name=session['name'])

@app.route('/book/<int:movie_id>')
def book_movie(movie_id):
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
    movie = cursor.fetchone()
    conn.close()
    return render_template('book.html', movie=movie)


@app.route('/api/reserve', methods=['POST'])
def reserve():
    data = request.json
    u_id, m_id, time, new_seats = session['user_id'], data['movie_id'], data['show_time'], data['seats']
    
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    
    # RDBMS CHECK: Prevent Double Booking
    cursor.execute("SELECT seats_selected FROM bookings WHERE movie_id = %s AND show_time = %s", (m_id, time))
    booked_rows = cursor.fetchall()
    occupied = []
    for row in booked_rows: occupied.extend(row['seats_selected'].split(','))
    
    for seat in new_seats:
        if seat in occupied: return jsonify({'status': 'error', 'message': f'Seat {seat} already taken!'})

    cursor.execute("INSERT INTO bookings (user_id, movie_id, show_time, seats_selected, total_price) VALUES (%s,%s,%s,%s,%s)",
                   (u_id, m_id, time, ",".join(new_seats), data['total_price']))
    conn.commit(); conn.close()
    return jsonify({'status': 'success'})
@app.route('/my-bookings')
def my_bookings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # We use 'seats_selected' because that is what your SQL table has
    query = """
        SELECT b.id, m.title, b.seats_selected, b.total_price, b.booking_date, b.movie_id
        FROM bookings b 
        JOIN movies m ON b.movie_id = m.id 
        WHERE b.user_id = %s
        ORDER BY b.booking_date DESC
    """
    
    # This maps your movie IDs to your static filenames manually
    image_map = {
        1: 'majili.jpg', 2: 'dune.jpg', 3: 'batman.jpg', 
        4: 'oppenheimer.jpg', 5: 'spider.jpg', 6: 'avatar.jpg', 
        7: 'inception.jpg', 8: 'metro.jpg'
    }

    try:
        cursor.execute(query, (session['user_id'],))
        bookings_data = cursor.fetchall()
        
        # We manually add the image filename to each booking result
        for b in bookings_data:
            b['image_url'] = image_map.get(b['movie_id'], 'placeholder.jpg')
            
    except Exception as e:
        print(f"Database Error: {e}")
        bookings_data = []
    finally:
        conn.close()
        
    return render_template('my_bookings.html', bookings=bookings_data)
@app.route('/admin')
def admin_dashboard():
    # 1. Security Gatekeeper
    if session.get('role') != 'admin': 
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 2. Movie Inventory (For the delete/view section)
    cursor.execute("SELECT * FROM movies")
    movies_list = cursor.fetchall()
    
    # 3. The Master RDBMS JOIN (For the Recent Transactions table)
    cursor.execute("""
        SELECT b.id, u.fullname, m.title, b.show_time, b.seats_selected, b.total_price 
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN movies m ON b.movie_id = m.id
        ORDER BY b.booking_date DESC
    """)
    bookings_list = cursor.fetchall()
    
    # 4. Analytics: Calculate Total Revenue (RDBMS SUM Function)
    cursor.execute("SELECT SUM(total_price) AS total FROM bookings")
    revenue_res = cursor.fetchone()
    total_revenue = revenue_res['total'] if revenue_res['total'] else 0
    
    # 5. Analytics: Total Users (RDBMS COUNT Function)
    cursor.execute("SELECT COUNT(id) AS count FROM users WHERE role = 'user'")
    user_count_res = cursor.fetchone()
    total_users = user_count_res['count']
    
    conn.close()
    
    # 6. Return everything to the template
    # Note: Variable names here MUST match your admin.html (revenue, user_count, bookings, movies)
    return render_template('admin.html', 
                           bookings=bookings_list, 
                           movies=movies_list, 
                           revenue=total_revenue, 
                           user_count=total_users)
@app.route('/admin/delete_movie/<int:movie_id>')
def delete_movie(movie_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # This is where the RDBMS 'Cascade' happens!
    cursor.execute("DELETE FROM movies WHERE id = %s", (movie_id,))
    
    conn.commit()
    conn.close()
    flash("Movie and all associated bookings removed successfully!")
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)