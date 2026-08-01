import db
import sys

print("=== Oscar Air Care Database Verification ===")
try:
    print("Step 1: Initializing database and tables...")
    success = db.init_db()
    if not success:
        print("Database initialization failed.")
        sys.exit(1)
        
    print("Step 2: Adding a test booking...")
    tracking_code = db.add_booking(
        name="Test Customer",
        phone="9999999999",
        email="test@example.com",
        ac_type="Split AC",
        issue="Test issue description",
        pref_date="2026-08-01",
        pref_time="Morning (9 AM - 12 PM)"
    )
    print(f"Test booking added. Tracking code generated: {tracking_code}")
    
    print("Step 3: Retrieving booking details...")
    booking = db.get_booking(tracking_code)
    if not booking:
        print("Failed to retrieve booking.")
        sys.exit(1)
    print(f"Successfully retrieved booking details: Customer={booking['customer_name']}, Status={booking['status']}")
    
    print("Step 4: Updating booking status to 'Processing'...")
    updated = db.update_status(tracking_code, "Processing")
    if not updated:
        print("Failed to update status.")
        sys.exit(1)
        
    booking_updated = db.get_booking(tracking_code)
    print(f"Status updated in DB. Current status: {booking_updated['status']}")
    
    print("Step 5: Cleaning up test booking...")
    deleted = db.delete_booking(tracking_code)
    if not deleted:
        print("Failed to delete test booking.")
        sys.exit(1)
    print("Test booking deleted successfully.")
    
    print("=== Verification Successful! Database is ready! ===")
    
except Exception as e:
    print(f"Verification Failed with error: {e}")
    sys.exit(1)
