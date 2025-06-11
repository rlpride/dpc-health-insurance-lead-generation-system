"""Validation utilities for data quality checks."""

import re
from typing import Optional
from email_validator import validate_email as email_validate, EmailNotValidError


def validate_email(email: Optional[str]) -> bool:
    """Validate email address format and deliverability."""
    if not email:
        return False
    
    try:
        # Validate and normalize email
        validation = email_validate(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def validate_phone(phone: Optional[str]) -> bool:
    """Validate phone number format (US numbers)."""
    if not phone:
        return False
    
    # Remove common formatting characters
    cleaned = re.sub(r'[\s\-\(\)\+\.]', '', phone)
    
    # Check if it's a valid US phone number (10 or 11 digits)
    if re.match(r'^1?\d{10}$', cleaned):
        return True
    
    return False


def clean_company_name(name: str) -> str:
    """Clean and normalize company name."""
    if not name:
        return ""
    
    # Remove common suffixes
    suffixes = [
        "Inc.", "Inc", "LLC", "L.L.C.", "Corp.", "Corp", 
        "Corporation", "Ltd.", "Ltd", "Limited", "Co.", "Co"
    ]
    
    cleaned = name.strip()
    for suffix in suffixes:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-len(suffix)].strip().rstrip(",")
    
    return cleaned 