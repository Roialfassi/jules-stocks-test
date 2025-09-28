document.addEventListener('DOMContentLoaded', function() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Fetch Admin Analytics
    fetch('/api/research/analytics')
        .then(response => response.json())
        .then(data => {
            document.getElementById('total-users').textContent = data.totalUsers;
            document.getElementById('total-trades').textContent = data.totalTrades;
            document.getElementById('group-1-users').textContent = data.usersByGroup['1'] || 0;
            document.getElementById('group-2-users').textContent = data.usersByGroup['2'] || 0;
            document.getElementById('group-3-users').textContent = data.usersByGroup['3'] || 0;
            document.getElementById('group-4-users').textContent = data.usersByGroup['4'] || 0;
        })
        .catch(error => console.error('Error fetching admin analytics:', error));

    // Fetch All Users
    fetch('/api/research/users')
        .then(response => response.json())
        .then(users => {
            const usersTableBody = document.getElementById('users-table');
            usersTableBody.innerHTML = ''; // Clear loading state
            if (users.length === 0) {
                usersTableBody.innerHTML = '<tr><td colspan="7">No users found.</td></tr>';
                return;
            }
            users.forEach(user => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${user.username}</td>
                    <td>${user.email}</td>
                    <td>${user.participantId}</td>
                    <td>${user.researchGroup}</td>
                    <td>${user.role}</td>
                    <td>${new Date(user.createdAt).toLocaleDateString()}</td>
                    <td><button class="button" disabled>Edit</button></td>
                `;
                usersTableBody.appendChild(row);
            });
        })
        .catch(error => console.error('Error fetching users:', error));

    // Handle Data Export
    document.querySelectorAll('.export-buttons .button').forEach(button => {
        button.addEventListener('click', () => {
            const collection = button.dataset.collection;
            const url = `/api/research/export?collection=${collection}`;

            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        const blob = new Blob([data.csv], { type: 'text/csv' });
                        const link = document.createElement('a');
                        link.href = URL.createObjectURL(blob);
                        link.download = `${collection}_export_${new Date().toISOString().split('T')[0]}.csv`;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                    } else {
                        alert(`Error exporting ${collection}: ${data.message}`);
                    }
                })
                .catch(error => {
                    console.error(`Error exporting ${collection}:`, error)
                    alert(`An error occurred while exporting ${collection}.`);
                });
        });
    });
});