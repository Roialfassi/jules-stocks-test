from datetime import datetime, timezone, timedelta
from services import sqlite_service

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
    db = sqlite_service.get_db()
    user = sqlite_service.get_user_by_id(user_id)
    if not user or user['researchGroup'] not in [3, 4]:
        return

    stats_row = db.execute('SELECT * FROM gamification WHERE user_id = ?', (user_id,)).fetchone()
    if stats_row:
        stats = dict(stats_row)
        current_xp = stats.get('totalXP', 0)
        current_level = stats.get('currentLevel', 1)
        xp_to_next = stats.get('xpToNextLevel', 100)

        new_xp = current_xp + points

        while new_xp >= xp_to_next:
            current_level += 1
            new_xp -= xp_to_next
            xp_to_next = int(xp_to_next * 1.5)

        db.execute(
            'UPDATE gamification SET totalXP = ?, currentLevel = ?, xpToNextLevel = ? WHERE user_id = ?',
            (new_xp, current_level, xp_to_next, user_id)
        )
        db.commit()

def check_and_award_achievements(user_id, event_type, event_data=None):
    """
    Checks all relevant achievements for a user based on an event.
    """
    user_data = get_user_state_for_achievements(user_id)
    if not user_data or not user_data.get('user'):
        return

    if user_data['user'].get('researchGroup', 1) < 2:
        return # No achievements for group 1

    for code, achievement in ACHIEVEMENTS.items():
        if user_data['user']['researchGroup'] not in achievement.get('visibleToGroups', []):
            continue

        if code in user_data['achievements']:
            continue

        try:
            triggered = False
            if event_type == 'trade' and code == 'early_bird':
                if achievement['trigger'](user_data, trade_time=datetime.now(timezone.utc)):
                    triggered = True
            elif achievement['trigger'](user_data):
                triggered = True

            if triggered:
                award_achievement(user_id, code, achievement)
        except Exception as e:
            print(f"Error checking achievement {code} for user {user_id}: {e}")


def award_achievement(user_id, code, achievement_data):
    """
    Awards a specific achievement to a user and grants XP.
    """
    print(f"Awarding achievement '{code}' to user {user_id}")
    db = sqlite_service.get_db()

    db.execute(
        'INSERT INTO achievements (user_id, achievement_id, completedAt) VALUES (?, ?, ?)',
        (user_id, code, datetime.now(timezone.utc))
    )
    db.commit()
    award_xp(user_id, achievement_data.get('points', 0))


def get_user_state_for_achievements(user_id):
    """
    Gathers all necessary user data from different SQLite tables
    to evaluate achievement conditions.
    """
    db = sqlite_service.get_db()

    user_row = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    balance_row = db.execute('SELECT * FROM balances WHERE user_id = ?', (user_id,)).fetchone()
    gamification_row = db.execute('SELECT * FROM gamification WHERE user_id = ?', (user_id,)).fetchone()
    holdings_rows = db.execute('SELECT * FROM holdings WHERE user_id = ?', (user_id,)).fetchall()
    achievements_rows = db.execute('SELECT * FROM achievements WHERE user_id = ?', (user_id,)).fetchall()

    return {
        'user': dict(user_row) if user_row else {},
        'balances': dict(balance_row) if balance_row else {},
        'gamification': dict(gamification_row) if gamification_row else {},
        'portfolio': [dict(row) for row in holdings_rows],
        'achievements': {row['achievement_id']: dict(row) for row in achievements_rows}
    }

def get_leaderboard():
    """
    Gets the top 10 users by total portfolio value from SQLite.
    """
    db = sqlite_service.get_db()
    query = """
        SELECT u.username, b.totalPortfolioValue
        FROM balances b
        JOIN users u ON b.user_id = u.id
        ORDER BY b.totalPortfolioValue DESC
        LIMIT 10
    """
    leaderboard_rows = db.execute(query).fetchall()

    leaderboard = [
        {'username': row['username'], 'portfolioValue': row['totalPortfolioValue']}
        for row in leaderboard_rows
    ]
    return leaderboard