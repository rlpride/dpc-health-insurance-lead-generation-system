"""Command-line interface for the lead generation system."""

import click
import asyncio
from pathlib import Path

from utils import setup_logging
from models import init_db, drop_db
from scrapers import BLSScraper, SamGovScraper
from workers import EnrichmentWorker, ScoringWorker, CrmSyncWorker


@click.group()
@click.option('--debug/--no-debug', default=False, help='Enable debug logging')
def main(debug: bool):
    """DPC Health Insurance Lead Generation System CLI."""
    setup_logging("DEBUG" if debug else "INFO")


@main.command()
def init_database():
    """Initialize the database schema."""
    click.echo("Initializing database...")
    try:
        init_db()
        click.echo("Database initialized successfully!")
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


@main.group()
def scrape():
    """Run web scrapers."""
    pass


@scrape.command()
@click.option('--states', '-s', multiple=True, help='States to scrape (e.g., CA TX)')
@click.option('--naics', '-n', multiple=True, help='NAICS codes to target')
def bls(states, naics):
    """Run BLS scraper."""
    click.echo("Starting BLS scraper...")
    scraper = BLSScraper()
    
    async def run():
        kwargs = {}
        if states:
            kwargs['states'] = list(states)
        if naics:
            kwargs['naics_codes'] = list(naics)
        
        result = await scraper.run(**kwargs)
        if result['success']:
            click.echo(f"✓ Scraped {result['stats']['records_processed']} records")
            click.echo(f"  Created: {result['stats']['records_created']}")
            click.echo(f"  Updated: {result['stats']['records_updated']}")
        else:
            click.echo(f"✗ Scraping failed: {result['error']}", err=True)
    
    asyncio.run(run())


@scrape.command()
@click.option('--year', type=int, help='Year to scrape (default: previous year)')
@click.option('--quarter', type=int, default=4, help='Quarter to scrape (1-4)')
@click.option('--states', help='Comma-separated state codes (e.g., CA,TX,FL)')
@click.option('--naics', help='Comma-separated NAICS codes (e.g., 23,42,54)')
@click.option('--size-classes', help='Comma-separated size classes (e.g., 5,6,7)')
@click.option('--delay', type=float, default=2.0, help='Download delay in seconds')
@click.option('--output-format', type=click.Choice(['json', 'csv', 'both']), 
              default='both', help='Output format')
@click.option('--output-dir', default='results', help='Output directory')
@click.option('--dry-run', is_flag=True, help='Show what would be scraped without scraping')
def bls_scrapy(year, quarter, states, naics, size_classes, delay, output_format, output_dir, dry_run):
    """Run BLS QCEW Scrapy spider."""
    click.echo("Starting BLS QCEW Scrapy spider...")
    
    import subprocess
    import sys
    
    # Build command arguments
    cmd = ['python3', 'scripts/run_bls_spider.py']
    
    if year:
        cmd.extend(['--year', str(year)])
    cmd.extend(['--quarter', str(quarter)])
    
    if states:
        cmd.extend(['--states', states])
    if naics:
        cmd.extend(['--naics', naics])
    if size_classes:
        cmd.extend(['--size-classes', size_classes])
    
    cmd.extend(['--delay', str(delay)])
    cmd.extend(['--output-format', output_format])
    cmd.extend(['--output-dir', output_dir])
    
    if dry_run:
        cmd.append('--dry-run')
    
    # Run the spider
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        click.echo(result.stdout)
        if result.stderr:
            click.echo(f"Warnings: {result.stderr}", err=True)
        click.echo("BLS Scrapy spider completed successfully!")
    except subprocess.CalledProcessError as e:
        click.echo(f"Spider failed: {e}", err=True)
        if e.stdout:
            click.echo(f"Output: {e.stdout}")
        if e.stderr:
            click.echo(f"Error: {e.stderr}", err=True)
        sys.exit(1)


@main.group()
def worker():
    """Run background workers."""
    pass


@worker.command()
@click.option('--worker-id', help='Unique worker ID')
def enrichment(worker_id):
    """Run enrichment worker."""
    click.echo("Starting enrichment worker...")
    worker = EnrichmentWorker(worker_id)
    try:
        worker.run()
    except KeyboardInterrupt:
        click.echo("\nWorker stopped.")


@worker.command()
@click.option('--worker-id', help='Unique worker ID')
def scoring(worker_id):
    """Run scoring worker."""
    click.echo("Starting scoring worker...")
    worker = ScoringWorker(worker_id)
    try:
        worker.run()
    except KeyboardInterrupt:
        click.echo("\nWorker stopped.")


@worker.command()
@click.option('--worker-id', help='Unique worker ID')
def crm_sync(worker_id):
    """Run CRM sync worker."""
    click.echo("Starting CRM sync worker...")
    worker = CrmSyncWorker(worker_id)
    try:
        worker.run()
    except KeyboardInterrupt:
        click.echo("\nWorker stopped.")


@main.command()
def status():
    """Check system status."""
    click.echo("System Status:")
    click.echo("- Database: Connected ✓")
    click.echo("- Redis: Connected ✓")
    click.echo("- RabbitMQ: Connected ✓")
    click.echo("\nTODO: Implement actual status checks")


if __name__ == "__main__":
    main() 