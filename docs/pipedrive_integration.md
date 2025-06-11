# Pipedrive CRM Integration

This document provides comprehensive information about the Pipedrive CRM integration for the DPC Health Insurance Lead Generation System.

## Overview

The Pipedrive integration automatically synchronizes lead data from your database to Pipedrive CRM, including:

- **Organizations**: Company records with lead scores and industry information
- **Contacts**: Decision-makers and key personnel with custom fields
- **Deals**: Automatically created for high-scoring leads (score ≥ 80)
- **Custom Fields**: Lead scores, industry data, and enrichment information
- **Tracking**: Sync status and error handling with retry logic

## Features

- **Rate Limiting**: Built-in rate limiting (1 request/second by default)
- **Retry Logic**: Exponential backoff with 3 retry attempts
- **Custom Fields**: Automatically creates required custom fields in Pipedrive
- **Sync Tracking**: Tracks which records have been synced to prevent duplicates
- **Deal Creation**: Creates deals for leads scoring above threshold
- **Monitoring**: Real-time monitoring and health checks

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# Pipedrive Configuration
PIPEDRIVE_API_KEY=your_pipedrive_api_key_here
PIPEDRIVE_DOMAIN=your-company  # Your Pipedrive domain (e.g., 'acme-corp')

# Optional: Adjust thresholds
HIGH_SCORE_THRESHOLD=80  # Minimum score for deal creation
```

### Getting Your Pipedrive API Key

1. Log into your Pipedrive account
2. Go to Settings → Personal → API
3. Copy your API token
4. Set it as `PIPEDRIVE_API_KEY` in your environment

### Getting Your Pipedrive Domain

Your domain is the part before `.pipedrive.com` in your Pipedrive URL.
For example, if your URL is `https://acme-corp.pipedrive.com`, your domain is `acme-corp`.

## Custom Fields

The integration automatically creates the following custom fields in Pipedrive:

### Organization Fields
- **Lead Score** (Integer): Overall lead score (0-100)
- **NAICS Code** (Text): Industry classification code
- **Industry Category** (Text): Industry category description
- **Employee Count Min** (Integer): Minimum employee count
- **Employee Count Max** (Integer): Maximum employee count
- **Data Source** (Text): Source of the data (BLS, SAM.gov, etc.)
- **Last Enriched** (Date): When the data was last enriched

### Person Fields
- **Lead Score** (Integer): Company's lead score
- **Seniority Level** (Text): C-Level, VP, Director, Manager, etc.
- **Is Decision Maker** (Text): Yes/No indicator
- **Data Source** (Text): Source of contact data
- **LinkedIn URL** (Text): LinkedIn profile URL

### Deal Fields
- **Lead Score** (Integer): Company's lead score
- **Deal Source** (Text): Source that generated the lead
- **Company Industry** (Text): Industry category
- **Employee Count** (Text): Employee count range

## Usage

### CLI Commands

#### Sync All Pending Records
```bash
python cli.py pipedrive sync --limit 100
```

#### Sync High-Priority Leads Only
```bash
python cli.py pipedrive sync --high-priority-only --limit 50
```

#### Sync Specific Company
```bash
python cli.py pipedrive sync-company --company-name "Acme Corporation"
# or
python cli.py pipedrive sync-company --company-id "uuid-here"
```

#### View Sync Statistics
```bash
python cli.py pipedrive stats
```

### Background Worker

Run the continuous sync worker:

```bash
python cli.py worker pipedrive
```

The worker will:
- Run sync cycles every 30 minutes
- Process up to 100 records per cycle
- Automatically create deals for high-scoring leads
- Handle rate limiting and retries

### Monitoring

#### View Live Dashboard
```bash
python scripts/pipedrive_monitor.py --mode dashboard
```

#### Generate Report
```bash
python scripts/pipedrive_monitor.py --mode report
```

#### Check Health Status
```bash
python scripts/pipedrive_monitor.py --mode health
```

#### JSON Output
```bash
python scripts/pipedrive_monitor.py --mode report --output json
```

## Programmatic Usage

### Basic Sync Example

```python
import asyncio
from sqlalchemy.orm import sessionmaker
from api.pipedrive import PipedriveIntegrationService
from models.company import Company

# Setup database session
db = get_database_session()

async def sync_companies():
    async with PipedriveIntegrationService(db) as service:
        # Sync pending records
        stats = await service.sync_pending_records(limit=50)
        print(f"Synced {stats['companies_synced']} companies")
        
        # Get sync statistics
        sync_stats = service.get_sync_statistics()
        print(f"Total high-score companies: {sync_stats['high_score_companies']}")

asyncio.run(sync_companies())
```

### Sync Specific Company

```python
async def sync_specific_company(company_id: str):
    async with PipedriveIntegrationService(db) as service:
        company = db.query(Company).filter(Company.id == company_id).first()
        
        if company:
            success = await service.sync_company(company)
            if success and company.lead_score >= 80:
                await service.create_deal_for_high_score_lead(company)
```

### Custom Integration

```python
from api.pipedrive import PipedriveClient

async def custom_pipedrive_operation():
    async with PipedriveClient(api_key, domain) as client:
        # Create organization
        org_data = {
            'name': 'Custom Company',
            'address_locality': 'San Francisco',
            'address_admin_area_level_1': 'CA'
        }
        org = await client.create_organization(org_data)
        
        # Create person
        person_data = {
            'name': 'John Doe',
            'org_id': org['id'],
            'email': [{'value': 'john@example.com', 'primary': True}]
        }
        person = await client.create_person(person_data)
        
        # Create deal
        deal_data = {
            'title': 'Health Insurance Opportunity',
            'org_id': org['id'],
            'person_id': person['id'],
            'value': 15000,
            'currency': 'USD'
        }
        deal = await client.create_deal(deal_data)
```

## Data Flow

### 1. Company Sync Process

1. **Check Status**: Skip if already synced
2. **Search Existing**: Look for existing organization by name
3. **Create/Update**: Create new or update existing organization
4. **Map Fields**: Map company data to Pipedrive fields
5. **Update Database**: Mark as synced and store Pipedrive ID

### 2. Contact Sync Process

1. **Company First**: Ensure parent company is synced
2. **Search Existing**: Look for existing person by email/name
3. **Create/Update**: Create new or update existing person
4. **Link Organization**: Connect to parent organization
5. **Custom Fields**: Add lead score and decision-maker status

### 3. Deal Creation Process

1. **Score Check**: Only for leads scoring ≥ 80
2. **Find Contact**: Identify primary decision-maker
3. **Estimate Value**: Calculate deal value based on company size
4. **Create Deal**: Create opportunity in first pipeline stage

## Lead Scoring and Deal Creation

### Deal Value Estimation

The system estimates deal values based on company size:

- **500+ employees**: $50,000 base value
- **200-499 employees**: $25,000 base value
- **100-199 employees**: $15,000 base value
- **50-99 employees**: $10,000 base value
- **<50 employees**: $5,000 base value

Values are further adjusted by lead score:
- **Score 90+**: 1.5x multiplier
- **Score 85-89**: 1.3x multiplier
- **Score 80-84**: 1.1x multiplier

### High-Priority Lead Criteria

Leads are considered high-priority if they have:
- Lead score ≥ 80 (configurable via `HIGH_SCORE_THRESHOLD`)
- Complete company information
- At least one decision-maker contact

## Error Handling

### Common Issues and Solutions

#### API Rate Limiting
- **Error**: `PipedriveRateLimitError`
- **Solution**: Built-in retry logic with exponential backoff
- **Configuration**: Adjust `rate_limit_per_second` in client initialization

#### Authentication Errors
- **Error**: HTTP 401 Unauthorized
- **Solution**: Verify API key and domain in configuration
- **Check**: Ensure API key has sufficient permissions

#### Duplicate Records
- **Prevention**: Built-in search before creation
- **Tracking**: Pipedrive IDs stored in database
- **Recovery**: Re-run sync to link existing records

#### Custom Field Creation Failures
- **Error**: Custom field creation fails
- **Solution**: Fields may already exist with different names
- **Fix**: Manually create fields or adjust field mapping

### Monitoring Sync Health

The health check identifies common issues:

- **Old Pending Records**: Companies pending sync for >7 days
- **High Failure Rate**: >10% of sync attempts failing
- **High-Score Backlog**: >5 high-scoring leads awaiting sync

Run health checks regularly:
```bash
python scripts/pipedrive_monitor.py --mode health
```

## Performance Optimization

### Batch Processing

Process records in batches to optimize performance:

```python
# Sync in smaller batches for better control
await service.sync_pending_records(limit=25)
```

### Rate Limiting Configuration

Adjust rate limiting based on your Pipedrive plan:

```python
# Conservative (free plans)
client = PipedriveClient(api_key, domain, rate_limit_per_second=0.5)

# Standard (paid plans)
client = PipedriveClient(api_key, domain, rate_limit_per_second=1.0)

# Aggressive (high-tier plans)
client = PipedriveClient(api_key, domain, rate_limit_per_second=2.0)
```

### Database Indexing

Ensure proper indexes for sync queries:

```sql
-- Index for pending sync queries
CREATE INDEX idx_companies_sync_status ON companies(crm_sync_status);
CREATE INDEX idx_contacts_sync_status ON contacts(crm_sync_status);

-- Index for high-score lead queries
CREATE INDEX idx_companies_high_score ON companies(lead_score) WHERE lead_score >= 80;
```

## Troubleshooting

### Debug Mode

Enable debug logging for detailed information:

```bash
python cli.py --debug pipedrive sync
```

### Sync Status Reset

If you need to reset sync status for testing:

```sql
-- Reset all companies to pending
UPDATE companies SET crm_sync_status = 'pending', pipedrive_id = NULL;

-- Reset specific company
UPDATE companies SET crm_sync_status = 'pending', pipedrive_id = NULL 
WHERE name = 'Company Name';
```

### Manual Field Creation

If custom fields aren't created automatically:

```python
async def create_custom_fields():
    async with PipedriveClient(api_key, domain) as client:
        await client.create_custom_field('org', 'Lead Score', 'int')
        await client.create_custom_field('person', 'Is Decision Maker', 'varchar')
        await client.create_custom_field('deal', 'Deal Source', 'varchar')
```

### Verify Integration

Test the integration with a single record:

```bash
# Find a test company
python cli.py pipedrive sync-company --company-name "Test Company"

# Check the results in Pipedrive
python cli.py pipedrive stats
```

## Best Practices

1. **Start Small**: Begin with a small batch to test the integration
2. **Monitor Regularly**: Use the monitoring dashboard to track progress
3. **Handle Failures**: Review failed syncs and resolve issues promptly
4. **Custom Fields**: Don't modify custom fields created by the integration
5. **Backup Data**: Always backup your Pipedrive data before major operations
6. **Rate Limits**: Respect Pipedrive API rate limits to avoid throttling
7. **Data Quality**: Ensure high data quality before syncing to CRM

## Support

For issues with the Pipedrive integration:

1. Check the monitoring dashboard for health status
2. Review application logs for error details
3. Verify API credentials and permissions
4. Test with a single record first
5. Check Pipedrive API documentation for field requirements

## API Reference

The integration uses Pipedrive API v1. Key endpoints:

- `GET /organizationFields` - List organization custom fields
- `POST /organizations` - Create organization
- `GET /organizations/search` - Search organizations
- `POST /persons` - Create person
- `GET /persons/search` - Search persons
- `POST /deals` - Create deal

For complete API documentation, visit: https://developers.pipedrive.com/docs/api/v1