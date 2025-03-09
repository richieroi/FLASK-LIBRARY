/**
 * Library Management System - Member Action Handlers
 */

// Initialize member actions when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeMemberActions();
});

// Initialize all member-related functionality
function initializeMemberActions() {
    setupMemberFormValidation();
}

// Set up form validation for member forms
function setupMemberFormValidation() {
    const memberForms = document.querySelectorAll('.member-form');
    memberForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

// Fetch member details from API
async function fetchMember(memberId) {
    try {
        const response = await fetch(`/api/members/${memberId}`);
        if (!response.ok) {
            throw new Error(`Error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching member data:', error);
        showToast('Failed to load member details', 'danger');
        return null;
    }
}

// Fetch member loans from API
async function fetchMemberLoans(memberId) {
    try {
        const response = await fetch(`/api/members/${memberId}/loans`);
        if (!response.ok) {
            throw new Error(`Error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching member loans:', error);
        showToast('Failed to load member loan history', 'danger');
        return [];
    }
}

// Load member data into edit form
function loadMemberData(member, formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    // Set basic fields
    form.querySelector('[name="firstName"]').value = member.FirstName;
    form.querySelector('[name="lastName"]').value = member.LastName;
    form.querySelector('[name="email"]').value = member.Email;
    
    // Set optional fields if they exist
    const phoneInput = form.querySelector('[name="phone"]');
    if (phoneInput && member.Phone) phoneInput.value = member.Phone;
    
    const addressInput = form.querySelector('[name="address"]');
    if (addressInput && member.Address) addressInput.value = member.Address;
    
    // Set status if it exists
    const statusSelect = form.querySelector('[name="status"]');
    if (statusSelect && member.Status) statusSelect.value = member.Status;
    
    // Set expiry date if it exists
    const expiryInput = form.querySelector('[name="expiryDate"]');
    if (expiryInput && member.MembershipExpiry) {
        // Format date as YYYY-MM-DD for input
        const expiry = new Date(member.MembershipExpiry);
        const year = expiry.getFullYear();
        const month = String(expiry.getMonth() + 1).padStart(2, '0');
        const day = String(expiry.getDate()).padStart(2, '0');
        expiryInput.value = `${year}-${month}-${day}`;
    }
}

// Display member loan history in a table
function displayMemberLoans(loans, tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (loans.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="6" class="text-center">No loans found for this member.</td>';
        tbody.appendChild(row);
        return;
    }
    
    loans.forEach(loan => {
        const row = document.createElement('tr');
        
        // Format dates for display
        const loanDate = new Date(loan.LoanDate).toLocaleDateString();
        const dueDate = new Date(loan.DueDate).toLocaleDateString();
        const returnDate = loan.ReturnDate ? new Date(loan.ReturnDate).toLocaleDateString() : '-';
        
        // Determine status badge class
        let statusClass = 'bg-secondary';
        if (loan.Status === 'Borrowed') statusClass = 'bg-warning';
        else if (loan.Status === 'Returned') statusClass = 'bg-success';
        else if (loan.Status === 'Overdue') statusClass = 'bg-danger';
        
        row.innerHTML = `
            <td>${loan.BookTitle}</td>
            <td>${loan.BookAuthor}</td>
            <td>${loanDate}</td>
            <td>${dueDate}</td>
            <td>${returnDate}</td>
            <td><span class="badge ${statusClass}">${loan.Status}</span></td>
            <td>$${loan.FineAmount.toFixed(2)}</td>
        `;
        
        tbody.appendChild(row);
    });
}
