def extract_symptoms(text: str | None, lexicon: dict) -> set[str]:
    """Extract canonical symptom tokens from free-text chief complaint.

    Lowercases the input and checks each lexicon phrase as a substring match.
    Returns set of matched canonical symptom token names.
    """
    if not text or not isinstance(text, str):
        return set()

    text_lower = text.lower().strip()
    if not text_lower:
        return set()

    matched = set()
    for token, phrases in lexicon.items():
        for phrase in phrases:
            if phrase.lower() in text_lower:
                matched.add(token)
                break

    return matched
