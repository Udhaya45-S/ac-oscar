
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from functools import wraps
from collections import Counter, defaultdict
from datetime import datetime, date
import calendar
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
        'admin_analytics', 'admin_service_prices', 'admin_update_service_price',
        'admin_reviews', 'admin_delete_review',
        'submit_review', 'public_reviews',
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
 
 
def serialize_review(r):
    """Formats review database fields for JSON response (admin use — includes tracking_code)."""
    if not r:
        return None
    res = r.copy()
    if res.get('created_at'):
        res['created_at'] = res['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    return res
 
 
def serialize_review_public(r):
    """Formats a review for the public testimonials feed — omits tracking_code
    so the homepage can't be used to look up other customers' bookings."""
    res = serialize_review(r)
    if res:
        res.pop('tracking_code', None)
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
        # Notify the customer on their booking phone number, and notify the
        # business owner on WhatsApp. Neither ever blocks or fails the
        # booking itself — see notifications.py.
        notifications.send_booking_confirmation_sms(phone, name, code)
        notifications.send_owner_whatsapp_notification({
            'tracking_code': code,
            'customer_name': name,
            'phone': phone,
            'ac_type': ac_type,
            'issue_description': issue,
            'preferred_date': pref_date,
            'preferred_time': pref_time,
        })
        return jsonify({'success': True, 'tracking_code': code})
    except Exception as e:
        app.logger.exception("Error adding booking")
        return jsonify({'success': False, 'error': 'Something went wrong while saving your booking.'}), 500
 
 
@app.route('/api/track/<tracking_code>', methods=['GET'])
def track_repair(tracking_code):
    try:
        code = tracking_code.strip().upper()
        booking = db.get_booking(code)
        if booking:
            result = serialize_booking(booking)
            # Let the frontend know whether to show the review form —
            # avoids needing a separate public lookup that could leak
            # other customers' tracking codes.
            result['already_reviewed'] = db.get_review_by_tracking_code(code) is not None
            return jsonify({'success': True, 'booking': result})
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
 
 
 
# ---------------------------------------------------------------------------
# Customer reviews — public submit (only for a Completed booking, one per
# tracking_code) + public read (for homepage testimonials) + admin moderation.
# ---------------------------------------------------------------------------
 
@app.route('/api/review', methods=['POST'])
def submit_review():
    data = request.json or {}
    tracking_code = (data.get('tracking_code') or '').strip().upper()
    rating = data.get('rating')
    review_text = data.get('review_text', '')
 
    if not tracking_code or rating is None:
        return jsonify({'success': False, 'error': 'Tracking code and rating are required.'}), 400
 
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Rating must be a number between 1 and 5.'}), 400
 
    if rating < 1 or rating > 5:
        return jsonify({'success': False, 'error': 'Rating must be between 1 and 5.'}), 400
 
    try:
        booking = db.get_booking(tracking_code)
        if not booking:
            return jsonify({'success': False, 'error': 'No booking found with this tracking code.'}), 404
        if booking['status'] != 'Completed':
            return jsonify({'success': False, 'error': 'You can only review a completed service.'}), 400
        if db.get_review_by_tracking_code(tracking_code):
            return jsonify({'success': False, 'error': 'This booking has already been reviewed.'}), 400
 
        db.add_review(tracking_code, booking['customer_name'], rating, review_text)
        return jsonify({'success': True, 'message': 'Thank you for your feedback!'})
    except Exception as e:
        app.logger.exception("Error submitting review")
        return jsonify({'success': False, 'error': 'Something went wrong while submitting your review.'}), 500
 
 
@app.route('/api/reviews', methods=['GET'])
def public_reviews():
    """Public testimonials feed for the homepage — no auth required."""
    try:
        reviews = db.get_all_reviews()
        serialized = [serialize_review_public(r) for r in reviews]
        avg_rating = round(sum(r['rating'] for r in reviews) / len(reviews), 1) if reviews else None
        return jsonify({'success': True, 'reviews': serialized, 'average_rating': avg_rating, 'count': len(reviews)})
    except Exception as e:
        app.logger.exception("Error fetching public reviews")
        return jsonify({'success': False, 'error': 'Something went wrong while fetching reviews.'}), 500
 
 
@app.route('/api/admin/reviews', methods=['GET'])
@admin_api_required
def admin_reviews():
    try:
        reviews = db.get_all_reviews()
        serialized = [serialize_review(r) for r in reviews]
        return jsonify({'success': True, 'reviews': serialized})
    except Exception as e:
        app.logger.exception("Error fetching reviews")
        return jsonify({'success': False, 'error': 'Something went wrong while fetching reviews.'}), 500
 
 
@app.route('/api/admin/reviews/<int:review_id>', methods=['DELETE'])
@admin_api_required
def admin_delete_review(review_id):
    try:
        success = db.delete_review(review_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Review not found.'}), 404
    except Exception as e:
        app.logger.exception("Error deleting review")
        return jsonify({'success': False, 'error': 'Something went wrong while deleting the review.'}), 500
 
 
# ---------------------------------------------------------------------------
# Service prices (admin-only) — base price per AC type, used for the
# analytics dashboard's revenue estimate.
# ---------------------------------------------------------------------------
 
@app.route('/api/admin/service-prices', methods=['GET'])
@admin_api_required
def admin_service_prices():
    try:
        prices = db.get_all_service_prices()
        return jsonify({'success': True, 'prices': prices})
    except Exception as e:
        app.logger.exception("Error fetching service prices")
        return jsonify({'success': False, 'error': 'Something went wrong while fetching prices.'}), 500
 
 
@app.route('/api/admin/service-prices', methods=['POST'])
@admin_api_required
def admin_update_service_price():
    data = request.json or {}
    ac_type = data.get('ac_type')
    base_price = data.get('base_price')
 
    if not ac_type or base_price in (None, ''):
        return jsonify({'success': False, 'error': 'AC type and price are required.'}), 400
 
    try:
        base_price = float(base_price)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Price must be a number.'}), 400
 
    try:
        db.update_service_price(ac_type, base_price)
        return jsonify({'success': True})
    except Exception as e:
        app.logger.exception("Error updating service price")
        return jsonify({'success': False, 'error': 'Something went wrong while updating the price.'}), 500
 
 
# ---------------------------------------------------------------------------
# Analytics dashboard (admin-only)
# ---------------------------------------------------------------------------
 
@app.route('/api/admin/analytics', methods=['GET'])
@admin_api_required
def admin_analytics():
    try:
        bookings, prices = db.get_analytics_data()
 
        today = date.today()
        this_month_bookings = [
            b for b in bookings
            if b['created_at'].year == today.year and b['created_at'].month == today.month
        ]
 
        status_breakdown = Counter(b['status'] for b in this_month_bookings)
        ac_type_breakdown_month = Counter(b['ac_type'] for b in this_month_bookings)
        revenue_estimate = sum(prices.get(b['ac_type'], 0) for b in this_month_bookings)
 
        # Busy days of week & slots — computed over all bookings so the
        # pattern isn't skewed by a slow start-of-month.
        busy_days = Counter()
        busy_slots = Counter()
        ac_type_breakdown_all = Counter()
        for b in bookings:
            if b.get('preferred_date'):
                day_name = calendar.day_name[b['preferred_date'].weekday()]
                busy_days[day_name] += 1
            if b.get('preferred_time'):
                busy_slots[b['preferred_time']] += 1
            ac_type_breakdown_all[b['ac_type']] += 1
 
        # Last 6 months trend (booking count + revenue estimate per month)
        monthly_trend = []
        cursor_date = today.replace(day=1)
        month_buckets = []
        for i in range(5, -1, -1):
            # Step back i months from the current month
            year = cursor_date.year
            month = cursor_date.month - i
            while month <= 0:
                month += 12
                year -= 1
            month_buckets.append((year, month))
 
        for year, month in month_buckets:
            month_bookings = [b for b in bookings if b['created_at'].year == year and b['created_at'].month == month]
            month_revenue = sum(prices.get(b['ac_type'], 0) for b in month_bookings)
            monthly_trend.append({
                'label': f"{calendar.month_abbr[month]} {year}",
                'bookings': len(month_bookings),
                'revenue': round(month_revenue, 2),
            })
 
        ordered_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
 
        return jsonify({
            'success': True,
            'this_month': {
                'total_bookings': len(this_month_bookings),
                'revenue_estimate': round(revenue_estimate, 2),
                'status_breakdown': dict(status_breakdown),
                'ac_type_breakdown': dict(ac_type_breakdown_month),
            },
            'busy_days': {day: busy_days.get(day, 0) for day in ordered_days},
            'busy_slots': dict(busy_slots),
            'ac_type_breakdown_all_time': dict(ac_type_breakdown_all),
            'monthly_trend': monthly_trend,
            'total_bookings_all_time': len(bookings),
        })
    except Exception as e:
        app.logger.exception("Error computing analytics")
        return jsonify({'success': False, 'error': 'Something went wrong while computing analytics.'}), 500
 
 
if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
 
