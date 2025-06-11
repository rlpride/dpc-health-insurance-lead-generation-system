#!/usr/bin/env python3
"""Script to run the BLS spider with various configurations."""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run BLS spider."""
    parser = argparse.ArgumentParser(description='Run BLS QCEW Spider')
    
    # Spider parameters
    parser.add_argument('--year', type=int, 
                       help='Year to scrape (default: previous year)')
    parser.add_argument('--quarter', type=int, choices=[1, 2, 3, 4],
                       default=4, help='Quarter to scrape (1-4)')
    parser.add_argument('--states', type=str,
                       help='Comma-separated state codes (e.g., CA,TX,FL)')
    parser.add_argument('--naics', type=str,
                       help='Comma-separated NAICS codes (e.g., 23,42,54)')
    parser.add_argument('--size-classes', type=str,
                       help='Comma-separated size classes (e.g., 5,6,7)')
    
    # Output options
    parser.add_argument('--output-format', choices=['json', 'csv', 'both'],
                       default='both', help='Output format')
    parser.add_argument('--output-dir', type=str, default='results',
                       help='Output directory')
    
    # Scrapy settings
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Download delay in seconds')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Log level')
    parser.add_argument('--concurrent-requests', type=int, default=1,
                       help='Number of concurrent requests')
    
    # Dry run mode
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be scraped without actually scraping')
    
    args = parser.parse_args()
    
    # Set defaults
    if not args.year:
        args.year = datetime.now().year - 1
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    if args.dry_run:
        show_dry_run_info(args)
        return
    
    # Configure Scrapy settings
    settings = get_project_settings()
    settings.set('DOWNLOAD_DELAY', args.delay)
    settings.set('CONCURRENT_REQUESTS', args.concurrent_requests)
    settings.set('LOG_LEVEL', args.log_level)
    
    # Configure output feeds
    feeds = {}
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if args.output_format in ['json', 'both']:
        feeds[f'{args.output_dir}/bls_data_{timestamp}.json'] = {
            'format': 'json',
            'encoding': 'utf8',
            'store_empty': False,
            'indent': 2,
        }
    
    if args.output_format in ['csv', 'both']:
        feeds[f'{args.output_dir}/bls_data_{timestamp}.csv'] = {
            'format': 'csv',
            'encoding': 'utf8',
            'store_empty': False,
        }
    
    settings.set('FEEDS', feeds)
    
    # Build spider arguments
    spider_args = {
        'year': str(args.year),
        'quarter': str(args.quarter),
    }
    
    if args.states:
        spider_args['states'] = args.states
    if args.naics:
        spider_args['naics'] = args.naics
    if args.size_classes:
        spider_args['size_classes'] = args.size_classes
    
    logger.info(f"Starting BLS spider with settings:")
    logger.info(f"  Year: {args.year}, Quarter: {args.quarter}")
    logger.info(f"  States: {args.states or 'all target states'}")
    logger.info(f"  NAICS: {args.naics or 'all target codes'}")
    logger.info(f"  Size Classes: {args.size_classes or 'all target sizes'}")
    logger.info(f"  Delay: {args.delay}s")
    logger.info(f"  Output: {args.output_format} to {args.output_dir}")
    
    # Run spider
    try:
        process = CrawlerProcess(settings)
        process.crawl('bls_qcew', **spider_args)
        process.start()
        
        logger.info("Spider completed successfully!")
        
    except Exception as e:
        logger.error(f"Spider failed: {e}")
        sys.exit(1)


def show_dry_run_info(args):
    """Show information about what would be scraped in dry run mode."""
    print("\n" + "="*60)
    print("DRY RUN MODE - No actual scraping will be performed")
    print("="*60)
    
    print(f"\nScraping Configuration:")
    print(f"  Year: {args.year}")
    print(f"  Quarter: {args.quarter}")
    print(f"  States: {args.states or 'CA,TX,FL,NY,PA,IL,OH,GA,NC,MI,NJ,VA,WA,AZ,MA,TN,IN,MO,MD,WI'}")
    print(f"  NAICS Codes: {args.naics or '23,31-33,42,44-45,48-49,51,52,53,54,56,62,72'}")
    print(f"  Size Classes: {args.size_classes or '5,6,7 (50-499 employees)'}")
    
    print(f"\nSpider Settings:")
    print(f"  Download Delay: {args.delay} seconds")
    print(f"  Concurrent Requests: {args.concurrent_requests}")
    print(f"  Log Level: {args.log_level}")
    print(f"  Output Format: {args.output_format}")
    print(f"  Output Directory: {args.output_dir}")
    
    # Calculate estimated requests
    states = args.states.split(',') if args.states else 20  # Default 20 states
    naics = args.naics.split(',') if args.naics else 12     # Default 12 NAICS
    sizes = args.size_classes.split(',') if args.size_classes else 3  # Default 3 sizes
    
    if isinstance(states, list):
        state_count = len(states)
    else:
        state_count = states
        
    if isinstance(naics, list):
        naics_count = len(naics)
    else:
        naics_count = naics
        
    if isinstance(sizes, list):
        size_count = len(sizes)
    else:
        size_count = sizes
    
    total_requests = state_count * naics_count * size_count
    estimated_time = total_requests * args.delay / 60  # Minutes
    
    print(f"\nEstimated Workload:")
    print(f"  Total API Requests: {total_requests}")
    print(f"  Estimated Time: {estimated_time:.1f} minutes")
    print(f"  Rate: {60/args.delay:.1f} requests per minute")
    
    print(f"\nTo run for real, remove the --dry-run flag")
    print("="*60)


if __name__ == '__main__':
    main() 