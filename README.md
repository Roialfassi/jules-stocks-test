# Gamified Trading Platform

## 1. Project Overview
This project is a web-based trading simulator for academic research. Users receive $10,000 in virtual money to trade stocks and cryptocurrencies. The platform is designed to facilitate behavioral research by randomly assigning users to one of four groups with varying levels of gamification. This allows researchers to compare the effects of different gamified elements on trading behavior.

The platform is built with a focus on simplicity, security, and data integrity, making it a suitable tool for academic studies.

## 2. Tech Stack
- **Backend**: Flask 3.0+
- **Database**: Firebase Firestore (NoSQL)
- **Authentication**: Firebase Auth
- **Storage**: Firebase Storage (for data exports)
- **Task Queue**: APScheduler for background tasks
- **API Integration**: `yfinance` for stock and crypto data
- **Frontend**: Vanilla HTML5, CSS3, and ES6+ JavaScript
- **Charts**: Chart.js (via CDN)
- **Icons**: Font Awesome (via CDN)

## 3. Prerequisites
- Python 3.10+
- A Google Firebase account
- `git` for cloning the repository

## 4. Firebase Setup
Before running the application, you need to set up a Firebase project.

1.  **Create a Firebase Project**: Go to the [Firebase Console](https://console.firebase.google.com/) and create a new project.
2.  **Enable Authentication**: In your Firebase project, go to the "Authentication" section and enable the "Email/Password" sign-in method.
3.  **Create Firestore Database**: Go to the "Firestore Database" section and create a new database. Start in **test mode** for initial setup, but be sure to secure it with proper security rules for production.
4.  **Get Service Account Key**:
    *   In your Firebase project settings, go to the "Service accounts" tab.
    *   Click "Generate new private key" to download a JSON file with your service account credentials.
    *   **Rename this file to `firebase_config.json`** and place it in the root directory of this project. This file is listed in `.gitignore` and should never be committed to version control.
5.  **Get Web App Credentials**:
    *   In your Firebase project settings, go to the "General" tab.
    *   Under "Your apps", click the web icon (`</>`) to create a new web app.
    *   After creating the app, Firebase will provide you with a `firebaseConfig` object. You will need these values for your `.env` file.

## 5. Quick Start Guide

```bash
# 1. Clone the repository
git clone https://github.com/your-username/gamified-trading-platform.git
cd gamified-trading-platform

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env

# 5. Edit the .env file with your Firebase web app credentials.
#    Fill in the following variables from your Firebase project's web app config:
#    - FIREBASE_API_KEY
#    - FIREBASE_AUTH_DOMAIN
#    - FIREBASE_PROJECT_ID
#    - FIREBASE_STORAGE_BUCKET
#    - FIREBASE_MESSAGING_SENDER_ID
#    - FIREBASE_APP_ID

# 6. Place your `firebase_config.json` in the root directory.

# 7. Run the application
python app.py

# 8. Access the platform at http://127.0.0.1:5000
```

## 6. Environment Variables
Your `.env` file should contain the following variables. `FLASK_SECRET_KEY` is for session security, and the `FIREBASE_*` variables are from your Firebase web app configuration.

-   `FLASK_APP=app.py`
-   `FLASK_ENV=development`
-   `SECRET_KEY`: A long, random string for Flask session security.
-   `FIREBASE_API_KEY`: Your Firebase project's web API key.
-   `FIREBASE_AUTH_DOMAIN`: Your Firebase project's auth domain.
-   `FIREBASE_PROJECT_ID`: Your Firebase project ID.
-   `FIREBASE_STORAGE_BUCKET`: Your Firebase storage bucket URL.
-   `FIREBASE_MESSAGING_SENDER_ID`: Your Firebase messaging sender ID.
-   `FIREBASE_APP_ID`: Your Firebase web app ID.

## 7. Database Initialization
To seed the database with initial data (e.g., achievements, asset lists, and test users), run the seeding script:

```bash
python seed_data.py
```
This will:
- Populate the `achievements` collection.
- Cache popular stock and cryptocurrency symbols in the `priceCache`.
- Create four test users, one for each research group.

## 8. Creating an Admin User
To access the admin dashboard, you need to set a user's role to `admin` in Firestore.

1.  Register a new user through the web interface.
2.  Go to your Firebase Console -> Firestore Database.
3.  Navigate to the `users` collection and find the document for your registered user.
4.  Add a new field to the document:
    -   **Field name**: `role`
    -   **Type**: `string`
    -   **Value**: `admin`
5.  Log out and log back in. You should now have access to the `/admin` route.

## 9. Project Structure
```
gamified-trading-platform/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── firebase_config.json        # Service account key (gitignored)
├── static/
│   ├── css/                    # Stylesheets
│   ├── js/                     # JavaScript files
│   └── images/                 # Icons and badges
├── templates/                  # HTML templates
├── services/                   # Backend services (Firebase, trading, etc.)
├── utils/                      # Utilities (decorators, validators)
├── tasks/                      # APScheduler background tasks
├── tests/                      # Pytest tests
├── README.md                   # This file
└── DEPLOYMENT.md               # Deployment guide
```

## 10. Research Groups
The platform is designed to study the impact of gamification on trading behavior. Upon registration, users are randomly assigned to one of four groups:

-   **Group 1 (Control)**: The baseline experience with no gamification elements. The interface is clean and functional, focused purely on trading.
-   **Group 2 (Basic Badges)**: This group sees a set of 10 achievement badges they can earn for specific trading milestones (e.g., "First Trade," "First Profit").
-   **Group 3 (Progress + XP)**: Includes all features from Group 2, plus an Experience Points (XP) and leveling system. Users earn XP for trades and achievements, providing a sense of progression.
-   **Group 4 (Social + Leaderboard)**: Includes all features from Group 3, plus a competitive leaderboard showing the top 10 users by portfolio value. This introduces a social comparison element.

The frontend dynamically adjusts the UI based on the user's assigned group using `data-group` attributes in the HTML.

## 11. Troubleshooting
-   **Firebase Authentication Errors**:
    -   Ensure your `.env` file has the correct Firebase web app credentials.
    -   Check that you have enabled "Email/Password" authentication in the Firebase console.
    -   Make sure the `firebase_config.json` service account file is valid and in the root directory.
-   **`yfinance` Data Issues**:
    -   The `yfinance` library relies on Yahoo Finance APIs, which can sometimes be unreliable or change. If you encounter data errors, check the [yfinance GitHub page](https://github.com/ranaroussi/yfinance) for known issues.
-   **500 Internal Server Error**:
    -   Check the Flask console output for detailed error messages. This is often caused by missing or incorrect environment variables or a problem connecting to Firebase.
-   **Dependencies Not Installing**:
    -   Ensure you are in an active virtual environment before running `pip install -r requirements.txt`.