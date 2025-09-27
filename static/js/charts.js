// --- Chart.js Integration ---

// Store chart instances to prevent duplicates and allow updates
const chartInstances = {};

/**
 * Default configuration for all charts to ensure a consistent look and feel.
 */
const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: false,
        },
        tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleFont: { size: 14, weight: 'bold' },
            bodyFont: { size: 12 },
            padding: 10,
            cornerRadius: 6,
        },
    },
    scales: {
        x: {
            grid: {
                display: false,
            },
            ticks: {
                color: '#6e6e73',
                font: { size: 10 }
            },
        },
        y: {
            grid: {
                color: '#e5e5ea',
            },
            ticks: {
                color: '#6e6e73',
                font: { size: 10 },
                callback: function(value) {
                    // Format Y-axis ticks as currency
                    return '$' + value.toLocaleString();
                }
            },
        },
    },
};

/**
 * Creates or updates a line chart for asset price history.
 * @param {string} canvasId - The ID of the canvas element.
 * @param {Array<Object>} historyData - The historical data points.
 */
function createPriceHistoryChart(canvasId, historyData) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const labels = historyData.map(d => d.Date);
    const data = historyData.map(d => d.Close);

    const chartData = {
        labels: labels,
        datasets: [{
            label: 'Price',
            data: data,
            borderColor: data[0] <= data[data.length - 1] ? 'var(--success-color)' : 'var(--danger-color)',
            backgroundColor: 'transparent',
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.1,
        }]
    };

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].data = chartData;
        chartInstances[canvasId].update();
    } else {
        chartInstances[canvasId] = new Chart(ctx, {
            type: 'line',
            data: chartData,
            options: defaultChartOptions,
        });
    }
}

/**
 * Creates or updates a doughnut chart for portfolio composition.
 * @param {string} canvasId - The ID of the canvas element.
 * @param {Array<Object>} holdings - The user's portfolio holdings.
 */
function createPortfolioSummaryChart(canvasId, holdings) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const labels = holdings.map(h => h.symbol);
    const data = holdings.map(h => h.currentValue);

    // Add cash to the chart
    const cashBalance = parseFloat(document.getElementById('cash-balance')?.textContent.replace(/[^0-9.-]+/g,"") || 0);
    labels.push('Cash');
    data.push(cashBalance);

    const chartData = {
        labels: labels,
        datasets: [{
            data: data,
            backgroundColor: [
                '#0a84ff', '#34c759', '#ff9500', '#ff3b30', '#af52de',
                '#5ac8fa', '#ffcc00', '#8e8e93', '#a2845e', '#5856d6'
            ],
            borderWidth: 0,
        }]
    };

    const options = {
        ...defaultChartOptions,
        cutout: '70%',
        plugins: {
            ...defaultChartOptions.plugins,
            legend: {
                display: true,
                position: 'right',
                labels: {
                    boxWidth: 12,
                    font: { size: 11 }
                }
            }
        }
    };
    // Remove scales for doughnut chart
    delete options.scales;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].data = chartData;
        chartInstances[canvasId].update();
    } else {
        chartInstances[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: chartData,
            options: options,
        });
    }
}


/**
 * Creates a line chart showing portfolio value over time.
 * @param {string} canvasId - The ID of the canvas element.
 * @param {Array<Object>} history - An array of {timestamp, value} objects.
 */
function createPerformanceChart(canvasId, history) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const labels = history.map(point => new Date(point.timestamp).toLocaleDateString());
    const data = history.map(point => point.value);

    const chartData = {
        labels: labels,
        datasets: [{
            label: 'Portfolio Value',
            data: data,
            borderColor: 'var(--primary-color)',
            backgroundColor: 'rgba(10, 132, 255, 0.1)',
            fill: true,
            borderWidth: 2,
            pointRadius: 2,
        }]
    };

     if (chartInstances[canvasId]) {
        chartInstances[canvasId].data = chartData;
        chartInstances[canvasId].update();
    } else {
        chartInstances[canvasId] = new Chart(ctx, {
            type: 'line',
            data: chartData,
            options: defaultChartOptions,
        });
    }
}

/**
 * Hides the canvas and shows a placeholder message.
 * @param {string} canvasId - The ID of the canvas element.
 * @param {string} placeholderId - The ID of the placeholder element.
 */
function showChartPlaceholder(canvasId, placeholderId) {
    const canvas = document.getElementById(canvasId);
    const placeholder = document.getElementById(placeholderId);
    if (canvas) canvas.style.display = 'none';
    if (placeholder) placeholder.style.display = 'block';
}

/**
 * Hides the placeholder and shows the chart canvas.
 * @param {string} canvasId - The ID of the canvas element.
 * @param {string} placeholderId - The ID of the placeholder element.
 */
function hideChartPlaceholder(canvasId, placeholderId) {
    const canvas = document.getElementById(canvasId);
    const placeholder = document.getElementById(placeholderId);
    if (canvas) canvas.style.display = 'block';
    if (placeholder) placeholder.style.display = 'none';
}