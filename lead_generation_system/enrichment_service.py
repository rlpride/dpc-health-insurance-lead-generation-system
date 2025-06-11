"""Comprehensive enrichment service for finding and verifying decision-maker contacts."""

import logging
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal

import redis
from sqlalchemy.orm import Session

from api import ApolloClient, ProxycurlClient, DropcontactClient
from models import Company, Contact, ApiUsage, get_db_session
from config.settings import Settings

logger = logging.getLogger(__name__)


class EnrichmentService:
    """Service for enriching companies with decision-maker contact information."""
    
    def __init__(self, settings: Settings, redis_client: Optional[redis.Redis] = None):
        """Initialize the enrichment service."""
        self.settings = settings
        self.redis_client = redis_client or redis.from_url(settings.redis_url)
        
        # Initialize API clients
        self.apollo_client = None
        self.proxycurl_client = None
        self.dropcontact_client = None
        
        if settings.apollo_api_key:
            self.apollo_client = ApolloClient(settings.apollo_api_key)
            
        if settings.proxycurl_api_key:
            self.proxycurl_client = ProxycurlClient(settings.proxycurl_api_key)
            
        if settings.dropcontact_api_key:
            self.dropcontact_client = DropcontactClient(settings.dropcontact_api_key)
    
    def _generate_cache_key(self, prefix: str, company_name: str, **kwargs) -> str:
        """Generate a cache key for storing results."""
        # Create a unique key based on company name and parameters
        key_data = f"{company_name}_{json.dumps(kwargs, sort_keys=True)}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"enrichment:{prefix}:{key_hash}"
    
    async def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available and not expired."""
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                result = json.loads(cached_data)
                # Check if cache is still valid (24 hours)
                cache_time = datetime.fromisoformat(result.get("cached_at", ""))
                if datetime.utcnow() - cache_time < timedelta(hours=24):
                    logger.info(f"Cache hit for key: {cache_key}")
                    return result.get("data")
                else:
                    # Expired cache
                    self.redis_client.delete(cache_key)
        except Exception as e:
            logger.warning(f"Cache retrieval error: {str(e)}")
        
        return None
    
    async def _cache_result(self, cache_key: str, data: Any, ttl_hours: int = 24):
        """Cache result with TTL."""
        try:
            cache_data = {
                "data": data,
                "cached_at": datetime.utcnow().isoformat()
            }
            # Cache for 24 hours by default
            self.redis_client.setex(
                cache_key, 
                int(ttl_hours * 3600), 
                json.dumps(cache_data, default=str)
            )
        except Exception as e:
            logger.warning(f"Cache storage error: {str(e)}")
    
    async def _track_api_usage(self, provider: str, request_type: str, 
                             response_status: int = 200, records_returned: int = 0,
                             company_id: Optional[str] = None, success: bool = True):
        """Track API usage for cost monitoring."""
        try:
            with get_db_session() as db:
                cost = ApiUsage.calculate_cost(provider, request_type, 1)
                
                usage = ApiUsage(
                    provider=provider,
                    request_type=request_type,
                    request_count=1,
                    response_status=response_status,
                    success=success,
                    total_cost=cost,
                    records_returned=records_returned,
                    company_id=company_id,
                    month=datetime.utcnow().strftime("%Y-%m")
                )
                
                db.add(usage)
                db.commit()
                
                logger.info(f"Tracked {provider} API usage: {request_type}, cost: ${cost}")
                
        except Exception as e:
            logger.error(f"Error tracking API usage: {str(e)}")
    
    async def _check_monthly_limits(self, provider: str) -> bool:
        """Check if monthly API limits have been exceeded."""
        try:
            with get_db_session() as db:
                current_month = datetime.utcnow().strftime("%Y-%m")
                
                monthly_usage = db.query(ApiUsage).filter(
                    ApiUsage.provider == provider,
                    ApiUsage.month == current_month
                ).count()
                
                limits = {
                    "apollo": self.settings.apollo_monthly_limit,
                    "proxycurl": self.settings.proxycurl_monthly_limit,
                    "dropcontact": self.settings.dropcontact_monthly_limit
                }
                
                limit = limits.get(provider, 0)
                if monthly_usage >= limit:
                    logger.warning(f"Monthly limit exceeded for {provider}: {monthly_usage}/{limit}")
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"Error checking monthly limits: {str(e)}")
            return True  # Default to allowing requests if check fails
    
    async def find_decision_makers(self, company: Company) -> List[Dict[str, Any]]:
        """Find decision-makers for a company using Apollo and Proxycurl as fallback."""
        
        # Check cache first
        cache_key = self._generate_cache_key(
            "decision_makers", 
            company.name,
            state=company.state,
            domain=company.email_domain
        )
        
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        all_contacts = []
        
        # Try Apollo first
        if self.apollo_client and await self._check_monthly_limits("apollo"):
            try:
                logger.info(f"Searching Apollo for decision-makers at {company.name}")
                
                # Determine employee range for Apollo
                employee_range = None
                if company.employee_count_min and company.employee_count_max:
                    if company.employee_count_min <= 50:
                        employee_range = "1,50"
                    elif company.employee_count_min <= 200:
                        employee_range = "51,200"
                    elif company.employee_count_min <= 500:
                        employee_range = "201,500"
                    else:
                        employee_range = "501,1000"
                
                apollo_contacts = await self.apollo_client.find_decision_makers(
                    company_name=company.name,
                    company_domain=company.email_domain,
                    location=company.state,
                    employee_range=employee_range
                )
                
                await self._track_api_usage(
                    provider="apollo",
                    request_type="search",
                    records_returned=len(apollo_contacts),
                    company_id=str(company.id),
                    success=True
                )
                
                all_contacts.extend(apollo_contacts)
                logger.info(f"Found {len(apollo_contacts)} contacts via Apollo")
                
            except Exception as e:
                logger.error(f"Apollo search failed for {company.name}: {str(e)}")
                await self._track_api_usage(
                    provider="apollo",
                    request_type="search",
                    response_status=500,
                    company_id=str(company.id),
                    success=False
                )
        
        # Use Proxycurl as fallback if we have fewer than 3 contacts
        if (self.proxycurl_client and 
            len(all_contacts) < 3 and 
            await self._check_monthly_limits("proxycurl")):
            
            try:
                logger.info(f"Using Proxycurl fallback for {company.name}")
                
                proxycurl_contacts = await self.proxycurl_client.find_decision_makers(
                    company_name=company.name
                )
                
                await self._track_api_usage(
                    provider="proxycurl",
                    request_type="search",
                    records_returned=len(proxycurl_contacts),
                    company_id=str(company.id),
                    success=True
                )
                
                all_contacts.extend(proxycurl_contacts)
                logger.info(f"Found {len(proxycurl_contacts)} additional contacts via Proxycurl")
                
            except Exception as e:
                logger.error(f"Proxycurl search failed for {company.name}: {str(e)}")
                await self._track_api_usage(
                    provider="proxycurl",
                    request_type="search",
                    response_status=500,
                    company_id=str(company.id),
                    success=False
                )
        
        # Remove duplicates based on email or name
        unique_contacts = []
        seen_emails = set()
        seen_names = set()
        
        for contact in all_contacts:
            email = contact.get("email", "").lower().strip()
            name = contact.get("full_name", "").lower().strip()
            
            if email and email in seen_emails:
                continue
            if name and name in seen_names:
                continue
                
            if email:
                seen_emails.add(email)
            if name:
                seen_names.add(name)
                
            unique_contacts.append(contact)
        
        # Cache the results
        await self._cache_result(cache_key, unique_contacts)
        
        logger.info(f"Found {len(unique_contacts)} unique decision-makers for {company.name}")
        return unique_contacts
    
    async def verify_contacts(self, contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Verify and enrich contact emails using Dropcontact."""
        
        if not self.dropcontact_client or not await self._check_monthly_limits("dropcontact"):
            logger.warning("Dropcontact not available or limit exceeded, skipping verification")
            return contacts
        
        # Filter contacts that have emails and need verification
        contacts_to_verify = [
            contact for contact in contacts 
            if contact.get("email") and not contact.get("email_verified")
        ]
        
        if not contacts_to_verify:
            return contacts
        
        try:
            logger.info(f"Verifying {len(contacts_to_verify)} emails with Dropcontact")
            
            verified_contacts = await self.dropcontact_client.verify_emails_batch(contacts_to_verify)
            
            await self._track_api_usage(
                provider="dropcontact",
                request_type="verify",
                records_returned=len(verified_contacts),
                success=True
            )
            
            # Merge verified data back into original contacts
            email_to_verified = {
                contact.get("email", "").lower(): contact 
                for contact in verified_contacts
            }
            
            for contact in contacts:
                email = contact.get("email", "").lower()
                if email in email_to_verified:
                    verified_data = email_to_verified[email]
                    contact.update(verified_data)
            
            verified_count = sum(1 for c in contacts if c.get("email_verified"))
            logger.info(f"Email verification complete: {verified_count}/{len(contacts_to_verify)} verified")
            
            return contacts
            
        except Exception as e:
            logger.error(f"Email verification failed: {str(e)}")
            await self._track_api_usage(
                provider="dropcontact",
                request_type="verify",
                response_status=500,
                success=False
            )
            return contacts
    
    async def enrich_company(self, company: Company) -> Tuple[bool, List[Contact]]:
        """Complete enrichment process for a company."""
        try:
            logger.info(f"Starting enrichment for company: {company.name}")
            
            # Find decision-makers
            decision_makers = await self.find_decision_makers(company)
            
            if not decision_makers:
                logger.warning(f"No decision-makers found for {company.name}")
                return False, []
            
            # Verify emails
            verified_contacts = await self.verify_contacts(decision_makers)
            
            # Save contacts to database
            saved_contacts = []
            with get_db_session() as db:
                for contact_data in verified_contacts:
                    try:
                        # Check if contact already exists
                        existing = db.query(Contact).filter(
                            Contact.company_id == company.id,
                            Contact.email == contact_data.get("email")
                        ).first()
                        
                        if existing:
                            # Update existing contact
                            for key, value in contact_data.items():
                                if hasattr(existing, key) and value:
                                    setattr(existing, key, value)
                            saved_contacts.append(existing)
                        else:
                            # Create new contact
                            contact_data["company_id"] = company.id
                            new_contact = Contact(**contact_data)
                            db.add(new_contact)
                            saved_contacts.append(new_contact)
                    
                    except Exception as e:
                        logger.error(f"Error saving contact {contact_data.get('full_name')}: {str(e)}")
                        continue
                
                # Update company enrichment status
                company.enrichment_status = "enriched"
                company.last_enriched_at = datetime.utcnow()
                
                db.commit()
            
            logger.info(f"Enrichment complete for {company.name}: {len(saved_contacts)} contacts saved")
            return True, saved_contacts
            
        except Exception as e:
            logger.error(f"Enrichment failed for company {company.id}: {str(e)}")
            
            # Update company status to failed
            with get_db_session() as db:
                company.enrichment_status = "failed"
                db.commit()
            
            return False, []
    
    async def get_enrichment_stats(self) -> Dict[str, Any]:
        """Get enrichment statistics and API usage summary."""
        try:
            with get_db_session() as db:
                current_month = datetime.utcnow().strftime("%Y-%m")
                
                # Get API usage stats
                api_stats = {}
                for provider in ["apollo", "proxycurl", "dropcontact"]:
                    usage = db.query(ApiUsage).filter(
                        ApiUsage.provider == provider,
                        ApiUsage.month == current_month
                    ).all()
                    
                    total_requests = len(usage)
                    total_cost = sum(u.total_cost for u in usage)
                    successful_requests = sum(1 for u in usage if u.success)
                    
                    api_stats[provider] = {
                        "total_requests": total_requests,
                        "successful_requests": successful_requests,
                        "total_cost": float(total_cost),
                        "success_rate": successful_requests / total_requests if total_requests > 0 else 0
                    }
                
                # Get enrichment stats
                total_companies = db.query(Company).count()
                enriched_companies = db.query(Company).filter(
                    Company.enrichment_status == "enriched"
                ).count()
                
                total_contacts = db.query(Contact).count()
                verified_contacts = db.query(Contact).filter(
                    Contact.email_verified == True
                ).count()
                
                return {
                    "api_usage": api_stats,
                    "companies": {
                        "total": total_companies,
                        "enriched": enriched_companies,
                        "enrichment_rate": enriched_companies / total_companies if total_companies > 0 else 0
                    },
                    "contacts": {
                        "total": total_contacts,
                        "verified": verified_contacts,
                        "verification_rate": verified_contacts / total_contacts if total_contacts > 0 else 0
                    },
                    "month": current_month
                }
                
        except Exception as e:
            logger.error(f"Error getting enrichment stats: {str(e)}")
            return {}