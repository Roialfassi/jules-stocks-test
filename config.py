import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DB_TYPE = os.getenv('DB_TYPE', 'sqlite')
    FIREBASE_CONFIG_PATH = os.getenv('FIREBASE_CONFIG_PATH', 'firebase_config.json')
    FIREBASE_API_KEY = os.getenv('FIREBASE_API_KEY')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@example.com')

    # Session config
    SESSION_COOKIE_SECURE = True if os.getenv('FLASK_ENV') == 'production' else False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Scheduler
    SCHEDULER_API_ENABLED = True
