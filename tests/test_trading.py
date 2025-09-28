import pytest
import os
import uuid
from app import create_app
from services import sqlite_service, trading_service
from unittest.mock import patch

# --- Fixtures ---

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    db_path = f"test_trading_{uuid.uuid4()}.sqlite"
    app = create_app('testing')
    app.config.update({"DATABASE": db_path})

    with app.app_context():
        sqlite_service.init_db()
        # Seed with a test user
        db = sqlite_service.get_db()
        user_id = 'test_user_123'
        db.execute(
            "INSERT INTO users (id, username, email, password, participantId, researchGroup, consentGiven, consentTimestamp, consentIP, createdAt, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, 'testtrader', 'trader@test.com', 'password', 'P0001', 1, 1, '2023-01-01', '127.0.0.1', '2023-01-01', 'user')
        )
        db.execute(
            "INSERT INTO balances (user_id, cashBalance) VALUES (?, ?)",
            (user_id, 10000.0)
        )
        db.commit()

    yield app

    # Cleanup
    os.unlink(db_path)


# --- Mock Data ---
MOCK_USER_ID = "test_user_123"
MOCK_SYMBOL = "TEST"
MOCK_PRICE = 100.0

# --- Tests ---

@patch('services.trading_service.research_service.log_action')
@patch('services.trading_service.gamification.check_and_award_achievements')
@patch('services.market_data.get_current_price')
def test_execute_buy_order_success(mock_get_price, mock_check_achievements, mock_log_action, app):
    mock_get_price.return_value = MOCK_PRICE

    with app.app_context():
        result = trading_service.execute_buy_order(MOCK_USER_ID, MOCK_SYMBOL, 5)
        db = sqlite_service.get_db()

        # Assertions
        assert result['status'] == 'success'
        assert result['new_balance'] == 9500.0  # 10000 - (5 * 100)

        balance = db.execute("SELECT * FROM balances WHERE user_id = ?", (MOCK_USER_ID,)).fetchone()
        assert balance['cashBalance'] == 9500.0
        assert balance['investedValue'] == 500.0

        holding = db.execute("SELECT * FROM holdings WHERE user_id = ? AND symbol = ?", (MOCK_USER_ID, MOCK_SYMBOL)).fetchone()
        assert holding is not None
        assert holding['quantity'] == 5
        assert holding['average_price'] == 100.0

        transaction = db.execute("SELECT * FROM transactions WHERE user_id = ?", (MOCK_USER_ID,)).fetchone()
        assert transaction is not None
        assert transaction['transaction_type'] == 'BUY'

        mock_check_achievements.assert_called_once()
        mock_log_action.assert_called_once()


@patch('services.market_data.get_current_price')
def test_execute_buy_order_insufficient_funds(mock_get_price, app):
    mock_get_price.return_value = MOCK_PRICE

    with app.app_context():
        # Set user's balance to be low
        db = sqlite_service.get_db()
        db.execute("UPDATE balances SET cashBalance = 400.0 WHERE user_id = ?", (MOCK_USER_ID,))
        db.commit()

        result = trading_service.execute_buy_order(MOCK_USER_ID, MOCK_SYMBOL, 5) # Cost is 500

        # Assertions
        assert result['status'] == 'error'
        assert 'Insufficient funds' in result['message']

        balance = db.execute("SELECT * FROM balances WHERE user_id = ?", (MOCK_USER_ID,)).fetchone()
        assert balance['cashBalance'] == 400.0
        holding = db.execute("SELECT * FROM holdings WHERE user_id = ? AND symbol = ?", (MOCK_USER_ID, MOCK_SYMBOL)).fetchone()
        assert holding is None


@patch('services.trading_service.research_service.log_action')
@patch('services.trading_service.gamification.check_and_award_achievements')
@patch('services.market_data.get_current_price')
def test_execute_sell_order_success(mock_get_price, mock_check_achievements, mock_log_action, app):
    mock_get_price.return_value = 110.0 # Selling for a profit

    with app.app_context():
        db = sqlite_service.get_db()
        # First, give the user something to sell
        db.execute(
            'INSERT INTO holdings (user_id, symbol, quantity, average_price) VALUES (?, ?, ?, ?)',
            (MOCK_USER_ID, MOCK_SYMBOL, 10, 100.0) # 10 shares bought at $100
        )
        db.commit()

        result = trading_service.execute_sell_order(MOCK_USER_ID, MOCK_SYMBOL, 5) # Selling 5 shares

        # Assertions
        assert result['status'] == 'success'
        # Initial cash: 10000. Proceeds: 5 * 110 = 550. New balance: 10550
        assert result['new_balance'] == 10550.0

        balance = db.execute("SELECT * FROM balances WHERE user_id = ?", (MOCK_USER_ID,)).fetchone()
        assert balance['cashBalance'] == 10550.0
        assert balance['totalRealizedPnL'] == 50.0 # (110 - 100) * 5
        assert balance['winningTrades'] == 1

        holding = db.execute("SELECT * FROM holdings WHERE user_id = ? AND symbol = ?", (MOCK_USER_ID, MOCK_SYMBOL)).fetchone()
        assert holding is not None
        assert holding['quantity'] == 5 # 10 - 5 = 5 left

        transaction = db.execute("SELECT * FROM transactions WHERE user_id = ? AND transaction_type = 'SELL'", (MOCK_USER_ID,)).fetchone()
        assert transaction is not None
        assert transaction['quantity'] == 5

        mock_check_achievements.assert_called_once()
        mock_log_action.assert_called_once()