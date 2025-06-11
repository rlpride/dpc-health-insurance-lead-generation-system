"""Command-line interface for the lead generation system."""

import click
import asyncio
from pathlib import Path

from utils import setup_logging
from models import init_db, drop_db, get_db_session, Company
from scrapers import BLSScraper, SamGovScraper
from workers import EnrichmentWorker, ScoringWorker, CrmSyncWorker
from lead_generation_system.enrichment_service import EnrichmentService
from config.settings import Settings


@click.group()
@click.option('--debug/--no-debug', default=False, help='Enable debug logging')
def main(debug: bool):
    """DPC Health Insurance Lead Generation System CLI."""
    setup_logging("DEBUG" if debug else "INFO")


@main.command()
def init_database():
    """Initialize database tables."""
    click.echo("Initializing database...")
    try:
        init_db()
        click.echo("Database initialized!")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.confirmation_option(prompt='Are you sure you want to drop all tables?')
def drop_database():
    """Drop all database tables."""
    click.echo("Dropping database tables...")
    try:
        drop_db()
        click.echo("Database tables dropped!")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option('--worker-type', type=click.Choice(['enrichment', 'scoring', 'crm_sync']), 
              required=True, help='Type of worker to start')
@click.option('--worker-id', help='Worker ID (optional)')
@click.option('--max-messages', type=int, default=100, help='Maximum messages to process')
def start_worker(worker_type: str, worker_id: str, max_messages: int):
    """Start a worker process."""
    click.echo(f"Starting {worker_type} worker...")
    
    worker_classes = {
        'enrichment': EnrichmentWorker,
        'scoring': ScoringWorker,
        'crm_sync': CrmSyncWorker
    }
    
    try:
        worker_class = worker_classes[worker_type]
        worker = worker_class(worker_id)
        worker.start(max_messages=max_messages)
    except KeyboardInterrupt:
        click.echo("Worker stopped by user")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option('--state', help='Filter by state (e.g., CA, NY)')
@click.option('--limit', type=int, default=10, help='Number of companies to enrich')
@click.option('--force', is_flag=True, help='Force re-enrichment even if recently enriched')
def enrich_companies(state: str, limit: int, force: bool):
    """Enrich companies with decision-maker contacts."""
    click.echo(f"Starting enrichment for {limit} companies...")
    
    try:
        settings = Settings()
        enrichment_service = EnrichmentService(settings)
        
        # Get companies to enrich
        with get_db_session() as db:
            query = db.query(Company)
            
            if state:
                query = query.filter(Company.state == state.upper())
            
            if not force:
                query = query.filter(Company.enrichment_status != "enriched")
            
            companies = query.limit(limit).all()
            
            if not companies:
                click.echo("No companies found to enrich")
                return
            
            click.echo(f"Found {len(companies)} companies to enrich")
            
            # Enrich companies
            for i, company in enumerate(companies, 1):
                click.echo(f"[{i}/{len(companies)}] Enriching {company.name}...")
                
                try:
                    success, contacts = asyncio.run(enrichment_service.enrich_company(company))
                    
                    if success:
                        click.echo(f"  ✓ Found {len(contacts)} decision-makers")
                    else:
                        click.echo(f"  ✗ No contacts found")
                        
                except Exception as e:
                    click.echo(f"  ✗ Error: {str(e)}")
            
            click.echo("Enrichment complete!")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.argument('company_name')
@click.option('--state', help='Company state')
@click.option('--domain', help='Company email domain')
def test_enrichment(company_name: str, state: str, domain: str):
    """Test enrichment for a specific company."""
    click.echo(f"Testing enrichment for: {company_name}")
    
    try:
        settings = Settings()
        enrichment_service = EnrichmentService(settings)
        
        # Create a temporary company object for testing
        from uuid import uuid4
        test_company = Company(
            id=uuid4(),
            name=company_name,
            state=state,
            email_domain=domain,
            source="test"
        )
        
        # Find decision-makers
        click.echo("Finding decision-makers...")
        decision_makers = asyncio.run(enrichment_service.find_decision_makers(test_company))
        
        if not decision_makers:
            click.echo("No decision-makers found")
            return
        
        click.echo(f"Found {len(decision_makers)} decision-makers:")
        
        for i, contact in enumerate(decision_makers, 1):
            click.echo(f"\n{i}. {contact.get('full_name', 'Unknown')}")
            click.echo(f"   Title: {contact.get('title', 'Unknown')}")
            click.echo(f"   Email: {contact.get('email', 'Not found')}")
            click.echo(f"   Source: {contact.get('source', 'Unknown')}")
            click.echo(f"   Department: {contact.get('department', 'Unknown')}")
        
        # Test email verification
        if any(c.get('email') for c in decision_makers):
            click.echo("\nTesting email verification...")
            verified_contacts = asyncio.run(enrichment_service.verify_contacts(decision_makers))
            
            verified_count = sum(1 for c in verified_contacts if c.get('email_verified'))
            click.echo(f"Email verification: {verified_count}/{len(decision_makers)} verified")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
def enrichment_stats():
    """Show enrichment statistics and API usage."""
    click.echo("Getting enrichment statistics...")
    
    try:
        settings = Settings()
        enrichment_service = EnrichmentService(settings)
        
        stats = asyncio.run(enrichment_service.get_enrichment_stats())
        
        if not stats:
            click.echo("No statistics available")
            return
        
        click.echo(f"\n=== Enrichment Statistics ({stats.get('month', 'N/A')}) ===")
        
        # API Usage
        click.echo("\nAPI Usage:")
        for provider, usage in stats.get('api_usage', {}).items():
            click.echo(f"  {provider.title()}:")
            click.echo(f"    Requests: {usage['total_requests']} (success rate: {usage['success_rate']:.1%})")
            click.echo(f"    Cost: ${usage['total_cost']:.2f}")
        
        # Companies
        companies = stats.get('companies', {})
        click.echo(f"\nCompanies:")
        click.echo(f"  Total: {companies.get('total', 0)}")
        click.echo(f"  Enriched: {companies.get('enriched', 0)} ({companies.get('enrichment_rate', 0):.1%})")
        
        # Contacts
        contacts = stats.get('contacts', {})
        click.echo(f"\nContacts:")
        click.echo(f"  Total: {contacts.get('total', 0)}")
        click.echo(f"  Verified: {contacts.get('verified', 0)} ({contacts.get('verification_rate', 0):.1%})")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option('--scraper', type=click.Choice(['bls', 'sam_gov']), required=True)
@click.option('--state', help='State to scrape (2-letter code)')
@click.option('--limit', type=int, default=100, help='Maximum companies to collect')
def collect_companies(scraper: str, state: str, limit: int):
    """Collect companies using specified scraper."""
    click.echo(f"Starting {scraper.upper()} scraper...")
    
    scrapers = {
        'bls': BLSScraper,
        'sam_gov': SamGovScraper
    }
    
    try:
        scraper_class = scrapers[scraper]
        scraper_instance = scraper_class()
        
        # Run scraper with parameters
        if scraper == 'bls':
            companies = scraper_instance.scrape_by_state(state, limit=limit)
        else:
            companies = scraper_instance.scrape_companies(limit=limit, state=state)
        
        click.echo(f"Collected {len(companies)} companies")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main() 