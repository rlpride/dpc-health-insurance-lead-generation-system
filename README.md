# DPC Health Insurance Lead Generation System

A Python-based web scraping system that automatically identifies and qualifies businesses with 50-1200 employees as candidates for self-funded health insurance plans with Direct Primary Care (DPC).

## Features

- **Government Data Collection**: Scrapes business data from BLS and SAM.gov
- **Contact Enrichment**: Finds decision-maker contacts using Apollo.io and Proxycurl
- **Lead Scoring**: Automatically scores leads based on industry, size, and data quality
- **CRM Integration**: Syncs qualified leads to Pipedrive CRM
- **Scalable Architecture**: Uses RabbitMQ for message queuing and supports parallel processing
- **Cost Monitoring**: Tracks API usage and costs across all enrichment providers

## Project Structure

```
lead_generation_system/
├── api/                    # External API client implementations
│   ├── apollo/            # Apollo.io API client
│   ├── pipedrive/         # Pipedrive CRM client
│   └── proxycurl/         # Proxycurl API client
├── config/                # Configuration management
├── database/              # Database migrations and seeds
├── models/                # SQLAlchemy database models
├── scrapers/              # Web scrapers for data collection
│   └── government/        # Government data source scrapers
├── workers/               # Background workers for processing
├── utils/                 # Utility functions and helpers
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── scripts/              # Utility scripts
├── monitoring/           # Monitoring and dashboards
└── logs/                 # Application logs
```

## Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- RabbitMQ 3.8+
- Docker and Docker Compose (for local development)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourcompany/lead-generation-system.git
cd lead-generation-system
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment configuration:
```bash
cp env.example .env
# Edit .env with your API keys and configuration
```

5. Start infrastructure services:
```bash
docker-compose up -d
```

6. Initialize the database:
```bash
python cli.py init-database
```

## Usage

### Command Line Interface

The system provides a CLI for managing scrapers and workers:

```bash
# Run BLS scraper for specific states
python cli.py scrape bls --states CA TX FL

# Start workers
python cli.py worker enrichment
python cli.py worker scoring
python cli.py worker crm-sync

# Check system status
python cli.py status
```

### Running Scrapers

Scrapers collect business data from government sources:

```python
from scrapers import BLSScraper
import asyncio

async def run_scraper():
    scraper = BLSScraper()
    result = await scraper.run(states=["CA", "TX"])
    print(f"Scraped {result['stats']['records_processed']} records")

asyncio.run(run_scraper())
```

### Starting Workers

Workers process data through the enrichment pipeline:

```bash
# Start multiple workers for parallel processing
python cli.py worker enrichment --worker-id enrichment-1 &
python cli.py worker enrichment --worker-id enrichment-2 &
python cli.py worker scoring --worker-id scoring-1 &
```

## Configuration

Key configuration options in `.env`:

- `BLS_API_KEY`: Bureau of Labor Statistics API key
- `APOLLO_API_KEY`: Apollo.io API key for contact enrichment
- `PIPEDRIVE_API_KEY`: Pipedrive CRM API key
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `RABBITMQ_URL`: RabbitMQ connection string

See `env.example` for all available options.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest tests/unit/test_validators.py
```

### Code Style

The project uses Black for code formatting and Flake8 for linting:

```bash
# Format code
black .

# Check linting
flake8 .

# Type checking
mypy .
```

## API Documentation

### Database Models

- **Company**: Stores business information from government sources
- **Contact**: Stores decision-maker contact information
- **LeadScore**: Tracks lead scoring history and calculations
- **ScrapingLog**: Logs scraping operations for monitoring
- **ApiUsage**: Tracks API usage for cost management

### Message Queue Topics

- `companies.to_enrich`: Companies pending enrichment
- `companies.to_score`: Companies pending scoring
- `companies.to_sync`: Companies ready for CRM sync

## Monitoring

- RabbitMQ Management UI: http://localhost:15672 (admin/admin)
- pgAdmin: http://localhost:5050 (admin@example.com/admin)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary software. All rights reserved.

## Support

For support, email support@yourcompany.com or create an issue in the repository. 