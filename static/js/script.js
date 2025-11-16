// Flash message auto-dismiss
document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
    
    // Star rating functionality
    const starRatingInputs = document.querySelectorAll('.star-rating input[type="radio"]');
    starRatingInputs.forEach(input => {
        input.addEventListener('change', function() {
            console.log('Rating selected:', this.value);
        });
    });
});

// Confirmation dialogs
function confirmAction(message) {
    return confirm(message);
}

// Book search functionality
function searchBooks(query) {
    // This can be extended for AJAX search
    console.log('Searching for:', query);
}
