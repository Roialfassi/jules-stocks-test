import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from services import trading_service

# --- Fixtures ---

@pytest.fixture
def app():
    """
    Create a new app instance for each test, with Firebase services fully mocked.
    """
    with patch('services.firebase_service.db', MagicMock()) as mock_db:
        with patch('services.firebase_service.auth', MagicMock()):
            app = create_app('testing')
            app.mock_db = mock_db
            yield app

# --- Mock Data ---
MOCK_USER_ID = "test_user_123"
MOCK_SYMBOL = "TEST"
MOCK_PRICE = 100.0

# --- Helper for Mocks ---

def setup_transaction_mocks(db_mock):
    """Sets up common mocks for a Firestore transaction."""
    mock_transaction = MagicMock()
    db_mock.transaction.return_value = mock_transaction

    mock_balance_ref = db_mock.collection('balances').document(MOCK_USER_ID)
    mock_portfolio_ref = db_mock.collection('users').document(MOCK_USER_ID).collection('portfolio').document(MOCK_SYMBOL)

    return mock_transaction, mock_balance_ref, mock_portfolio_ref

# --- Tests ---

@patch('services.trading_service.research_service.log_action')
@patch('services.trading_service.gamification.check_and_award_achievements')
@patch('services.market_data.get_current_price')
@patch('services.market_data.get_asset_details')
def test_execute_buy_order_success(mock_asset_details, mock_get_price, mock_check_achievements, mock_log_action, app):
    mock_get_price.return_value = MOCK_PRICE
    mock_asset_details.return_value = {'name': 'Test Inc.', 'type': 'EQUITY'}
    mock_transaction, mock_balance_ref, mock_portfolio_ref = setup_transaction_mocks(app.mock_db)

    # Mock the transaction's behavior
    @firestore.transactional
    def buy_transaction_mock(transaction, *args, **kwargs):
        # Simulate the transaction logic for the test's purpose
        transaction.get(mock_balance_ref)
        transaction.set(mock_portfolio_ref, {})
        transaction.update(mock_balance_ref, {})
        return 9500.0 # Return the expected new balance

    with patch('services.trading_service.firestore.transactional', return_value=buy_transaction_mock):
        result = trading_service.execute_buy_order(MOCK_USER_ID, MOCK_SYMBOL, 5)

    assert result['status'] == 'success'
    assert result['new_balance'] == 9500.0
    mock_check_achievements.assert_called_once()
    mock_log_action.assert_called_once()

@patch('services.market_data.get_current_price')
def test_execute_buy_order_insufficient_funds(mock_get_price, app):
    mock_get_price.return_value = MOCK_PRICE

    # Simulate the transaction raising a ValueError
    @firestore.transactional
    def buy_transaction_mock_fail(transaction, *args, **kwargs):
        raise ValueError("Insufficient funds")

    with patch('services.trading_service.firestore.transactional', return_value=buy_transaction_mock_fail):
        result = trading_service.execute_buy_order(MOCK_USER_ID, MOCK_SYMBOL, 5)

    assert result['status'] == 'error'
    assert 'Insufficient funds' in result['message']

@patch('services.trading_service.research_service.log_action')
@patch('services.trading_service.gamification.check_and_award_achievements')
@patch('services.market_data.get_current_price')
def test_execute_sell_order_success(mock_get_price, mock_check_achievements, mock_log_action, app):
    mock_get_price.return_value = 110.0

    @firestore.transactional
    def sell_transaction_mock(transaction, *args, **kwargs):
        return 5550.0

    with patch('services.trading_service.firestore.transactional', return_value=sell_transaction_mock):
        result = trading_service.execute_sell_order(MOCK_USER_ID, MOCK_SYMBOL, 5)

    assert result['status'] == 'success'
    assert result['new_balance'] == 5550.0
    mock_check_achievements.assert_called_once()
    mock_log_action.assert_called_once()

# This import is needed for the test to understand the firestore object
from google.cloud import firestore