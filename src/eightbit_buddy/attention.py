from __future__ import annotations

import re

_EXPLICIT_INPUT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in (
        r"\b(?:i|we) need your (?:input|approval|confirmation|choice|decision)\b",
        r"\b(?:this|that) requires your (?:input|approval|confirmation)\b",
        r"\bplease (?:provide|choose|select|confirm|approve|answer)\b",
        r"\bwaiting for your (?:input|approval|confirmation|response)\b",
        (
            r"\b(?:which|what) "
            r"(?:option|approach|path|value|account|environment|framework)\b[^?]*\?\s*$"
        ),
        (
            r"\b(?:can|could|would) you "
            r"(?:provide|choose|select|confirm|approve|clarify|share)\b[^?]*\?\s*$"
        ),
        r"\bdo you want me to\b[^?]*\?\s*$",
        r"\bshall i\b[^?]*\?\s*$",
    )
)


def needs_user_attention(message: str) -> bool:
    """Conservatively identify a final response that cannot continue without the user."""
    text = " ".join(message.split())
    if not text:
        return False
    return any(pattern.search(text) for pattern in _EXPLICIT_INPUT_PATTERNS)
