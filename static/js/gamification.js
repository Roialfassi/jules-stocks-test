// This script is loaded on multiple pages to handle gamification elements.

// --- State ---
let userGroup = null;
let userGamificationStats = null;
let allAchievements = null;
let userAchievements = null;

/**
 * Main function to fetch all gamification data and update the UI.
 * This can be called from page-specific scripts (dashboard.js, profile.js).
 */
async function updateGamificationElements() {
    try {
        // Fetch data in parallel
        const [profile, stats, achievements, progress, leaderboard] = await Promise.all([
            apiRequest('/api/user/profile'),
            apiRequest('/api/gamification/stats'),
            apiRequest('/api/achievements'),
            apiRequest('/api/achievements/progress'),
            apiRequest('/api/leaderboard').catch(() => null) // Leaderboard might fail for non-group 4
        ]);

        userGroup = profile?.researchGroup;
        userGamificationStats = stats;
        allAchievements = achievements;
        userAchievements = progress;

        // Set the data-group attribute on the root html element
        if (userGroup) {
            document.documentElement.dataset.group = userGroup;
        }

        // Update various UI components if they exist on the current page
        updateXpCounter();
        updateProfileProgress();
        renderAchievementsGrid();
        updateRecentAchievements();
        if (leaderboard) {
            renderLeaderboard(leaderboard, profile?.username);
        }

    } catch (error) {
        console.error("Failed to update gamification elements:", error);
    }
}

/**
 * Updates the XP counter and progress bar in the main navbar.
 */
function updateXpCounter() {
    const userLevelEl = document.getElementById('user-level');
    const userXpProgressEl = document.getElementById('user-xp-progress');
    const userXpEl = document.getElementById('user-xp');
    const userXpNextEl = document.getElementById('user-xp-next');

    if (userLevelEl && userGamificationStats) {
        userLevelEl.textContent = userGamificationStats.currentLevel;
        userXpEl.textContent = userGamificationStats.totalXP;
        userXpNextEl.textContent = userGamificationStats.xpToNextLevel;
        userXpProgressEl.value = userGamificationStats.totalXP;
        userXpProgressEl.max = userGamificationStats.xpToNextLevel;
    }
}

/**
 * Updates the progress display on the profile page.
 */
function updateProfileProgress() {
    const profileLevelEl = document.getElementById('profile-level');
    const profileXpProgressEl = document.getElementById('profile-xp-progress');
    const profileCurrentXpEl = document.getElementById('profile-current-xp');
    const profileNextLevelXpEl = document.getElementById('profile-next-level-xp');

    if (profileLevelEl && userGamificationStats) {
        profileLevelEl.textContent = userGamificationStats.currentLevel;
        profileCurrentXpEl.textContent = userGamificationStats.totalXP;
        profileNextLevelXpEl.textContent = userGamificationStats.xpToNextLevel;
        profileXpProgressEl.value = userGamificationStats.totalXP;
        profileXpProgressEl.max = userGamificationStats.xpToNextLevel;
    }
}

/**
 * Renders the full grid of all possible achievements on the profile page.
 */
function renderAchievementsGrid() {
    const container = document.getElementById('achievements-container');
    if (!container || !allAchievements) return;

    container.innerHTML = '';
    allAchievements.forEach(ach => {
        const userAch = userAchievements.find(ua => ua.code === ach.code);
        const isUnlocked = userAch && userAch.isCompleted;

        const badge = document.createElement('div');
        badge.className = `achievement-badge ${isUnlocked ? 'unlocked' : 'locked'}`;
        badge.title = `${ach.name} - ${ach.description}`;

        badge.innerHTML = `
            <div class="badge-icon">
                <i class="fa-solid ${isUnlocked ? 'fa-trophy' : 'fa-lock'}"></i>
            </div>
            <div class="badge-name">${ach.name}</div>
        `;
        container.appendChild(badge);
    });
}

/**
 * Renders a small grid of recently unlocked achievements on the dashboard.
 */
function updateRecentAchievements() {
    const container = document.getElementById('recent-achievements-grid');
    if (!container || !userAchievements) return;

    const unlocked = userAchievements
        .filter(ua => ua.isCompleted)
        .sort((a, b) => new Date(b.completedAt) - new Date(a.completedAt))
        .slice(0, 5); // Show latest 5

    container.innerHTML = '';
    if (unlocked.length > 0) {
        unlocked.forEach(ach => {
            const badge = document.createElement('div');
            badge.className = 'achievement-badge unlocked';
            badge.title = ach.name;
            badge.innerHTML = `
                <div class="badge-icon"><i class="fa-solid fa-trophy"></i></div>
                <div class="badge-name">${ach.name}</div>
            `;
            container.appendChild(badge);
        });
    } else {
        container.innerHTML = '<p>No achievements unlocked yet. Start trading!</p>';
    }
}

/**
 * Renders the leaderboard on the dashboard.
 * @param {Array<Object>} leaderboardData - The top users.
 * @param {string} currentUsername - The logged-in user's name to highlight them.
 */
function renderLeaderboard(leaderboardData, currentUsername) {
    const tableBody = document.getElementById('leaderboard-table');
    const rankDisplay = document.getElementById('user-rank-display');
    if (!tableBody) return;

    tableBody.innerHTML = '';
    let userRank = 'N/A';
    if (leaderboardData && leaderboardData.length > 0) {
        leaderboardData.forEach((entry, index) => {
            const rank = index + 1;
            const row = document.createElement('tr');
            if (entry.username === currentUsername) {
                row.classList.add('current-user');
                userRank = `#${rank}`;
            }
            row.innerHTML = `
                <td>#${rank}</td>
                <td>${entry.username}</td>
                <td>${formatCurrency(entry.portfolioValue)}</td>
            `;
            tableBody.appendChild(row);
        });
    } else {
        tableBody.innerHTML = '<tr><td colspan="3">Leaderboard is not yet available.</td></tr>';
    }

    if (rankDisplay) {
        rankDisplay.textContent = `Your Rank: ${userRank}`;
    }
}

// Initial check when the DOM is loaded.
// Page-specific scripts will call `updateGamificationElements` to fetch and render.
document.addEventListener('DOMContentLoaded', () => {
    // Attempt to get user group from session storage or a quick API call if needed.
    // For now, we rely on page-specific scripts to trigger the main update function.
});