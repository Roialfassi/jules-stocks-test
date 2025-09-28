import pytest
import os
import uuid
from app import create_app
from services import sqlite_service, gamification
from unittest.mock import patch, MagicMock

# --- Fixtures ---

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    db_path = f"test_gamification_{uuid.uuid4()}.sqlite"
    app = create_app('testing')
    app.config.update({"DATABASE": db_path})

    with app.app_context():
        sqlite_service.init_db()
        # Seed with test users in different groups
        db = sqlite_service.get_db()
        users_to_seed = [
            ('user_group1', 'user1@test.com', 1),
            ('user_group2', 'user2@test.com', 2),
            ('user_group3', 'user3@test.com', 3),
            ('user_group4', 'user4@test.com', 4)
        ]
        for user_id, email, group in users_to_seed:
            db.execute(
                "INSERT INTO users (id, username, email, password, researchGroup, participantId, consentGiven, consentTimestamp, consentIP, createdAt, role) VALUES (?, ?, ?, ?, ?, ?, 1, '2023-01-01 12:00:00', '127.0.0.1', '2023-01-01 12:00:00', 'user')",
                (user_id, user_id, email, 'password', group, f'P{group}')
            )
            db.execute("INSERT INTO balances (user_id) VALUES (?)", (user_id,))
            db.execute("INSERT INTO gamification (user_id) VALUES (?)", (user_id,))
        db.commit()

    yield app
    os.unlink(db_path)

# --- Mock Data ---
USER_G1 = "user_group1"
USER_G2 = "user_group2"
USER_G3 = "user_group3"

# --- Tests ---

@patch('services.gamification.award_achievement')
def test_first_trade_achievement(mock_award, app):
    """Test that 'first_trade' achievement is awarded after the first trade."""
    with app.app_context():
        db = sqlite_service.get_db()
        db.execute("UPDATE balances SET totalTrades = 1 WHERE user_id = ?", (USER_G2,))
        db.commit()

        gamification.check_and_award_achievements(USER_G2, 'trade')

    mock_award.assert_called_once_with(USER_G2, 'first_trade', gamification.ACHIEVEMENTS['first_trade'])


def test_no_achievements_for_group_1(app):
    """Test that users in research group 1 do not receive achievements."""
    with app.app_context(), patch('services.gamification.award_achievement') as mock_award:
        db = sqlite_service.get_db()
        db.execute("UPDATE balances SET totalTrades = 1 WHERE user_id = ?", (USER_G1,))
        db.commit()

        gamification.check_and_award_achievements(USER_G1, 'trade')
        mock_award.assert_not_called()


def test_xp_awarded_for_group_3_and_4_not_2(app):
    """Test XP is awarded to groups 3 & 4, but not 2."""
    with app.app_context():
        db = sqlite_service.get_db()

        # Group 2 should not get XP
        gamification.award_xp(USER_G2, 50)
        stats_g2 = db.execute("SELECT totalXP FROM gamification WHERE user_id = ?", (USER_G2,)).fetchone()
        assert stats_g2['totalXP'] == 0

        # Group 3 should get XP
        gamification.award_xp(USER_G3, 50)
        stats_g3 = db.execute("SELECT totalXP FROM gamification WHERE user_id = ?", (USER_G3,)).fetchone()
        assert stats_g3['totalXP'] == 50


def test_level_up_mechanic(app):
    """Test that a user levels up when XP exceeds the threshold."""
    with app.app_context():
        db = sqlite_service.get_db()
        # Set initial state: 80 XP, level 1, 100 to next
        db.execute("UPDATE gamification SET totalXP = 80 WHERE user_id = ?", (USER_G3,))
        db.commit()

        # Award 30 more XP, which should trigger a level up
        gamification.award_xp(USER_G3, 30)

        stats = db.execute("SELECT * FROM gamification WHERE user_id = ?", (USER_G3,)).fetchone()
        assert stats['currentLevel'] == 2
        assert stats['totalXP'] == 10 # 80 + 30 = 110. 110 - 100 = 10.
        assert stats['xpToNextLevel'] == 150 # 100 * 1.5