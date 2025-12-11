// Price polling
function updatePrices() {
    const priceElements = document.querySelectorAll('.loading-price');
    if (priceElements) {
        priceElements.forEach(async el => {
            const symbol = el.dataset.symbol;
            try {
                const res = await fetch(`/api/assets/${symbol}/price`);
                const data = await res.json();
                if (data.price) {
                    el.textContent = '$' + data.price.toFixed(2);
                    el.className = 'loading-price'; // reset
                    el.classList.add(data.price > 0 ? 'positive' : 'negative');
                } else {
                    el.textContent = 'N/A';
                }
            } catch (e) {
                console.error('Error fetching price', e);
            }
        });
    }
}

// Initial call
updatePrices();

// Poll every 10 seconds
setInterval(updatePrices, 10000);

// Log page view
async function logPageView() {
    try {
        await fetch('/api/research/action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                actionType: 'PAGE_VIEW',
                details: { url: window.location.pathname }
            })
        });
    } catch (e) { console.error(e); }
}

logPageView();
