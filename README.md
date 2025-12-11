# Gamified Trading Platform

A research platform for studying behavioral economics in trading with varying levels of gamification.

## Features

- **Trading Engine**: Real-time stock and crypto trading simulation.
- **Research Groups**: 4 randomized groups (Control, Badges, XP, Leaderboard).
- **Data Collection**: Comprehensive logging of user actions and trades.
- **Backend**: Flask + Firestore (or SQLite for testing).

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure**:
   Copy `.env.example` to `.env`.
   To run locally with SQLite (no Firebase needed):
   ```
   DB_TYPE=sqlite
   ```

3. **Run**:
   ```bash
   python app.py
   ```
   Access at `http://localhost:5000`.

## Testing

To run tests:
```bash
pytest
```

## Project Structure

- `app.py`: Main Flask application.
- `services/`: Business logic (Trading, Auth, Market Data).
- `templates/`: HTML views.
- `static/`: CSS/JS assets.
- `tasks/`: Background jobs.
