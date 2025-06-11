"""Dropcontact API client implementation."""

import logging
from typing import Dict, Any, List, Optional
import httpx
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class DropcontactClient:
    """Client for Dropcontact API for email verification and enrichment."""
    
    BASE_URL = "https://api.dropcontact.io"
    
    def __init__(self, api_key: str):
        """Initialize Dropcontact client."""
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    
    async def verify_email(self, email: str, first_name: Optional[str] = None, 
                          last_name: Optional[str] = None, company_name: Optional[str] = None) -> Dict[str, Any]:
        """Verify and enrich an email address."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "company": company_name
                }
                
                # Remove None values
                payload = {k: v for k, v in payload.items() if v is not None}
                
                response = await client.post(
                    f"{self.BASE_URL}/batch",
                    headers=self.headers,
                    json={"data": [payload]}
                )
                
                response.raise_for_status()
                result = response.json()
                
                if result.get("data") and len(result["data"]) > 0:
                    contact_data = result["data"][0]
                    return {
                        "email": contact_data.get("email"),
                        "email_verified": contact_data.get("email_status") == "valid",
                        "email_status": contact_data.get("email_status"),
                        "confidence": contact_data.get("confidence"),
                        "phone": contact_data.get("phone"),
                        "linkedin_url": contact_data.get("linkedin"),
                        "twitter": contact_data.get("twitter"),
                        "full_name": contact_data.get("full_name"),
                        "first_name": contact_data.get("first_name"),
                        "last_name": contact_data.get("last_name"),
                        "title": contact_data.get("civility"),
                        "website": contact_data.get("website"),
                        "company": contact_data.get("company")
                    }
                
                return {"email_verified": False, "email_status": "unknown"}
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Dropcontact API error {e.response.status_code}: {e.response.text}")
            return {"email_verified": False, "email_status": "error", "error": str(e)}
        except Exception as e:
            logger.error(f"Dropcontact verification error: {str(e)}")
            return {"email_verified": False, "email_status": "error", "error": str(e)}
    
    async def verify_emails_batch(self, contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Verify multiple emails in batch."""
        try:
            # Prepare batch data
            batch_data = []
            for contact in contacts:
                payload = {
                    "email": contact.get("email"),
                    "first_name": contact.get("first_name"),
                    "last_name": contact.get("last_name"),
                    "company": contact.get("company_name")
                }
                # Remove None values
                payload = {k: v for k, v in payload.items() if v is not None}
                batch_data.append(payload)
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/batch",
                    headers=self.headers,
                    json={"data": batch_data}
                )
                
                response.raise_for_status()
                result = response.json()
                
                verified_contacts = []
                for i, contact_data in enumerate(result.get("data", [])):
                    original_contact = contacts[i] if i < len(contacts) else {}
                    verified_contact = {
                        **original_contact,
                        "email": contact_data.get("email"),
                        "email_verified": contact_data.get("email_status") == "valid",
                        "email_status": contact_data.get("email_status"),
                        "confidence": contact_data.get("confidence"),
                        "phone": contact_data.get("phone") or original_contact.get("phone"),
                        "linkedin_url": contact_data.get("linkedin") or original_contact.get("linkedin_url"),
                        "full_name": contact_data.get("full_name") or original_contact.get("full_name"),
                        "verification_date": datetime.utcnow()
                    }
                    verified_contacts.append(verified_contact)
                
                return verified_contacts
                
        except Exception as e:
            logger.error(f"Dropcontact batch verification error: {str(e)}")
            # Return original contacts with verification failed
            return [
                {**contact, "email_verified": False, "email_status": "error"} 
                for contact in contacts
            ]
    
    async def find_email(self, first_name: str, last_name: str, company_domain: str) -> Dict[str, Any]:
        """Find email address for a person at a company."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "website": company_domain
                }
                
                response = await client.post(
                    f"{self.BASE_URL}/batch",
                    headers=self.headers,
                    json={"data": [payload]}
                )
                
                response.raise_for_status()
                result = response.json()
                
                if result.get("data") and len(result["data"]) > 0:
                    contact_data = result["data"][0]
                    return {
                        "email": contact_data.get("email"),
                        "email_verified": contact_data.get("email_status") == "valid",
                        "email_status": contact_data.get("email_status"),
                        "confidence": contact_data.get("confidence"),
                        "found": True
                    }
                
                return {"found": False}
                
        except Exception as e:
            logger.error(f"Dropcontact email finder error: {str(e)}")
            return {"found": False, "error": str(e)}