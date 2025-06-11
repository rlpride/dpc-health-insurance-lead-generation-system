"""Bureau of Labor Statistics (BLS) QCEW data scraper."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

from models import Company, get_db_session
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BLSScraper(BaseScraper):
    """Scraper for BLS Quarterly Census of Employment and Wages (QCEW) data."""
    
    BASE_URL = "https://data.bls.gov/cew/data/api"
    
    # NAICS codes for industries likely to benefit from self-funded health insurance
    TARGET_NAICS_CODES = [
        "23",    # Construction
        "31-33", # Manufacturing
        "42",    # Wholesale Trade
        "44-45", # Retail Trade
        "48-49", # Transportation and Warehousing
        "51",    # Information
        "52",    # Finance and Insurance
        "53",    # Real Estate
        "54",    # Professional Services
        "56",    # Administrative Services
        "62",    # Health Care
        "72",    # Accommodation and Food Services
    ]
    
    # States to focus on (can be configured)
    TARGET_STATES = [
        "CA", "TX", "FL", "NY", "PA", "IL", "OH", "GA", "NC", "MI",
        "NJ", "VA", "WA", "AZ", "MA", "TN", "IN", "MO", "MD", "WI"
    ]
    
    @property
    def source_name(self) -> str:
        return "BLS"
    
    @property
    def rate_limit_seconds(self) -> int:
        return self.settings.bls_rate_limit_seconds
    
    async def scrape(self, states: Optional[List[str]] = None, 
                    naics_codes: Optional[List[str]] = None,
                    year: Optional[int] = None,
                    quarter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape BLS QCEW data for specified parameters."""
        states = states or self.TARGET_STATES
        naics_codes = naics_codes or self.TARGET_NAICS_CODES
        year = year or datetime.now().year - 1  # Use previous year by default
        quarter = quarter or 4  # Use Q4 by default
        
        all_results = []
        
        for state in states:
            for naics in naics_codes:
                try:
                    logger.info(f"Scraping BLS data for state={state}, NAICS={naics}")
                    
                    # Construct API URL
                    url = f"{self.BASE_URL}/{year}/q{quarter}/area/{state}.json"
                    params = {
                        "key": self.settings.bls_api_key,
                        "naics": naics,
                        "size_class": "5"  # Size class 5 = 50-99 employees
                    }
                    
                    # Make request
                    response = await self.make_request(url, params=params)
                    data = response.json()
                    
                    # Process results
                    if "data" in data:
                        companies = self.parse_bls_response(data["data"], state, naics)
                        all_results.extend(companies)
                        self.stats["records_processed"] += len(companies)
                        
                        # Save to database
                        await self.save_companies(companies)
                    
                    # Rate limiting
                    self.rate_limit()
                    
                except Exception as e:
                    logger.error(f"Error scraping BLS data for {state}-{naics}: {str(e)}")
                    self.stats["errors"].append(f"{state}-{naics}: {str(e)}")
                    continue
        
        return all_results
    
    def parse_bls_response(self, data: List[Dict], state: str, naics: str) -> List[Dict[str, Any]]:
        """Parse BLS API response into company records."""
        companies = []
        
        for record in data:
            try:
                # Extract company information
                company_data = {
                    "name": record.get("legal_name", "").strip(),
                    "legal_name": record.get("legal_name", "").strip(),
                    "naics_code": naics,
                    "state": state,
                    "county": record.get("area_title", "").strip(),
                    "employee_count_min": self.parse_employee_range(record.get("size_class", "")),
                    "employee_count_max": self.parse_employee_range(record.get("size_class", ""), max_value=True),
                    "source": "BLS",
                    "source_id": record.get("establishment_id", ""),
                    "extra_data": {
                        "ownership": record.get("ownership", ""),
                        "annual_avg_weekly_pay": record.get("avg_annual_pay", 0),
                        "total_annual_wages": record.get("total_annual_wages", 0),
                        "taxable_annual_wages": record.get("taxable_annual_wages", 0),
                        "year": record.get("year", ""),
                        "quarter": record.get("qtr", ""),
                    }
                }
                
                # Clean and validate data
                company_data = self.clean_data(company_data)
                
                if self.validate_bls_data(company_data):
                    companies.append(company_data)
                    
            except Exception as e:
                logger.warning(f"Error parsing BLS record: {str(e)}")
                self.stats["records_failed"] += 1
                continue
        
        return companies
    
    def parse_employee_range(self, size_class: str, max_value: bool = False) -> Optional[int]:
        """Parse BLS size class into employee count."""
        size_mapping = {
            "1": (1, 4),
            "2": (5, 9),
            "3": (10, 19),
            "4": (20, 49),
            "5": (50, 99),
            "6": (100, 249),
            "7": (250, 499),
            "8": (500, 999),
            "9": (1000, None)
        }
        
        if size_class in size_mapping:
            min_emp, max_emp = size_mapping[size_class]
            return max_emp if max_value and max_emp else min_emp
        
        return None
    
    def validate_bls_data(self, data: Dict[str, Any]) -> bool:
        """Validate BLS company data."""
        # Must have a name
        if not data.get("name"):
            return False
        
        # Must have employee count in target range
        min_count = data.get("employee_count_min", 0)
        if min_count < 50 or min_count > 1200:
            return False
        
        return True
    
    async def save_companies(self, companies: List[Dict[str, Any]]):
        """Save companies to the database."""
        with get_db_session() as db:
            for company_data in companies:
                try:
                    # Check if company already exists
                    existing = db.query(Company).filter_by(
                        source="BLS",
                        source_id=company_data.get("source_id")
                    ).first()
                    
                    if existing:
                        # Update existing record
                        for key, value in company_data.items():
                            if key != "id" and value is not None:
                                setattr(existing, key, value)
                        existing.updated_at = datetime.utcnow()
                        self.stats["records_updated"] += 1
                    else:
                        # Create new record
                        new_company = Company(**company_data)
                        db.add(new_company)
                        self.stats["records_created"] += 1
                    
                    db.commit()
                    
                except Exception as e:
                    logger.error(f"Error saving company: {str(e)}")
                    db.rollback()
                    self.stats["records_failed"] += 1 