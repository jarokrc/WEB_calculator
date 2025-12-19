from datetime import date


def generate_variable_symbol() -> str:
    """
    Generate a simple variable symbol based on today's date (yyyymmdd).
    Kept standalone for future customization.
    """
    return date.today().strftime("%Y%m%d")
