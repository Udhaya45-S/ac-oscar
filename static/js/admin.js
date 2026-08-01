document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Navigation Menu Toggle
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');

    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
            const icon = navToggle.querySelector('i');
            if (navMenu.classList.contains('active')) {
                icon.className = 'fa-solid fa-xmark';
            } else {
                icon.className = 'fa-solid fa-bars';
            }
        });

        // Close menu when clicking nav links
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('active');
                navToggle.querySelector('i').className = 'fa-solid fa-bars';
            });
        });
    }

    // 2. Set min date for date input (today)
    const dateInput = document.getElementById('preferredDate');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.min = today;
        dateInput.value = today; // default to today
    }

    // 3. Customer Booking Form Submission
    const bookingForm = document.getElementById('bookingForm');
    const btnSubmit = document.getElementById('btnSubmitBooking');
    const btnText = document.getElementById('btnText');
    const btnSpinner = document.getElementById('btnSpinner');

    // Success Modal Elements
    const successModal = document.getElementById('successModal');
    const modalCustName = document.getElementById('modalCustName');
    const modalTrackingCode = document.getElementById('modalTrackingCode');
    const btnCloseModal = document.getElementById('btnCloseModal');
    const btnCopyCode = document.getElementById('btnCopyCode');

    if (bookingForm) {
        bookingForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Set loading state
            btnSubmit.disabled = true;
            btnText.textContent = "Booking Room...";
            btnSpinner.classList.remove('hide');

            const payload = {
                name: document.getElementById('customerName').value.trim(),
                phone: document.getElementById('customerPhone').value.trim(),
                email: document.getElementById('customerEmail').value.trim(),
                ac_type: document.getElementById('acType').value,
                issue: document.getElementById('issueDescription').value.trim(),
                pref_date: document.getElementById('preferredDate').value,
                pref_time: document.getElementById('preferredTime').value
            };

            try {
                const response = await fetch('/api/book', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Populate success modal
                    modalCustName.textContent = payload.name;
                    modalTrackingCode.textContent = result.tracking_code;
                    
                    // Show modal
                    successModal.classList.remove('hide');
                    
                    // Reset form
                    bookingForm.reset();
                    if (dateInput) {
                        const today = new Date().toISOString().split('T')[0];
                        dateInput.value = today;
                    }
                } else {
                    throw new Error(result.error || 'Server error occurred');
                }
            } catch (err) {
                alert(`Booking Failed: ${err.message}`);
            } finally {
                // Restore button state
                btnSubmit.disabled = false;
                btnText.textContent = "Confirm Booking";
                btnSpinner.classList.add('hide');
            }
        });
    }

    // Modal Operations
    if (btnCloseModal && successModal) {
        btnCloseModal.addEventListener('click', () => {
            successModal.classList.add('hide');
        });
    }

    if (btnCopyCode && modalTrackingCode) {
        btnCopyCode.addEventListener('click', () => {
            const codeText = modalTrackingCode.textContent;
            navigator.clipboard.writeText(codeText).then(() => {
                const icon = btnCopyCode.querySelector('i');
                icon.className = 'fa-solid fa-check';
                icon.style.color = '#00f5d4';
                setTimeout(() => {
                    icon.className = 'fa-solid fa-copy';
                    icon.style.color = '';
                }, 2000);
            }).catch(err => {
                console.error('Could not copy text: ', err);
            });
        });
    }

    // 4. Status Tracking Engine
    const trackingForm = document.getElementById('trackingForm');
    const trackingCodeInput = document.getElementById('trackingCodeInput');
    const trackingResult = document.getElementById('trackingResult');
    const trackingError = document.getElementById('trackingError');
    const trackingErrorText = document.getElementById('trackingErrorText');

    // Dynamic result placeholders
    const resTrackingCode = document.getElementById('resTrackingCode');
    const resStatusBadge = document.getElementById('resStatusBadge');
    const resCustName = document.getElementById('resCustName');
    const resAcType = document.getElementById('resAcType');
    const resDateTime = document.getElementById('resDateTime');
    const resIssue = document.getElementById('resIssue');

    // Stepper elements
    const progressFill = document.getElementById('progressFill');
    const stepBooked = document.getElementById('step-booked');
    const stepProcessing = document.getElementById('step-processing');
    const stepCompleted = document.getElementById('step-completed');

    if (trackingForm) {
        trackingForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const code = trackingCodeInput.value.trim().toUpperCase();
            
            if (!code) return;

            trackingResult.classList.add('hide');
            trackingError.classList.add('hide');

            try {
                const response = await fetch(`/api/track/${code}`);
                const result = await response.json();

                if (result.success) {
                    const booking = result.booking;

                    // Update values
                    resTrackingCode.textContent = booking.tracking_code;
                    resStatusBadge.textContent = booking.status;
                    resStatusBadge.className = `status-badge status-${booking.status.toLowerCase()}`;
                    resCustName.textContent = booking.customer_name;
                    resAcType.textContent = booking.ac_type;
                    resDateTime.textContent = `${booking.preferred_date} | ${booking.preferred_time}`;
                    resIssue.textContent = booking.issue_description;

                    // Reset steps
                    stepBooked.classList.remove('active');
                    stepProcessing.classList.remove('active');
                    stepCompleted.classList.remove('active');

                    // Stepper animation logic
                    if (booking.status === 'Booked') {
                        progressFill.style.width = '0%';
                        stepBooked.classList.add('active');
                    } else if (booking.status === 'Processing') {
                        progressFill.style.width = '50%';
                        stepBooked.classList.add('active');
                        stepProcessing.classList.add('active');
                    } else if (booking.status === 'Completed') {
                        progressFill.style.width = '100%';
                        stepBooked.classList.add('active');
                        stepProcessing.classList.add('active');
                        stepCompleted.classList.add('active');
                    }

                    // Reveal result
                    trackingResult.classList.remove('hide');
                    
                    // Smooth scroll to tracking details
                    trackingResult.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } else {
                    throw new Error(result.error || 'Tracking code not found');
                }
            } catch (err) {
                trackingError.classList.remove('hide');
                trackingErrorText.textContent = err.message;
            }
        });
    }
});
