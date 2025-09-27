from apscheduler.schedulers.background import BackgroundScheduler
from services import market_data, firebase_service, gamification
from datetime import datetime

scheduler = BackgroundScheduler(daemon=True, timezone='UTC')

def update_all_asset_prices():
    """
    Scheduled Job 1: Fetches the latest prices for all unique assets held by users
    and updates the 'priceCache' collection in Firestore.
    """
    print(f"[{datetime.utcnow()}] Running job: update_all_asset_prices")
    try:
        db = firebase_service.db
        if not db:
            print("Firestore client not initialized. Skipping price update.")
            return

        # 1. Get all unique symbols from user portfolios
        portfolio_docs = db.collection_group('portfolio').select(['symbol']).stream()
        unique_symbols = {doc.get('symbol') for doc in portfolio_docs if doc.get('symbol')}

        # 2. Add popular assets to the list to ensure they are cached
        unique_symbols.update(market_data.get_popular_assets())

        if not unique_symbols:
            print("No symbols to update.")
            return

        # 3. Batch fetch prices and update Firestore
        batch = db.batch()
        updated_count = 0
        for symbol in unique_symbols:
            price = market_data.get_current_price(symbol)
            if price is not None:
                price_ref = db.collection('priceCache').document(symbol)
                batch.set(price_ref, {
                    'symbol': symbol,
                    'price': price,
                    'lastUpdated': datetime.utcnow()
                })
                updated_count += 1

        batch.commit()
        print(f"Successfully updated prices for {updated_count}/{len(unique_symbols)} symbols.")

    except Exception as e:
        print(f"Error during price update job: {e}")


def recalculate_all_portfolio_values():
    """
    Scheduled Job 2: Recalculates the portfolio value for all active users.
    This is critical for displaying up-to-date P&L.
    """
    print(f"[{datetime.utcnow()}] Running job: recalculate_all_portfolio_values")
    try:
        db = firebase_service.db
        if not db:
            print("Firestore client not initialized. Skipping portfolio calculation.")
            return

        users_ref = db.collection('users').stream()
        for user in users_ref:
            user_id = user.id
            holdings_ref = db.collection('users').document(user_id).collection('portfolio').stream()

            invested_value = 0
            current_portfolio_value = 0
            total_unrealized_pnl = 0

            for holding_doc in holdings_ref:
                holding = holding_doc.to_dict()
                symbol = holding.get('symbol')

                # Get price from our cache for efficiency
                price_doc = db.collection('priceCache').document(symbol).get()
                if price_doc.exists:
                    current_price = price_doc.to_dict().get('price')
                else:
                    # Fallback to live price if not in cache
                    current_price = market_data.get_current_price(symbol)

                if current_price is not None:
                    quantity = holding.get('quantity', 0)
                    total_cost = holding.get('totalCost', 0)

                    current_value = quantity * current_price
                    unrealized_pnl = current_value - total_cost

                    invested_value += total_cost
                    current_portfolio_value += current_value
                    total_unrealized_pnl += unrealized_pnl

            # Update the user's balance document
            balance_ref = db.collection('balances').document(user_id)
            balance_doc = balance_ref.get()
            if balance_doc.exists:
                cash_balance = balance_doc.to_dict().get('cashBalance', 0)
                balance_ref.update({
                    'investedValue': invested_value,
                    'totalPortfolioValue': cash_balance + current_portfolio_value,
                    'totalUnrealizedPnL': total_unrealized_pnl,
                    'lastCalculated': datetime.utcnow()
                })
        print("Finished recalculating portfolio values for all users.")
    except Exception as e:
        print(f"Error during portfolio value calculation job: {e}")

def check_achievements_for_all_users():
    """
    Scheduled Job 3: Periodically checks for non-event-based achievements
    (e.g., portfolio growth, diversification).
    """
    print(f"[{datetime.utcnow()}] Running job: check_achievements_for_all_users")
    try:
        db = firebase_service.db
        if not db:
            return

        users_ref = db.collection('users').stream()
        for user in users_ref:
            # This will check all achievements that are not tied to a specific action
            gamification.check_and_award_achievements(user.id, 'scheduled_check')
        print("Finished checking achievements for all users.")
    except Exception as e:
        print(f"Error during achievement check job: {e}")

def cleanup_old_sessions():
    """
    Scheduled Job 4: Cleans up old data, e.g., user action logs or sessions.
    (Implementation is a placeholder for now).
    """
    print(f"[{datetime.utcnow()}] Running job: cleanup_old_sessions")
    # Example: Delete action logs older than 90 days
    # collection_ref = firebase_service.db.collection('userActions')
    # cutoff_date = datetime.utcnow() - timedelta(days=90)
    # old_logs = collection_ref.where('timestamp', '<', cutoff_date).stream()
    # for log in old_logs:
    #     log.reference.delete()
    print("Cleanup job complete (placeholder).")


def init_app(app):
    """
    Initializes the scheduler and adds jobs.
    Called from the main app factory.
    """
    if not scheduler.running:
        # Add jobs to the scheduler
        scheduler.add_job(id='update_prices', func=update_all_asset_prices, trigger='interval', minutes=15)
        scheduler.add_job(id='recalculate_portfolios', func=recalculate_all_portfolio_values, trigger='interval', minutes=15)
        scheduler.add_job(id='check_achievements', func=check_achievements_for_all_users, trigger='interval', minutes=5)
        scheduler.add_job(id='cleanup_sessions', func=cleanup_old_sessions, trigger='cron', day_of_week='*', hour=3)

        # Start the scheduler
        scheduler.start()
        print("APScheduler started with jobs.")

        # It's good practice to shut down the scheduler when the app exits
        import atexit
        atexit.register(lambda: scheduler.shutdown())