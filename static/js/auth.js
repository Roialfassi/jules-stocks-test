// Append to auth.js (or just overwrite since we only had login there)

// If auth.js is loaded in both, we need to check if element exists
const loginForm = document.getElementById('login-form');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const errorDiv = document.getElementById('error-msg');

        errorDiv.textContent = '';

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (data.success) {
                window.location.href = '/dashboard';
            } else {
                errorDiv.textContent = data.error || 'Login failed';
            }
        } catch (err) {
            errorDiv.textContent = 'An error occurred. Please try again.';
        }
    });
}

const registerForm = document.getElementById('register-form');
if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const consent = document.getElementById('consent').checked;
        const errorDiv = document.getElementById('error-msg');

        errorDiv.textContent = '';

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ username, email, password, consent })
            });

            const data = await response.json();

            if (data.success) {
                window.location.href = '/dashboard';
            } else {
                errorDiv.textContent = data.error || 'Registration failed';
            }
        } catch (err) {
            errorDiv.textContent = 'An error occurred. Please try again.';
        }
    });
}
