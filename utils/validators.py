import re

def is_valid_email(email):
    """
    Checks if the provided string is a valid email address.
    """
    if not email:
        return False
    # A simple regex for email validation
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

def is_strong_password(password):
    """
    Checks if the password meets strength requirements.
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number."
    return True, "Password is strong."

def is_valid_username(username):
    """
    Checks if the username is valid.
    - 3-20 characters
    - Alphanumeric characters and underscores only
    """
    if not username:
        return False
    return 3 <= len(username) <= 20 and re.match(r'^[a-zA-Z0-9_]+$', username) is not None

def is_valid_quantity(quantity):
    """
    Checks if the trading quantity is a valid positive number.
    """
    try:
        val = float(quantity)
        return val > 0
    except (ValueError, TypeError):
        return False

def is_valid_symbol(symbol):
    """
    Checks if a stock/crypto symbol has a valid format.
    - 1-10 characters
    - Uppercase letters, numbers, and optionally a hyphen.
    """
    if not symbol:
        return False
    return 1 <= len(symbol) <= 10 and re.match(r'^[A-Z0-9-.]+$', symbol.upper()) is not None