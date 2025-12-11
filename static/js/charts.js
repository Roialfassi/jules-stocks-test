// Chart.js Helper Functions

let priceChartInstance = null;
let portfolioChartInstance = null;

async function renderPriceChart(canvasId, symbol) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    // Fetch history
    try {
        const response = await fetch(`/api/assets/${symbol}/history`);
        const data = await response.json();

        // Data format from yfinance history usually includes timestamps and close prices
        // Assuming API returns { dates: [], prices: [] } or similar list of objects
        // If the service just returns list of dicts: [{'date': '...', 'close': ...}, ...]

        const labels = data.map(item => {
            const d = new Date(item.date);
            return d.toLocaleDateString();
        });
        const prices = data.map(item => item.close);

        if (priceChartInstance) {
            priceChartInstance.destroy();
        }

        priceChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: `${symbol} Price`,
                    data: prices,
                    borderColor: '#3498db',
                    tension: 0.1,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        beginAtZero: false
                    }
                }
            }
        });

    } catch (e) {
        console.error("Error loading chart:", e);
    }
}

async function renderPortfolioChart(canvasId) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    try {
        const response = await fetch('/api/portfolio/history');
        const data = await response.json();

        // Expecting data to be list of { date: '...', value: ... }
        // If mocked/empty, handle gracefully

        if (!data || data.length === 0) {
            console.log("No portfolio history");
            return;
        }

        const labels = data.map(item => item.date);
        const values = data.map(item => item.value);

        if (portfolioChartInstance) {
            portfolioChartInstance.destroy();
        }

        portfolioChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Portfolio Value',
                    data: values,
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true
            }
        });
    } catch (e) {
        console.error("Error loading portfolio chart:", e);
    }
}
