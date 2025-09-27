import yfinance as yf
from functools import lru_cache

# List of popular stocks and cryptocurrencies to ensure they are available
POPULAR_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM", "JNJ", "V",
    "WMT", "PG", "MA", "UNH", "HD", "BAC", "DIS", "PYPL", "NFLX", "ADBE"
]
POPULAR_CRYPTO = [
    "BTC-USD", "ETH-USD", "BNB-USD", "ADA-USD", "SOL-USD", "XRP-USD", "DOT-USD",
    "DOGE-USD", "SHIB-USD", "LTC-USD"
]

@lru_cache(maxsize=128)
def get_ticker(symbol):
    """
    Returns a yfinance Ticker object. Uses caching to avoid repeated API calls.
    """
    return yf.Ticker(symbol)

def get_current_price(symbol):
    """
    Gets the current market price for a given stock or crypto symbol.
    Tries to get 'regularMarketPrice', falls back to 'currentPrice' or 'previousClose'.
    """
    try:
        ticker = get_ticker(symbol)
        info = ticker.info

        price_keys = ['regularMarketPrice', 'currentPrice', 'previousClose']
        for key in price_keys:
            if key in info and info[key] is not None:
                return float(info[key])

        # Fallback for some assets, e.g., crypto
        hist = ticker.history(period="1d", interval="1m")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])

        print(f"Warning: Could not determine price for {symbol}. Info keys available: {info.keys()}")
        return None
    except Exception as e:
        print(f"Error fetching price for {symbol} from yfinance: {e}")
        return None

def search_assets(query):
    """
    Searches for assets using yfinance.
    Note: yfinance does not have a direct search function. This is a simple workaround.
    A more robust solution would use a dedicated financial API.
    For now, we will just validate if a ticker is valid.
    """
    if not query:
        return []

    try:
        ticker = yf.Ticker(query)
        info = ticker.info
        if info and info.get('quoteType') != 'NONE':
            return [{
                'symbol': info.get('symbol', query.upper()),
                'name': info.get('longName', info.get('shortName', 'N/A')),
                'type': info.get('quoteType', 'N/A')
            }]
        return []
    except Exception:
        return []

def get_historical_data(symbol, period="1mo", interval="1d"):
    """
    Gets historical price data for a symbol.
    """
    try:
        ticker = get_ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            return None
        # Reset index to make 'Date' a column
        hist = hist.reset_index()
        # Convert timestamp to string
        hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')
        return hist[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].to_dict('records')
    except Exception as e:
        print(f"Error fetching historical data for {symbol}: {e}")
        return None

def get_asset_details(symbol):
    """
    Gets detailed information for a given asset.
    """
    try:
        ticker = get_ticker(symbol)
        info = ticker.info
        return {
            'symbol': info.get('symbol'),
            'name': info.get('longName') or info.get('shortName'),
            'type': info.get('quoteType'),
            'marketCap': info.get('marketCap'),
            'volume': info.get('regularMarketVolume'),
            'dayHigh': info.get('dayHigh'),
            'dayLow': info.get('dayLow'),
            'previousClose': info.get('previousClose')
        }
    except Exception as e:
        print(f"Error fetching asset details for {symbol}: {e}")
        return None

def get_popular_assets():
    """
    Returns the predefined list of popular stocks and crypto.
    """
    return POPULAR_STOCKS + POPULAR_CRYPTO