"""Text redaction for privacy protection."""

import re


def redact(text: str) -> str:
    """
    Redact sensitive information from text.
    
    Redacts:
    - Email addresses -> [[REDACTED]]
    - Phone numbers -> [[REDACTED]]
    - Consecutive digits >= 6 -> [[REDACTED]]
    
    Args:
        text: Input text to redact.
    
    Returns:
        Redacted text.
    """
    # Redact email addresses
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[[REDACTED]]', text)
    
    # Redact phone numbers (various formats)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[[REDACTED]]', text)
    text = re.sub(r'\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}\b', '[[REDACTED]]', text)
    
    # Redact consecutive digits >= 6
    text = re.sub(r'\b\d{6,}\b', '[[REDACTED]]', text)
    
    return text
