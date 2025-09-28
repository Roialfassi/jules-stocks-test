from datetime import datetime, timezone
import uuid
from services import sqlite_service, market_data, gamification, research_service

def execute_buy_order(user_id, symbol, quantity):
    """
    Executes a buy order for a user.
    """
    db = sqlite_service.get_db()
    try:
        quantity = float(quantity)
        if quantity <= 0:
            return {'status': 'error', 'message': 'Quantity must be positive.'}

        price = market_data.get_current_price(symbol)
        if price is None:
            return {'status': 'error', 'message': f'Could not retrieve price for {symbol}.'}

        total_cost = price * quantity

        # --- Transaction Start ---
        # 1. Get user's current balance
        balance_row = db.execute('SELECT * FROM balances WHERE user_id = ?', (user_id,)).fetchone()
        if not balance_row:
            raise Exception("User balance record not found.")

        cash_before = balance_row['cashBalance']
        if cash_before < total_cost:
            raise ValueError("Insufficient funds to complete the purchase.")

        # 2. Get user's current holding for this asset (if any)
        holding_row = db.execute('SELECT * FROM holdings WHERE user_id = ? AND symbol = ?', (user_id, symbol)).fetchone()

        # 3. Update or create portfolio holding
        if holding_row:
            new_quantity = holding_row['quantity'] + quantity
            new_avg_price = ((holding_row['average_price'] * holding_row['quantity']) + (price * quantity)) / new_quantity
            db.execute(
                'UPDATE holdings SET quantity = ?, average_price = ? WHERE id = ?',
                (new_quantity, new_avg_price, holding_row['id'])
            )
        else:
            db.execute(
                'INSERT INTO holdings (user_id, symbol, quantity, average_price) VALUES (?, ?, ?, ?)',
                (user_id, symbol, quantity, price)
            )

        # 4. Update user's balance
        db.execute(
            'UPDATE balances SET cashBalance = cashBalance - ?, investedValue = investedValue + ?, totalTrades = totalTrades + 1, lastCalculated = ? WHERE user_id = ?',
            (total_cost, total_cost, datetime.now(timezone.utc), user_id)
        )

        # 5. Log the transaction
        tx_id = str(uuid.uuid4())
        db.execute(
            'INSERT INTO transactions (id, user_id, symbol, transaction_type, quantity, price, total_value, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (tx_id, user_id, symbol, 'BUY', quantity, price, total_cost, datetime.now(timezone.utc))
        )

        db.commit()
        # --- Transaction End ---

        # 6. Post-transaction tasks
        gamification.check_and_award_achievements(user_id, 'trade')
        research_service.log_action(user_id, 'trade', 'buy', {'symbol': symbol, 'quantity': quantity, 'price': price})

        new_balance_row = db.execute('SELECT cashBalance FROM balances WHERE user_id = ?', (user_id,)).fetchone()
        return {
            'status': 'success',
            'message': f'Successfully bought {quantity} of {symbol}.',
            'new_balance': new_balance_row['cashBalance'] if new_balance_row else None
        }

    except ValueError as ve:
        db.rollback()
        return {'status': 'error', 'message': str(ve)}
    except Exception as e:
        db.rollback()
        print(f"Error executing buy order: {e}")
        return {'status': 'error', 'message': f'An unexpected error occurred: {e}'}


def execute_sell_order(user_id, symbol, quantity):
    """
    Executes a sell order for a user.
    """
    db = sqlite_service.get_db()
    try:
        quantity = float(quantity)
        if quantity <= 0:
            return {'status': 'error', 'message': 'Quantity must be positive.'}

        price = market_data.get_current_price(symbol)
        if price is None:
            return {'status': 'error', 'message': f'Could not retrieve price for {symbol}.'}

        total_proceeds = price * quantity

        # --- Transaction Start ---
        # 1. Get user's current holding
        holding_row = db.execute('SELECT * FROM holdings WHERE user_id = ? AND symbol = ?', (user_id, symbol)).fetchone()
        if not holding_row:
            raise ValueError("You do not own this asset.")

        current_quantity = holding_row['quantity']
        if current_quantity < quantity:
            raise ValueError(f"You only own {current_quantity} of {symbol}. Cannot sell {quantity}.")

        # 2. Calculate realized P&L
        avg_price = holding_row['average_price']
        cost_of_sold_shares = avg_price * quantity
        realized_pnl = total_proceeds - cost_of_sold_shares

        # 3. Update or delete portfolio holding
        new_quantity = current_quantity - quantity
        if new_quantity < 1e-6: # Use a small epsilon for float comparison
            db.execute('DELETE FROM holdings WHERE id = ?', (holding_row['id'],))
        else:
            db.execute('UPDATE holdings SET quantity = ? WHERE id = ?', (new_quantity, holding_row['id']))

        # 4. Update user's balance
        winning_trades_update = 1 if realized_pnl > 0 else 0
        losing_trades_update = 1 if realized_pnl < 0 else 0
        db.execute(
            '''UPDATE balances
               SET cashBalance = cashBalance + ?,
                   investedValue = investedValue - ?,
                   totalRealizedPnL = totalRealizedPnL + ?,
                   totalTrades = totalTrades + 1,
                   winningTrades = winningTrades + ?,
                   losingTrades = losingTrades + ?,
                   lastCalculated = ?
               WHERE user_id = ?''',
            (total_proceeds, cost_of_sold_shares, realized_pnl, winning_trades_update, losing_trades_update, datetime.now(timezone.utc), user_id)
        )

        # 5. Log the transaction
        tx_id = str(uuid.uuid4())
        db.execute(
            'INSERT INTO transactions (id, user_id, symbol, transaction_type, quantity, price, total_value, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (tx_id, user_id, symbol, 'SELL', quantity, price, total_proceeds, datetime.now(timezone.utc))
        )

        db.commit()
        # --- Transaction End ---

        # 6. Post-transaction tasks
        gamification.check_and_award_achievements(user_id, 'trade')
        research_service.log_action(user_id, 'trade', 'sell', {'symbol': symbol, 'quantity': quantity, 'price': price})

        new_balance_row = db.execute('SELECT cashBalance FROM balances WHERE user_id = ?', (user_id,)).fetchone()
        return {
            'status': 'success',
            'message': f'Successfully sold {quantity} of {symbol}.',
            'new_balance': new_balance_row['cashBalance'] if new_balance_row else None
        }

    except ValueError as ve:
        db.rollback()
        return {'status': 'error', 'message': str(ve)}
    except Exception as e:
        db.rollback()
        print(f"Error executing sell order: {e}")
        return {'status': 'error', 'message': f'An unexpected error occurred: {e}'}

def get_portfolio_holdings(user_id):
    """
    Retrieves a user's portfolio holdings and calculates current value.
    """
    db = sqlite_service.get_db()
    try:
        holdings_rows = db.execute('SELECT * FROM holdings WHERE user_id = ?', (user_id,)).fetchall()
        holdings = []
        for row in holdings_rows:
            holding_data = dict(row)
            symbol = holding_data['symbol']
            current_price = market_data.get_current_price(symbol)

            if current_price is not None:
                total_cost = holding_data['average_price'] * holding_data['quantity']
                holding_data['currentPrice'] = current_price
                holding_data['currentValue'] = holding_data['quantity'] * current_price
                holding_data['unrealizedPnL'] = holding_data['currentValue'] - total_cost
            else:
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
    db = sqlite_service.get_db()
    try:
        tx_rows = db.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC', (user_id,)).fetchall()
        transactions = [dict(row) for row in tx_rows]
        return transactions
    except Exception as e:
        print(f"Error getting transaction history for user {user_id}: {e}")
        return []