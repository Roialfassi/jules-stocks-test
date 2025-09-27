import os
import sys
from datetime import datetime

# Add the project root to the Python path to allow importing app modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services import firebase_service, market_data, gamification
from config import Config

# --- Configuration ---
# Manually load environment variables for the script
from dotenv import load_dotenv
load_dotenv()

# Initialize Firebase
try:
    firebase_service.initialize_firebase(Config.FIREBASE_CONFIG_PATH)
    db = firebase_service.db
except Exception as e:
    print(f"CRITICAL: Could not initialize Firebase. Ensure your firebase_config.json is correct. Error: {e}")
    sys.exit(1)


def seed_achievements():
    """
    Populates the 'achievements' collection in Firestore with predefined achievements.
    """
    print("Seeding achievements...")
    batch = db.batch()
    achievements_ref = db.collection('achievements')

    for code, data in gamification.ACHIEVEMENTS.items():
        doc_ref = achievements_ref.document(code)
        batch.set(doc_ref, {
            'code': code,
            'name': data['name'],
            'description': data['description'],
            'iconUrl': f'/static/images/{data.get("icon", "default.png")}',
            'pointsAwarded': data['points'],
            'visibleToGroups': data['visibleToGroups'],
            'isRepeatable': data.get('isRepeatable', False),
            'isActive': True
        })

    batch.commit()
    print("✅ Achievements seeded successfully.")

def seed_assets():
    """
    Caches the prices of popular stocks and cryptocurrencies in the 'priceCache' collection.
    """
    print("\nSeeding popular asset prices...")
    batch = db.batch()
    price_cache_ref = db.collection('priceCache')
    popular_assets = market_data.get_popular_assets()

    seeded_count = 0
    for symbol in popular_assets:
        price = market_data.get_current_price(symbol)
        if price is not None:
            doc_ref = price_cache_ref.document(symbol)
            batch.set(doc_ref, {
                'symbol': symbol,
                'price': price,
                'lastUpdated': datetime.utcnow()
            })
            seeded_count += 1
            print(f"  - Cached {symbol} at ${price:.2f}")
        else:
            print(f"  - Could not fetch price for {symbol}")

    batch.commit()
    print(f"✅ {seeded_count}/{len(popular_assets)} popular assets cached successfully.")


def seed_users():
    """
    Creates four test users, one for each research group.
    WARNING: This will create actual users in your Firebase Authentication.
    """
    print("\nSeeding test users...")

    test_users = [
        {'email': 'user.group1@example.com', 'username': 'control_user'},
        {'email': 'user.group2@example.com', 'username': 'badge_user'},
        {'email': 'user.group3@example.com', 'username': 'xp_user'},
        {'email': 'user.group4@example.com', 'username': 'leaderboard_user'},
    ]

    # Override random group assignment for seeding
    original_randint = firebase_service.random.randint

    for i, user_info in enumerate(test_users):
        group = i + 1
        print(f"Creating user for Group {group}...")

        # Temporarily mock randint to assign a specific group
        firebase_service.random.randint = lambda a, b: group

        try:
            firebase_service.create_user_with_group(
                email=user_info['email'],
                password='password123',
                username=user_info['username'],
                consent_given=True,
                ip_address='127.0.0.1'
            )
            print(f"  - Successfully created {user_info['email']} in Group {group}.")
        except ValueError as e:
            # This likely means the user already exists
            print(f"  - INFO: {e}")
        except Exception as e:
            print(f"  - ERROR creating user {user_info['email']}: {e}")

    # Restore the original randint function
    firebase_service.random.randint = original_randint
    print("✅ Test users seeded.")


if __name__ == '__main__':
    print("--- Starting Database Seeding ---")

    # Confirmation prompt
    proceed = input("This script will add data to your Firestore database. Are you sure you want to continue? (y/n): ")
    if proceed.lower() != 'y':
        print("Seeding cancelled.")
        sys.exit(0)

    seed_achievements()
    seed_assets()
    seed_users()

    print("\n--- Database Seeding Complete ---")
    print("You can now run the application with 'python app.py'")
    print("Test user password for all accounts is: password123")