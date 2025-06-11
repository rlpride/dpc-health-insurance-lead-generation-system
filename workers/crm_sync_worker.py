"""Worker for syncing qualified leads to Pipedrive CRM."""

import logging
from typing import Dict, Any

from workers.base_worker import BaseWorker
from models import Company, Contact, get_db_session
from api.pipedrive import PipedriveClient

logger = logging.getLogger(__name__)


class CrmSyncWorker(BaseWorker):
    """Worker that syncs high-quality leads to Pipedrive CRM."""
    
    def __init__(self, worker_id=None):
        super().__init__(worker_id)
        self.pipedrive_client = PipedriveClient(
            api_key=self.settings.pipedrive_api_key,
            domain=self.settings.pipedrive_domain
        )
    
    @property
    def worker_name(self) -> str:
        return "crm_sync_worker"
    
    @property
    def queue_name(self) -> str:
        return "companies.to_sync"
    
    def process_message(self, body: Dict[str, Any]) -> bool:
        """Process CRM sync request for a company."""
        try:
            company_id = body.get("company_id")
            if not company_id:
                logger.error("No company_id in message")
                return False
            
            # Sync to CRM
            with get_db_session() as db:
                company = db.query(Company).filter_by(id=company_id).first()
                if not company:
                    logger.error(f"Company {company_id} not found")
                    return False
                
                # Sync company and contacts
                success = self.sync_to_pipedrive(company)
                
                if success:
                    company.crm_sync_status = "synced"
                else:
                    company.crm_sync_status = "failed"
                
                db.commit()
                
            return success
            
        except Exception as e:
            logger.error(f"Error processing CRM sync: {str(e)}")
            return False
    
    def sync_to_pipedrive(self, company: Company) -> bool:
        """Sync company and contacts to Pipedrive."""
        try:
            # Create or update organization
            org_data = {
                "name": company.name,
                "address": f"{company.city}, {company.state}" if company.city else company.state,
                "custom_fields": {
                    "employee_count": company.employee_count_min,
                    "naics_code": company.naics_code,
                    "lead_score": company.lead_score,
                    "source": "Lead Generation System"
                }
            }
            
            # Placeholder for actual Pipedrive API calls
            logger.info(f"Would sync company {company.name} to Pipedrive")
            
            # Sync contacts
            for contact in company.contacts[:3]:  # Sync top 3 contacts
                logger.info(f"Would sync contact {contact.full_name} to Pipedrive")
            
            return True
            
        except Exception as e:
            logger.error(f"Error syncing to Pipedrive: {str(e)}")
            return False 