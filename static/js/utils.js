/**
 * A wrapper for the fetch API to simplify making authenticated requests.
 * It automatically adds the CSRF token and the Firebase Auth token.
 *
 * @param {string} url - The URL to fetch.
 * @param {object} options - The options for the fetch request (e.g., method, body).
 * @returns {Promise<any>} - A promise that resolves with the JSON response.
 */
async function apiRequest(url, options = {}) {
    // Get the Firebase Auth token
    const user = firebase.auth().currentUser;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (user) {
        try {
            const token = await user.getIdToken(true); // Force refresh token
            headers['Authorization'] = `Bearer ${token}`;
        } catch (error) {
            console.error("Error getting auth token:", error);
            // If token fails, maybe redirect to login
            window.location.href = '/login';
            return;
        }
    }

    // Add CSRF token for POST/PUT/DELETE requests
    const method = options.method || 'GET';
    if (['POST', 'PUT', 'DELETE'].includes(method.toUpperCase())) {
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
    }

    try {
        const response = await fetch(url, { ...options, headers });
        if (!response.ok) {
            // Try to parse error message from server
            const errorData = await response.json().catch(() => ({ message: response.statusText }));
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        return response.json();
    } catch (error) {
        console.error(`API request to ${url} failed:`, error);
        showToast(error.message, 'error');
        throw error;
    }
}

/**
 * Displays a toast notification.
 *
 * @param {string} message - The message to display.
 * @param {string} type - The type of toast ('success', 'error', 'info').
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // The toast will remove itself after the animation finishes
    toast.addEventListener('animationend', (e) => {
        if (e.animationName === 'fadeOut') {
            toast.remove();
        }
    });
}

/**
 * Formats a number as a currency string.
 * @param {number} value - The number to format.
 * @returns {string} - The formatted currency string.
 */
function formatCurrency(value, showSign = false) {
    if (typeof value !== 'number') return '$0.00';
    const options = { style: 'currency', currency: 'USD' };
    if (showSign) {
        options.signDisplay = 'always';
    }
    return new Intl.NumberFormat('en-US', options).format(value);
}

/**
 * Updates the color of an element based on its numeric value (positive/negative).
 * @param {HTMLElement} element - The element to update.
 * @param {number} value - The numeric value.
 */
function updateElementStatus(element, value) {
    if (!element) return;
    element.dataset.status = value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral';
}

/**
 * Debounces a function to limit the rate at which it gets called.
 * @param {Function} func - The function to debounce.
 * @param {number} delay - The debounce delay in milliseconds.
 * @returns {Function} - The debounced function.
 */
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}