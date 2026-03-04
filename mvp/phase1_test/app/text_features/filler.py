"""
Filler word detection for Step3 Text Features (MVP-0).

Filler word list (frozen):
- Single characters: ["嗯","啊","呃"]
- Common filler phrases: ["就是","然后","那个","其实","我觉得","你知道","怎么说呢"]

Counting rules:
- Count phrase fillers first
- Then count single-character fillers (avoid double counting same position)
"""

from typing import Tuple, Dict, List, Any

# Filler phrases (multi-character) - frozen MVP list
FILLER_PHRASES = [
    "就是",
    "然后",
    "那个",
    "其实",
    "我觉得",
    "你知道",
    "怎么说呢",
]

# Filler words (single character) - frozen MVP list
FILLER_WORDS = [
    "嗯",
    "啊",
    "呃",
]

# All fillers combined
ALL_FILLERS = FILLER_PHRASES + FILLER_WORDS


def count_fillers(text: str) -> Tuple[int, Dict[str, int]]:
    """
    Count filler words/phrases in text.
    
    Rules:
    1. Count phrase fillers first
    2. Replace matched phrases with placeholder to avoid double counting
    3. Count single-character fillers
    
    Args:
        text: input text
    
    Returns:
        (total_count, breakdown dict {filler: count})
    """
    breakdown: Dict[str, int] = {}
    total_count = 0
    
    # Work with a copy of text for replacement
    remaining_text = text
    
    # Sort phrases by length (longest first) to avoid partial matches
    sorted_phrases = sorted(FILLER_PHRASES, key=len, reverse=True)
    
    # Count phrase fillers first
    for phrase in sorted_phrases:
        count = remaining_text.count(phrase)
        if count > 0:
            breakdown[phrase] = breakdown.get(phrase, 0) + count
            total_count += count
            # Replace with placeholder to avoid double counting
            remaining_text = remaining_text.replace(phrase, "___")
    
    # Count single-character fillers
    for word in FILLER_WORDS:
        count = remaining_text.count(word)
        if count > 0:
            breakdown[word] = breakdown.get(word, 0) + count
            total_count += count
    
    return total_count, breakdown


def top_k_breakdown(breakdown: Dict[str, int], k: int = 5) -> List[Dict[str, Any]]:
    """
    Get top K filler tokens by count.
    
    Args:
        breakdown: dict {filler: count}
        k: number of top items (default 5)
    
    Returns:
        list of {"token": str, "count": int} sorted by count desc
    """
    sorted_items = sorted(breakdown.items(), key=lambda x: (-x[1], x[0]))
    return [{"token": token, "count": count} for token, count in sorted_items[:k]]
