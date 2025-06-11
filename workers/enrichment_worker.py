"""Worker for enriching company data with contact information."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from workers.base_worker import BaseWorker
from models import Company, Contact, ApiUsage, get_db_session
from api.apollo import ApolloClient
from api.proxycurl import ProxycurlClient

logger = logging.getLogger(__name__)


class EnrichmentWorker(BaseWorker):
    """Worker that enriches companies with decision-maker contact information."""
    
    def __init__(self, worker_id: Optional[str] = None):
        super().__init__(worker_id)
        self.apollo_client = None
        self.proxycurl_client = None
        self._init_api_clients()
    
    @property
    def worker_name(self) -> str:
        return "enrichment_worker"
    
    @property
    def queue_name(self) -> str:
        return "companies.to_enrich"
    
    def _init_api_clients(self):
        """Initialize API clients for enrichment."""
        if self.settings.apollo_api_key:
            self.apollo_client = ApolloClient(self.settings.apollo_api_key)
        
        if self.settings.proxycurl_api_key:
            self.proxycurl_client = ProxycurlClient(self.settings.proxycurl_api_key)
    
    def process_message(self, body: Dict[str, Any]) -> bool:
        """Process enrichment request for a company."""
        try:
            company_id = body.get("company_id")
            if not company_id:
                logger.error("No company_id in message")
                return False
            
            # Get company from database
            with get_db_session() as db:
                company = db.query(Company).filter_by(id=company_id).first()
                if not company:
                    logger.error(f"Company {company_id} not found")
                    return False
                
                # Check if already enriched
                if company.enrichment_status == "enriched":
                    logger.info(f"Company {company_id} already enriched")
                    return True
                
                # Run enrichment
                success = asyncio.run(self.enrich_company(company))
                
                if success:
                    # Update company status
                    company.enrichment_status = "enriched"
                    company.last_enriched_at = datetime.utcnow()
                    
                    # Publish to scoring queue
                    self.publish_message(
                        {"company_id": str(company_id)},
                        "companies.to_score.tasks"
                    )
                else:
                    company.enrichment_status = "failed"
                
                db.commit()
                
            return success
            
        except Exception as e:
            logger.error(f"Error processing enrichment: {str(e)}")
            return False
    
    async def enrich_company(self, company: Company) -> bool:
        """Enrich a company with contact information."""
        try:
            contacts_found = []
            
            # Try Apollo first if available
            if self.apollo_client:
                apollo_contacts = await self.find_contacts_apollo(company)
                contacts_found.extend(apollo_contacts)
            
            # Try Proxycurl if we need more contacts
            if self.proxycurl_client and len(contacts_found) < 3:
                proxycurl_contacts = await self.find_contacts_proxycurl(company)
                contacts_found.extend(proxycurl_contacts)
            
            # Save contacts to database
            if contacts_found:
                self.save_contacts(company.id, contacts_found)
                return True
            
            logger.warning(f"No contacts found for company {company.id}")
            return False
            
        except Exception as e:
            logger.error(f"Error enriching company {company.id}: {str(e)}")
            return False
    
    async def find_contacts_apollo(self, company: Company) -> List[Dict[str, Any]]:
        """Find contacts using Apollo API."""
        try:
            # Search for people at the company
            search_params = {
                "organization_name": company.name,
                "organization_locations": [company.state] if company.state else None,
                "person_titles": [
                    "CEO", "CFO", "COO", "President", "Owner",
                    "VP HR", "Director HR", "Benefits Manager",
                    "Human Resources Manager", "VP Benefits"
                ],
                "limit": 5
            }
            
            results = await self.apollo_client.search_people(**search_params)
            
            # Track API usage
            self.track_api_usage(
                provider="apollo",
                request_type="search",
                records_returned=len(results.get("people", []))
            )
            
            # Parse results
            contacts = []
            for person in results.get("people", []):
                contact = {
                    "full_name": person.get("name"),
                    "first_name": person.get("first_name"),
                    "last_name": person.get("last_name"),
                    "title": person.get("title"),
                    "email": person.get("email"),
                    "phone": person.get("phone_numbers", [{}])[0].get("number") if person.get("phone_numbers") else None,
                    "linkedin_url": person.get("linkedin_url"),
                    "source": "apollo",
                    "source_id": person.get("id"),
                    "confidence_score": "high" if person.get("email_verified") else "medium"
                }
                contacts.append(contact)
            
            return contacts
            
        except Exception as e:
            logger.error(f"Apollo search error: {str(e)}")
            return []
    
    async def find_contacts_proxycurl(self, company: Company) -> List[Dict[str, Any]]:
        """Find contacts using Proxycurl API."""
        # Implementation placeholder
        return []
    
    def save_contacts(self, company_id: str, contacts: List[Dict[str, Any]]):
        """Save contacts to the database."""
        with get_db_session() as db:
            for contact_data in contacts:
                try:
                    # Check if contact already exists
                    existing = db.query(Contact).filter_by(
                        company_id=company_id,
                        email=contact_data.get("email")
                    ).first()
                    
                    if not existing and contact_data.get("email"):
                        contact_data["company_id"] = company_id
                        new_contact = Contact(**contact_data)
                        db.add(new_contact)
                        logger.info(f"Added contact: {contact_data.get('full_name')}")
                    
                except Exception as e:
                    logger.error(f"Error saving contact: {str(e)}")
                    continue
            
            db.commit()
    
    def track_api_usage(self, provider: str, request_type: str, 
                       records_returned: int = 0, cost: float = 0):
        """Track API usage for cost monitoring."""
        try:
            with get_db_session() as db:
                usage = ApiUsage(
                    provider=provider,
                    request_type=request_type,
                    records_returned=records_returned,
                    total_cost=cost or ApiUsage.calculate_cost(provider, request_type),
                    month=datetime.utcnow().strftime("%Y-%m"),
                    worker_id=self.worker_id
                )
                db.add(usage)
                db.commit()
                
        except Exception as e:
            logger.error(f"Error tracking API usage: {str(e)}") 