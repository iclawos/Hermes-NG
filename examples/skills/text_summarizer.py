"""Text summarization skill for Zilli evolution testing."""


def summarize(text: str, max_sentences: int = 3) -> str:
    """Summarize text by extracting the first N sentences."""
    sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    return ". ".join(sentences[:max_sentences]) + "."


def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def truncate(text: str, max_chars: int = 200) -> str:
    """Truncate text to max chars with ellipsis."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3] + "..."
