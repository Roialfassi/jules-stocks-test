from apscheduler.schedulers.background import BackgroundScheduler
from services.db import db
from services.market_data import market_data
from services.trading import trading_service
import datetime

def update_prices():
    """
    Updates prices for assets that are currently held by users.
    In a real system, this would subscribe to a websocket or batch update.
    Here we check all portfolios to find unique assets.
    """
    print("Updating prices...")
    try:
        # Get all portfolios.
        # In NoSQL, iterating all users then all portfolios is expensive.
        # Ideally we maintain a 'watched_assets' set.
        # For this implementation, we will check 'priceCache' and update those if they are stale.
        # And maybe add assets from active users (stub).

        cached_docs = db.collection('priceCache').stream()
        for doc in cached_docs:
            data = doc.to_dict()
            symbol = doc.id
            # Force refresh price
            try:
                # We can't easily force refresh market_data.get_price without bypassing cache check
                # unless we modify get_price or just call yfinance directly.
                # But market_data.get_price has a cache check.
                # If we want to background update, we should fetch new price and set it.

                # Fetch fresh from yfinance
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                if hasattr(ticker, 'fast_info'):
                    price = ticker.fast_info['last_price']
                else:
                    price = ticker.info.get('regularMarketPrice') or ticker.info.get('currentPrice')

                if price:
                    db.collection('priceCache').document(symbol).set({
                        'price': price,
                        'lastUpdated': datetime.datetime.now().isoformat(),
                        'source': 'yfinance_sched'
                    })
            except Exception as e:
                print(f"Failed to update {symbol}: {e}")

    except Exception as e:
        print(f"Error in update_prices: {e}")

def calculate_portfolio_values():
    """
    Recalculates total portfolio value for all users based on latest prices.
    """
    print("Calculating portfolio values...")
    try:
        users = db.collection('users').stream()
        for user_doc in users:
            user_id = user_doc.id if hasattr(user_doc, 'id') else user_doc.to_dict().get('id')
            if not user_id: continue # Should not happen

            # Recalculate
            portfolio_docs = db.collection('users').document(user_id).collection('portfolio').stream()
            current_invested_value = 0.0

            for p_doc in portfolio_docs:
                item = p_doc.to_dict()
                symbol = item['symbol']
                qty = item['quantity']

                # Get latest price from cache or fetch
                price = market_data.get_price(symbol) or item['averageCost']

                val = qty * price
                current_invested_value += val

                # Update item current value
                db.collection('users').document(user_id).collection('portfolio').document(symbol).update({
                    'currentValue': val,
                    'lastUpdated': datetime.datetime.now().isoformat()
                })

            # Get cash
            balance_doc = db.collection('balances').document(user_id).get()
            if balance_doc.exists:
                balance = balance_doc.to_dict()
                cash = balance['cashBalance']
                total_val = cash + current_invested_value

                unrealized_pnl = 0 # Calculate correctly if needed

                db.collection('balances').document(user_id).update({
                    'investedValue': current_invested_value,
                    'totalPortfolioValue': total_val,
                    'lastCalculated': datetime.datetime.now().isoformat()
                })

                # Log for history (simple version)
                # Ensure a history collection exists for charts
                # In a real app we might do this once a day, not every 15 min.
                # But for demo purposes:
                history_id = datetime.datetime.now().strftime('%Y%m%d%H%M')
                db.collection('users').document(user_id).collection('history').document(history_id).set({
                    'date': datetime.datetime.now().isoformat(),
                    'value': total_val,
                    'cash': cash
                })

    except Exception as e:
        print(f"Error in calculate_portfolio_values: {e}")

def init_scheduler(app):
    scheduler = BackgroundScheduler()
    # In production, increase interval. For demo, keep it short or as requested.
    scheduler.add_job(func=update_prices, trigger="interval", minutes=15)
    scheduler.add_job(func=calculate_portfolio_values, trigger="interval", minutes=15)
    scheduler.start()

    import atexit
    atexit.register(lambda: scheduler.shutdown())
