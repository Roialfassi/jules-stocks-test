async function loadPortfolio() {
    if (typeof renderPortfolioChart === 'function') {
        renderPortfolioChart('portfolioChart');
    }

    const res = await fetch('/api/portfolio');
    const holdings = await res.json();
    const tbody = document.querySelector('#holdings-table tbody');
    if (tbody) {
        tbody.innerHTML = '';

        if(holdings.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No holdings found. Start trading!</td></tr>';
            return;
        }

        holdings.forEach(h => {
            const tr = document.createElement('tr');
            // Basic PnL calculation (using cached currentValue or fetching new price ideally)
            // Here assuming currentValue is somewhat fresh or just displaying as is.
            const ret = ((h.currentValue - h.totalCost) / h.totalCost) * 100;

            tr.innerHTML = `
                <td>${h.symbol}</td>
                <td>${h.quantity.toFixed(4)}</td>
                <td>$${h.averageCost.toFixed(2)}</td>
                <td>$${h.currentValue.toFixed(2)}</td>
                <td class="${ret >= 0 ? 'positive' : 'negative'}">${ret.toFixed(2)}%</td>
            `;
            tbody.appendChild(tr);
        });
    }
}

// Only run if on portfolio page
if (document.getElementById('holdings-table')) {
    loadPortfolio();
}
