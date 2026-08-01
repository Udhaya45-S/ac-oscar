New Features: Employee Salary Management + Booking SMS Notifications
1. Files changed / added
File	What changed
`db.py`	Added `employees` table + `add_employee`, `get_all_employees`, `get_employee`, `update_employee`, `delete_employee`
`app.py`	Added `/api/admin/employees` (GET/POST) and `/api/admin/employees/<id>` (PUT/DELETE), all behind admin login. Calls `notifications.send_booking_confirmation_sms()` after a booking is saved, and `send_status_update_sms()` when status changes.
`notifications.py`	New file. Wraps Twilio SMS sending. If Twilio env vars aren't set, it just logs and skips — bookings still work.
`admin.html`	Added a "Bookings / Employees & Salary" tab switcher and an Add/Edit employee modal.
`admin.js`	Added employee fetch/render/add/edit/delete logic and section-tab switching.
`requirements.txt`	Added `twilio==9.3.7`
`.env.example`	Added `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
`style-additions.css`	Two small classes (`.btn-icon`, `.btn-secondary`) used by the new employee table — append to your existing `style.css` if those classes don't already exist there.
Copy all of these into your repo (overwriting the old `db.py`, `app.py`, `admin.html`, `admin.js`, `requirements.txt`, `.env.example`), commit, and push. Render will redeploy automatically.
2. Employee salary data — who can see it
Every employee route requires an active admin session (`admin_api_required` + it's listed in `check_admin_session`'s `allowed_endpoints`). There is no public route that exposes salary data. Only whoever has your `ADMIN_USERNAME` / `ADMIN_PASSCODE` can view or edit it.
3. Setting up SMS (Twilio)
SMS is optional — if you skip this, bookings still work exactly as before, the app just logs `[SMS skipped - Twilio not configured]` instead of sending a text.
To enable it:
Go to twilio.com → sign up (free trial gives some credit).
From the Twilio Console dashboard, copy:
Account SID
Auth Token
Get a Twilio phone number: Console → Phone Numbers → Buy a number (trial accounts get one free number, or use the trial number provided).
On a trial Twilio account, you can only send SMS to phone numbers you've manually verified in the Twilio console (Console → Verified Caller IDs) — this is a Twilio trial restriction, not something in this code. To send to any customer's number without pre-verifying it, you need to upgrade the Twilio account (add billing).
Add these to Render's Environment tab (same place as `DB_HOST` etc.):
`TWILIO_ACCOUNT_SID`
`TWILIO_AUTH_TOKEN`
`TWILIO_FROM_NUMBER` (your Twilio number, in `+1XXXXXXXXXX` format)
Save → Render redeploys.
4. What triggers an SMS
Customer books a repair (`/api/book`) → SMS sent to the phone number they entered, confirming the tracking code.
Admin changes a booking's status (Booked → Processing → Completed) → SMS sent to the customer's phone number about the new status.
Phone numbers are auto-formatted assuming India (`+91` + 10 digits). If a number doesn't look like a valid 10-digit Indian number, the SMS is skipped (logged, not an error) rather than failing the booking.
