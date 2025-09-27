document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('/admin')) return;

    // --- DOM Elements ---
    const totalUsersEl = document.getElementById('admin-total-users');
    const totalTradesEl = document.getElementById('admin-total-trades');
    const groupUsersEls = {
        1: document.getElementById('admin-group1-users'),
        2: document.getElementById('admin-group2-users'),
        3: document.getElementById('admin-group3-users'),
        4: document.getElementById('admin-group4-users'),
    };
    const userSearchInput = document.getElementById('user-search-input');
    const userListTableBody = document.getElementById('user-list-table-body');
    const exportButtons = document.querySelectorAll('.data-export-card .btn');

    // --- State ---
    let allUsers = [];

    /**
     * Main function to load all admin dashboard data.
     */
    async function loadAdminDashboard() {
        try {
            const [analytics, users] = await Promise.all([
                apiRequest('/api/research/analytics'),
                apiRequest('/api/research/users')
            ]);

            allUsers = users || [];

            renderAnalytics(analytics);
            renderUserList(allUsers);

        } catch (error) {
            console.error("Failed to load admin dashboard:", error);
            showToast("Could not load admin data.", 'error');
        }
    }

    /**
     * Renders the top analytics cards.
     * @param {object} analytics - The analytics data from the API.
     */
    function renderAnalytics(analytics) {
        if (!analytics) return;
        totalUsersEl.textContent = analytics.totalUsers;
        totalTradesEl.textContent = analytics.totalTrades;
        if (analytics.usersByGroup) {
            for (const group in groupUsersEls) {
                if (groupUsersEls[group]) {
                    groupUsersEls[group].textContent = analytics.usersByGroup[group] || 0;
                }
            }
        }
    }

    /**
     * Renders the list of users in the main table.
     * @param {Array<object>} users - The list of users to render.
     */
    function renderUserList(users) {
        userListTableBody.innerHTML = '';
        if (users && users.length > 0) {
            users.forEach(user => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${user.participantId}</td>
                    <td>${user.username}</td>
                    <td>${user.email}</td>
                    <td>Group ${user.researchGroup}</td>
                    <td>${new Date(user.createdAt).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-secondary btn-sm">View Details</button>
                    </td>
                `;
                userListTableBody.appendChild(row);
            });
        } else {
            userListTableBody.innerHTML = '<tr><td colspan="6">No users found.</td></tr>';
        }
    }

    /**
     * Handles the user search input to filter the rendered user list.
     */
    const handleUserSearch = debounce(() => {
        const query = userSearchInput.value.toLowerCase().trim();
        if (query === '') {
            renderUserList(allUsers);
            return;
        }

        const filteredUsers = allUsers.filter(user =>
            user.email.toLowerCase().includes(query) ||
            user.participantId.toLowerCase().includes(query) ||
            user.username.toLowerCase().includes(query)
        );
        renderUserList(filteredUsers);
    }, 300);

    /**
     * Handles the click event for data export buttons.
     * @param {Event} e - The click event.
     */
    async function handleExport(e) {
        const button = e.target;
        const collectionName = button.dataset.collection;
        if (!collectionName) return;

        showToast(`Exporting ${collectionName}...`, 'info');
        button.disabled = true;

        try {
            const csvData = await apiRequest(`/api/research/export?collection=${collectionName}`);
            if (csvData && csvData.csv) {
                // Create a blob and trigger download
                const blob = new Blob([csvData.csv], { type: 'text/csv;charset=utf-8;' });
                const link = document.createElement('a');
                const url = URL.createObjectURL(blob);
                link.setAttribute('href', url);
                link.setAttribute('download', `${collectionName}_export_${new Date().toISOString().split('T')[0]}.csv`);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                showToast(`${collectionName} exported successfully.`, 'success');
            } else {
                throw new Error("No CSV data received from server.");
            }
        } catch (error) {
            console.error(`Failed to export ${collectionName}:`, error);
            showToast(`Could not export ${collectionName}.`, 'error');
        } finally {
            button.disabled = false;
        }
    }

    // --- Event Listeners ---
    userSearchInput.addEventListener('keyup', handleUserSearch);
    exportButtons.forEach(button => button.addEventListener('click', handleExport));

    // --- Initial Load ---
    loadAdminDashboard();
});