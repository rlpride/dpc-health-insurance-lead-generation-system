"""Proxycurl API client implementation."""

import logging
from typing import Dict, Any, Optional, List
import httpx
import asyncio
from urllib.parse import quote

logger = logging.getLogger(__name__)


class ProxycurlClient:
    """Client for Proxycurl API."""
    
    BASE_URL = "https://nubela.co/proxycurl/api/v2"
    
    def __init__(self, api_key: str):
        """Initialize Proxycurl client."""
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def get_company_employees(self, company_url: str) -> Dict[str, Any]:
        """Get employees of a company from LinkedIn."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                params = {
                    "url": company_url,
                    "enrich_profiles": "enrich",
                    "page_size": 25,
                    "employment_status": "current",
                    "sort_by": "recently-joined"
                }
                
                response = await client.get(
                    f"{self.BASE_URL}/api/linkedin/company/employees/",
                    headers=self.headers,
                    params=params
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Proxycurl API error {e.response.status_code}: {e.response.text}")
            return {"employees": [], "error": str(e)}
        except Exception as e:
            logger.error(f"Proxycurl error: {str(e)}")
            return {"employees": [], "error": str(e)}
    
    async def find_decision_makers(self, company_name: str, company_linkedin_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find decision-makers at a company using LinkedIn data."""
        
        # If we don't have the LinkedIn URL, try to find the company first
        if not company_linkedin_url:
            company_data = await self.search_company(company_name)
            if company_data.get("companies"):
                company_linkedin_url = company_data["companies"][0].get("linkedin_profile_url")
        
        if not company_linkedin_url:
            logger.warning(f"No LinkedIn URL found for company: {company_name}")
            return []
        
        try:
            # Get company employees
            employees_result = await self.get_company_employees(company_linkedin_url)
            
            if not employees_result.get("employees"):
                return []
            
            decision_makers = []
            target_keywords = [
                # HR & Benefits keywords
                "hr", "human resources", "benefits", "compensation", "people", "talent",
                "employee", "workforce", "payroll", "recruiting", "recruitment",
                
                # Finance keywords  
                "cfo", "finance", "financial", "controller", "treasurer", "accounting",
                
                # Executive keywords
                "ceo", "president", "owner", "founder", "executive", "chief", "vp", 
                "vice president", "director", "head of", "managing", "general manager"
            ]
            
            for employee in employees_result["employees"]:
                profile = employee.get("profile", {})
                
                # Check if employee is a decision-maker based on title
                title = (profile.get("occupation") or "").lower()
                
                is_decision_maker = any(keyword in title for keyword in target_keywords)
                
                if is_decision_maker:
                    contact = {
                        "source": "proxycurl",
                        "source_id": profile.get("public_identifier"),
                        "full_name": profile.get("full_name"),
                        "first_name": profile.get("first_name"),
                        "last_name": profile.get("last_name"),
                        "title": profile.get("occupation"),
                        "linkedin_url": profile.get("profile_pic_url"),  # Note: This might be profile URL
                        "company_name": company_name,
                        "confidence_score": "medium",
                        "is_decision_maker": True
                    }
                    
                    # Extract additional info
                    if profile.get("summary"):
                        contact["summary"] = profile["summary"]
                    
                    # Determine department
                    if any(keyword in title for keyword in ["hr", "human resources", "benefits", "people", "talent"]):
                        contact["department"] = "Human Resources"
                    elif any(keyword in title for keyword in ["cfo", "finance", "controller", "treasurer"]):
                        contact["department"] = "Finance"  
                    elif any(keyword in title for keyword in ["ceo", "president", "owner", "founder"]):
                        contact["department"] = "Executive"
                    
                    decision_makers.append(contact)
            
            # Sort by priority similar to Apollo
            def priority_score(contact):
                title = (contact.get("title") or "").lower()
                if any(keyword in title for keyword in ["ceo", "president", "owner", "founder"]):
                    return 1
                elif any(keyword in title for keyword in ["cfo", "vp", "vice president", "director"]):
                    return 2
                elif any(keyword in title for keyword in ["hr", "human resources", "benefits", "people"]):
                    return 3
                else:
                    return 4
            
            decision_makers.sort(key=priority_score)
            
            logger.info(f"Found {len(decision_makers)} decision-makers for {company_name} via Proxycurl")
            return decision_makers[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"Error finding decision-makers for {company_name}: {str(e)}")
            return []
    
    async def search_company(self, company_name: str) -> Dict[str, Any]:
        """Search for a company by name to get LinkedIn URL."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    "query": company_name,
                    "page_size": 5
                }
                
                response = await client.get(
                    f"{self.BASE_URL}/api/linkedin/company/search",
                    headers=self.headers,
                    params=params
                )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error searching company {company_name}: {str(e)}")
            return {"companies": []}
    
    async def get_person_profile(self, linkedin_url: str) -> Dict[str, Any]:
        """Get detailed profile information for a specific person."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    "url": linkedin_url,
                    "extra": "include",
                    "github_profile_id": "include",
                    "facebook_profile_id": "include",
                    "twitter_profile_id": "include"
                }
                
                response = await client.get(
                    f"{self.BASE_URL}/api/linkedin/profile",
                    headers=self.headers,
                    params=params
                )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error getting profile {linkedin_url}: {str(e)}")
            return {}
    
    async def find_contact_info(self, linkedin_url: str) -> Dict[str, Any]:
        """Find contact information (email, phone) for a LinkedIn profile."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    "linkedin_profile_url": linkedin_url
                }
                
                response = await client.get(
                    f"{self.BASE_URL}/api/contact-api/personal-email",
                    headers=self.headers,
                    params=params
                )
                
                response.raise_for_status()
                result = response.json()
                
                return {
                    "email": result.get("email"),
                    "email_verified": result.get("confidence") == "high" if result.get("email") else False,
                    "confidence": result.get("confidence")
                }
                
        except Exception as e:
            logger.error(f"Error finding contact info for {linkedin_url}: {str(e)}")
            return {"email": None, "email_verified": False} 