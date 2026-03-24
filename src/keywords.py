import re

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "for",
    "of",
    "in",
    "on",
    "at",
    "is",
    "are",
    "it",
    "this",
    "that",
    "with",
    "from",
    "as",
    "by",
    "be",
    "was",
    "were",
    "will",
    "just",
    "not",
    "you",
    "your",
    "our",
    "we",
}

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]{2,}")


def extract_keywords(text: str, max_keywords: int = 8) -> list[str]:
    text = (text or "").lower()
    tokens = TOKEN_RE.findall(text)

    cleaned = []
    for t in tokens:
        if t.startswith("http"):
            continue
        if t in STOPWORDS:
            continue
        if t.isdigit():
            continue
        cleaned.append(t)

    # frequency ranking
    freq: dict[str, int] = {}
    for t in cleaned:
        freq[t] = freq.get(t, 0) + 1

    ranked = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [k for k, _ in ranked[:max_keywords]]
