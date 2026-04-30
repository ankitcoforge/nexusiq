import re

SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
CC_PATTERN = re.compile(r'\b(?:\d{4}[- ]?){3}\d{4}\b')
DOB_PATTERN = re.compile(r'\b(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/\d{4}\b')

BLOCKED_PHRASES = [
    "claim denied", "claim is denied", "we are denying",
    "denial of claim", "denying the claim"
]
DISCLAIMER = "\n\n[DISCLAIMER: This is an AI analysis tool. Final claim decisions must be made by authorized personnel.]"

def mask_pii(text: str) -> str:
    text = SSN_PATTERN.sub("[SSN REDACTED]", text)
    text = EMAIL_PATTERN.sub("[EMAIL REDACTED]", text)
    text = CC_PATTERN.sub("[CC REDACTED]", text)
    text = DOB_PATTERN.sub("[DOB REDACTED]", text)
    return text

def apply_guardrails(text: str) -> str:
    text = mask_pii(text)
    lower = text.lower()
    for phrase in BLOCKED_PHRASES:
        if phrase in lower:
            text += DISCLAIMER
            break
    return text
