from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from functools import wraps
import os
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import db
import notifications

app = Flask(__name__)

# Secret key: read from env var; generate a random one as a fallback for local dev
# so the app never ships with a fixed, guessable key baked into source control.
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32)

# Admin credentials: must be set via environment variables. No hardcoded fallback
# for the password so the app fails loudly instead of running with a known passcode.
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSCODE = os.environ.get('ADMIN_PASSCODE')

if not ADMIN_PASSCODE:
    raise RuntimeError(
        "ADMIN_PASSCODE environment variable is not set. "
        "Set it before starting the app (see .env.example)."
    )

# Ensure DB & tables exist whenever this module loads — this runs under
# gunicorn too (not just `python app.py`), so production deploys always
# have the schema in place.
db.init_db()


@app.before_request
def check_admin_session():
    allowed_endpoints = {
        'admin_portal', 'admin_login', 'admin_logout', 'static',
        'admin_bookings', 'admin_update_status',
        'admin_employees', 'admin_add_employee', 'admin_update_employee', 'admin_delete_employee',
    }
    if not request.endpoint or request.endpoint not in allowed_endpoints:
        session.pop('admin_logged_in', None)


# Decorator to restrict API access to logged-in admins
def admin_api_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 401
        return f(*args, **kwargs)
    return decorated_function


def serialize_booking(b):
    """Formats database fields for JSON response."""
    if not b:
        return None
    res = b.copy()
    if res.get('preferred_date'):
        res['preferred_date'] = res['preferred_date'].strftime('%Y-%m-%d')
    if res.get('created_at'):
        res['created_at'] = res['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    return res


def serialize_employee(e):
    """Formats employee database fields for JSON response."""
    if not e:
        return None
    res = e.copy()
    if res.get('monthly_salary') is not None:
        res['monthly_salary'] = float(res['monthly_salary'])
    if res.get('created_at'):
        res['created_at'] = res['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    if res.get('updated_at'):
        res['updated_at'] = res['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
    return res


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/admin')
def admin_portal():
    if session.get('admin_logged_in'):
        return render_template('admin.html', logged_in=True)
    return render_template('admin.html', logged_in=False)


@app.route('/api/book', methods=['POST'])
def book_repair():
    data = request.json or request.form
    name = data.get('name')
    phone = data.get('phone')
    email = data.get('email')
    ac_type = data.get('ac_type')
    issue = data.get('issue')
    pref_date = data.get('pref_date')
    pref_time = data.get('pref_time')

    if not all([name, phone, ac_type, issue, pref_date, pref_time]):
        return jsonify({'success': False, 'error': 'Please fill all required fields.'}), 400

    try:
        code = db.add_booking(name, phone, email, ac_type, issue, pref_date, pref_time)
        # Notify the customer on their booking phone number. This never
        # blocks or fails the booking itself — see notifications.py.
        notifications.send_booking_confirmation_sms(phone, name, code)
        return jsonify({'success': True, 'tracking_code': code})
    except Exception as e:
        app.logger.exception("Error adding booking")
        return jsonify({'success': False, 'error': 'Something went wrong while saving your booking.'}), 500


@app.route('/api/track/<tracking_code>', methods=['GET'])
def track_repair(tracking_code):
    try:
        booking = db.get_booking(tracking_code.strip().upper())
        if booking:
            return jsonify({'success': True, 'booking': serialize_booking(booking)})
        else:
            return jsonify({'success': False, 'error': 'No booking found with this tracking code.'}), 404
    except Exception as e:
        app.logger.exception("Error tracking booking")
        return jsonify({'success': False, 'error': 'Something went wrong while looking up your booking.'}), 500


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json or {}
    username = data.get('username')
    passcode = data.get('passcode')

    if username == ADMIN_USERNAME and passcode == ADMIN_PASSCODE:
        session['admin_logged_in'] = True
        return jsonify({'success': True, 'message': 'Login successful'})
    else:
        return jsonify({'success': False, 'error': 'Invalid username or passcode'}), 401


@app.route('/api/admin/logout', methods=['POST', 'GET'])
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_portal'))


@app.route('/api/admin/bookings', methods=['GET'])
@admin_api_required
def admin_bookings():
    try:
        bookings = db.get_all_bookings()
        serialized = [serialize_booking(b) for b in bookings]
        return jsonify({'success': True, 'bookings': serialized})
    except Exception as e:
        app.logger.exception("Error fetching bookings")
        return jsonify({'success': False, 'error': 'Something went wrong while fetching bookings.'}), 500


@app.route('/api/admin/update-status', methods=['POST'])
@admin_api_required
def admin_update_status():
    data = request.json or {}
    tracking_code = data.get('tracking_code')
    new_status = data.get('status')

    if not tracking_code or not new_status:
        return jsonify({'success': False, 'error': 'Missing booking code or status.'}), 400

    try:
        success = db.update_status(tracking_code, new_status)
        if success:
            # Best-effort SMS to the customer about their status change.
            booking = db.get_booking(tracking_code)
            if booking:
                notifications.send_status_update_sms(booking['phone'], tracking_code, new_status)
            return jsonify({'success': True, 'message': f'Status updated to {new_status}'})
        else:
            return jsonify({'success': False, 'error': 'Booking not found or status not changed.'}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        app.logger.exception("Error updating status")
        return jsonify({'success': False, 'error': 'Something went wrong while updating status.'}), 500


# ---------------------------------------------------------------------------
# Employee salary management — admin-only. Every route below is protected by
# admin_api_required and also listed in allowed_endpoints above so a logged
# out session can't reach it.
# ---------------------------------------------------------------------------

@app.route('/api/admin/employees', methods=['GET'])
@admin_api_required
def admin_employees():
    try:
        employees = db.get_all_employees()
        serialized = [serialize_employee(e) for e in employees]
        return jsonify({'success': True, 'employees': serialized})
    except Exception as e:
        app.logger.exception("Error fetching employees")
        return jsonify({'success': False, 'error': 'Something went wrong while fetching employees.'}), 500


@app.route('/api/admin/employees', methods=['POST'])
@admin_api_required
def admin_add_employee():
    data = request.json or {}
    full_name = data.get('full_name')
    role = data.get('role')
    phone = data.get('phone')
    monthly_salary = data.get('monthly_salary')

    if not all([full_name, role]) or monthly_salary in (None, ''):
        return jsonify({'success': False, 'error': 'Name, role, and salary are required.'}), 400

    try:
        monthly_salary = float(monthly_salary)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Salary must be a number.'}), 400

    try:
        new_id = db.add_employee(full_name, role, phone, monthly_salary)
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        app.logger.exception("Error adding employee")
        return jsonify({'success': False, 'error': 'Something went wrong while adding the employee.'}), 500


@app.route('/api/admin/employees/<int:employee_id>', methods=['PUT'])
@admin_api_required
def admin_update_employee(employee_id):
    data = request.json or {}
    full_name = data.get('full_name')
    role = data.get('role')
    phone = data.get('phone')
    monthly_salary = data.get('monthly_salary')

    if not all([full_name, role]) or monthly_salary in (None, ''):
        return jsonify({'success': False, 'error': 'Name, role, and salary are required.'}), 400

    try:
        monthly_salary = float(monthly_salary)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Salary must be a number.'}), 400

    try:
        success = db.update_employee(employee_id, full_name, role, phone, monthly_salary)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Employee not found.'}), 404
    except Exception as e:
        app.logger.exception("Error updating employee")
        return jsonify({'success': False, 'error': 'Something went wrong while updating the employee.'}), 500


@app.route('/api/admin/employees/<int:employee_id>', methods=['DELETE'])
@admin_api_required
def admin_delete_employee(employee_id):
    try:
        success = db.delete_employee(employee_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Employee not found.'}), 404
    except Exception as e:
        app.logger.exception("Error deleting employee")
        return jsonify({'success': False, 'error': 'Something went wrong while deleting the employee.'}), 500


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
