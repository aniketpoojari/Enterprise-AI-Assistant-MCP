"""Regex patterns for guardrail detection."""

import re

# --- Prompt Injection Patterns ---

INJECTION_PATTERNS = [
    # Direct override attempts
    re.compile(r'ignore\s+(all\s+)?previous\s+(instructions|prompts|rules)', re.IGNORECASE),
    re.compile(r'disregard\s+(all\s+)?(previous|above|prior)', re.IGNORECASE),
    re.compile(r'forget\s+(all\s+)?(previous|prior|above)', re.IGNORECASE),
    re.compile(r'override\s+(system|previous|all)', re.IGNORECASE),
    re.compile(r'new\s+instructions?\s*:', re.IGNORECASE),
    re.compile(r'system\s*prompt\s*:', re.IGNORECASE),

    # Role-playing / persona switching
    re.compile(r'you\s+are\s+now\s+(?:a\s+)?(?:DAN|evil|unrestricted|jailbroken)', re.IGNORECASE),
    re.compile(r'pretend\s+(?:to\s+be|you\s+are)\s+(?:a\s+)?(?:different|new|unrestricted)', re.IGNORECASE),
    re.compile(r'act\s+as\s+(?:if\s+)?(?:you\s+have\s+no|without)\s+(?:rules|restrictions|limits)', re.IGNORECASE),
    re.compile(r'enter\s+(?:DAN|developer|debug|admin)\s+mode', re.IGNORECASE),

    # Instruction insertion
    re.compile(r'</?(system|instruction|prompt|context)>', re.IGNORECASE),
    re.compile(r'\[INST\]|\[/INST\]|\[SYSTEM\]', re.IGNORECASE),
    re.compile(r'BEGIN\s+(?:SYSTEM|INSTRUCTION|OVERRIDE)', re.IGNORECASE),

    # Context manipulation
    re.compile(r'the\s+above\s+(?:text|instructions?)\s+(?:is|are|was|were)\s+(?:fake|wrong|test)', re.IGNORECASE),
    re.compile(r'actual\s+instructions?\s+(?:are|is)\s*:', re.IGNORECASE),

    # Output manipulation
    re.compile(r'(?:print|output|return|say)\s+(?:only|exactly|just)\s*["\']', re.IGNORECASE),
]

# --- PII Patterns ---

PII_PATTERNS = {
    "ssn": re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'),
    "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    "email_input": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "phone_input": re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
}

# --- Off-Topic Patterns ---

OFF_TOPIC_PATTERNS = [
    re.compile(r'write\s+(?:me\s+)?(?:a\s+)?(?:poem|song|story|essay|code|script)', re.IGNORECASE),
    re.compile(r'(?:translate|convert)\s+(?:this|the\s+following)\s+(?:to|into)', re.IGNORECASE),
    re.compile(r'(?:tell|give)\s+me\s+a\s+(?:joke|riddle|fun\s+fact)', re.IGNORECASE),
    re.compile(r'what\s+(?:is|are)\s+(?:the\s+)?(?:meaning\s+of\s+life|your\s+name|you)', re.IGNORECASE),
    re.compile(r'(?:hack|exploit|attack|phish|scam|malware)', re.IGNORECASE),
]

# --- SQL Injection Patterns (for output validation) ---

SQL_INJECTION_PATTERNS = [
    re.compile(r";\s*(?:DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE|EXEC)", re.IGNORECASE),
    re.compile(r"UNION\s+(?:ALL\s+)?SELECT", re.IGNORECASE),
    re.compile(r"INTO\s+(?:OUTFILE|DUMPFILE)", re.IGNORECASE),
    re.compile(r"LOAD_FILE\s*\(", re.IGNORECASE),
    re.compile(r"xp_cmdshell", re.IGNORECASE),
    re.compile(r"(?:CHAR|CHR|NCHAR)\s*\(\s*\d+\s*\)", re.IGNORECASE),
]

# --- Data Masking Patterns ---

DATA_MASKING_PATTERNS = {
    "email": re.compile(r'\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'),
    "phone": re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
}
