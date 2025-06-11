# Enrichment Module Documentation

## Overview

The enrichment module is a comprehensive system for finding and verifying decision-maker contacts at companies using multiple APIs and fallback strategies. It includes:

1. **Apollo.io API integration** - Primary source for finding contacts
2. **Proxycurl API integration** - Fallback for LinkedIn-based contact discovery
3. **Dropcontact API integration** - Email verification and enrichment
4. **Smart caching** - Avoids duplicate lookups using Redis
5. **Cost tracking** - Monitors API usage and costs
6. **Monthly limits** - Prevents overspending on API calls

## Target Decision Makers

The module specifically targets:

### HR & Benefits
- HR Directors
- Human Resources Directors  
- Benefits Managers/Directors
- Compensation Managers
- People Operations
- Employee Benefits Managers

### Finance
- CFOs (Chief Financial Officers)
- VP Finance
- Finance Directors
- Controllers
- Treasurers

### Executive Level
- CEOs
- Presidents
- COOs
- Owners/Founders

## API Integrations

### Apollo.io
- **Purpose**: Primary contact discovery
- **Features**: People search with title/company filtering
- **Cost**: ~$0.01-0.05 per search
- **Rate Limits**: Configurable monthly limits

### Proxycurl
- **Purpose**: Fallback contact discovery via LinkedIn
- **Features**: Company employee discovery, profile enrichment
- **Cost**: ~$0.10-0.15 per request
- **Rate Limits**: Configurable monthly limits

### Dropcontact
- **Purpose**: Email verification and enrichment
- **Features**: Batch email verification, contact data enhancement
- **Cost**: ~$0.01-0.03 per verification
- **Rate Limits**: Configurable monthly limits

## Configuration

Set up API keys in your environment:

```bash
# Apollo.io
APOLLO_API_KEY=your_apollo_api_key_here

# Proxycurl
PROXYCURL_API_KEY=your_proxycurl_api_key_here

# Dropcontact
DROPCONTACT_API_KEY=your_dropcontact_api_key_here

# Redis for caching
REDIS_URL=redis://localhost:6379/0

# Monthly API limits
APOLLO_MONTHLY_LIMIT=10000
PROXYCURL_MONTHLY_LIMIT=5000
DROPCONTACT_MONTHLY_LIMIT=20000
```

## Usage

### CLI Commands

#### Test enrichment for a specific company:
```bash
python cli.py test-enrichment "Acme Corp" --state CA --domain acmecorp.com
```

#### Enrich companies from database:
```bash
# Enrich 10 companies
python cli.py enrich-companies --limit 10

# Enrich companies in California only
python cli.py enrich-companies --state CA --limit 5

# Force re-enrichment of already enriched companies
python cli.py enrich-companies --force --limit 5
```

#### View enrichment statistics:
```bash
python cli.py enrichment-stats
```

#### Start enrichment worker:
```bash
python cli.py start-worker --worker-type enrichment
```

### Programmatic Usage

```python
from lead_generation_system.enrichment_service import EnrichmentService
from config.settings import Settings
from models import Company

# Initialize service
settings = Settings()
enrichment_service = EnrichmentService(settings)

# Enrich a company
company = Company(name="Acme Corp", state="CA")
success, contacts = await enrichment_service.enrich_company(company)

if success:
    print(f"Found {len(contacts)} decision-makers")
    for contact in contacts:
        print(f"- {contact.full_name}: {contact.title}")
```

## Caching Strategy

The module implements intelligent caching to avoid duplicate API calls:

- **Cache Key**: Based on company name, state, and domain
- **TTL**: 24 hours for contact searches
- **Storage**: Redis with automatic expiration
- **Cache Invalidation**: Automatic cleanup of expired entries

## Cost Tracking

All API usage is automatically tracked in the database:

- **Provider**: Which API was used (apollo, proxycurl, dropcontact)
- **Request Type**: Type of operation (search, verify, enrich)
- **Cost**: Calculated cost per request
- **Monthly Totals**: Aggregated usage by month
- **Success Rates**: Track API reliability

## Fallback Strategy

1. **Apollo First**: Try Apollo.io for contact discovery
2. **Proxycurl Fallback**: If <3 contacts found, try Proxycurl
3. **Email Verification**: Verify all found emails with Dropcontact
4. **Deduplication**: Remove duplicates based on email/name
5. **Prioritization**: Sort by executive level, then HR, then others

## Data Models

### Contact Fields
- `full_name`, `first_name`, `last_name`
- `title`, `department`
- `email`, `email_verified`, `email_status`
- `phone`, `linkedin_url`
- `source` (apollo/proxycurl), `confidence_score`
- `is_decision_maker`, `company_id`

### API Usage Tracking
- `provider`, `request_type`, `cost`
- `records_returned`, `success`
- `month`, `created_at`

## Error Handling

The module includes comprehensive error handling:

- **API Failures**: Graceful fallback to alternative providers
- **Rate Limiting**: Automatic monthly limit checking
- **Timeout Protection**: Configurable request timeouts
- **Data Validation**: Input sanitization and validation
- **Logging**: Detailed logging for debugging and monitoring

## Performance Optimization

- **Concurrent Processing**: Support for batch enrichment
- **Smart Caching**: Avoid duplicate API calls
- **Connection Pooling**: Efficient HTTP client usage
- **Async/Await**: Non-blocking operations
- **Database Optimization**: Efficient queries and indexes

## Monitoring and Alerts

Monitor the enrichment module using:

- **Database Queries**: Check API usage and costs
- **Log Analysis**: Monitor for errors and performance issues
- **Cost Tracking**: Set up alerts for budget limits
- **Success Rates**: Track API reliability metrics

## Best Practices

1. **Start Small**: Test with a few companies before bulk enrichment
2. **Monitor Costs**: Regularly check API usage and costs
3. **Update Limits**: Adjust monthly limits based on budget
4. **Cache Management**: Monitor Redis usage and memory
5. **Data Quality**: Verify enriched contacts before use
6. **Regular Updates**: Re-enrich companies quarterly

## Troubleshooting

### Common Issues

**No contacts found:**
- Check API keys are valid
- Verify company name is accurate
- Check monthly limits not exceeded

**High API costs:**
- Review monthly limits
- Optimize caching strategy  
- Reduce enrichment frequency

**Cache issues:**
- Check Redis connection
- Verify Redis memory limits
- Clear cache if needed: `redis-cli FLUSHDB`

**Database errors:**
- Check database connection
- Run database migrations
- Verify table schemas

### Getting Help

- Check logs for detailed error messages
- Use `enrichment-stats` command to view usage
- Test with `test-enrichment` command first
- Monitor database for API usage patterns