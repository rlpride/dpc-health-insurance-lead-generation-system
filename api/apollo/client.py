"""Apollo.io API client implementation."""

import logging
from typing import Dict, Any, Optional, List
import httpx
import asyncio
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class ApolloClient:
    """Client for Apollo.io API."""
    
    BASE_URL = "https://api.apollo.io/v1"
    
    def __init__(self, api_key: str):
        """Initialize Apollo client."""
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key
        }
    
    async def search_people(self, **params) -> Dict[str, Any]:
        """Search for people using Apollo API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/mixed_people/search",
                    headers=self.headers,
                    json=params
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Apollo API error {e.response.status_code}: {e.response.text}")
            return {"people": [], "error": str(e)}
        except Exception as e:
            logger.error(f"Apollo search error: {str(e)}")
            return {"people": [], "error": str(e)}
    
    async def find_decision_makers(self, company_name: str, company_domain: Optional[str] = None, 
                                 location: Optional[str] = None, employee_range: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find decision-makers (HR Directors, Benefits Managers, CFOs) at a company."""
        
        # Define target titles for decision-makers
        target_titles = [
            # HR & Benefits
            "HR Director", "Human Resources Director", "Director of Human Resources",
            "VP HR", "VP Human Resources", "Vice President Human Resources",
            "Benefits Manager", "Benefits Director", "Director of Benefits",
            "Compensation Manager", "Compensation Director",
            "Employee Benefits Manager", "Employee Benefits Director",
            "People Operations", "Head of People", "Chief People Officer",
            
            # Finance
            "CFO", "Chief Financial Officer", "VP Finance", "Finance Director",
            "Controller", "Financial Controller", "Treasurer",
            
            # Executive level
            "CEO", "Chief Executive Officer", "President", "COO", "Chief Operating Officer",
            "Owner", "Founder", "Managing Partner"
        ]
        
        search_params = {
            "q_organization_name": company_name,
            "page": 1,
            "per_page": 25,
            "person_titles": target_titles[:10],  # Apollo has limits on title count
            "organization_num_employees_ranges": [employee_range] if employee_range else None
        }
        
        # Add domain if provided
        if company_domain:
            search_params["organization_domains"] = [company_domain]
        
        # Add location if provided
        if location:
            search_params["organization_locations"] = [location]
        
        # Remove None values
        search_params = {k: v for k, v in search_params.items() if v is not None}
        
        try:
            result = await self.search_people(**search_params)
            contacts = []
            
            for person in result.get("people", []):
                # Extract person data
                contact = {
                    "source": "apollo",
                    "source_id": person.get("id"),
                    "full_name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
                    "first_name": person.get("first_name"),
                    "last_name": person.get("last_name"),
                    "title": person.get("title"),
                    "email": person.get("email"),
                    "linkedin_url": person.get("linkedin_url"),
                    "phone": None,
                    "company_name": company_name,
                    "confidence_score": "high" if person.get("email") else "medium",
                    "is_decision_maker": True
                }
                
                # Extract phone if available
                if person.get("phone_numbers") and len(person["phone_numbers"]) > 0:
                    contact["phone"] = person["phone_numbers"][0].get("sanitized_number")
                
                # Set department based on title
                if contact["title"]:
                    title_lower = contact["title"].lower()
                    if any(keyword in title_lower for keyword in ["hr", "human resources", "benefits", "people", "compensation"]):
                        contact["department"] = "Human Resources"
                    elif any(keyword in title_lower for keyword in ["cfo", "finance", "controller", "treasurer"]):
                        contact["department"] = "Finance"
                    elif any(keyword in title_lower for keyword in ["ceo", "president", "coo", "owner", "founder"]):
                        contact["department"] = "Executive"
                
                contacts.append(contact)
            
            # Sort by priority (executives first, then HR, then others)
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
            
            contacts.sort(key=priority_score)
            
            logger.info(f"Found {len(contacts)} decision-makers for {company_name}")
            return contacts[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"Error finding decision-makers for {company_name}: {str(e)}")
            return []
    
    async def enrich_person(self, person_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific person."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/people/{person_id}",
                    headers=self.headers
                )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error enriching person {person_id}: {str(e)}")
            return {}
    
    async def search_organizations(self, name: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Search for organizations by name."""
        try:
            search_params = {
                "q_organization_name": name,
                "page": 1,
                "per_page": 10
            }
            
            if domain:
                search_params["organization_domains"] = [domain]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/organizations/search",
                    headers=self.headers,
                    json=search_params
                )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error searching organizations: {str(e)}")
            return {"organizations": []} 