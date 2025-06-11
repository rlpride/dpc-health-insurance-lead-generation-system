# BLS QCEW Scrapy Spider

This directory contains a Scrapy spider for extracting business data from the U.S. Bureau of Labor Statistics (BLS) Quarterly Census of Employment and Wages (QCEW) API.

## Features

- **Rate Limiting**: 2-second delay between requests (configurable)
- **Employee Filtering**: Targets businesses with 50-1200 employees
- **Industry Focus**: Extracts NAICS codes, location, and size classifications
- **Error Handling**: Comprehensive retry logic with exponential backoff
- **Compliance Logging**: Full request/response logging for compliance tracking
- **Data Validation**: Multi-stage validation and cleaning pipeline
- **Database Integration**: Saves data to PostgreSQL with deduplication

## Components

### Spider (`spiders/bls_spider.py`)
- Main spider that crawls BLS QCEW API
- Configurable parameters for year, quarter, states, NAICS codes
- Targets specific employee size ranges (50-1200 employees)

### Items (`items.py`)
- Structured data definitions for scraped business information
- Built-in data processors for cleaning and validation

### Middlewares (`middlewares.py`)
- **RateLimitMiddleware**: Enforces API rate limits
- **ComplianceLoggingMiddleware**: Logs all requests for compliance
- **APIKeyMiddleware**: Adds BLS API key to requests
- **RetryMiddleware**: Handles failed requests with backoff

### Pipelines (`pipelines.py`)
- **ValidationPipeline**: Validates required fields and employee ranges
- **CleaningPipeline**: Normalizes and cleans data
- **DeduplicationPipeline**: Removes duplicate establishments
- **DatabasePipeline**: Saves data to PostgreSQL database
- **QueueingPipeline**: Queues companies for enrichment

## Usage

### Basic Usage

```bash
# Run spider with default settings (previous year, Q4)
cd scrapy_spiders
scrapy crawl bls_qcew

# Run for specific year and quarter
scrapy crawl bls_qcew -a year=2023 -a quarter=3

# Target specific states
scrapy crawl bls_qcew -a states=CA,TX,FL

# Target specific NAICS codes  
scrapy crawl bls_qcew -a naics=23,42,54

# Target specific size classes
scrapy crawl bls_qcew -a size_classes=5,6,7
```

### Using the Runner Script

```bash
# Show what would be scraped (dry run)
python scripts/run_bls_spider.py --dry-run

# Run with custom parameters
python scripts/run_bls_spider.py --year 2023 --quarter 4 --states CA,TX,FL

# Adjust rate limiting
python scripts/run_bls_spider.py --delay 3.0 --log-level DEBUG

# Output to specific format
python scripts/run_bls_spider.py --output-format json --output-dir data/
```

### Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `year` | Year to scrape | Previous year |
| `quarter` | Quarter (1-4) | 4 |
| `states` | Comma-separated state codes | 20 target states |
| `naics` | Comma-separated NAICS codes | 12 target industries |
| `size_classes` | Employee size classes | 5,6,7 (50-499 employees) |
| `delay` | Seconds between requests | 2.0 |
| `concurrent_requests` | Concurrent requests | 1 |

## Target Data

### Industries (NAICS Codes)
- 23: Construction
- 31-33: Manufacturing
- 42: Wholesale Trade
- 44-45: Retail Trade  
- 48-49: Transportation
- 51: Information
- 52: Finance and Insurance
- 53: Real Estate
- 54: Professional Services
- 56: Administrative Services
- 62: Health Care
- 72: Accommodation and Food

### Employee Size Classes
- Class 5: 50-99 employees
- Class 6: 100-249 employees  
- Class 7: 250-499 employees

### Geographic Coverage
20 target states with high business density: CA, TX, FL, NY, PA, IL, OH, GA, NC, MI, NJ, VA, WA, AZ, MA, TN, IN, MO, MD, WI

## Data Fields

### Company Information
- `legal_name`: Official business name
- `trade_name`: DBA/trade name
- `establishment_id`: BLS establishment ID
- `naics_code`: Industry classification
- `naics_title`: Industry description

### Location Data
- `state`: State abbreviation
- `county`: County name
- `area_fips`: FIPS area code
- `area_title`: Geographic area description

### Employment Data
- `size_class`: BLS size classification
- `employee_count_min/max`: Employee range
- `avg_monthly_employment`: Average monthly employees
- `total_quarterly_wages`: Total wages paid
- `avg_weekly_wage`: Average weekly wage

### Metadata
- `year`/`quarter`: Data period
- `source`: Data source identifier
- `scraped_at`: Extraction timestamp
- `data_disclosure_flag`: Data quality flags

## Rate Limiting & Compliance

### API Limits
- 2-second delay between requests (default)
- Single concurrent request to respect API
- Adaptive throttling based on response times
- Comprehensive retry logic for failures

### Compliance Features
- All requests logged with timestamps
- User-Agent identifies system and contact
- Request/response tracking in database
- Error logging with full context
- Performance metrics collection

### Monitoring
- Request count tracking
- Response time monitoring  
- Error rate calculation
- Success rate reporting
- Database save statistics

## Database Integration

The spider integrates with the existing PostgreSQL database:

- **Companies Table**: Saves extracted business data
- **Scraping Logs**: Tracks all scraping operations
- **API Usage**: Monitors API costs and limits
- **Lead Scores**: Enables downstream scoring

## Error Handling

### Retry Logic
- Exponential backoff (2^attempt seconds)
- Configurable retry attempts (default: 3)
- Specific HTTP codes for retry (5xx, 429, 408)
- Request timeout handling

### Data Validation
- Required field checking
- Employee count validation
- NAICS code verification  
- Geographic data validation
- Duplicate detection

### Logging
- Structured logging with context
- Error classification and counting
- Performance metric tracking
- Compliance audit trail

## Output Formats

### JSON Output
```json
{
  "legal_name": "Example Company Inc",
  "naics_code": "54",
  "employee_count_min": 100,
  "employee_count_max": 249,
  "state": "CA",
  "county": "Los Angeles",
  "avg_weekly_wage": 1250.50
}
```

### CSV Output
Tabular format suitable for analysis tools.

### Database Storage
Normalized storage in PostgreSQL for integration with enrichment pipeline.

## Development

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export BLS_API_KEY=your_api_key_here
export DATABASE_URL=postgresql://user:pass@localhost/db

# Initialize database
python -m alembic upgrade head
```

### Testing
```bash
# Run with small dataset
scrapy crawl bls_qcew -a states=CA -a naics=54 -a year=2023

# Dry run to check configuration
python scripts/run_bls_spider.py --dry-run --states CA --naics 54
```

### Monitoring
- Check `logs/scrapy.log` for spider activity
- Monitor database `scraping_log` table for operations
- Review `results/` directory for output files

## API Reference

### BLS QCEW API
- Base URL: `https://data.bls.gov/cew/data/api`
- Format: `/{year}/q{quarter}/area/{state}.json`
- Authentication: API key in query parameter
- Rate limits: Respected via delays
- Documentation: https://www.bls.gov/cew/about-data/downloadable-file-layouts/quarterly/naics-based-quarterly-layout.htm 