"""Pipedrive CRM integration service."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .client import PipedriveClient, PipedriveError
from ...models.company import Company
from ...models.contact import Contact
from ...models.lead_score import LeadScore
from ...config.settings import get_settings

logger = logging.getLogger(__name__)


class PipedriveIntegrationService:
    """Service for integrating with Pipedrive CRM."""
    
    def __init__(self, db_session: Session):
        """Initialize the integration service.
        
        Args:
            db_session: Database session for data operations
        """
        self.db = db_session
        self.settings = get_settings()
        
        # Initialize Pipedrive client
        self.client = PipedriveClient(
            api_key=self.settings.pipedrive_api_key,
            domain=self.settings.pipedrive_domain,
            rate_limit_per_second=1.0  # Conservative rate limiting
        )
        
        # Custom field mappings (will be populated on first use)
        self._custom_fields: Dict[str, Dict[str, str]] = {
            'org': {},
            'person': {},
            'deal': {}
        }
        self._custom_fields_initialized = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def _initialize_custom_fields(self):
        """Initialize custom field mappings."""
        if self._custom_fields_initialized:
            return
        
        try:
            # Get existing custom fields
            org_fields = await self.client.get_organization_fields()
            person_fields = await self.client.get_person_fields()
            deal_fields = await self.client.get_deal_fields()
            
            # Map field names to keys
            for field in org_fields:
                self._custom_fields['org'][field['name']] = field['key']
            
            for field in person_fields:
                self._custom_fields['person'][field['name']] = field['key']
            
            for field in deal_fields:
                self._custom_fields['deal'][field['name']] = field['key']
            
            # Create missing custom fields
            await self._ensure_custom_fields_exist()
            
            self._custom_fields_initialized = True
            logger.info("Custom fields initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize custom fields: {e}")
            raise
    
    async def _ensure_custom_fields_exist(self):
        """Ensure required custom fields exist in Pipedrive."""
        # Required organization fields
        org_fields_needed = {
            'Lead Score': 'int',
            'NAICS Code': 'varchar',
            'Industry Category': 'varchar',
            'Employee Count Min': 'int',
            'Employee Count Max': 'int',
            'Data Source': 'varchar',
            'Last Enriched': 'date'
        }
        
        # Required person fields
        person_fields_needed = {
            'Lead Score': 'int',
            'Seniority Level': 'varchar',
            'Is Decision Maker': 'varchar',
            'Data Source': 'varchar',
            'LinkedIn URL': 'varchar'
        }
        
        # Required deal fields
        deal_fields_needed = {
            'Lead Score': 'int',
            'Deal Source': 'varchar',
            'Company Industry': 'varchar',
            'Employee Count': 'varchar'
        }
        
        # Create missing organization fields
        for field_name, field_type in org_fields_needed.items():
            if field_name not in self._custom_fields['org']:
                try:
                    result = await self.client.create_custom_field('org', field_name, field_type)
                    self._custom_fields['org'][field_name] = result.get('key', '')
                    logger.info(f"Created organization field: {field_name}")
                except Exception as e:
                    logger.warning(f"Failed to create org field {field_name}: {e}")
        
        # Create missing person fields
        for field_name, field_type in person_fields_needed.items():
            if field_name not in self._custom_fields['person']:
                try:
                    result = await self.client.create_custom_field('person', field_name, field_type)
                    self._custom_fields['person'][field_name] = result.get('key', '')
                    logger.info(f"Created person field: {field_name}")
                except Exception as e:
                    logger.warning(f"Failed to create person field {field_name}: {e}")
        
        # Create missing deal fields
        for field_name, field_type in deal_fields_needed.items():
            if field_name not in self._custom_fields['deal']:
                try:
                    result = await self.client.create_custom_field('deal', field_name, field_type)
                    self._custom_fields['deal'][field_name] = result.get('key', '')
                    logger.info(f"Created deal field: {field_name}")
                except Exception as e:
                    logger.warning(f"Failed to create deal field {field_name}: {e}")
    
    def _map_company_to_organization(self, company: Company) -> Dict[str, Any]:
        """Map Company model to Pipedrive organization data."""
        data = {
            'name': company.name,
            'address_street_1': company.street_address,
            'address_locality': company.city,
            'address_admin_area_level_1': company.state,
            'address_postal_code': company.zip_code,
            'address_country': company.country or 'US',
        }
        
        # Add optional fields
        if company.phone:
            data['phone'] = [{'value': company.phone, 'primary': True}]
        
        if company.website:
            data['website'] = company.website
        
        # Add custom fields
        if self._custom_fields['org'].get('Lead Score'):
            data[self._custom_fields['org']['Lead Score']] = company.lead_score
        
        if self._custom_fields['org'].get('NAICS Code') and company.naics_code:
            data[self._custom_fields['org']['NAICS Code']] = company.naics_code
        
        if self._custom_fields['org'].get('Industry Category') and company.industry_category:
            data[self._custom_fields['org']['Industry Category']] = company.industry_category
        
        if self._custom_fields['org'].get('Employee Count Min') and company.employee_count_min:
            data[self._custom_fields['org']['Employee Count Min']] = company.employee_count_min
        
        if self._custom_fields['org'].get('Employee Count Max') and company.employee_count_max:
            data[self._custom_fields['org']['Employee Count Max']] = company.employee_count_max
        
        if self._custom_fields['org'].get('Data Source'):
            data[self._custom_fields['org']['Data Source']] = company.source
        
        if self._custom_fields['org'].get('Last Enriched') and company.last_enriched_at:
            data[self._custom_fields['org']['Last Enriched']] = company.last_enriched_at.strftime('%Y-%m-%d')
        
        return data
    
    def _map_contact_to_person(self, contact: Contact, pipedrive_org_id: str) -> Dict[str, Any]:
        """Map Contact model to Pipedrive person data."""
        data = {
            'name': contact.full_name,
            'org_id': pipedrive_org_id,
        }
        
        # Add email
        if contact.email:
            data['email'] = [{'value': contact.email, 'primary': True}]
        
        # Add phone
        if contact.phone:
            data['phone'] = [{'value': contact.phone, 'primary': True}]
        
        # Add job title
        if contact.title:
            data['job_title'] = contact.title
        
        # Add custom fields
        if self._custom_fields['person'].get('Seniority Level') and contact.seniority_level:
            data[self._custom_fields['person']['Seniority Level']] = contact.seniority_level
        
        if self._custom_fields['person'].get('Is Decision Maker'):
            data[self._custom_fields['person']['Is Decision Maker']] = 'Yes' if contact.is_decision_maker else 'No'
        
        if self._custom_fields['person'].get('Data Source'):
            data[self._custom_fields['person']['Data Source']] = contact.source
        
        if self._custom_fields['person'].get('LinkedIn URL') and contact.linkedin_url:
            data[self._custom_fields['person']['LinkedIn URL']] = contact.linkedin_url
        
        # Add lead score from company
        if self._custom_fields['person'].get('Lead Score') and contact.company:
            data[self._custom_fields['person']['Lead Score']] = contact.company.lead_score
        
        return data
    
    def _create_deal_data(self, company: Company, pipedrive_org_id: str, pipedrive_person_id: Optional[str] = None) -> Dict[str, Any]:
        """Create deal data for high-scoring leads."""
        # Estimate deal value based on company size
        estimated_value = self._estimate_deal_value(company)
        
        data = {
            'title': f"Health Insurance - {company.name}",
            'org_id': pipedrive_org_id,
            'value': estimated_value,
            'currency': 'USD',
            'stage_id': 1,  # First stage - adjust based on your pipeline
        }
        
        if pipedrive_person_id:
            data['person_id'] = pipedrive_person_id
        
        # Add custom fields
        if self._custom_fields['deal'].get('Lead Score'):
            data[self._custom_fields['deal']['Lead Score']] = company.lead_score
        
        if self._custom_fields['deal'].get('Deal Source'):
            data[self._custom_fields['deal']['Deal Source']] = company.source
        
        if self._custom_fields['deal'].get('Company Industry') and company.industry_category:
            data[self._custom_fields['deal']['Company Industry']] = company.industry_category
        
        if self._custom_fields['deal'].get('Employee Count') and company.employee_range:
            data[self._custom_fields['deal']['Employee Count']] = company.employee_range
        
        return data
    
    def _estimate_deal_value(self, company: Company) -> int:
        """Estimate deal value based on company size and industry."""
        base_value = 5000  # Base value for small companies
        
        # Adjust based on employee count
        if company.employee_count_min:
            if company.employee_count_min >= 500:
                base_value = 50000
            elif company.employee_count_min >= 200:
                base_value = 25000
            elif company.employee_count_min >= 100:
                base_value = 15000
            elif company.employee_count_min >= 50:
                base_value = 10000
        
        # Adjust based on lead score
        if company.lead_score >= 90:
            base_value = int(base_value * 1.5)
        elif company.lead_score >= 85:
            base_value = int(base_value * 1.3)
        elif company.lead_score >= 80:
            base_value = int(base_value * 1.1)
        
        return base_value
    
    async def sync_company(self, company: Company) -> bool:
        """Sync a single company to Pipedrive.
        
        Args:
            company: Company to sync
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._initialize_custom_fields()
            
            # Check if already synced
            if company.pipedrive_id and company.crm_sync_status == 'synced':
                logger.debug(f"Company {company.name} already synced")
                return True
            
            # Check for existing organization
            existing_orgs = await self.client.search_organizations(company.name)
            pipedrive_org = None
            
            if existing_orgs:
                # Use existing organization
                pipedrive_org = existing_orgs[0]
                logger.info(f"Found existing organization for {company.name}")
            else:
                # Create new organization
                org_data = self._map_company_to_organization(company)
                pipedrive_org = await self.client.create_organization(org_data)
            
            # Update company record
            company.pipedrive_id = str(pipedrive_org['id'])
            company.crm_sync_status = 'synced'
            company.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Successfully synced company {company.name} (ID: {company.pipedrive_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync company {company.name}: {e}")
            company.crm_sync_status = 'failed'
            self.db.commit()
            return False
    
    async def sync_contact(self, contact: Contact) -> bool:
        """Sync a single contact to Pipedrive.
        
        Args:
            contact: Contact to sync
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._initialize_custom_fields()
            
            # Check if already synced
            if contact.pipedrive_person_id and contact.crm_sync_status == 'synced':
                logger.debug(f"Contact {contact.full_name} already synced")
                return True
            
            # Ensure company is synced first
            if not contact.company.pipedrive_id:
                await self.sync_company(contact.company)
            
            if not contact.company.pipedrive_id:
                logger.error(f"Cannot sync contact {contact.full_name}: company not synced")
                return False
            
            # Check for existing person
            existing_persons = []
            if contact.email:
                existing_persons = await self.client.search_persons(contact.email)
            
            if not existing_persons and contact.full_name:
                existing_persons = await self.client.search_persons(contact.full_name)
            
            pipedrive_person = None
            
            if existing_persons:
                # Use existing person
                pipedrive_person = existing_persons[0]
                logger.info(f"Found existing person for {contact.full_name}")
            else:
                # Create new person
                person_data = self._map_contact_to_person(contact, contact.company.pipedrive_id)
                pipedrive_person = await self.client.create_person(person_data)
            
            # Update contact record
            contact.pipedrive_person_id = str(pipedrive_person['id'])
            contact.crm_sync_status = 'synced'
            contact.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Successfully synced contact {contact.full_name} (ID: {contact.pipedrive_person_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync contact {contact.full_name}: {e}")
            contact.crm_sync_status = 'failed'
            self.db.commit()
            return False
    
    async def create_deal_for_high_score_lead(self, company: Company) -> bool:
        """Create a deal for companies with high lead scores.
        
        Args:
            company: Company to create deal for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if company qualifies for deal creation
            if company.lead_score < self.settings.high_score_threshold:
                logger.debug(f"Company {company.name} score {company.lead_score} below threshold")
                return False
            
            # Ensure company is synced
            if not company.pipedrive_id:
                await self.sync_company(company)
            
            if not company.pipedrive_id:
                logger.error(f"Cannot create deal: company {company.name} not synced")
                return False
            
            # Find best contact for the deal
            primary_contact = None
            for contact in company.contacts:
                if contact.is_decision_maker or contact.is_executive:
                    primary_contact = contact
                    break
            
            # Sync primary contact if found
            pipedrive_person_id = None
            if primary_contact:
                if not primary_contact.pipedrive_person_id:
                    await self.sync_contact(primary_contact)
                pipedrive_person_id = primary_contact.pipedrive_person_id
            
            # Create deal
            deal_data = self._create_deal_data(company, company.pipedrive_id, pipedrive_person_id)
            deal = await self.client.create_deal(deal_data)
            
            logger.info(f"Created deal for {company.name} (Deal ID: {deal['id']}, Value: ${deal_data['value']})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create deal for {company.name}: {e}")
            return False
    
    async def sync_pending_records(self, limit: int = 50) -> Dict[str, int]:
        """Sync records that are pending CRM sync.
        
        Args:
            limit: Maximum number of records to process
            
        Returns:
            Dictionary with sync statistics
        """
        stats = {
            'companies_synced': 0,
            'contacts_synced': 0,
            'deals_created': 0,
            'companies_failed': 0,
            'contacts_failed': 0
        }
        
        try:
            # Get pending companies
            pending_companies = (
                self.db.query(Company)
                .filter(Company.crm_sync_status == 'pending')
                .limit(limit)
                .all()
            )
            
            for company in pending_companies:
                success = await self.sync_company(company)
                if success:
                    stats['companies_synced'] += 1
                    
                    # Create deal if high score
                    if company.lead_score >= self.settings.high_score_threshold:
                        deal_success = await self.create_deal_for_high_score_lead(company)
                        if deal_success:
                            stats['deals_created'] += 1
                else:
                    stats['companies_failed'] += 1
            
            # Get pending contacts
            pending_contacts = (
                self.db.query(Contact)
                .filter(Contact.crm_sync_status == 'pending')
                .limit(limit)
                .all()
            )
            
            for contact in pending_contacts:
                success = await self.sync_contact(contact)
                if success:
                    stats['contacts_synced'] += 1
                else:
                    stats['contacts_failed'] += 1
            
            logger.info(f"Sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during bulk sync: {e}")
            raise
    
    def get_sync_statistics(self) -> Dict[str, int]:
        """Get CRM sync statistics."""
        company_stats = (
            self.db.query(Company.crm_sync_status, self.db.func.count(Company.id))
            .group_by(Company.crm_sync_status)
            .all()
        )
        
        contact_stats = (
            self.db.query(Contact.crm_sync_status, self.db.func.count(Contact.id))
            .group_by(Contact.crm_sync_status)
            .all()
        )
        
        return {
            'companies': {status: count for status, count in company_stats},
            'contacts': {status: count for status, count in contact_stats},
            'high_score_companies': (
                self.db.query(Company)
                .filter(Company.lead_score >= self.settings.high_score_threshold)
                .count()
            )
        }