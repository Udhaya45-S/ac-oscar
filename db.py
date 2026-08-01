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
