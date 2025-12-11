import yfinance as yf
import datetime
from services.db import db

class MarketDataService:
    def get_price(self, symbol):
        # Check cache first
        cache_doc = db.collection('priceCache').document(symbol).get()
        if cache_doc.exists:
            data = cache_doc.to_dict()
            last_updated = datetime.datetime.fromisoformat(data['lastUpdated'])
            # 15 min cache
            if (datetime.datetime.now() - last_updated).seconds < 900:
                return data['price']

        # Fetch from yfinance
        try:
            ticker = yf.Ticker(symbol)

            # 1. Try fast_info
            try:
                if hasattr(ticker, 'fast_info'):
                    # Sometimes accessing last_price triggers internal fetching error
                    price = ticker.fast_info.last_price
                else:
                    price = None
            except Exception:
                price = None

            # 2. Try info dict
            if not price:
                try:
                    price = ticker.info.get('regularMarketPrice') or ticker.info.get('currentPrice') or ticker.info.get('previousClose')
                except Exception:
                    pass

            # 3. Try history
            if not price:
                try:
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        price = hist['Close'].iloc[-1]
                except Exception:
                    pass

            if price:
                self._update_cache(symbol, price)
                return price

        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            return None

    def _update_cache(self, symbol, price):
        db.collection('priceCache').document(symbol).set({
            'price': price,
            'lastUpdated': datetime.datetime.now().isoformat(),
            'source': 'yfinance'
        })

    def search_assets(self, query):
        # Basic search (stub). yfinance doesn't have a good search API.
        # We might need a predefined list of assets.
        # For now, return a dummy list or try to fetch if it looks like a ticker.
        query = query.upper()
        popular = [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'type': 'Stock'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'type': 'Stock'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'type': 'Stock'},
            {'symbol': 'AMZN', 'name': 'Amazon.com', 'type': 'Stock'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'type': 'Stock'},
            {'symbol': 'META', 'name': 'Meta Platforms', 'type': 'Stock'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corp.', 'type': 'Stock'},
            {'symbol': 'BTC-USD', 'name': 'Bitcoin', 'type': 'Crypto'},
            {'symbol': 'ETH-USD', 'name': 'Ethereum', 'type': 'Crypto'},
            {'symbol': 'BNB-USD', 'name': 'Binance Coin', 'type': 'Crypto'},
            {'symbol': 'ADA-USD', 'name': 'Cardano', 'type': 'Crypto'},
            {'symbol': 'SOL-USD', 'name': 'Solana', 'type': 'Crypto'}
        ]
        results = [a for a in popular if query in a['symbol'] or query in a['name'].upper()]

        # If no results and query looks like a ticker, add it as option
        if not results and 2 <= len(query) <= 6 and query.isalpha():
             results.append({'symbol': query, 'name': query, 'type': 'Unknown'})

        return results

    def get_history(self, symbol):
        # Fetch historical data
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo")
            # Convert to list of dicts
            data = []
            for date, row in hist.iterrows():
                data.append({
                    'date': date.isoformat(),
                    'close': row['Close']
                })
            return data
        except Exception:
            return []

market_data = MarketDataService()
