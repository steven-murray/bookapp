// Dark mode toggle
document.addEventListener('DOMContentLoaded', function() {
    // Dark mode initialization and toggle
    const darkModeToggle = document.getElementById('darkModeToggle');
    const htmlElement = document.documentElement;
    
    // Check for saved dark mode preference, default to light mode
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    if (isDarkMode) {
        htmlElement.classList.add('dark-mode');
        updateToggleButton();
    }
    
    // Add click handler for toggle button
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            const isCurrentlyDark = htmlElement.classList.contains('dark-mode');
            if (isCurrentlyDark) {
                htmlElement.classList.remove('dark-mode');
                localStorage.setItem('darkMode', 'false');
            } else {
                htmlElement.classList.add('dark-mode');
                localStorage.setItem('darkMode', 'true');
            }
            updateToggleButton();
        });
    }
    
    function updateToggleButton() {
        const isCurrentlyDark = htmlElement.classList.contains('dark-mode');
        if (darkModeToggle) {
            darkModeToggle.textContent = isCurrentlyDark ? '☀️' : '🌙';
            darkModeToggle.title = isCurrentlyDark ? 'Switch to light mode' : 'Switch to dark mode';
        }
    }
    
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
    
    // Enrich book fields from OpenLibrary on admin create form
    const enrichBtn = document.getElementById('btn-enrich-ol');
    if (enrichBtn) {
        enrichBtn.addEventListener('click', async function() {
            const statusEl = document.getElementById('enrich-status');
            const titleInput = document.querySelector('input[name="title"]');
            const authorInput = document.querySelector('input[name="author"]');
            const isbnInput = document.querySelector('input[name="isbn"]');
            if (!titleInput || !authorInput) return;

            const title = (titleInput.value || '').trim();
            const author = (authorInput.value || '').trim();
            const isbn = isbnInput ? (isbnInput.value || '').trim() : '';
            if (!title || !author) {
                statusEl && (statusEl.textContent = 'Enter a title and author first');
                return;
            }
            enrichBtn.disabled = true;
            statusEl && (statusEl.textContent = 'Looking up suggestions…');
            try {
                const resp = await fetch('/admin/book/enrich', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, author, isbn })
                });
                const data = await resp.json();
                if (!data.ok) throw new Error(data.error || 'Lookup failed');

                // Populate fields if values returned
                const setVal = (selector, value) => {
                    const el = document.querySelector(selector);
                    if (el && value != null && value !== '') { el.value = value; }
                };
                setVal('select[name="book_type"]', data.book_type || '');
                setVal('input[name="genre"]', data.genre || '');
                setVal('input[name="sub_genre"]', data.sub_genre || '');
                // Description, topic, grade, lexile are not provided reliably by API; leave as-is
                statusEl && (statusEl.textContent = 'Filled suggestions. Review before saving.');
            } catch (e) {
                console.error(e);
                statusEl && (statusEl.textContent = 'Could not fetch suggestions.');
            } finally {
                enrichBtn.disabled = false;
            }
        });
    }
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
