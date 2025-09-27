from datetime import datetime
from services import firebase_service, market_data, gamification, research_service
from firebase_admin import firestore

def execute_buy_order(user_id, symbol, quantity):
    """
    Executes a buy order for a user.
    This entire function should be executed within a Firestore transaction.
    """
    try:
        quantity = float(quantity)
        if quantity <= 0:
            return {'status': 'error', 'message': 'Quantity must be positive.'}

        # 1. Get current market price
        price = market_data.get_current_price(symbol)
        if price is None:
            return {'status': 'error', 'message': f'Could not retrieve price for {symbol}.'}

        total_cost = price * quantity
        db = firebase_service.db

        # Use a Firestore transaction to ensure atomicity
        @firestore.transactional
        def buy_transaction(transaction, user_id, symbol, quantity, price, total_cost):
            # 2. Get user's current balance
            balance_ref = db.collection('balances').document(user_id)
            balance_snapshot = balance_ref.get(transaction=transaction)
            if not balance_snapshot.exists:
                raise Exception("User balance record not found.")

            balance_data = balance_snapshot.to_dict()
            cash_before = balance_data.get('cashBalance', 0)

            if cash_before < total_cost:
                raise ValueError("Insufficient funds to complete the purchase.")

            # 3. Get user's current holding for this asset (if any)
            portfolio_ref = db.collection('users').document(user_id).collection('portfolio').document(symbol)
            portfolio_snapshot = portfolio_ref.get(transaction=transaction)

            # 4. Update or create portfolio holding
            if portfolio_snapshot.exists:
                # User already owns this asset, update holding
                holding_data = portfolio_snapshot.to_dict()
                new_quantity = holding_data['quantity'] + quantity
                new_total_cost = holding_data['totalCost'] + total_cost
                new_avg_cost = new_total_cost / new_quantity

                transaction.update(portfolio_ref, {
                    'quantity': new_quantity,
                    'averageCost': new_avg_cost,
                    'totalCost': new_total_cost,
                    'lastUpdated': datetime.utcnow()
                })
            else:
                # New holding for this user
                asset_details = market_data.get_asset_details(symbol)
                transaction.set(portfolio_ref, {
                    'symbol': symbol,
                    'name': asset_details.get('name', 'Unknown'),
                    'assetType': asset_details.get('type', 'Unknown'),
                    'quantity': quantity,
                    'averageCost': price,
                    'totalCost': total_cost,
                    'firstPurchased': datetime.utcnow(),
                    'lastUpdated': datetime.utcnow()
                })

            # 5. Update user's balance
            new_cash_balance = cash_before - total_cost
            new_invested_value = balance_data.get('investedValue', 0) + total_cost
            new_total_trades = balance_data.get('totalTrades', 0) + 1

            transaction.update(balance_ref, {
                'cashBalance': new_cash_balance,
                'investedValue': new_invested_value,
                'totalTrades': new_total_trades,
                'lastCalculated': datetime.utcnow()
            })

            # 6. Log the transaction
            tx_ref = db.collection('transactions').document()
            transaction.set(tx_ref, {
                'userId': user_id,
                'symbol': symbol,
                'type': 'BUY',
                'quantity': quantity,
                'price': price,
                'totalAmount': total_cost,
                'timestamp': datetime.utcnow(),
                # 'decisionTimeMs': 0 # To be added from frontend
            })
            return new_cash_balance

        # Execute the transaction
        transaction = db.transaction()
        new_balance = buy_transaction(transaction, user_id, symbol, quantity, price, total_cost)

        # 7. Post-transaction tasks
        gamification.check_and_award_achievements(user_id, 'trade')
        research_service.log_action(user_id, 'trade', 'buy', {'symbol': symbol, 'quantity': quantity, 'price': price})

        return {
            'status': 'success',
            'message': f'Successfully bought {quantity} of {symbol}.',
            'new_balance': new_balance
        }

    except ValueError as ve:
        return {'status': 'error', 'message': str(ve)}
    except Exception as e:
        print(f"Error executing buy order: {e}")
        return {'status': 'error', 'message': f'An unexpected error occurred: {e}'}


def execute_sell_order(user_id, symbol, quantity):
    """
    Executes a sell order for a user.
    This entire function should be executed within a Firestore transaction.
    """
    try:
        quantity = float(quantity)
        if quantity <= 0:
            return {'status': 'error', 'message': 'Quantity must be positive.'}

        # 1. Get current market price
        price = market_data.get_current_price(symbol)
        if price is None:
            return {'status': 'error', 'message': f'Could not retrieve price for {symbol}.'}

        total_proceeds = price * quantity
        db = firebase_service.db

        @firestore.transactional
        def sell_transaction(transaction, user_id, symbol, quantity, price, total_proceeds):
            # 2. Get user's current holding
            portfolio_ref = db.collection('users').document(user_id).collection('portfolio').document(symbol)
            portfolio_snapshot = portfolio_ref.get(transaction=transaction)

            if not portfolio_snapshot.exists:
                raise ValueError("You do not own this asset.")

            holding_data = portfolio_snapshot.to_dict()
            current_quantity = holding_data['quantity']

            if current_quantity < quantity:
                raise ValueError(f"You only own {current_quantity} of {symbol}. Cannot sell {quantity}.")

            # 3. Calculate realized P&L
            avg_cost = holding_data['averageCost']
            cost_of_sold_shares = avg_cost * quantity
            realized_pnl = total_proceeds - cost_of_sold_shares

            # 4. Get user's balance
            balance_ref = db.collection('balances').document(user_id)
            balance_snapshot = balance_ref.get(transaction=transaction)
            if not balance_snapshot.exists:
                raise Exception("User balance record not found.")
            balance_data = balance_snapshot.to_dict()

            # 5. Update or delete portfolio holding
            new_quantity = current_quantity - quantity
            if new_quantity < 1e-6: # Use a small epsilon for float comparison
                # Sold all shares, delete holding
                transaction.delete(portfolio_ref)
            else:
                # Update holding
                new_total_cost = holding_data['totalCost'] - cost_of_sold_shares
                transaction.update(portfolio_ref, {
                    'quantity': new_quantity,
                    'totalCost': new_total_cost,
                    'lastUpdated': datetime.utcnow()
                })

            # 6. Update user's balance
            new_cash_balance = balance_data.get('cashBalance', 0) + total_proceeds
            new_invested_value = balance_data.get('investedValue', 0) - cost_of_sold_shares
            new_realized_pnl = balance_data.get('totalRealizedPnL', 0) + realized_pnl
            new_total_trades = balance_data.get('totalTrades', 0) + 1

            # Update win/loss count
            winning_trades = balance_data.get('winningTrades', 0)
            losing_trades = balance_data.get('losingTrades', 0)
            if realized_pnl > 0:
                winning_trades += 1
            elif realized_pnl < 0:
                losing_trades += 1

            transaction.update(balance_ref, {
                'cashBalance': new_cash_balance,
                'investedValue': new_invested_value,
                'totalRealizedPnL': new_realized_pnl,
                'totalTrades': new_total_trades,
                'winningTrades': winning_trades,
                'losingTrades': losing_trades,
                'lastCalculated': datetime.utcnow()
            })

            # 7. Log the transaction
            tx_ref = db.collection('transactions').document()
            transaction.set(tx_ref, {
                'userId': user_id,
                'symbol': symbol,
                'type': 'SELL',
                'quantity': quantity,
                'price': price,
                'totalAmount': total_proceeds,
                'realizedPnL': realized_pnl,
                'timestamp': datetime.utcnow(),
            })
            return new_cash_balance

        # Execute the transaction
        transaction = db.transaction()
        new_balance = sell_transaction(transaction, user_id, symbol, quantity, price, total_proceeds)

        # 8. Post-transaction tasks
        gamification.check_and_award_achievements(user_id, 'trade')
        research_service.log_action(user_id, 'trade', 'sell', {'symbol': symbol, 'quantity': quantity, 'price': price})

        return {
            'status': 'success',
            'message': f'Successfully sold {quantity} of {symbol}.',
            'new_balance': new_balance
        }

    except ValueError as ve:
        return {'status': 'error', 'message': str(ve)}
    except Exception as e:
        print(f"Error executing sell order: {e}")
        return {'status': 'error', 'message': f'An unexpected error occurred: {e}'}

def get_portfolio_holdings(user_id):
    """
    Retrieves a user's portfolio holdings and calculates current value.
    """
    try:
        holdings_ref = firebase_service.db.collection('users').document(user_id).collection('portfolio')
        holdings = []
        for doc in holdings_ref.stream():
            holding_data = doc.to_dict()
            symbol = holding_data['symbol']
            current_price = market_data.get_current_price(symbol)

            if current_price is not None:
                holding_data['currentPrice'] = current_price
                holding_data['currentValue'] = holding_data['quantity'] * current_price
                holding_data['unrealizedPnL'] = holding_data['currentValue'] - holding_data['totalCost']
            else:
                # If price is unavailable, use last known values
                holding_data['currentPrice'] = None
                holding_data['currentValue'] = None
                holding_data['unrealizedPnL'] = None

            holdings.append(holding_data)
        return holdings
    except Exception as e:
        print(f"Error getting portfolio holdings for user {user_id}: {e}")
        return []

def get_transaction_history(user_id):
    """
    Retrieves the transaction history for a user.
    """
    try:
        tx_ref = firebase_service.db.collection('transactions').where('userId', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING)
        transactions = [doc.to_dict() for doc in tx_ref.stream()]
        return transactions
    except Exception as e:
        print(f"Error getting transaction history for user {user_id}: {e}")
        return []