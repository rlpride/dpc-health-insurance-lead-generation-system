"""Unit tests for validation utilities."""

import pytest
from utils.validators import validate_email, validate_phone, clean_company_name


class TestEmailValidator:
    """Test email validation function."""
    
    def test_valid_emails(self):
        """Test that valid emails pass validation."""
        valid_emails = [
            "user@example.com",
            "john.doe@company.com",
            "contact+tag@domain.org",
            "admin@subdomain.example.com",
        ]
        
        for email in valid_emails:
            assert validate_email(email) is True
    
    def test_invalid_emails(self):
        """Test that invalid emails fail validation."""
        invalid_emails = [
            "",
            None,
            "not-an-email",
            "@example.com",
            "user@",
            "user @example.com",
            "user@.com",
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False


class TestPhoneValidator:
    """Test phone number validation function."""
    
    def test_valid_phones(self):
        """Test that valid US phone numbers pass validation."""
        valid_phones = [
            "1234567890",
            "11234567890",
            "(123) 456-7890",
            "123-456-7890",
            "123.456.7890",
            "+1 123 456 7890",
        ]
        
        for phone in valid_phones:
            assert validate_phone(phone) is True
    
    def test_invalid_phones(self):
        """Test that invalid phone numbers fail validation."""
        invalid_phones = [
            "",
            None,
            "123456789",  # Too short
            "12345678901",  # Too long (not starting with 1)
            "abcdefghij",
            "123-456-789a",
        ]
        
        for phone in invalid_phones:
            assert validate_phone(phone) is False


class TestCompanyNameCleaner:
    """Test company name cleaning function."""
    
    def test_clean_suffixes(self):
        """Test that common suffixes are removed."""
        test_cases = [
            ("Acme Corp.", "Acme"),
            ("Tech Solutions LLC", "Tech Solutions"),
            ("Global Industries, Inc.", "Global Industries"),
            ("Example Co", "Example"),
            ("Test Limited", "Test"),
        ]
        
        for input_name, expected in test_cases:
            assert clean_company_name(input_name) == expected
    
    def test_no_suffix(self):
        """Test that names without suffixes are unchanged."""
        names = ["Apple", "Microsoft", "Google"]
        
        for name in names:
            assert clean_company_name(name) == name
    
    def test_edge_cases(self):
        """Test edge cases."""
        assert clean_company_name("") == ""
        assert clean_company_name(None) == ""
        assert clean_company_name("   Spaces Inc.   ") == "Spaces" 