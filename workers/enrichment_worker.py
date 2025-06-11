"""Worker for enriching company data with contact information."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio

from workers.base_worker import BaseWorker
from models import Company, Contact, ApiUsage, get_db_session
from lead_generation_system.enrichment_service import EnrichmentService

logger = logging.getLogger(__name__)


class EnrichmentWorker(BaseWorker):
    """Worker that enriches companies with decision-maker contact information."""
    
    def __init__(self, worker_id: Optional[str] = None):
        super().__init__(worker_id)
        self.enrichment_service = EnrichmentService(self.settings)
    
    @property
    def worker_name(self) -> str:
        return "enrichment_worker"
    
    @property
    def queue_name(self) -> str:
        return "companies.to_enrich"
    
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
                
                # Check if already enriched recently (within 30 days)
                if (company.last_enriched_at and 
                    (datetime.utcnow() - company.last_enriched_at).days < 30):
                    logger.info(f"Company {company.name} already enriched recently, skipping")
                    return True
                
                # Run enrichment
                success, contacts = asyncio.run(self.enrichment_service.enrich_company(company))
                
                if success:
                    logger.info(f"Successfully enriched {company.name} with {len(contacts)} contacts")
                else:
                    logger.warning(f"Failed to enrich {company.name}")
                
                return success
            
        except Exception as e:
            logger.error(f"Error processing enrichment: {str(e)}")
            return False
    
    async def batch_enrich_companies(self, company_ids: List[str], max_concurrent: int = 5) -> Dict[str, Any]:
        """Enrich multiple companies concurrently."""
        try:
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def enrich_single(company_id: str) -> Tuple[str, bool, int]:
                async with semaphore:
                    try:
                        with get_db_session() as db:
                            company = db.query(Company).filter_by(id=company_id).first()
                            if not company:
                                return company_id, False, 0
                            
                            success, contacts = await self.enrichment_service.enrich_company(company)
                            return company_id, success, len(contacts)
                    
                    except Exception as e:
                        logger.error(f"Error enriching company {company_id}: {str(e)}")
                        return company_id, False, 0
            
            # Run enrichment tasks concurrently
            tasks = [enrich_single(company_id) for company_id in company_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            summary = {
                "total_companies": len(company_ids),
                "successful": 0,
                "failed": 0,
                "total_contacts": 0,
                "results": {}
            }
            
            for result in results:
                if isinstance(result, Exception):
                    summary["failed"] += 1
                    continue
                    
                company_id, success, contact_count = result
                summary["results"][company_id] = {
                    "success": success,
                    "contacts_found": contact_count
                }
                
                if success:
                    summary["successful"] += 1
                    summary["total_contacts"] += contact_count
                else:
                    summary["failed"] += 1
            
            logger.info(f"Batch enrichment complete: {summary['successful']}/{summary['total_companies']} successful")
            return summary
            
        except Exception as e:
            logger.error(f"Error in batch enrichment: {str(e)}")
            return {"error": str(e)}
    
    def get_enrichment_stats(self) -> Dict[str, Any]:
        """Get enrichment statistics."""
        try:
            return asyncio.run(self.enrichment_service.get_enrichment_stats())
        except Exception as e:
            logger.error(f"Error getting enrichment stats: {str(e)}")
            return {"error": str(e)} 