document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('/profile')) return;

    // --- DOM Elements ---
    const usernameEl = document.getElementById('profile-username');
    const emailEl = document.getElementById('profile-email');
    const participantIdEl = document.getElementById('profile-participant-id');
    const researchGroupEl = document.getElementById('profile-research-group');
    const createdAtEl = document.getElementById('profile-created-at');

    const totalTradesEl = document.getElementById('stats-total-trades');
    const winningTradesEl = document.getElementById('stats-winning-trades');
    const losingTradesEl = document.getElementById('stats-losing-trades');
    const winRateEl = document.getElementById('stats-win-rate');
    const totalPnlEl = document.getElementById('stats-total-pnl');

    const resetPasswordBtn = document.getElementById('reset-password-btn');
    const deleteAccountBtn = document.getElementById('delete-account-btn');

    /**
     * Main function to load all profile data.
     */
    async function loadProfile() {
        try {
            // Fetch all data in parallel
            const [profile, balance] = await Promise.all([
                apiRequest('/api/user/profile'),
                apiRequest('/api/user/balance')
            ]);

            renderUserInfo(profile);
            renderTradingStats(balance);

            // Trigger update for gamification elements (XP, achievements)
            // This function is defined in gamification.js
            updateGamificationElements();

        } catch (error) {
            console.error("Failed to load profile data:", error);
            showToast("Could not load your profile data.", 'error');
        }
    }

    /**
     * Renders the main user information card.
     * @param {object} profile - The user's profile data.
     */
    function renderUserInfo(profile) {
        if (!profile) return;
        usernameEl.textContent = profile.username;
        emailEl.textContent = profile.email;
        participantIdEl.textContent = profile.participantId;
        researchGroupEl.textContent = getResearchGroupName(profile.researchGroup);
        createdAtEl.textContent = new Date(profile.createdAt).toLocaleDateString();
    }

    /**
     * Renders the trading statistics card.
     * @param {object} balance - The user's balance data.
     */
    function renderTradingStats(balance) {
        if (!balance) return;
        totalTradesEl.textContent = balance.totalTrades;
        winningTradesEl.textContent = balance.winningTrades;
        losingTradesEl.textContent = balance.losingTrades;
        totalPnlEl.textContent = formatCurrency(balance.totalRealizedPnL, true);
        updateElementStatus(totalPnlEl, balance.totalRealizedPnL);

        if (balance.totalTrades > 0) {
            const winRate = (balance.winningTrades / balance.totalTrades) * 100;
            winRateEl.textContent = `${winRate.toFixed(1)}%`;
        } else {
            winRateEl.textContent = 'N/A';
        }
    }

    function getResearchGroupName(groupNumber) {
        switch(groupNumber) {
            case 1: return '1 (Control)';
            case 2: return '2 (Badges)';
            case 3: return '3 (XP & Progress)';
            case 4: return '4 (Social & Leaderboard)';
            default: return 'Unknown';
        }
    }

    // --- Event Listeners for Account Management ---
    resetPasswordBtn.addEventListener('click', () => {
        const email = emailEl.textContent;
        if (email && confirm(`Send a password reset link to ${email}?`)) {
            firebase.auth().sendPasswordResetEmail(email)
                .then(() => {
                    showToast('Password reset email sent!', 'success');
                })
                .catch((error) => {
                    showToast(error.message, 'error');
                });
        }
    });

    deleteAccountBtn.addEventListener('click', async () => {
        if (confirm('Are you absolutely sure you want to delete your account? This action is permanent and cannot be undone.')) {
            try {
                const response = await apiRequest('/api/user/delete', { method: 'DELETE' });
                showToast(response.message, 'success');
                // Log the user out, which will trigger a redirect to the login page
                await firebase.auth().signOut();
                window.location.href = '/login';
            } catch (error) {
                showToast('Failed to delete account. Please try again.', 'error');
            }
        }
    });


    // --- Initial Load ---
    loadProfile();
});