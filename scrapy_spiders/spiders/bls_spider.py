"""BLS QCEW API Spider for extracting business data."""

import json
import logging
from datetime import datetime
from typing import Iterator, Dict, Any, List, Optional
from urllib.parse import urlencode

import scrapy
from scrapy.http import Request, Response
from itemloaders import ItemLoader

from scrapy_spiders.items import BusinessItem
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BLSSpider(scrapy.Spider):
    """
    Spider to extract business data from BLS QCEW API.
    
    This spider targets businesses with 50-1200 employees across
    specified NAICS codes and geographic areas.
    """
    
    name = 'bls_qcew'
    allowed_domains = ['data.bls.gov']
    
    # Base URL for BLS QCEW API
    base_url = 'https://data.bls.gov/cew/data/api'
    
    # Target NAICS codes (2-digit) for health insurance prospects
    target_naics_codes = [
        '23',    # Construction
        '31-33', # Manufacturing 
        '42',    # Wholesale Trade
        '44-45', # Retail Trade
        '48-49', # Transportation and Warehousing
        '51',    # Information
        '52',    # Finance and Insurance
        '53',    # Real Estate
        '54',    # Professional Services
        '56',    # Administrative Services
        '62',    # Health Care
        '72',    # Accommodation and Food Services
    ]
    
    # Target states (configurable via spider arguments)
    target_states = [
        'CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI',
        'NJ', 'VA', 'WA', 'AZ', 'MA', 'TN', 'IN', 'MO', 'MD', 'WI'
    ]
    
    # Size classes to target (50-1200 employees)
    target_size_classes = ['5', '6', '7']  # 50-99, 100-249, 250-499
    
    custom_settings = {
        # Rate limiting - 2 seconds between requests
        'DOWNLOAD_DELAY': 2,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'BLS_DOWNLOAD_DELAY': 2.0,
        'BLS_RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        
        # Retry settings
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 404],
        'BLS_RETRY_TIMES': 3,
        'BLS_RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        
        # Concurrent requests
        'CONCURRENT_REQUESTS': 1,  # Conservative for API
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        
        # Enable custom middlewares
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy_spiders.middlewares.RateLimitMiddleware': 100,
            'scrapy_spiders.middlewares.ComplianceLoggingMiddleware': 200,
            'scrapy_spiders.middlewares.APIKeyMiddleware': 300,
            'scrapy_spiders.middlewares.RetryMiddleware': 400,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,  # Disable default
        },
        
        # Enable custom pipelines
        'ITEM_PIPELINES': {
            'scrapy_spiders.pipelines.ValidationPipeline': 100,
            'scrapy_spiders.pipelines.CleaningPipeline': 200,
            'scrapy_spiders.pipelines.DeduplicationPipeline': 300,
            'scrapy_spiders.pipelines.DatabasePipeline': 400,
            'scrapy_spiders.pipelines.QueueingPipeline': 500,
        },
        
        # API configuration
        'BLS_API_KEY': settings.bls_api_key if hasattr(settings, 'bls_api_key') else None,
        
        # User agent
        'USER_AGENT': 'Lead Generation System/1.0 (Compliance-Enabled; +https://yourcompany.com/contact)',
        
        # Respect robots.txt
        'ROBOTSTXT_OBEY': True,
        
        # AutoThrottle for adaptive rate limiting
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 2,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'AUTOTHROTTLE_DEBUG': True,
    }
    
    def __init__(self, year: Optional[str] = None, quarter: Optional[str] = None,
                 states: Optional[str] = None, naics: Optional[str] = None,
                 size_classes: Optional[str] = None, *args, **kwargs):
        """
        Initialize spider with optional parameters.
        
        Args:
            year: Year to scrape (default: previous year)
            quarter: Quarter to scrape (1-4, default: 4)
            states: Comma-separated state codes (default: all target states)
            naics: Comma-separated NAICS codes (default: all target codes)
            size_classes: Comma-separated size classes (default: 5,6,7)
        """
        super().__init__(*args, **kwargs)
        
        # Set parameters with defaults
        current_year = datetime.now().year
        self.year = int(year) if year else current_year - 1
        self.quarter = int(quarter) if quarter else 4
        
        # Parse comma-separated lists
        self.states = states.split(',') if states else self.target_states
        self.naics_codes = naics.split(',') if naics else self.target_naics_codes
        self.size_classes = size_classes.split(',') if size_classes else self.target_size_classes
        
        self.logger.info(
            f"Initialized BLS spider: year={self.year}, quarter={self.quarter}, "
            f"states={len(self.states)}, naics={len(self.naics_codes)}, "
            f"size_classes={self.size_classes}"
        )
    
    def start_requests(self) -> Iterator[Request]:
        """Generate initial requests for each state/NAICS combination."""
        request_count = 0
        
        for state in self.states:
            for naics_code in self.naics_codes:
                for size_class in self.size_classes:
                    url = self._build_api_url(state, naics_code, size_class)
                    
                    request_count += 1
                    self.logger.info(f"Queuing request {request_count}: {state}-{naics_code}-{size_class}")
                    
                    yield Request(
                        url=url,
                        callback=self.parse_api_response,
                        meta={
                            'state': state,
                            'naics_code': naics_code,
                            'size_class': size_class,
                            'year': self.year,
                            'quarter': self.quarter,
                        },
                        headers={
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                        }
                    )
        
        self.logger.info(f"Generated {request_count} total requests")
    
    def _build_api_url(self, state: str, naics_code: str, size_class: str) -> str:
        """Build BLS QCEW API URL for given parameters."""
        # BLS QCEW API endpoint pattern
        endpoint = f"{self.base_url}/{self.year}/q{self.quarter}/area/{state}.json"
        
        # Add query parameters
        params = {
            'naics': naics_code,
            'size': size_class,
            'ownership': '5',  # Private ownership only
        }
        
        # API key will be added by middleware
        if hasattr(self.settings, 'BLS_API_KEY') and self.settings.get('BLS_API_KEY'):
            params['registrationkey'] = self.settings.get('BLS_API_KEY')
        
        return f"{endpoint}?{urlencode(params)}"
    
    def parse_api_response(self, response: Response) -> Iterator[BusinessItem]:
        """Parse API response and extract business data."""
        try:
            data = response.json()
            
            # Extract metadata from request
            state = response.meta['state']
            naics_code = response.meta['naics_code']
            size_class = response.meta['size_class']
            year = response.meta['year']
            quarter = response.meta['quarter']
            
            self.logger.info(
                f"Processing response for {state}-{naics_code}-{size_class}: "
                f"Status {response.status}"
            )
            
            # Check for API errors
            if 'error' in data:
                self.logger.error(f"API error: {data['error']}")
                return
            
            # Extract data array
            records = data.get('data', [])
            if not records:
                self.logger.warning(f"No data found for {state}-{naics_code}-{size_class}")
                return
            
            self.logger.info(f"Found {len(records)} records for {state}-{naics_code}-{size_class}")
            
            # Process each record
            for record in records:
                try:
                    item = self._extract_business_item(record, response.meta)
                    if item:
                        yield item
                        
                except Exception as e:
                    self.logger.error(f"Error processing record: {e}")
                    continue
                    
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response: {e}")
            
        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")
    
    def _extract_business_item(self, record: Dict[str, Any], meta: Dict[str, Any]) -> Optional[BusinessItem]:
        """Extract and validate business item from API record."""
        try:
            loader = ItemLoader(item=BusinessItem())
            
            # Basic company information
            loader.add_value('establishment_id', record.get('establishment_id'))
            loader.add_value('legal_name', record.get('legal_name', '').strip())
            loader.add_value('trade_name', record.get('trade_name', '').strip())
            
            # Industry classification
            loader.add_value('naics_code', meta['naics_code'])
            loader.add_value('naics_title', record.get('naics_title', ''))
            loader.add_value('industry_code', record.get('industry_code'))
            
            # Location information
            loader.add_value('area_fips', record.get('area_fips'))
            loader.add_value('area_title', record.get('area_title', ''))
            loader.add_value('state', meta['state'])
            
            # Extract county from area_title if available
            area_title = record.get('area_title', '')
            if ',' in area_title:
                county = area_title.split(',')[0].strip()
                loader.add_value('county', county)
            
            # Size classification
            loader.add_value('size_class', meta['size_class'])
            
            # Employment and wage data
            loader.add_value('avg_monthly_employment', record.get('month1_emplvl'))
            loader.add_value('total_quarterly_wages', record.get('total_qtrly_wages'))
            loader.add_value('taxable_quarterly_wages', record.get('taxable_qtrly_wages'))
            loader.add_value('quarterly_contributions', record.get('qtrly_contributions'))
            loader.add_value('avg_weekly_wage', record.get('avg_wkly_wage'))
            
            # Data period
            loader.add_value('year', str(meta['year']))
            loader.add_value('quarter', str(meta['quarter']))
            
            # Ownership classification
            loader.add_value('ownership_code', record.get('own_code'))
            loader.add_value('ownership_title', record.get('own_title'))
            
            # Source information
            loader.add_value('source_url', record.get('url', ''))
            
            # Data quality flags
            loader.add_value('data_disclosure_flag', record.get('disclosure_code'))
            
            item = loader.load_item()
            
            # Basic validation before yielding
            if not item.get('legal_name'):
                self.logger.warning("Skipping record with no legal_name")
                return None
            
            return item
            
        except Exception as e:
            self.logger.error(f"Error extracting item: {e}")
            return None
    
    def closed(self, reason: str):
        """Called when spider closes."""
        self.logger.info(f"BLS spider closed: {reason}")
        
        # Log final statistics
        stats = self.crawler.stats
        if stats:
            self.logger.info(
                f"Final stats - "
                f"Requests: {stats.get_value('downloader/request_count', 0)}, "
                f"Responses: {stats.get_value('downloader/response_count', 0)}, "
                f"Items: {stats.get_value('item_scraped_count', 0)}, "
                f"Errors: {stats.get_value('spider_exceptions', 0)}"
            ) 