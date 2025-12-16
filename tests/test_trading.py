import pytest
import os
from services.trading import TradingService
from services.db import db, Config

# Use SQLite for testing
Config.DB_TYPE = 'sqlite'

@pytest.fixture
def trading_service():
    return TradingService()

@pytest.fixture
def setup_user():
    user_id = 'test_user_1'
    # Clear DB for this user
    db.delete('balances', user_id)
    # Clear portfolio
    # Use delete_collection method for SQLite
    # db is the SQLiteDB instance in this case
    if hasattr(db, 'delete_collection'):
        db.delete_collection(f'users/{user_id}/portfolio')
    return user_id

def test_initial_balance(trading_service, setup_user):
    user_id = setup_user
    balance = trading_service.get_balance(user_id)
    assert balance['cashBalance'] == 10000.0

def test_buy_stock(trading_service, setup_user):
    user_id = setup_user
    # Mock price?
    # The trading service calls market_data.get_price. We should mock that.

    # Simple monkeypatch for market_data
    from services.market_data import market_data
    market_data.get_price = lambda symbol: 150.0

    res = trading_service.execute_trade(user_id, 'AAPL', 10, 'BUY')
    assert res['success'] == True

    balance = trading_service.get_balance(user_id)
    assert balance['cashBalance'] == 10000.0 - (150.0 * 10)

    portfolio = list(trading_service.get_portfolio(user_id))
    assert len(portfolio) == 1
    assert portfolio[0].to_dict()['symbol'] == 'AAPL'
    assert portfolio[0].to_dict()['quantity'] == 10

def test_sell_stock(trading_service, setup_user):
    user_id = setup_user
    from services.market_data import market_data
    market_data.get_price = lambda symbol: 150.0

    # Buy first
    trading_service.execute_trade(user_id, 'AAPL', 10, 'BUY')

    # Price goes up
    market_data.get_price = lambda symbol: 160.0

    # Sell 5
    res = trading_service.execute_trade(user_id, 'AAPL', 5, 'SELL')
    assert res['success'] == True

    balance = trading_service.get_balance(user_id)
    # Cash = Start - Buy(1500) + Sell(160*5 = 800) = 10000 - 1500 + 800 = 9300
    assert balance['cashBalance'] == 9300.0

    portfolio = list(trading_service.get_portfolio(user_id))
    assert portfolio[0].to_dict()['quantity'] == 5
    # Total cost remaining should be 750 (5 * 150)
    assert portfolio[0].to_dict()['totalCost'] == 750.0
