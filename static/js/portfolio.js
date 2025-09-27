document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('/portfolio')) return;

    // --- DOM Elements ---
    const totalValueEl = document.getElementById('portfolio-total-value');
    const realizedPnlEl = document.getElementById('portfolio-realized-pnl');
    const unrealizedPnlEl = document.getElementById('portfolio-unrealized-pnl');
    const cashBalanceEl = document.getElementById('portfolio-cash-balance');
    const holdingsTableBody = document.getElementById('holdings-table-body');
    const transactionsTableBody = document.getElementById('transactions-table-body');
    const txFilter = document.getElementById('tx-filter');

    // --- State ---
    let allTransactions = [];

    /**
     * Main function to load all portfolio data.
     */
    async function loadPortfolio() {
        try {
            // Fetch all data in parallel
            const [balance, holdings, transactions] = await Promise.all([
                apiRequest('/api/user/balance'),
                apiRequest('/api/portfolio/holdings'),
                apiRequest('/api/transactions')
            ]);

            allTransactions = transactions || [];

            renderMetrics(balance);
            renderHoldings(holdings);
            renderTransactions(); // Initial render with 'all' filter

            // Load performance chart data
            const performanceHistory = await apiRequest('/api/portfolio/value_history');
            if(performanceHistory && performanceHistory.length > 1) {
                hideChartPlaceholder('performance-chart', 'performance-chart-placeholder');
                createPerformanceChart('performance-chart', performanceHistory);
            } else {
                showChartPlaceholder('performance-chart', 'performance-chart-placeholder');
            }

        } catch (error) {
            console.error("Failed to load portfolio data:", error);
            showToast("Could not load your portfolio. Please try again.", 'error');
        }
    }

    /**
     * Renders the key metric cards at the top of the page.
     * @param {object} balance - The user's balance data.
     */
    function renderMetrics(balance) {
        if (!balance) return;
        totalValueEl.textContent = formatCurrency(balance.totalPortfolioValue);
        realizedPnlEl.textContent = formatCurrency(balance.totalRealizedPnL, true);
        unrealizedPnlEl.textContent = formatCurrency(balance.totalUnrealizedPnL, true);
        cashBalanceEl.textContent = formatCurrency(balance.cashBalance);

        updateElementStatus(realizedPnlEl, balance.totalRealizedPnL);
        updateElementStatus(unrealizedPnlEl, balance.totalUnrealizedPnL);
    }

    /**
     * Renders the holdings table.
     * @param {Array<object>} holdings - The user's asset holdings.
     */
    function renderHoldings(holdings) {
        holdingsTableBody.innerHTML = '';
        if (holdings && holdings.length > 0) {
            holdings.forEach(h => {
                const row = document.createElement('tr');
                const pnl = h.unrealizedPnL || 0;
                row.innerHTML = `
                    <td>
                        <div class="asset-name">${h.symbol}</div>
                        <div class="subtle-text">${h.name}</div>
                    </td>
                    <td>${h.quantity.toFixed(6)}</td>
                    <td>${formatCurrency(h.averageCost)}</td>
                    <td>${h.currentPrice ? formatCurrency(h.currentPrice) : 'N/A'}</td>
                    <td>${h.currentValue ? formatCurrency(h.currentValue) : 'N/A'}</td>
                    <td data-status="${pnl > 0 ? 'positive' : 'negative'}">
                        ${h.unrealizedPnL ? formatCurrency(h.unrealizedPnL, true) : 'N/A'}
                    </td>
                `;
                holdingsTableBody.appendChild(row);
            });
        } else {
            holdingsTableBody.innerHTML = '<tr><td colspan="6">You do not have any holdings.</td></tr>';
        }
    }

    /**
     * Renders the transaction history table based on the current filter.
     */
    function renderTransactions() {
        transactionsTableBody.innerHTML = '';
        const filterValue = txFilter.value;
        const filteredTxs = allTransactions.filter(tx => filterValue === 'all' || tx.type === filterValue);

        if (filteredTxs.length > 0) {
            filteredTxs.forEach(tx => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${new Date(tx.timestamp).toLocaleString()}</td>
                    <td>${tx.symbol}</td>
                    <td data-status="${tx.type === 'BUY' ? 'positive' : 'negative'}">${tx.type}</td>
                    <td>${tx.quantity.toFixed(6)}</td>
                    <td>${formatCurrency(tx.price)}</td>
                    <td>${formatCurrency(tx.totalAmount)}</td>
                `;
                transactionsTableBody.appendChild(row);
            });
        } else {
            transactionsTableBody.innerHTML = '<tr><td colspan="6">No transactions found for this filter.</td></tr>';
        }
    }

    // --- Event Listeners ---
    txFilter.addEventListener('change', renderTransactions);

    // --- Initial Load ---
    loadPortfolio();
});