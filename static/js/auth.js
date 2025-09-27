document.addEventListener('DOMContentLoaded', () => {
    const auth = firebase.auth();

    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const logoutButton = document.getElementById('logout-button');
    const forgotPasswordLink = document.getElementById('forgot-password-link');

    // --- Firebase Auth State Listener ---
    // Manages user session and redirects
    auth.onAuthStateChanged(async (user) => {
        const currentPath = window.location.pathname;
        const protectedPages = ['/dashboard', '/trading', '/portfolio', '/profile', '/admin'];

        if (user) {
            // User is signed in.
            try {
                const token = await user.getIdToken();
                // Send token to backend to create a session
                await fetch('/api/session-login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token: token })
                });

                // Set research group on HTML tag for CSS rules
                const userProfile = await apiRequest('/api/user/profile');
                if(userProfile && userProfile.researchGroup) {
                    document.documentElement.dataset.group = userProfile.researchGroup;
                }

                if (currentPath === '/login' || currentPath === '/register') {
                    window.location.href = '/dashboard';
                }
            } catch (error) {
                console.error("Error during session login or profile fetch:", error);
                // If session creation fails, log out to be safe
                await auth.signOut();
            }
        } else {
            // User is signed out.
            if (protectedPages.includes(currentPath)) {
                window.location.href = '/login';
            }
        }
    });

    // --- Login Form Handler ---
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = loginForm.email.value;
            const password = loginForm.password.value;
            const errorDiv = document.getElementById('form-error');
            errorDiv.textContent = '';

            try {
                await auth.signInWithEmailAndPassword(email, password);
                // onAuthStateChanged will handle the redirect
            } catch (error) {
                errorDiv.textContent = error.message;
                console.error("Login failed:", error);
            }
        });
    }

    // --- Registration Form Handler ---
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = registerForm.username.value;
            const email = registerForm.email.value;
            const password = registerForm.password.value;
            const confirmPassword = registerForm['confirm-password'].value;
            const consent = registerForm.consent.checked;
            const errorDiv = document.getElementById('form-error');
            errorDiv.textContent = '';

            // Client-side validation
            if (password !== confirmPassword) {
                errorDiv.textContent = 'Passwords do not match.';
                return;
            }
            if (!consent) {
                errorDiv.textContent = 'You must agree to the consent form to register.';
                return;
            }
            if (password.length < 8) {
                 errorDiv.textContent = 'Password must be at least 8 characters long.';
                return;
            }

            try {
                const response = await apiRequest('/api/register', {
                    method: 'POST',
                    body: JSON.stringify({ username, email, password, consent })
                });

                if (response.status === 'success') {
                    // Automatically sign in the new user
                    await auth.signInWithEmailAndPassword(email, password);
                    // onAuthStateChanged will handle the redirect
                } else {
                    errorDiv.textContent = response.message;
                }
            } catch (error) {
                errorDiv.textContent = error.message;
                console.error("Registration failed:", error);
            }
        });
    }

    // --- Logout Button Handler ---
    if (logoutButton) {
        logoutButton.addEventListener('click', async () => {
            try {
                // Sign out from Firebase
                await auth.signOut();
                // Sign out from backend session
                await fetch('/api/logout', { method: 'POST' });
                // onAuthStateChanged will redirect to /login
                window.location.href = '/login';
            } catch (error) {
                console.error("Logout failed:", error);
            }
        });
    }

    // --- Forgot Password Handler ---
    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener('click', (e) => {
            e.preventDefault();
            const email = prompt("Please enter your email address to receive a password reset link:");
            if (email) {
                auth.sendPasswordResetEmail(email)
                    .then(() => {
                        showToast('Password reset email sent. Please check your inbox.', 'success');
                    })
                    .catch((error) => {
                        showToast(error.message, 'error');
                        console.error("Password reset failed:", error);
                    });
            }
        });
    }
});