"""
Repeat statistics for Step3 Text Features (MVP-0).

Repeat rules (frozen):
- token_counts = Counter(tokens)
- repeated_tokens = sum(max(0, count-1) for each token)  # "extra occurrences"
- repeat_ratio = repeated_tokens / total_tokens (total_tokens==0 -> null)
- repeat_word_ratio = repeat_ratio (MVP same value)
- top_repeated_tokens = top 5 by count desc (count>=2)
"""

from collections import Counter
from typing import Dict, List, Any, Optional


def compute_repeat(tokens: List[str]) -> Dict[str, Any]:
    """
    Compute repeat statistics.
    
    Args:
        tokens: list of tokens
    
    Returns:
        dict with:
        - total_tokens: int
        - repeated_tokens: int
        - repeat_ratio: float|null
        - repeat_word_ratio: float|null (same as repeat_ratio in MVP)
        - top_repeated_tokens: list of {"token": str, "count": int}
    """
    total_tokens = len(tokens)
    
    if total_tokens == 0:
        return {
            "total_tokens": 0,
            "repeated_tokens": 0,
            "repeat_ratio": None,
            "repeat_word_ratio": None,
            "top_repeated_tokens": [],
        }
    
    token_counts = Counter(tokens)
    
    # Count repeated tokens (extra occurrences beyond the first)
    repeated_tokens = sum(max(0, count - 1) for count in token_counts.values())
    
    # Calculate ratios
    repeat_ratio = repeated_tokens / total_tokens
    repeat_word_ratio = repeat_ratio  # MVP: same value
    
    # Get top repeated tokens (count >= 2)
    repeated_items = [(token, count) for token, count in token_counts.items() if count >= 2]
    sorted_repeated = sorted(repeated_items, key=lambda x: (-x[1], x[0]))
    top_repeated_tokens = [{"token": token, "count": count} for token, count in sorted_repeated[:5]]
    
    return {
        "total_tokens": total_tokens,
        "repeated_tokens": repeated_tokens,
        "repeat_ratio": round(repeat_ratio, 4),
        "repeat_word_ratio": round(repeat_word_ratio, 4),
        "top_repeated_tokens": top_repeated_tokens,
    }
