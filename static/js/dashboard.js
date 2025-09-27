document.addEventListener('DOMContentLoaded', () => {
    // This script runs on the dashboard page
    if (window.location.pathname !== '/dashboard') return;

    // --- DOM Element Selectors ---
    const usernameDisplay = document.getElementById('username-display');
    const totalPortfolioValueEl = document.getElementById('total-portfolio-value');
    const cashBalanceEl = document.getElementById('cash-balance');
    const totalPnlEl = document.getElementById('total-pnl');
    const investedValueEl = document.getElementById('invested-value');
    const marketWatchlistEl = document.getElementById('market-watchlist');
    const recentTradesTableEl = document.getElementById('recent-trades-table');

    /**
     * Fetches and renders all dashboard data.
     */
    async function loadDashboard() {
        try {
            // Fetch all data in parallel
            const [user, balance, holdings, transactions] = await Promise.all([
                apiRequest('/api/user/profile'),
                apiRequest('/api/user/balance'),
                apiRequest('/api/portfolio/holdings'),
                apiRequest('/api/transactions?limit=5')
            ]);

            // Render each section
            renderHeader(user);
            renderPortfolioSummary(balance);
            renderRecentTrades(transactions);

            // The portfolio chart uses holdings and balance data
            if (holdings && balance) {
                const holdingsWithValue = holdings.filter(h => h.currentValue !== null);
                if (holdingsWithValue.length > 0) {
                    createPortfolioSummaryChart('portfolio-summary-chart', holdingsWithValue, balance.cashBalance);
                }
            }

            // Gamification elements are loaded by gamification.js, but we can trigger updates
            updateGamificationElements();

        } catch (error) {
            console.error("Failed to load dashboard data:", error);
            showToast("Could not load dashboard data. Please try again later.", 'error');
        }

        // Load market data separately as it's less critical
        loadMarketWatchlist();
    }

    /**
     * Renders the header with the user's name.
     * @param {object} user - The user profile object.
     */
    function renderHeader(user) {
        if (user && user.username) {
            usernameDisplay.textContent = user.username;
        }
    }

    /**
     * Renders the portfolio summary metrics.
     * @param {object} balance - The user balance object.
     */
    function renderPortfolioSummary(balance) {
        if (!balance) return;

        const totalPnl = balance.totalRealizedPnL + balance.totalUnrealizedPnL;

        totalPortfolioValueEl.textContent = formatCurrency(balance.totalPortfolioValue);
        cashBalanceEl.textContent = formatCurrency(balance.cashBalance);
        investedValueEl.textContent = formatCurrency(balance.investedValue);
        totalPnlEl.textContent = formatCurrency(totalPnl, true);

        updateElementStatus(totalPnlEl, totalPnl);
    }

    /**
     * Loads and displays a watchlist of popular market assets.
     */
    async function loadMarketWatchlist() {
        try {
            const assets = await apiRequest('/api/market/popular');
            marketWatchlistEl.innerHTML = ''; // Clear loading message

            if (assets && assets.length > 0) {
                assets.forEach(asset => {
                    const li = document.createElement('li');
                    li.innerHTML = `
                        <div>
                            <span class="symbol">${asset.symbol}</span>
                            <span class="name">${asset.name}</span>
                        </div>
                        <div>
                            <span class="price">${formatCurrency(asset.price)}</span>
                            <span class="change" data-status="${asset.change >= 0 ? 'positive' : 'negative'}">
                                ${asset.change.toFixed(2)}%
                            </span>
                        </div>
                    `;
                    marketWatchlistEl.appendChild(li);
                });
            } else {
                marketWatchlistEl.innerHTML = '<li>Market data is currently unavailable.</li>';
            }
        } catch (error) {
            console.error("Failed to load market watchlist:", error);
            marketWatchlistEl.innerHTML = '<li>Could not load market data.</li>';
        }
    }

    /**
     * Renders the list of recent transactions.
     * @param {Array<object>} transactions - A list of transaction objects.
     */
    function renderRecentTrades(transactions) {
        recentTradesTableEl.innerHTML = ''; // Clear loading message
        if (transactions && transactions.length > 0) {
            transactions.forEach(tx => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${new Date(tx.timestamp).toLocaleDateString()}</td>
                    <td>${tx.symbol}</td>
                    <td data-status="${tx.type === 'BUY' ? 'positive' : 'negative'}">${tx.type}</td>
                    <td>${tx.quantity.toFixed(4)}</td>
                    <td>${formatCurrency(tx.price)}</td>
                `;
                recentTradesTableEl.appendChild(row);
            });
        } else {
            recentTradesTableEl.innerHTML = '<tr><td colspan="5">You have no recent trades.</td></tr>';
        }
    }

    // Initial load
    loadDashboard();
});