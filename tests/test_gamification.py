import pytest
from services.gamification import GamificationService
from services.db import db, Config

Config.DB_TYPE = 'sqlite'

@pytest.fixture
def gamification_service():
    return GamificationService()

@pytest.fixture
def setup_user():
    user_id = 'test_user_game'
    # Clear data
    if hasattr(db, 'delete_collection'):
        db.delete_collection(f'users/{user_id}/achievements')
    db.delete('gamification', user_id)
    return user_id

def test_xp_award(gamification_service, setup_user):
    user_id = setup_user
    gamification_service.award_xp(user_id, 150)

    data = gamification_service.get_user_gamification(user_id)
    assert data['totalXP'] == 150
    # Level = 1 + 150 // 100 = 2
    assert data['currentLevel'] == 2
    # XP to next = 100 - (150 % 100) = 50
    assert data['xpToNextLevel'] == 50

def test_unlock_achievement(gamification_service, setup_user):
    user_id = setup_user
    res = gamification_service.unlock_achievement(user_id, 'FIRST_TRADE')
    assert res == True

    # Try again
    res = gamification_service.unlock_achievement(user_id, 'FIRST_TRADE')
    assert res == False

    achievements = gamification_service.get_all_achievements(user_id)
    found = False
    for a in achievements:
        if a['code'] == 'FIRST_TRADE' and a['unlocked']:
            found = True
            break
    assert found == True
