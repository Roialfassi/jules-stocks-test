document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('/trading')) return;

    // --- State ---
    let selectedSymbol = null;
    let currentPrice = 0;
    let priceUpdateInterval = null;

    // --- DOM Elements ---
    const searchInput = document.getElementById('asset-search-input');
    const searchResults = document.getElementById('search-results');
    const assetDisplay = document.getElementById('asset-display');

    const assetNameEl = document.getElementById('asset-name');
    const assetSymbolEl = document.getElementById('asset-symbol');
    const assetPriceEl = document.getElementById('asset-price');
    const assetChangeEl = document.getElementById('asset-change');

    const buyForm = document.getElementById('buy-form');
    const sellForm = document.getElementById('sell-form');
    const buyQuantityInput = document.getElementById('buy-quantity');
    const sellQuantityInput = document.getElementById('sell-quantity');
    const buyEstimatedCostEl = document.getElementById('buy-estimated-cost');
    const sellEstimatedProceedsEl = document.getElementById('sell-estimated-proceeds');
    const tradeFormErrorEl = document.getElementById('trade-form-error');

    const priceChartCanvas = document.getElementById('price-chart');
    const chartPeriodBtns = document.querySelectorAll('.chart-period-btn');

    const modal = document.getElementById('confirmation-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalSummary = document.getElementById('modal-summary');
    const modalConfirmBtn = document.getElementById('modal-confirm-btn');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');
    const modalCloseBtn = document.getElementById('modal-close-btn');

    // --- Asset Search ---
    const handleSearch = debounce(async () => {
        const query = searchInput.value.trim().toUpperCase();
        if (query.length < 1) {
            searchResults.classList.add('hidden');
            return;
        }

        try {
            const results = await apiRequest(`/api/assets/search?q=${query}`);
            renderSearchResults(results);
        } catch (error) {
            console.error('Search failed:', error);
            searchResults.classList.add('hidden');
        }
    }, 300);

    function renderSearchResults(results) {
        searchResults.innerHTML = '';
        if (results.length > 0) {
            results.forEach(asset => {
                const item = document.createElement('div');
                item.className = 'search-result-item';
                item.dataset.symbol = asset.symbol;
                item.innerHTML = `<span class="symbol">${asset.symbol}</span><span class="name">${asset.name}</span>`;
                item.addEventListener('click', () => selectAsset(asset.symbol));
                searchResults.appendChild(item);
            });
            searchResults.classList.remove('hidden');
        } else {
            searchResults.classList.add('hidden');
        }
    }

    searchInput.addEventListener('input', handleSearch);

    // --- Asset Selection & Display ---
    async function selectAsset(symbol) {
        selectedSymbol = symbol;
        searchResults.classList.add('hidden');
        searchInput.value = symbol;
        assetDisplay.classList.remove('hidden');

        // Stop any previous price updates
        if (priceUpdateInterval) clearInterval(priceUpdateInterval);

        try {
            // Fetch initial data
            await updateAssetPrice(symbol);
            await updatePriceChart('1mo');

            // Start polling for price updates every 15 seconds
            priceUpdateInterval = setInterval(() => updateAssetPrice(symbol), 15000);
        } catch (error) {
            console.error(`Failed to load data for ${symbol}:`, error);
            showToast(`Could not load data for ${symbol}`, 'error');
        }
    }

    async function updateAssetPrice(symbol) {
        try {
            const data = await apiRequest(`/api/assets/${symbol}/price`);
            currentPrice = data.price;

            assetNameEl.textContent = data.name;
            assetSymbolEl.textContent = data.symbol;
            assetPriceEl.textContent = formatCurrency(data.price);

            const change = data.price - data.previousClose;
            const changePercent = (change / data.previousClose) * 100;
            assetChangeEl.textContent = `${formatCurrency(change, true)} (${changePercent.toFixed(2)}%)`;
            updateElementStatus(assetChangeEl, change);

            // Update form symbol fields
            buyForm.querySelector('#buy-symbol').value = symbol;
            sellForm.querySelector('#sell-symbol').value = symbol;
            updateTradeEstimates();

        } catch (error) {
            console.error(`Failed to update price for ${symbol}:`, error);
            if(priceUpdateInterval) clearInterval(priceUpdateInterval);
        }
    }

    async function updatePriceChart(period) {
        try {
            hideChartPlaceholder('price-chart', 'chart-placeholder');
            const history = await apiRequest(`/api/assets/${selectedSymbol}/history?period=${period}`);
            if (history && history.length > 0) {
                createPriceHistoryChart('price-chart', history);
                chartPeriodBtns.forEach(btn => btn.classList.remove('active'));
                document.querySelector(`.chart-period-btn[data-period="${period}"]`).classList.add('active');
            } else {
                showChartPlaceholder('price-chart', 'chart-placeholder');
            }
        } catch (error) {
            console.error('Failed to update chart:', error);
            showChartPlaceholder('price-chart', 'chart-placeholder');
        }
    }

    chartPeriodBtns.forEach(btn => {
        btn.addEventListener('click', () => updatePriceChart(btn.dataset.period));
    });

    // --- Trade Form Logic ---
    function updateTradeEstimates() {
        const buyQuantity = parseFloat(buyQuantityInput.value) || 0;
        buyEstimatedCostEl.textContent = formatCurrency(buyQuantity * currentPrice);

        const sellQuantity = parseFloat(sellQuantityInput.value) || 0;
        sellEstimatedProceedsEl.textContent = formatCurrency(sellQuantity * currentPrice);
    }

    buyQuantityInput.addEventListener('input', updateTradeEstimates);
    sellQuantityInput.addEventListener('input', updateTradeEstimates);

    buyForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const quantity = parseFloat(buyQuantityInput.value);
        if (quantity > 0) {
            openConfirmationModal('BUY', selectedSymbol, quantity, currentPrice);
        } else {
            tradeFormErrorEl.textContent = 'Please enter a valid quantity.';
        }
    });

    sellForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const quantity = parseFloat(sellQuantityInput.value);
        if (quantity > 0) {
            openConfirmationModal('SELL', selectedSymbol, quantity, currentPrice);
        } else {
            tradeFormErrorEl.textContent = 'Please enter a valid quantity.';
        }
    });

    // --- Confirmation Modal ---
    let confirmAction = null;

    function openConfirmationModal(type, symbol, quantity, price) {
        tradeFormErrorEl.textContent = '';
        const total = formatCurrency(quantity * price);
        modalTitle.textContent = `Confirm ${type} Order`;
        modalSummary.textContent = `Are you sure you want to ${type.toLowerCase()} ${quantity} of ${symbol} for approximately ${total}?`;

        // Store the action to be executed on confirm
        confirmAction = async () => {
            try {
                const endpoint = type === 'BUY' ? '/api/trade/buy' : '/api/trade/sell';
                const response = await apiRequest(endpoint, {
                    method: 'POST',
                    body: JSON.stringify({ symbol, quantity }),
                });
                showToast(response.message, 'success');
                buyQuantityInput.value = '';
                sellQuantityInput.value = '';
                updateTradeEstimates();
            } catch (error) {
                // apiRequest already shows a toast
            } finally {
                closeModal();
            }
        };

        modal.classList.remove('hidden');
    }

    function closeModal() {
        modal.classList.add('hidden');
        confirmAction = null;
    }

    modalConfirmBtn.addEventListener('click', () => {
        if (confirmAction) {
            confirmAction();
        }
    });
    modalCancelBtn.addEventListener('click', closeModal);
    modalCloseBtn.addEventListener('click', closeModal);

    // --- Initial Page State ---
    showChartPlaceholder('price-chart', 'chart-placeholder');
});