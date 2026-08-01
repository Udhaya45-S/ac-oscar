document.addEventListener('DOMContentLoaded', () => {
    // Check sessionStorage to ensure admin session is active for this tab/window.
    if (!sessionStorage.getItem('admin_session_active')) {
        window.location.href = '/api/admin/logout';
        return;
    }
 
    let allBookings = [];
    let currentFilter = 'all';
    let allEmployees = [];
 
    // DOM Elements - Bookings
    const bookingsTableBody = document.getElementById('bookingsTableBody');
    const dbSearchInput = document.getElementById('dbSearchInput');
    const filterTabs = document.querySelectorAll('#bookingsSection .filter-tab');
    const adminToast = document.getElementById('adminToast');
    const toastMessage = document.getElementById('toastMessage');
    const logoutBtn = document.getElementById('adminLogoutBtn');
 
    // Stat Count Elements
    const statTotal = document.getElementById('statTotal');
    const statBooked = document.getElementById('statBooked');
    const statProcessing = document.getElementById('statProcessing');
    const statCompleted = document.getElementById('statCompleted');
 
    // DOM Elements - Section switching
    const sectionTabs = document.querySelectorAll('[data-section]');
    const bookingsSection = document.getElementById('bookingsSection');
    const employeesSection = document.getElementById('employeesSection');
 
    // DOM Elements - Employees
    const employeesTableBody = document.getElementById('employeesTableBody');
    const btnAddEmployee = document.getElementById('btnAddEmployee');
    const employeeModal = document.getElementById('employeeModal');
    const employeeModalTitle = document.getElementById('employeeModalTitle');
    const employeeForm = document.getElementById('employeeForm');
    const btnCloseEmployeeModal = document.getElementById('btnCloseEmployeeModal');
    const employeeError = document.getElementById('employeeError');
    const employeeErrorText = document.getElementById('employeeErrorText');
    const empId = document.getElementById('empId');
    const empName = document.getElementById('empName');
    const empRole = document.getElementById('empRole');
    const empPhone = document.getElementById('empPhone');
    const empSalary = document.getElementById('empSalary');
 
    // Initialize Dashboard
    const initDashboard = async () => {
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                sessionStorage.removeItem('admin_session_active');
            });
        }
        await fetchBookings();
        setupSearch();
        setupTabs();
        setupSectionTabs();
        setupEmployeeUI();
    };
 
    // ===================== SECTION SWITCHING =====================
    const setupSectionTabs = () => {
        sectionTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                sectionTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
 
                const section = tab.getAttribute('data-section');
                if (section === 'bookings') {
                    bookingsSection.classList.remove('hide');
                    employeesSection.classList.add('hide');
                } else {
                    bookingsSection.classList.add('hide');
                    employeesSection.classList.remove('hide');
                    fetchEmployees();
                }
            });
        });
    };
 
    // ===================== BOOKINGS =====================
 
    // Fetch Bookings from API
    const fetchBookings = async () => {
        try {
            const response = await fetch('/api/admin/bookings');
            if (response.status === 401) {
                // Not authenticated, reload page to show login
                window.location.reload();
                return;
            }
            const result = await response.json();
            if (result.success) {
                allBookings = result.bookings;
                calculateStats();
                applyFilters();
            } else {
                throw new Error(result.error || 'Failed to fetch bookings');
            }
        } catch (err) {
            bookingsTableBody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; color: var(--color-danger); padding: 30px;">
                        <i class="fa-solid fa-triangle-exclamation"></i> Error: ${err.message}
                    </td>
                </tr>
            `;
        }
    };
 
    // Calculate Statistics Counters
    const calculateStats = () => {
        const counts = {
            Total: allBookings.length,
            Booked: 0,
            Processing: 0,
            Completed: 0
        };
 
        allBookings.forEach(booking => {
            if (counts[booking.status] !== undefined) {
                counts[booking.status]++;
            }
        });
 
        // Set Text
        statTotal.textContent = counts.Total;
        statBooked.textContent = counts.Booked;
        statProcessing.textContent = counts.Processing;
        statCompleted.textContent = counts.Completed;
    };
 
    // Filter and Search bookings logic
    const applyFilters = () => {
        const searchQuery = dbSearchInput.value.toLowerCase().trim();
        
        const filtered = allBookings.filter(booking => {
            // Tab filter matching
            const matchesTab = currentFilter === 'all' || booking.status === currentFilter;
            
            // Search query matching (Code, Name, Phone)
            const matchesSearch = 
                booking.tracking_code.toLowerCase().includes(searchQuery) ||
                booking.customer_name.toLowerCase().includes(searchQuery) ||
                booking.phone.includes(searchQuery);
 
            return matchesTab && matchesSearch;
        });
 
        renderTable(filtered);
    };
 
    // Render bookings rows
    const renderTable = (bookings) => {
        if (bookings.length === 0) {
            bookingsTableBody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 40px;">
                        <i class="fa-solid fa-folder-open" style="font-size: 24px; margin-bottom: 8px; display: block;"></i>
                        No booking records found.
                    </td>
                </tr>
            `;
            return;
        }
 
        bookingsTableBody.innerHTML = bookings.map(b => {
            // Check status select bindings
            const isBooked = b.status === 'Booked' ? 'selected' : '';
            const isProcessing = b.status === 'Processing' ? 'selected' : '';
            const isCompleted = b.status === 'Completed' ? 'selected' : '';
 
            // Format date nicely
            let formattedDate = b.created_at;
            try {
                const dateObj = new Date(b.created_at);
                formattedDate = dateObj.toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch(e) {}
 
            return `
                <tr id="row-${b.tracking_code}">
                    <td style="color: var(--text-secondary); font-size: 13px;">${formattedDate}</td>
                    <td class="col-code">${b.tracking_code}</td>
                    <td class="col-cust">${b.customer_name}</td>
                    <td><a href="tel:${b.phone}" style="color: var(--color-blue); font-weight: 500;"><i class="fa-solid fa-phone" style="font-size: 11px; margin-right: 4px;"></i>${b.phone}</a></td>
                    <td><span class="badge" style="margin: 0; padding: 4px 10px; font-size: 11px;">${b.ac_type}</span></td>
                    <td class="col-issue" title="${b.issue_description}">${b.issue_description}</td>
                    <td><span style="font-size: 13px; font-weight: 500;">${b.preferred_date}</span> <br/> <span style="font-size: 11px; color: var(--text-muted);">${b.preferred_time}</span></td>
                    <td>
                        <select class="status-dropdown" data-code="${b.tracking_code}" data-status="${b.status}">
                            <option value="Booked" ${isBooked}>Booked</option>
                            <option value="Processing" ${isProcessing}>Processing</option>
                            <option value="Completed" ${isCompleted}>Completed</option>
                        </select>
                    </td>
                </tr>
            `;
        }).join('');
 
        // Bind dropdown change handlers
        const dropdowns = bookingsTableBody.querySelectorAll('.status-dropdown');
        dropdowns.forEach(select => {
            // Apply initial coloring status attribute
            const initialStatus = select.getAttribute('data-status');
            select.style.borderColor = `var(--status-${initialStatus.toLowerCase()})`;
            select.style.color = `var(--status-${initialStatus.toLowerCase()})`;
 
            select.addEventListener('change', async (e) => {
                const trackingCode = select.getAttribute('data-code');
                const newStatus = e.target.value;
                
                // Disable temporarily
                select.disabled = true;
 
                try {
                    const response = await fetch('/api/admin/update-status', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tracking_code: trackingCode, status: newStatus })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        // Update local list
                        const bookingIndex = allBookings.findIndex(item => item.tracking_code === trackingCode);
                        if (bookingIndex !== -1) {
                            allBookings[bookingIndex].status = newStatus;
                        }
                        
                        // Recalculate stats counters
                        calculateStats();
                        
                        // Update styling dropdown
                        select.setAttribute('data-status', newStatus);
                        select.style.borderColor = `var(--status-${newStatus.toLowerCase()})`;
                        select.style.color = `var(--status-${newStatus.toLowerCase()})`;
 
                        // If tabs filter is active and status changes, we might want to refresh rows
                        if (currentFilter !== 'all') {
                            applyFilters();
                        }
                        
                        // Show popup Toast
                        showToast(`Booking ${trackingCode} status updated to ${newStatus}`);
                    } else {
                        throw new Error(result.error || 'Failed to update status');
                    }
                } catch(err) {
                    alert(`Error updating status: ${err.message}`);
                    // Revert select back to old state
                    select.value = select.getAttribute('data-status');
                } finally {
                    select.disabled = false;
                }
            });
        });
    };
 
    // Setup tabs listeners
    const setupTabs = () => {
        filterTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                filterTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentFilter = tab.getAttribute('data-filter');
                applyFilters();
            });
        });
    };
 
    // Setup live search listener
    const setupSearch = () => {
        dbSearchInput.addEventListener('input', () => {
            applyFilters();
        });
    };
 
    // Show dynamic toast popup
    const showToast = (message) => {
        toastMessage.textContent = message;
        adminToast.classList.remove('hide');
        
        // Hide after 3 seconds
        setTimeout(() => {
            adminToast.classList.add('hide');
        }, 3000);
    };
 
    // ===================== EMPLOYEES =====================
 
    const fetchEmployees = async () => {
        employeesTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="table-loading">
                    <i class="fa-solid fa-circle-notch fa-spin"></i> Fetching employee records...
                </td>
            </tr>
        `;
        try {
            const response = await fetch('/api/admin/employees');
            if (response.status === 401) {
                window.location.reload();
                return;
            }
            const result = await response.json();
            if (result.success) {
                allEmployees = result.employees;
                renderEmployeesTable();
            } else {
                throw new Error(result.error || 'Failed to fetch employees');
            }
        } catch (err) {
            employeesTableBody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; color: var(--color-danger); padding: 30px;">
                        <i class="fa-solid fa-triangle-exclamation"></i> Error: ${err.message}
                    </td>
                </tr>
            `;
        }
    };
 
    const renderEmployeesTable = () => {
        if (allEmployees.length === 0) {
            employeesTableBody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 40px;">
                        <i class="fa-solid fa-id-badge" style="font-size: 24px; margin-bottom: 8px; display: block;"></i>
                        No employee records yet. Click "Add Employee" to create one.
                    </td>
                </tr>
            `;
            return;
        }
 
        employeesTableBody.innerHTML = allEmployees.map(emp => `
            <tr id="emp-row-${emp.id}">
                <td class="col-cust">${emp.full_name}</td>
                <td><span class="badge" style="margin: 0; padding: 4px 10px; font-size: 11px;">${emp.role}</span></td>
                <td>${emp.phone ? `<a href="tel:${emp.phone}" style="color: var(--color-blue); font-weight: 500;">${emp.phone}</a>` : '-'}</td>
                <td style="font-weight: 600;">₹${Number(emp.monthly_salary).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                <td style="color: var(--text-secondary); font-size: 13px;">${emp.updated_at || emp.created_at}</td>
                <td>
                    <button class="btn-icon btn-edit-emp" data-id="${emp.id}" title="Edit"><i class="fa-solid fa-pen"></i></button>
                    <button class="btn-icon btn-delete-emp" data-id="${emp.id}" title="Delete"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `).join('');
 
        // Bind edit buttons
        employeesTableBody.querySelectorAll('.btn-edit-emp').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.getAttribute('data-id'));
                const emp = allEmployees.find(e => e.id === id);
                if (emp) openEmployeeModal(emp);
            });
        });
 
        // Bind delete buttons
        employeesTableBody.querySelectorAll('.btn-delete-emp').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = parseInt(btn.getAttribute('data-id'));
                const emp = allEmployees.find(e => e.id === id);
                if (!emp) return;
                if (!confirm(`Delete salary record for ${emp.full_name}?`)) return;
 
                try {
                    const response = await fetch(`/api/admin/employees/${id}`, { method: 'DELETE' });
                    const result = await response.json();
                    if (result.success) {
                        allEmployees = allEmployees.filter(e => e.id !== id);
                        renderEmployeesTable();
                        showToast(`Removed ${emp.full_name} from employee records`);
                    } else {
                        throw new Error(result.error || 'Failed to delete employee');
                    }
                } catch (err) {
                    alert(`Error deleting employee: ${err.message}`);
                }
            });
        });
    };
 
    const openEmployeeModal = (emp = null) => {
        employeeError.classList.add('hide');
        employeeForm.reset();
        if (emp) {
            employeeModalTitle.textContent = 'Edit Employee';
            empId.value = emp.id;
            empName.value = emp.full_name;
            empRole.value = emp.role;
            empPhone.value = emp.phone || '';
            empSalary.value = emp.monthly_salary;
        } else {
            employeeModalTitle.textContent = 'Add Employee';
            empId.value = '';
        }
        employeeModal.classList.remove('hide');
    };
 
    const closeEmployeeModal = () => {
        employeeModal.classList.add('hide');
    };
 
    const setupEmployeeUI = () => {
        if (btnAddEmployee) {
            btnAddEmployee.addEventListener('click', () => openEmployeeModal());
        }
        if (btnCloseEmployeeModal) {
            btnCloseEmployeeModal.addEventListener('click', closeEmployeeModal);
        }
 
        if (employeeForm) {
            employeeForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                employeeError.classList.add('hide');
 
                const payload = {
                    full_name: empName.value.trim(),
                    role: empRole.value.trim(),
                    phone: empPhone.value.trim(),
                    monthly_salary: empSalary.value
                };
 
                const isEdit = !!empId.value;
                const url = isEdit ? `/api/admin/employees/${empId.value}` : '/api/admin/employees';
                const method = isEdit ? 'PUT' : 'POST';
 
                try {
                    const response = await fetch(url, {
                        method,
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const result = await response.json();
 
                    if (result.success) {
                        closeEmployeeModal();
                        showToast(isEdit ? 'Employee record updated' : 'Employee added');
                        fetchEmployees();
                    } else {
                        throw new Error(result.error || 'Failed to save employee');
                    }
                } catch (err) {
                    employeeErrorText.textContent = err.message;
                    employeeError.classList.remove('hide');
                }
            });
        }
    };
 
    // Run Dashboard Init
    initDashboard();
});
