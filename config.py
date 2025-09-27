import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    FLASK_APP = os.environ.get('FLASK_APP')
    FLASK_ENV = os.environ.get('FLASK_ENV')

    # Firebase Configuration
    FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY')
    FIREBASE_AUTH_DOMAIN = os.environ.get('FIREBASE_AUTH_DOMAIN')
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET')
    FIREBASE_MESSAGING_SENDER_ID = os.environ.get('FIREBASE_MESSAGING_SENDER_ID')
    FIREBASE_APP_ID = os.environ.get('FIREBASE_APP_ID')
    FIREBASE_DATABASE_URL = f"https://{FIREBASE_PROJECT_ID}.firebaseio.com"

    # Path to Firebase service account key
    FIREBASE_CONFIG_PATH = os.environ.get('FIREBASE_CONFIG_PATH') or 'firebase_config.json'

    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URI = "memory://"

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-different-secret-key'

    # Content Security Policy
    # This is a starting point. It needs to be configured carefully.
    CSP = {
        'default-src': [
            '\'self\'',
            'https://*.firebaseio.com',
            'https://www.googleapis.com',
            'https://cdn.jsdelivr.net' # For Chart.js
        ],
        'script-src': [
            '\'self\'',
            '\'unsafe-inline\'', # Required for some inline scripts, review for production
            'https://www.gstatic.com',
            'https://apis.google.com',
            'https://cdn.jsdelivr.net'
        ],
        'style-src': [
            '\'self\'',
            '\'unsafe-inline\'', # Required for inline styles
            'https://cdnjs.cloudflare.com' # For Font Awesome
        ],
        'font-src': [
            '\'self\'',
            'https://cdnjs.cloudflare.com'
        ],
        'connect-src': [
            '\'self\'',
            'https://*.firebaseio.com',
            'wss://*.firebaseio.com', # For Firestore real-time updates
            'https://securetoken.googleapis.com',
            'https://identitytoolkit.googleapis.com'
        ]
    }

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    # Ensure secure cookies in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Use a more persistent rate limit store in production, e.g., Redis
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI") or "memory://"


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Makes url_for work without a request context
    SERVER_NAME = 'localhost.localdomain'
    DEBUG = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}