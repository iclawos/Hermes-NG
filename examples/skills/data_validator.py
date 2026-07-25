"""Data validation skill for Zilli evolution testing."""


def is_email(text: str) -> bool:
    """Check if text looks like an email address."""
    return "@" in text and "." in text.split("@")[-1]


def is_positive_number(value) -> bool:
    """Check if value is a positive number."""
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def clamp(value: float, low: float, high: float) -> float:
    """Clamp value to [low, high]."""
    return max(low, min(high, value))
