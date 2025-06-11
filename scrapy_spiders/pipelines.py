"""Scrapy pipelines for processing BLS business data."""

import logging
from datetime import datetime
from typing import Dict, Any
from itemadapter import ItemAdapter

from scrapy import Spider
from scrapy.exceptions import DropItem

from models import Company, get_db_session
from scrapy_spiders.items import BusinessItem, parse_employee_count
from utils.validators import clean_company_name, validate_email

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """Pipeline to validate scraped items."""
    
    def process_item(self, item: BusinessItem, spider: Spider) -> BusinessItem:
        """Validate item data before further processing."""
        adapter = ItemAdapter(item)
        
        # Check required fields
        if not adapter.get('legal_name'):
            raise DropItem(f"Missing legal_name in {item}")
        
        if not adapter.get('naics_code'):
            raise DropItem(f"Missing naics_code in {item}")
        
        if not adapter.get('size_class'):
            raise DropItem(f"Missing size_class in {item}")
        
        # Validate employee count range
        size_class = adapter.get('size_class')
        min_emp, max_emp = parse_employee_count(size_class)
        
        if min_emp is None or min_emp < 50:
            raise DropItem(f"Employee count below threshold: {min_emp}")
        
        if min_emp > 1200:
            raise DropItem(f"Employee count above threshold: {min_emp}")
        
        # Set employee count fields
        adapter['employee_count_min'] = min_emp
        adapter['employee_count_max'] = max_emp
        
        spider.logger.debug(f"Validated item: {adapter.get('legal_name')}")
        return item


class CleaningPipeline:
    """Pipeline to clean and normalize data."""
    
    def process_item(self, item: BusinessItem, spider: Spider) -> BusinessItem:
        """Clean and normalize item data."""
        adapter = ItemAdapter(item)
        
        # Clean company name
        legal_name = adapter.get('legal_name')
        if legal_name:
            adapter['legal_name'] = clean_company_name(legal_name)
        
        # Extract state from area_title if needed
        area_title = adapter.get('area_title', '')
        if area_title and not adapter.get('state'):
            # Try to extract state from area title
            parts = area_title.split(',')
            if len(parts) > 1:
                state = parts[-1].strip()
                if len(state) == 2:  # State abbreviation
                    adapter['state'] = state.upper()
        
        # Set scraped timestamp
        adapter['scraped_at'] = datetime.utcnow()
        
        # Set source information
        adapter['source'] = 'BLS_SCRAPY'
        
        # Convert numeric fields
        numeric_fields = [
            'avg_monthly_employment',
            'total_quarterly_wages',
            'taxable_quarterly_wages',
            'quarterly_contributions',
            'avg_weekly_wage'
        ]
        
        for field in numeric_fields:
            value = adapter.get(field)
            if value and isinstance(value, str):
                try:
                    # Remove commas and convert to float
                    cleaned_value = value.replace(',', '').replace('$', '')
                    adapter[field] = float(cleaned_value) if cleaned_value else None
                except (ValueError, AttributeError):
                    adapter[field] = None
        
        spider.logger.debug(f"Cleaned item: {adapter.get('legal_name')}")
        return item


class DeduplicationPipeline:
    """Pipeline to check for and handle duplicate items."""
    
    def __init__(self):
        """Initialize deduplication pipeline."""
        self.seen_establishments = set()
    
    def process_item(self, item: BusinessItem, spider: Spider) -> BusinessItem:
        """Check for duplicate establishments."""
        adapter = ItemAdapter(item)
        
        establishment_id = adapter.get('establishment_id')
        if establishment_id:
            if establishment_id in self.seen_establishments:
                raise DropItem(f"Duplicate establishment: {establishment_id}")
            self.seen_establishments.add(establishment_id)
        
        spider.logger.debug(f"Deduplicated item: {adapter.get('legal_name')}")
        return item


class DatabasePipeline:
    """Pipeline to save items to the database."""
    
    def __init__(self):
        """Initialize database pipeline."""
        self.items_processed = 0
        self.items_saved = 0
        self.items_updated = 0
        self.items_failed = 0
    
    def open_spider(self, spider: Spider):
        """Initialize pipeline when spider opens."""
        spider.logger.info("Database pipeline opened")
    
    def close_spider(self, spider: Spider):
        """Log statistics when spider closes."""
        spider.logger.info(
            f"Database pipeline closed. "
            f"Processed: {self.items_processed}, "
            f"Saved: {self.items_saved}, "
            f"Updated: {self.items_updated}, "
            f"Failed: {self.items_failed}"
        )
    
    def process_item(self, item: BusinessItem, spider: Spider) -> BusinessItem:
        """Save item to database."""
        adapter = ItemAdapter(item)
        self.items_processed += 1
        
        try:
            with get_db_session() as db:
                # Check if company already exists
                establishment_id = adapter.get('establishment_id')
                existing = None
                
                if establishment_id:
                    existing = db.query(Company).filter_by(
                        source='BLS_SCRAPY',
                        source_id=establishment_id
                    ).first()
                
                if existing:
                    # Update existing record
                    self._update_company(existing, adapter)
                    self.items_updated += 1
                    spider.logger.debug(f"Updated company: {existing.name}")
                else:
                    # Create new record
                    new_company = self._create_company(adapter)
                    db.add(new_company)
                    self.items_saved += 1
                    spider.logger.debug(f"Saved new company: {new_company.name}")
                
                db.commit()
                
        except Exception as e:
            self.items_failed += 1
            spider.logger.error(f"Failed to save item: {e}")
            # Don't drop the item, just log the error
        
        return item
    
    def _create_company(self, adapter: ItemAdapter) -> Company:
        """Create a new Company instance from item data."""
        return Company(
            name=adapter.get('legal_name'),
            legal_name=adapter.get('legal_name'),
            dba_name=adapter.get('trade_name'),
            naics_code=adapter.get('naics_code'),
            naics_description=adapter.get('naics_title'),
            employee_count_min=adapter.get('employee_count_min'),
            employee_count_max=adapter.get('employee_count_max'),
            employee_range=f"{adapter.get('employee_count_min')}-{adapter.get('employee_count_max')}" 
                          if adapter.get('employee_count_max') else str(adapter.get('employee_count_min')),
            state=adapter.get('state'),
            county=adapter.get('county'),
            source='BLS_SCRAPY',
            source_id=adapter.get('establishment_id'),
            source_url=adapter.get('source_url'),
            extra_data={
                'area_fips': adapter.get('area_fips'),
                'area_title': adapter.get('area_title'),
                'size_class': adapter.get('size_class'),
                'avg_monthly_employment': adapter.get('avg_monthly_employment'),
                'total_quarterly_wages': adapter.get('total_quarterly_wages'),
                'taxable_quarterly_wages': adapter.get('taxable_quarterly_wages'),
                'quarterly_contributions': adapter.get('quarterly_contributions'),
                'avg_weekly_wage': adapter.get('avg_weekly_wage'),
                'ownership_code': adapter.get('ownership_code'),
                'ownership_title': adapter.get('ownership_title'),
                'year': adapter.get('year'),
                'quarter': adapter.get('quarter'),
                'data_disclosure_flag': adapter.get('data_disclosure_flag'),
                'scraped_at': adapter.get('scraped_at').isoformat() if adapter.get('scraped_at') else None
            }
        )
    
    def _update_company(self, company: Company, adapter: ItemAdapter):
        """Update existing company with new data."""
        # Update basic fields
        if adapter.get('legal_name'):
            company.legal_name = adapter.get('legal_name')
            company.name = adapter.get('legal_name')
        
        if adapter.get('trade_name'):
            company.dba_name = adapter.get('trade_name')
        
        if adapter.get('naics_code'):
            company.naics_code = adapter.get('naics_code')
        
        if adapter.get('naics_title'):
            company.naics_description = adapter.get('naics_title')
        
        if adapter.get('employee_count_min'):
            company.employee_count_min = adapter.get('employee_count_min')
            company.employee_count_max = adapter.get('employee_count_max')
            company.employee_range = f"{adapter.get('employee_count_min')}-{adapter.get('employee_count_max')}" \
                                   if adapter.get('employee_count_max') else str(adapter.get('employee_count_min'))
        
        if adapter.get('state'):
            company.state = adapter.get('state')
        
        if adapter.get('county'):
            company.county = adapter.get('county')
        
        # Update extra_data with latest information
        if company.extra_data is None:
            company.extra_data = {}
        
        company.extra_data.update({
            'area_fips': adapter.get('area_fips'),
            'area_title': adapter.get('area_title'),
            'size_class': adapter.get('size_class'),
            'avg_monthly_employment': adapter.get('avg_monthly_employment'),
            'total_quarterly_wages': adapter.get('total_quarterly_wages'),
            'taxable_quarterly_wages': adapter.get('taxable_quarterly_wages'),
            'quarterly_contributions': adapter.get('quarterly_contributions'),
            'avg_weekly_wage': adapter.get('avg_weekly_wage'),
            'ownership_code': adapter.get('ownership_code'),
            'ownership_title': adapter.get('ownership_title'),
            'year': adapter.get('year'),
            'quarter': adapter.get('quarter'),
            'data_disclosure_flag': adapter.get('data_disclosure_flag'),
            'last_scraped_at': adapter.get('scraped_at').isoformat() if adapter.get('scraped_at') else None
        })
        
        company.updated_at = datetime.utcnow()


class QueueingPipeline:
    """Pipeline to queue companies for enrichment."""
    
    def __init__(self):
        """Initialize queueing pipeline."""
        self.queued_count = 0
    
    def close_spider(self, spider: Spider):
        """Log queueing statistics."""
        spider.logger.info(f"Queued {self.queued_count} companies for enrichment")
    
    def process_item(self, item: BusinessItem, spider: Spider) -> BusinessItem:
        """Queue qualifying companies for enrichment."""
        adapter = ItemAdapter(item)
        
        # Only queue companies that meet our criteria
        min_employees = adapter.get('employee_count_min', 0)
        if 50 <= min_employees <= 1200:
            try:
                # TODO: Implement queue publishing
                # This would publish to RabbitMQ for enrichment
                self.queued_count += 1
                spider.logger.debug(f"Queued for enrichment: {adapter.get('legal_name')}")
                
            except Exception as e:
                spider.logger.error(f"Failed to queue item: {e}")
        
        return item 