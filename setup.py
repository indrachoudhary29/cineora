import mysql.connector

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Indracrv"  # Replace with your MySQL root password
)
cursor = db.cursor()

# Create database
cursor.execute("CREATE DATABASE IF NOT EXISTS cineora")
cursor.execute("USE cineora")

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50),
    email VARCHAR(50) UNIQUE,
    password VARCHAR(100),
    role ENUM('admin','user') DEFAULT 'user'
)
""")

# Insert admin if not exists
cursor.execute("SELECT * FROM users WHERE email='admin@cineora.com'")
if cursor.fetchone() is None:
    cursor.execute("""
    INSERT INTO users(name,email,password,role) 
    VALUES ('Admin','admin@cineora.com','admin123','admin')
    """)
    print("✅ Admin created")
else:
    print("ℹ Admin user already exists, skipping insert.")

# Movies table
cursor.execute("""
CREATE TABLE IF NOT EXISTS movies(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    genre VARCHAR(50),
    poster VARCHAR(255),
    price DECIMAL(5,2)
)
""")

# Seats table
cursor.execute("""
CREATE TABLE IF NOT EXISTS seats(
    id INT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT,
    seat_no VARCHAR(5),
    status ENUM('available','booked') DEFAULT 'available',
    FOREIGN KEY(movie_id) REFERENCES movies(id)
)
""")

# Bookings table
cursor.execute("""
CREATE TABLE IF NOT EXISTS bookings(
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    movie_id INT,
    seats VARCHAR(50),
    total DECIMAL(6,2),
    booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(movie_id) REFERENCES movies(id)
)
""")

db.commit()
cursor.close()
db.close()
print("🎉 Database and tables are ready!")
