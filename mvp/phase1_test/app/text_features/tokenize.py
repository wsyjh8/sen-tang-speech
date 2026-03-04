"""
Tokenization for Step3 Text Features (MVP-0).

Tokenization rules (frozen):
1. Convert text to lowercase
2. Extract tokens using regex:
   - Continuous Chinese characters: [\u4e00-\u9fff]+
   - Continuous English/digits: [a-z0-9]+
3. tokens = all matched sequences (in order)
"""

import re
from typing import List


# Regex pattern for tokenization (frozen)
# Matches: Chinese characters OR English letters/digits
TOKEN_PATTERN = re.compile(r'[\u4e00-\u9fff]+|[a-z0-9]+')


def normalize_text(text: str) -> str:
    """
    Normalize text for tokenization.
    
    Args:
        text: input text
    
    Returns:
        lowercase text
    """
    return text.lower()


def tokenize(text: str) -> List[str]:
    """
    Tokenize text using frozen MVP rules.
    
    Rules:
    1. Convert to lowercase
    2. Extract Chinese character sequences: [\u4e00-\u9fff]+
    3. Extract English/digit sequences: [a-z0-9]+
    
    Args:
        text: input text
    
    Returns:
        list of tokens
    """
    normalized = normalize_text(text)
    tokens = TOKEN_PATTERN.findall(normalized)
    return tokens
