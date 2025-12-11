import sys
import os
import random
import datetime

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth import auth_service
from services.db import db
from services.trading import trading_service
from services.gamification import gamification_service

def seed():
    print("Seeding database...")

    # 1. Create 4 users, one for each group
    users = []
    groups = [1, 2, 3, 4]

    for i, group in enumerate(groups):
        email = f"user{group}@test.com"
        username = f"UserGroup{group}"
        password = "password123"

        # Check if exists
        # In SQLite/Mock we can check via db. In Firebase we can't easily check auth without admin sdk in a specific way,
        # but auth_service.register_user handles it.

        try:
            print(f"Creating {username} (Group {group})...")
            # We want to force the group. Register user assigns random group.
            # We will update it after creation.

            # Using register_user with consent=True
            uid, user_data = auth_service.register_user(email, password, username, consent=True)

            # Force update group
            db.collection('users').document(uid).update({'researchGroup': group})
            users.append(uid)
            print(f"Created {username} with ID {uid}")

            # Add some initial trades for everyone
            trading_service.execute_trade(uid, 'AAPL', 10, 'BUY') # Spend 1500ish

            # Add some XP for Group 3/4 users to show progress
            if group >= 3:
                gamification_service.award_xp(uid, 150) # Level 2

        except Exception as e:
            print(f"Skipping {username}: {e}")

    print("Seeding complete. Use the following logins:")
    for g in groups:
        print(f"Group {g}: user{g}@test.com / password123")

if __name__ == "__main__":
    seed()
