New Features: Analytics Dashboard + Reviews/Ratings + WhatsApp Button
Files changed
File	What changed
db.py	Added service_prices table (pre-filled with default prices), reviews table, and matching CRUD + get_analytics_data()
app.py	Added /api/admin/analytics, /api/admin/service-prices (GET/POST), /api/review (public submit), /api/reviews (public feed), /api/admin/reviews (GET/DELETE)
admin.html	Added "Analytics" and "Reviews" tabs, Chart.js CDN script
admin.js	Charts (bookings/revenue trend, busy days, busy slots, AC type breakdown), price editor, review moderation table
base.html	WhatsApp floating click-to-chat button (bottom-right, every page)
index.html	Star-rating review form (shown after tracking a Completed booking) + a public Testimonials section on the homepage
main.js	Review submission logic, star rating interaction, testimonials fetch
style-additions.css	New CSS for charts, WhatsApp button, review stars, testimonials — append to your style.css, don't replace it

requirements.txt — unchanged, no new Python packages needed (charts run client-side via CDN).

1. Analytics Dashboard
This month: total bookings, estimated revenue, busiest day, busiest time slot.
Charts: last 6 months bookings + revenue trend, busy days of week, busy time slots, AC type breakdown.
Service prices: editable table under the Analytics tab — each AC type's base price used for the revenue estimate. Defaults:
AC Type	Default Price
Split AC	₹599
Window AC	₹499
Inverter AC	₹699
Cassette AC	₹899
Central AC	₹1499

Edit these anytime in Admin → Analytics → Service Base Prices. This is an estimate only (base price × bookings) — it doesn't know about parts cost, discounts, etc.

2. Customer Reviews & Ratings
When a customer tracks a booking that's Completed, a star-rating form appears asking them to rate the service.
One review per booking — enforced both by the database (UNIQUE on tracking_code) and the UI (shows "already reviewed" instead of the form).
Reviews show up in a Testimonials section on the homepage automatically (only rating + comment + customer name — the tracking code itself is never exposed publicly, so nobody can use a review to look up someone else's booking/phone number).
Admin can view and delete reviews from Admin → Reviews.
3. WhatsApp Click-to-Chat
A green floating button (bottom-right corner) on every page.
Currently points to 919150821143 (your listed support number) with a pre-filled message: "Hi, I want to book an AC repair service".
If this isn't your WhatsApp Business number, open base.html, find:
html
  <a href="https://wa.me/919150821143?text=..."

and change 919150821143 to the correct number (with country code, no + or spaces).

No Twilio, no API key, no cost — this is just a link.
Deploying
Copy all these files into your repo at the same paths as before (root files at root, templates/ files into templates/, static/js/ files into static/js/).
Append the CSS from style-additions.css to your existing static/css/style.css.
Commit → push → Render redeploys automatically.
New tables (service_prices, reviews) are created automatically on startup — no manual SQL needed (same db.init_db() mechanism as before).
Testing checklist
 Book a test AC repair → mark it Completed in Admin → Bookings
 Track that booking on the homepage → star rating form should appear → submit a review
 Scroll to the homepage Testimonials section → your review should appear
 Admin → Analytics → check numbers reflect your test booking, edit a price
 Admin → Reviews → see and optionally delete your test review
 Click the green WhatsApp button (bottom-right) → should open WhatsApp with a pre-filled message
