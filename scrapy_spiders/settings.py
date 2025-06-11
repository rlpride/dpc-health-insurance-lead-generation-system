"""Scrapy settings for BLS spider project."""

import os
from pathlib import Path

# Project settings
BOT_NAME = 'bls_spider'

SPIDER_MODULES = ['scrapy_spiders.spiders']
NEWSPIDER_MODULE = 'scrapy_spiders.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# User agent
USER_AGENT = 'Lead Generation System/1.0 (Compliance-Enabled; +https://yourcompany.com/contact)'

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 1  # Conservative for API scraping
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# Configure delays for requests
DOWNLOAD_DELAY = 2  # 2 seconds delay between requests
RANDOMIZE_DOWNLOAD_DELAY = 0.5  # Randomize delay (0.5 * to 1.5 * DOWNLOAD_DELAY)

# Auto-throttle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = True  # Enable to see throttling stats

# Configure pipelines
ITEM_PIPELINES = {
    'scrapy_spiders.pipelines.ValidationPipeline': 100,
    'scrapy_spiders.pipelines.CleaningPipeline': 200,
    'scrapy_spiders.pipelines.DeduplicationPipeline': 300,
    'scrapy_spiders.pipelines.DatabasePipeline': 400,
    'scrapy_spiders.pipelines.QueueingPipeline': 500,
}

# Configure downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'scrapy_spiders.middlewares.RateLimitMiddleware': 100,
    'scrapy_spiders.middlewares.ComplianceLoggingMiddleware': 200,
    'scrapy_spiders.middlewares.APIKeyMiddleware': 300,
    'scrapy_spiders.middlewares.RetryMiddleware': 400,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,  # Disable default retry
}

# Retry settings
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 404]

# Disable cookies (not needed for API)
COOKIES_ENABLED = False

# Disable telnet console
TELNETCONSOLE_ENABLED = False

# Request fingerprinting implementation
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'

# Twisted reactor
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

# Feed exports
FEEDS = {
    'results/bls_data.json': {
        'format': 'json',
        'encoding': 'utf8',
        'store_empty': False,
        'indent': 2,
    },
    'results/bls_data.csv': {
        'format': 'csv',
        'encoding': 'utf8',
        'store_empty': False,
    }
}

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/scrapy.log'

# BLS specific settings
BLS_DOWNLOAD_DELAY = 2.0
BLS_RANDOMIZE_DOWNLOAD_DELAY = 0.5
BLS_RETRY_TIMES = 3
BLS_RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# API keys (loaded from environment)
BLS_API_KEY = os.getenv('BLS_API_KEY')

# Custom settings for different environments
if os.getenv('SCRAPY_ENV') == 'production':
    # Production settings
    LOG_LEVEL = 'WARNING'
    AUTOTHROTTLE_DEBUG = False
    DOWNLOAD_DELAY = 3  # More conservative in production
    
elif os.getenv('SCRAPY_ENV') == 'development':
    # Development settings
    LOG_LEVEL = 'DEBUG'
    AUTOTHROTTLE_DEBUG = True
    
# Create necessary directories
Path('logs').mkdir(exist_ok=True)
Path('results').mkdir(exist_ok=True) 