"""Scrapy items for BLS business data."""

import scrapy
from itemloaders.processors import TakeFirst, MapCompose
from w3lib.html import remove_tags


def clean_text(value):
    """Clean and normalize text values."""
    if value:
        return value.strip()
    return value


def parse_employee_count(value):
    """Parse employee count from BLS size classification."""
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
    
    if value in size_mapping:
        return size_mapping[value]
    return (None, None)


class BusinessItem(scrapy.Item):
    """Item for business data from BLS QCEW API."""
    
    # Basic company information
    establishment_id = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    legal_name = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    trade_name = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    # Industry classification
    naics_code = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    naics_title = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    industry_code = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    # Location information
    area_fips = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    area_title = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    state = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    county = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    # Size classification
    size_class = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    employee_count_min = scrapy.Field()
    employee_count_max = scrapy.Field()
    avg_monthly_employment = scrapy.Field()
    
    # Employment and wage data
    total_quarterly_wages = scrapy.Field()
    taxable_quarterly_wages = scrapy.Field()
    quarterly_contributions = scrapy.Field()
    avg_weekly_wage = scrapy.Field()
    
    # Data period
    year = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    quarter = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    # Ownership classification
    ownership_code = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    ownership_title = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    # Source information
    source = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    source_url = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    # Metadata
    scraped_at = scrapy.Field()
    data_disclosure_flag = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    ) 