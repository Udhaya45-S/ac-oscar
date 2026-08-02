
import mysql.connector
from mysql.connector import Error
import random
import string
import os
 
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD'),
}
DB_NAME = os.environ.get('DB_NAME', 'oscar_air_care')
 
if not DB_CONFIG['password']:
    raise RuntimeError(
        "DB_PASSWORD environment variable is not set. "
        "Set it before starting the app (see .env.example)."
    )
 
 
def get_connection(include_db=True):
    config = DB_CONFIG.copy()
    if include_db:
        config['database'] = DB_NAME
    return mysql.connector.connect(**config)
 
 
def init_db():
    """Initializes the database and required tables if they do not exist."""
    try:
        # First connect without selecting a database to ensure the DB exists
        conn = get_connection(include_db=False)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
        cursor.close()
        conn.close()
 
        # Connect to the specific DB and build the tables
        conn = get_connection(include_db=True)
        cursor = conn.cursor()
 
        create_bookings_table = """
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tracking_code VARCHAR(15) UNIQUE NOT NULL,
            customer_name VARCHAR(100) NOT NULL,
            phone VARCHAR(15) NOT NULL,
            email VARCHAR(100),
            ac_type VARCHAR(50) NOT NULL,
            issue_description TEXT NOT NULL,
            preferred_date DATE NOT NULL,
            preferred_time VARCHAR(50) NOT NULL,
            status VARCHAR(20) DEFAULT 'Booked',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_bookings_table)
 
        # Employee salary records — admin-only, never exposed via public endpoints
        create_employees_table = """
        CREATE TABLE IF NOT EXISTS employees (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            role VARCHAR(50) NOT NULL,
            phone VARCHAR(15),
            monthly_salary DECIMAL(10, 2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_employees_table)
 
        # Estimated base price per AC type, used to compute revenue estimates
        # on the analytics dashboard. Editable by admin.
        create_prices_table = """
        CREATE TABLE IF NOT EXISTS service_prices (
            ac_type VARCHAR(50) PRIMARY KEY,
            base_price DECIMAL(10, 2) NOT NULL
        );
        """
        cursor.execute(create_prices_table)
 
        default_prices = [
            ('Split AC', 599.00),
            ('Window AC', 499.00),
            ('Inverter AC', 699.00),
            ('Cassette AC', 899.00),
            ('Central AC', 1499.00),
        ]
        for ac_type, price in default_prices:
            cursor.execute(
                "INSERT IGNORE INTO service_prices (ac_type, base_price) VALUES (%s, %s)",
                (ac_type, price)
            )
 
        # Customer reviews — one review per completed booking (enforced by
        # UNIQUE on tracking_code so a customer can't submit twice).
        create_reviews_table = """
        CREATE TABLE IF NOT EXISTS reviews (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tracking_code VARCHAR(15) UNIQUE NOT NULL,
            customer_name VARCHAR(100) NOT NULL,
            rating TINYINT NOT NULL,
            review_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5)
        );
        """
        cursor.execute(create_reviews_table)
 
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully.")
        return True
    except Error as e:
        print(f"Error during MySQL database initialization: {e}")
        return False
 
 
def generate_tracking_code():
    """Generates a random 6-character uppercase alphanumeric tracking code, excluding confusing letters."""
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
    return 'OAC-' + ''.join(random.choices(chars, k=6))
 
 
def add_booking(name, phone, email, ac_type, issue, pref_date, pref_time):
    """Inserts a new booking into the database, generating a unique tracking code."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
 
    attempts = 0
    while attempts < 10:
        tracking_code = generate_tracking_code()
        try:
            insert_query = """
            INSERT INTO bookings (tracking_code, customer_name, phone, email, ac_type, issue_description, preferred_date, preferred_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                tracking_code,
                name,
                phone,
                email if email else None,
                ac_type,
                issue,
                pref_date,
                pref_time
            ))
            conn.commit()
            cursor.close()
            conn.close()
            return tracking_code
        except mysql.connector.IntegrityError as err:
            if err.errno == 1062:
                attempts += 1
                continue
            else:
                cursor.close()
                conn.close()
                raise err
    cursor.close()
    conn.close()
    raise Exception("Could not generate a unique tracking code after several attempts.")
 
 
def get_booking(tracking_code):
    """Retrieves a single booking details matching the tracking code."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM bookings WHERE tracking_code = %s"
    cursor.execute(query, (tracking_code,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result
 
 
def get_all_bookings():
    """Retrieves all bookings from the database, ordered by latest booking first."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM bookings ORDER BY created_at DESC"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results
 
 
def update_status(tracking_code, new_status):
    """Updates the progress status of a specific booking."""
    if new_status not in ['Booked', 'Processing', 'Completed']:
        raise ValueError("Invalid booking status")
 
    conn = get_connection()
    cursor = conn.cursor()
    query = "UPDATE bookings SET status = %s WHERE tracking_code = %s"
    cursor.execute(query, (new_status, tracking_code))
    conn.commit()
    rows_affected = cursor.rowcount
    cursor.close()
    conn.close()
    return rows_affected > 0
 
 
def delete_booking(tracking_code):
    """Deletes a booking matching the tracking code."""
    conn = get_connection()
    cursor = conn.cursor()
    query = "DELETE FROM bookings WHERE tracking_code = %s"
    cursor.execute(query, (tracking_code,))
    conn.commit()
    rows_affected = cursor.rowcount
    cursor.close()
    conn.close()
    return rows_affected > 0
 
 
# ---------------------------------------------------------------------------
# Employee salary records (admin-only — routes in app.py must stay behind
# admin_api_required so this data is never publicly reachable)
# ---------------------------------------------------------------------------
 
def add_employee(full_name, role, phone, monthly_salary):
    """Inserts a new employee salary record."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
    INSERT INTO employees (full_name, role, phone, monthly_salary)
    VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (full_name, role, phone if phone else None, monthly_salary))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return new_id
 
 
def get_all_employees():
    """Retrieves all employee salary records, ordered by name."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM employees ORDER BY full_name ASC"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results
 
 
def get_employee(employee_id):
    """Retrieves a single employee record by id."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM employees WHERE id = %s"
    cursor.execute(query, (employee_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result
 
 
def update_employee(employee_id, full_name, role, phone, monthly_salary):
    """Updates an existing employee salary record."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
    UPDATE employees
    SET full_name = %s, role = %s, phone = %s, monthly_salary = %s
    WHERE id = %s
    """
    cursor.execute(query, (full_name, role, phone if phone else None, monthly_salary, employee_id))
    conn.commit()
    rows_affected = cursor.rowcount
    cursor.close()
    conn.close()
    return rows_affected > 0
 
 
def delete_employee(employee_id):
    """Deletes an employee salary record."""
    conn = get_connection()
    cursor = conn.cursor()
    query = "DELETE FROM employees WHERE id = %s"
    cursor.execute(query, (employee_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    cursor.close()
    conn.close()
    return rows_affected > 0
 
 
# ---------------------------------------------------------------------------
# Service prices (admin-editable, used for revenue estimates)
# ---------------------------------------------------------------------------
 
def get_all_service_prices():
    """Returns {ac_type: base_price} for every configured AC type."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT ac_type, base_price FROM service_prices")
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return {row['ac_type']: float(row['base_price']) for row in results}
 
 
def update_service_price(ac_type, base_price):
    """Upserts the base price for a given AC type."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
    INSERT INTO service_prices (ac_type, base_price) VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE base_price = VALUES(base_price)
    """
    cursor.execute(query, (ac_type, base_price))
    conn.commit()
    cursor.close()
    conn.close()
    return True
 
 
# ---------------------------------------------------------------------------
# Customer reviews
# ---------------------------------------------------------------------------
 
def add_review(tracking_code, customer_name, rating, review_text):
    """Inserts a review for a completed booking. tracking_code is UNIQUE,
    so this raises IntegrityError if the booking was already reviewed."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
    INSERT INTO reviews (tracking_code, customer_name, rating, review_text)
    VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (tracking_code, customer_name, rating, review_text))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return new_id
 
 
def get_review_by_tracking_code(tracking_code):
    """Checks whether a booking has already been reviewed."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reviews WHERE tracking_code = %s", (tracking_code,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result
 
 
def get_all_reviews():
    """Retrieves all reviews, newest first."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reviews ORDER BY created_at DESC")
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results
 
 
def delete_review(review_id):
    """Deletes a review (admin moderation)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reviews WHERE id = %s", (review_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    cursor.close()
    conn.close()
    return rows_affected > 0
 
 
# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
 
def get_analytics_data():
    """
    Returns the raw data analytics needs: all bookings (with computed price
    per row) plus current service prices. Aggregation (monthly totals, busy
    day/slot breakdowns, etc.) is done in app.py so this stays a simple,
    testable data-fetch function.
    """
    bookings = get_all_bookings()
    prices = get_all_service_prices()
    return bookings, prices
 
