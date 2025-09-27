import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from services import gamification

# --- Fixtures ---

@pytest.fixture
def app():
    """
    Create a new app instance for each test, with Firebase services fully mocked.
    """
    with patch('services.firebase_service.db', MagicMock()), \
         patch('services.firebase_service.auth', MagicMock()), \
         patch('services.firebase_service.get_user') as mock_get_user:

        app = create_app('testing')
        app.mock_get_user = mock_get_user
        yield app

# --- Mock Data ---
MOCK_USER_ID = "test_user_gamified"

def get_mock_user_state(
    total_trades=0, winning_trades=0, losing_trades=0,
    portfolio_value=10000, portfolio_items=0,
    achievements={}, research_group=2
):
    """Helper function to create a mock state for achievement checks."""
    return {
        'user': {'researchGroup': research_group},
        'balances': {
            'totalTrades': total_trades, 'winningTrades': winning_trades,
            'losingTrades': losing_trades, 'totalPortfolioValue': portfolio_value
        },
        'portfolio': [{} for _ in range(portfolio_items)],
        'achievements': achievements,
        'gamification': {}
    }

# --- Tests ---

@patch('services.gamification.award_achievement')
@patch('services.gamification.get_user_state_for_achievements')
def test_first_trade_achievement(mock_get_state, mock_award, app):
    """Test that the 'first_trade' achievement is awarded correctly."""
    mock_get_state.return_value = get_mock_user_state(total_trades=1)

    with app.app_context():
        gamification.check_and_award_achievements(MOCK_USER_ID, 'trade')

    mock_award.assert_called_once_with(MOCK_USER_ID, 'first_trade', gamification.ACHIEVEMENTS['first_trade'])

@patch('services.gamification.award_achievement')
@patch('services.gamification.get_user_state_for_achievements')
def test_no_achievements_for_group_1(mock_get_state, mock_award, app):
    """Test that users in research group 1 do not receive achievements."""
    mock_get_state.return_value = get_mock_user_state(total_trades=1, research_group=1)

    with app.app_context():
        gamification.check_and_award_achievements(MOCK_USER_ID, 'trade')

    mock_award.assert_not_called()

@patch('services.gamification.firebase_service.db')
def test_xp_awarded_for_group_3_and_4(mock_db, app):
    """Test that XP is awarded to users in groups 3 and 4, but not 2."""
    mock_gamification_ref = mock_db.collection().document()
    mock_gamification_doc = MagicMock(exists=True, to_dict=lambda: {'totalXP': 50, 'currentLevel': 1, 'xpToNextLevel': 100})
    mock_gamification_ref.get.return_value = mock_gamification_doc

    # Test Group 3
    app.mock_get_user.return_value = {'researchGroup': 3}
    with app.app_context():
        gamification.award_xp(MOCK_USER_ID, 20)
    mock_gamification_ref.update.assert_called_once_with({'totalXP': 70, 'currentLevel': 1, 'xpToNextLevel': 100})
    mock_gamification_ref.update.reset_mock()

    # Test Group 2 (should not get XP)
    app.mock_get_user.return_value = {'researchGroup': 2}
    with app.app_context():
        gamification.award_xp(MOCK_USER_ID, 20)
    mock_gamification_ref.update.assert_not_called()

@patch('services.gamification.firebase_service.db')
def test_level_up_mechanic(mock_db, app):
    """Test that a user levels up when their XP exceeds the threshold."""
    app.mock_get_user.return_value = {'researchGroup': 3}
    mock_gamification_ref = mock_db.collection().document()
    mock_gamification_doc = MagicMock(exists=True, to_dict=lambda: {'totalXP': 80, 'currentLevel': 1, 'xpToNextLevel': 100})
    mock_gamification_ref.get.return_value = mock_gamification_doc

    with app.app_context():
        gamification.award_xp(MOCK_USER_ID, 30)

    mock_gamification_ref.update.assert_called_once_with({
        'totalXP': 10, 'currentLevel': 2, 'xpToNextLevel': 150
    })