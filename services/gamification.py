from datetime import datetime, timedelta
from services import firebase_service

# --- Achievement Definitions ---
# Each achievement has a code, name, description, points, and a trigger function.
ACHIEVEMENTS = {
    'first_trade': {
        'name': 'First Trade',
        'description': 'Execute your first trade.',
        'icon': 'first_trade.png',
        'points': 20,
        'visibleToGroups': [2, 3, 4],
        'trigger': lambda user_data: user_data['balances']['totalTrades'] >= 1
    },
    'first_profit': {
        'name': 'First Profit',
        'description': 'Make your first profitable trade.',
        'icon': 'first_profit.png',
        'points': 50,
        'visibleToGroups': [2, 3, 4],
        'trigger': lambda user_data: user_data['balances']['winningTrades'] >= 1
    },
    'ten_trades': {
        'name': '10 Trades Milestone',
        'description': 'Execute a total of 10 trades.',
        'icon': 'ten_trades.png',
        'points': 100,
        'visibleToGroups': [2, 3, 4],
        'trigger': lambda user_data: user_data['balances']['totalTrades'] >= 10
    },
    'first_loss': {
        'name': 'Learning Experience',
        'description': 'Make your first trade that results in a loss. Every expert was once a beginner.',
        'icon': 'first_loss.png',
        'points': 10,
        'visibleToGroups': [2, 3, 4],
        'trigger': lambda user_data: user_data['balances']['losingTrades'] >= 1
    },
    'daily_login_3': {
        'name': 'Consistent Investor',
        'description': 'Log in for 3 consecutive days.',
        'icon': 'daily_login.png',
        'points': 30,
        'visibleToGroups': [2, 3, 4],
        'trigger': lambda user_data: user_data['gamification'].get('loginStreak', 0) >= 3
    },
    'portfolio_growth_5': {
        'name': 'Growing Strong',
        'description': 'Increase your total portfolio value by 5% from your initial deposit.',
        'icon': 'portfolio_growth.png',
        'points': 150,
        'visibleToGroups': [2, 3, 4],
        'trigger': lambda user_data: user_data['balances']['totalPortfolioValue'] >= 10000 * 1.05
    },
    'diversification_5': {
        'name': 'Diversified',
        'description': 'Hold at least 5 different assets at the same time.',
        'icon': 'diversification.png',
        'points': 75,
        'visibleToGroups': [2, 3, 4],
        'trigger': lambda user_data: len(user_data['portfolio']) >= 5
    },
    'early_bird': {
        'name': 'Early Bird',
        'description': 'Execute a trade before 10 AM local time.',
        'icon': 'early_bird.png',
        'points': 20,
        'visibleToGroups': [2, 3, 4],
        'isRepeatable': False, # This is a one-time check based on the trade time
        'trigger': lambda user_data, trade_time=None: trade_time and trade_time.hour < 10
    },
    'profit_100': {
        'name': '$100 Profit',
        'description': 'Achieve a total realized profit of $100.',
        'icon': 'profit_100.png',
        'points': 200,
        'visibleToGroups': [2, 3, 4],
        'trigger': lambda user_data: user_data['balances']['totalRealizedPnL'] >= 100
    },
    'active_week': {
        'name': 'Active Week',
        'description': 'Log in every day for 7 consecutive days.',
        'icon': 'active_week.png',
        'points': 100,
        'visibleToGroups': [2, 3, 4],
        'trigger': lambda user_data: user_data['gamification'].get('loginStreak', 0) >= 7
    }
}

def award_xp(user_id, points):
    """
    Awards XP to a user and handles leveling up.
    Applicable only to users in groups 3 and 4.
    """
    db = firebase_service.db
    gamification_ref = db.collection('gamification').document(user_id)

    user = firebase_service.get_user(user_id)
    if user.get('researchGroup') not in [3, 4]:
        return

    gamification_doc = gamification_ref.get()
    if gamification_doc.exists:
        stats = gamification_doc.to_dict()
        current_xp = stats.get('totalXP', 0)
        current_level = stats.get('currentLevel', 1)
        xp_to_next = stats.get('xpToNextLevel', 100)

        new_xp = current_xp + points

        while new_xp >= xp_to_next:
            current_level += 1
            new_xp -= xp_to_next
            xp_to_next = int(xp_to_next * 1.5) # Increase XP requirement for next level

        gamification_ref.update({
            'totalXP': new_xp,
            'currentLevel': current_level,
            'xpToNextLevel': xp_to_next
        })

def check_and_award_achievements(user_id, event_type, event_data=None):
    """
    Checks all relevant achievements for a user based on an event.
    """
    db = firebase_service.db
    user_data = get_user_state_for_achievements(user_id)

    if user_data['user'].get('researchGroup') < 2:
        return # No achievements for group 1

    for code, achievement in ACHIEVEMENTS.items():
        # Skip achievements not visible to the user's group
        if user_data['user']['researchGroup'] not in achievement['visibleToGroups']:
            continue

        # Check if user already has this achievement
        if code in user_data['achievements']:
            continue

        # Check trigger condition
        try:
            if event_type == 'trade' and code == 'early_bird':
                # Special handling for time-based achievement
                if achievement['trigger'](user_data, trade_time=datetime.now()):
                    award_achievement(user_id, code, achievement)
            elif achievement['trigger'](user_data):
                award_achievement(user_id, code, achievement)
        except Exception as e:
            print(f"Error checking achievement {code} for user {user_id}: {e}")


def award_achievement(user_id, code, achievement_data):
    """
    Awards a specific achievement to a user and grants XP.
    """
    print(f"Awarding achievement '{code}' to user {user_id}")
    db = firebase_service.db
    achievement_ref = db.collection('users').document(user_id).collection('achievements').document(code)

    achievement_ref.set({
        'code': code,
        'name': achievement_data['name'],
        'isCompleted': True,
        'completedAt': datetime.utcnow()
    })

    # Award XP if the user is in the right group
    award_xp(user_id, achievement_data['points'])


def get_user_state_for_achievements(user_id):
    """
    Gathers all necessary user data from different Firestore collections
    to evaluate achievement conditions.
    """
    db = firebase_service.db

    user_doc = db.collection('users').document(user_id).get()
    balance_doc = db.collection('balances').document(user_id).get()
    gamification_doc = db.collection('gamification').document(user_id).get()

    portfolio_docs = db.collection('users').document(user_id).collection('portfolio').stream()
    achievements_docs = db.collection('users').document(user_id).collection('achievements').stream()

    return {
        'user': user_doc.to_dict() if user_doc.exists else {},
        'balances': balance_doc.to_dict() if balance_doc.exists else {},
        'gamification': gamification_doc.to_dict() if gamification_doc.exists else {},
        'portfolio': [doc.to_dict() for doc in portfolio_docs],
        'achievements': {doc.id: doc.to_dict() for doc in achievements_docs}
    }

def get_leaderboard():
    """
    Gets the top 10 users by total portfolio value.
    This can be an expensive query. For production, this data should be
    aggregated and cached periodically by a background job.
    """
    db = firebase_service.db
    users_ref = db.collection('users')
    balances_ref = db.collection('balances').order_by('totalPortfolioValue', direction='DESCENDING').limit(10)

    leaderboard = []
    for balance_doc in balances_ref.stream():
        user_id = balance_doc.id
        user_doc = users_ref.document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            balance_data = balance_doc.to_dict()
            leaderboard.append({
                'username': user_data.get('username', 'Anonymous'),
                'portfolioValue': balance_data.get('totalPortfolioValue', 0)
            })
    return leaderboard