let currentPrice = 0;
let currentSymbol = '';
let pollInterval = null;

const searchBtn = document.getElementById('search-btn');
const searchInput = document.getElementById('asset-search');

async function fetchPrice(symbol) {
    const res = await fetch(`/api/assets/${symbol}/price`);
    if(res.ok) {
        const data = await res.json();
        currentPrice = data.price;
        document.getElementById('asset-price').textContent = '$' + currentPrice.toFixed(2);
        updateTotal();
    }
}

if (searchBtn) {
    searchBtn.addEventListener('click', async () => {
        const query = searchInput.value;
        if(!query) return;

        const res = await fetch(`/api/assets/${query}/price`);
        if(res.ok) {
            const data = await res.json();
            currentPrice = data.price;
            currentSymbol = data.symbol;

            document.getElementById('asset-symbol').textContent = currentSymbol;
            document.getElementById('asset-price').textContent = '$' + currentPrice.toFixed(2);
            document.getElementById('asset-info').style.display = 'block';
            document.getElementById('trade-form').style.display = 'block';
            updateTotal();

            // Render Chart
            if (typeof renderPriceChart === 'function') {
                renderPriceChart('priceChart', currentSymbol);
            }

            // Start Polling
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(() => fetchPrice(currentSymbol), 10000);

            // Log search
             logResearch('SEARCH', { query: query, symbol: currentSymbol });

        } else {
            alert('Asset not found');
        }
    });
}

const qtyInput = document.getElementById('trade-qty');
if (qtyInput) {
    qtyInput.addEventListener('input', updateTotal);
}

function updateTotal() {
    const qty = parseFloat(document.getElementById('trade-qty').value) || 0;
    const total = qty * currentPrice;
    document.getElementById('trade-total').textContent = '$' + total.toFixed(2);
}

const confirmBtn = document.getElementById('confirm-trade-btn');
if (confirmBtn) {
    confirmBtn.addEventListener('click', async () => {
        const action = document.getElementById('trade-action').value;
        const quantity = parseFloat(document.getElementById('trade-qty').value);
        const msgDiv = document.getElementById('trade-msg');
        const startTime = performance.now();

        msgDiv.textContent = 'Processing...';

        try {
            const res = await fetch('/api/trade', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    symbol: currentSymbol,
                    action: action,
                    quantity: quantity
                })
            });

            const endTime = performance.now();
            const data = await res.json();
            if (data.success) {
                msgDiv.innerHTML = `<span class="positive">Trade Executed! ID: ${data.transaction_id}</span>`;
                // Log detailed action
                logResearch('TRADE_ATTEMPT', {
                    symbol: currentSymbol,
                    action: action,
                    quantity: quantity,
                    success: true,
                    durationMs: endTime - startTime
                });
            } else {
                msgDiv.innerHTML = `<span class="negative">Error: ${data.error}</span>`;
                 logResearch('TRADE_ATTEMPT', {
                    symbol: currentSymbol,
                    success: false,
                    error: data.error
                });
            }
        } catch (e) {
            msgDiv.textContent = 'Error executing trade.';
        }
    });
}

async function logResearch(actionType, details) {
    try {
        await fetch('/api/research/action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                actionType: actionType,
                details: details
            })
        });
    } catch (e) { console.error(e); }
}
