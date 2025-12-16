import uuid
import datetime
from services.db import db
from services.market_data import market_data
import threading

class TradingService:
    INITIAL_CASH = 10000.0
    _lock = threading.Lock()

    def get_portfolio(self, user_id):
        return db.collection('users').document(user_id).collection('portfolio').stream()

    def get_balance(self, user_id):
        doc = db.collection('balances').document(user_id).get()
        if doc.exists:
            return doc.to_dict()
        else:
            # Initialize balance
            initial_balance = {
                'cashBalance': self.INITIAL_CASH,
                'investedValue': 0.0,
                'totalPortfolioValue': self.INITIAL_CASH,
                'totalRealizedPnL': 0.0,
                'totalUnrealizedPnL': 0.0,
                'totalTrades': 0,
                'winningTrades': 0,
                'losingTrades': 0,
                'lastCalculated': datetime.datetime.now().isoformat()
            }
            db.collection('balances').document(user_id).set(initial_balance)
            return initial_balance

    def execute_trade(self, user_id, symbol, quantity, action_type):
      with self._lock:
        # 1. Get current price
        price = market_data.get_price(symbol)
        if not price:
            return {'success': False, 'error': 'Price unavailable'}

        total_amount = price * quantity

        # 2. Get User Balance
        balance = self.get_balance(user_id)
        cash = balance['cashBalance']

        # 3. Validate Trade
        if action_type == 'BUY':
            if cash < total_amount:
                return {'success': False, 'error': 'Insufficient funds'}
        elif action_type == 'SELL':
            portfolio_item = db.collection('users').document(user_id).collection('portfolio').document(symbol).get()
            if not portfolio_item.exists or portfolio_item.to_dict()['quantity'] < quantity:
                 return {'success': False, 'error': 'Insufficient holdings'}

        # 4. Execute
        timestamp = datetime.datetime.now().isoformat()

        # Update Balance
        new_cash = cash - total_amount if action_type == 'BUY' else cash + total_amount

        # Update Portfolio
        portfolio_ref = db.collection('users').document(user_id).collection('portfolio').document(symbol)
        p_doc = portfolio_ref.get()

        if p_doc.exists:
            current_data = p_doc.to_dict()
            current_qty = current_data['quantity']
            current_total_cost = current_data.get('totalCost', 0)

            if action_type == 'BUY':
                new_qty = current_qty + quantity
                new_total_cost = current_total_cost + total_amount
                avg_cost = new_total_cost / new_qty
            else:
                new_qty = current_qty - quantity
                # When selling, total cost reduces proportionally
                cost_removed = (current_total_cost / current_qty) * quantity
                new_total_cost = current_total_cost - cost_removed
                avg_cost = current_data['averageCost'] # Avg cost doesn't change on sell

                # Calculate Realized PnL for this trade
                # Profit = (Sell Price - Avg Cost) * Quantity
                trade_pnl = (price - avg_cost) * quantity

            if new_qty == 0:
                portfolio_ref.delete()
            else:
                portfolio_ref.update({
                    'quantity': new_qty,
                    'averageCost': avg_cost,
                    'totalCost': new_total_cost,
                    'currentValue': new_qty * price,
                    'lastUpdated': timestamp
                })
        elif action_type == 'BUY':
            portfolio_ref.set({
                'symbol': symbol,
                'quantity': quantity,
                'averageCost': price,
                'totalCost': total_amount,
                'currentValue': total_amount,
                'firstPurchased': timestamp,
                'lastUpdated': timestamp,
                'assetType': 'Crypto' if '-' in symbol else 'Stock' # Simple heuristic
            })

        # Log Transaction
        tx_id = str(uuid.uuid4())
        tx_data = {
            'userId': user_id,
            'assetId': symbol,
            'symbol': symbol,
            'type': action_type,
            'quantity': quantity,
            'price': price,
            'totalAmount': total_amount,
            'cashBefore': cash,
            'cashAfter': new_cash,
            'timestamp': timestamp
        }
        if action_type == 'SELL' and 'trade_pnl' in locals():
            tx_data['realizedPnL'] = trade_pnl

        db.collection('transactions').document(tx_id).set(tx_data)

        # Update Balances
        balance['cashBalance'] = new_cash
        balance['totalTrades'] += 1
        balance['lastCalculated'] = timestamp
        # Recalculate total value roughly (should be done by background task properly)
        balance['investedValue'] = balance.get('investedValue', 0) + (total_amount if action_type == 'BUY' else -total_amount) # Simple approx
        balance['totalPortfolioValue'] = new_cash + balance['investedValue']

        db.collection('balances').document(user_id).update(balance)

        return {'success': True, 'transaction_id': tx_id, 'price': price}

    def get_portfolio_history(self, user_id):
        # Retrieve history for chart
        docs = db.collection('users').document(user_id).collection('history').stream()
        history = []
        for d in docs:
            data = d.to_dict()
            history.append({
                'date': data['date'],
                'value': data['value']
            })
        # Sort by date
        history.sort(key=lambda x: x['date'])
        return history

trading_service = TradingService()
