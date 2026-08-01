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


@app.before_request
def check_admin_session():
    allowed_endpoints = {'admin_portal', 'admin_login', 'admin_logout', 'admin_bookings', 'admin_update_status', 'static'}
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
            return jsonify({'success': True, 'message': f'Status updated to {new_status}'})
        else:
            return jsonify({'success': False, 'error': 'Booking not found or status not changed.'}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        app.logger.exception("Error updating status")
        return jsonify({'success': False, 'error': 'Something went wrong while updating status.'}), 500


if __name__ == '__main__':
    db.init_db()
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
