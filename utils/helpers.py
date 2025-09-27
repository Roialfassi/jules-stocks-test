"""
This file contains miscellaneous helper functions that can be used across the application.
"""

def format_currency(value):
    """
    Formats a numeric value as a currency string (e.g., $1,234.56).
    """
    if value is None:
        return "N/A"
    try:
        return f"${value:,.2f}"
    except (ValueError, TypeError):
        return str(value)

def format_percentage(value):
    """
    Formats a numeric value as a percentage string (e.g., 5.25%).
    """
    if value is None:
        return "N/A"
    try:
        return f"{value:.2%}"
    except (ValueError, TypeError):
        return str(value)

def format_timestamp(ts):
    """
    Formats a datetime object into a user-friendly string.
    """
    if ts is None:
        return "N/A"
    try:
        # Assuming ts is a datetime object
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    except AttributeError:
        return str(ts)