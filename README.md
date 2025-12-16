# Gamified Trading Platform

A research platform for studying behavioral economics in trading with varying levels of gamification.

## Features

- **Trading Engine**: Real-time stock and crypto trading simulation.
- **Research Groups**: 4 randomized groups (Control, Badges, XP, Leaderboard).
- **Data Collection**: Comprehensive logging of user actions and trades.
- **Backend**: Flask + Firestore (or SQLite for testing).

## Quick Start (Local Development)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure**:
   Copy `.env.example` to `.env`.
   To run locally with SQLite (no Firebase needed):
   ```
   DB_TYPE=sqlite
   # FIREBASE_CONFIG_PATH can remain as is for sqlite mode
   ```

3. **Seed Test Users (Crucial for Testing Levels)**:
   This script creates 4 users, one for each research group (Level 1-4).
   ```bash
   python scripts/seed_data.py
   ```

   Logins created:
   - **Group 1 (Control)**: user1@test.com / password123
   - **Group 2 (Badges)**: user2@test.com / password123
   - **Group 3 (XP/Progress)**: user3@test.com / password123
   - **Group 4 (Leaderboard)**: user4@test.com / password123

4. **Run**:
   ```bash
   python app.py
   ```
   Access at `http://localhost:5000`.

## Testing Different Levels

To verify the "Level 2" (Badges) and "Level 3" (XP) features:

1.  **Log in as `user2@test.com` (Group 2 - Badges)**:
    - Go to **Dashboard**: You should see "Recent Achievements".
    - Go to **Profile**: You should see a grid of Badges (locked/unlocked).
    - **Trigger a Badge**: Buy 10 units of AAPL. Sell them. This should trigger `FIRST_TRADE` and potentially `FIRST_PROFIT`. Check Profile again.

2.  **Log in as `user3@test.com` (Group 3 - XP)**:
    - Look at the **Header**: You should see a Progress Bar and Level indicator (HTML5).
    - **Earn XP**: Make a trade. Watch the XP counter increase in the header (refresh may be required depending on implementation, or it updates on page load).

3.  **Log in as `user4@test.com` (Group 4 - Leaderboard)**:
    - Go to **Dashboard**: You should see the Leaderboard widget on the right.

## Running Tests

To run automated backend tests:
```bash
pytest
```

## Project Structure

- `app.py`: Main Flask application.
- `services/`: Business logic (Trading, Auth, Market Data, Gamification).
- `templates/`: HTML views (Jinja2).
- `static/`: CSS/JS assets.
- `scripts/`: Helper scripts like `seed_data.py`.
