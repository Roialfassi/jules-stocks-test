from services.db import db
import datetime

class GamificationService:
    ACHIEVEMENTS = {
        'FIRST_TRADE': {'name': 'First Trade', 'desc': 'Complete your first trade', 'xp': 50},
        'FIRST_PROFIT': {'name': 'First Profit', 'desc': 'Close a trade with profit', 'xp': 100},
        'TRADER_10': {'name': 'Active Trader', 'desc': 'Complete 10 trades', 'xp': 150},
        'FIRST_LOSS': {'name': 'Learning Curve', 'desc': 'Experience your first loss', 'xp': 20},
        'DAILY_LOGIN_3': {'name': 'Dedicated', 'desc': 'Login 3 days in a row', 'xp': 100},
        'GROWTH_5': {'name': 'Growing', 'desc': 'Portfolio up 5%', 'xp': 200},
        'DIVERSIFY_5': {'name': 'Diversified', 'desc': 'Hold 5 different assets', 'xp': 100},
        'EARLY_BIRD': {'name': 'Early Bird', 'desc': 'Trade before 10 AM', 'xp': 50},
        'PROFIT_100': {'name': 'Big Earner', 'desc': 'Make $100 profit in one trade', 'xp': 200},
        'WEEKLY_ACTIVE': {'name': 'Weekly Active', 'desc': 'Active for 7 days', 'xp': 300},
    }

    def get_user_gamification(self, user_id):
        doc = db.collection('gamification').document(user_id).get()
        if doc.exists:
            return doc.to_dict()
        return {
            'totalXP': 0,
            'currentLevel': 1,
            'xpToNextLevel': 100,
            'loginStreak': 0,
            'lastLogin': None
        }

    def award_xp(self, user_id, amount):
        ref = db.collection('gamification').document(user_id)
        doc = ref.get()

        data = {
            'totalXP': 0,
            'currentLevel': 1,
            'xpToNextLevel': 100
        }
        if doc.exists:
            data = doc.to_dict()

        data['totalXP'] += amount
        # Calculate level: Level = 1 + (XP / 100)
        data['currentLevel'] = (data['totalXP'] // 100) + 1
        data['xpToNextLevel'] = 100 - (data['totalXP'] % 100)

        ref.set(data, merge=True)

    def unlock_achievement(self, user_id, achievement_code):
        ach_ref = db.collection('users').document(user_id).collection('achievements').document(achievement_code)
        doc = ach_ref.get()

        if not doc.exists:
            ach_def = self.ACHIEVEMENTS.get(achievement_code)
            if ach_def:
                ach_ref.set({
                    'code': achievement_code,
                    'name': ach_def['name'],
                    'description': ach_def['desc'],
                    'unlockedAt': datetime.datetime.now().isoformat(),
                    'isNew': True
                })
                self.award_xp(user_id, ach_def['xp'])
                return True
        return False

    def check_trade_achievements(self, user_id, trade_result):
        # 1. First Trade / 10 Trades
        stats_doc = db.collection('balances').document(user_id).get()
        if stats_doc.exists:
            stats = stats_doc.to_dict()
            if stats['totalTrades'] == 1:
                self.unlock_achievement(user_id, 'FIRST_TRADE')
            if stats['totalTrades'] == 10:
                self.unlock_achievement(user_id, 'TRADER_10')

        # 2. Early Bird
        now = datetime.datetime.now()
        if 6 <= now.hour < 10:
            self.unlock_achievement(user_id, 'EARLY_BIRD')

        # 3. Diversification
        portfolio_count = len(list(db.collection('users').document(user_id).collection('portfolio').stream()))
        if portfolio_count >= 5:
            self.unlock_achievement(user_id, 'DIVERSIFY_5')

    def check_daily_login(self, user_id):
        # Update streak
        ref = db.collection('gamification').document(user_id)
        data = ref.get().to_dict() or {}

        today = datetime.date.today().isoformat()
        last_login = data.get('lastLogin')
        streak = data.get('loginStreak', 0)

        if last_login:
            last_date = datetime.date.fromisoformat(last_login)
            if last_date == datetime.date.today() - datetime.timedelta(days=1):
                streak += 1
            elif last_date != datetime.date.today():
                streak = 1
        else:
            streak = 1

        if streak >= 3:
            self.unlock_achievement(user_id, 'DAILY_LOGIN_3')

        ref.set({
            'lastLogin': today,
            'loginStreak': streak
        }, merge=True)

    def get_recent_achievements(self, user_id):
        # Get unlocked achievements that are marked as new?
        # Or just last 3
        # For NoSQL this is tricky without index.
        # Just fetch all and sort in memory (small number)
        docs = db.collection('users').document(user_id).collection('achievements').stream()
        achs = [d.to_dict() for d in docs]
        achs.sort(key=lambda x: x['unlockedAt'], reverse=True)
        return achs[:3]

    def get_all_achievements(self, user_id):
        docs = db.collection('users').document(user_id).collection('achievements').stream()
        unlocked = {d.to_dict()['code']: d.to_dict() for d in docs}

        all_achs = []
        for code, meta in self.ACHIEVEMENTS.items():
            ach = meta.copy()
            ach['code'] = code
            if code in unlocked:
                ach['unlocked'] = True
                ach['unlockedAt'] = unlocked[code]['unlockedAt']
            else:
                ach['unlocked'] = False
            all_achs.append(ach)
        return all_achs

    def get_leaderboard(self):
        # Inefficient for large datasets, but ok for research
        # Fetch all balances, sort by totalPortfolioValue
        # Return top 10
        docs = db.collection('balances').stream()
        all_balances = []
        for d in docs:
            b = d.to_dict()
            # Need to attach username. This requires a join.
            # Very inefficient. In real app, store username in balance or mirror portfolio value in user doc.
            # Let's get user doc
            user_doc = db.collection('users').document(d.id).get()
            username = "Unknown"
            if user_doc.exists:
                username = user_doc.to_dict().get('username', 'Unknown')

            all_balances.append({
                'username': username,
                'value': b.get('totalPortfolioValue', 0)
            })

        all_balances.sort(key=lambda x: x['value'], reverse=True)
        # Add rank
        for i, b in enumerate(all_balances):
            b['rank'] = i + 1

        return all_balances[:10]

gamification_service = GamificationService()
