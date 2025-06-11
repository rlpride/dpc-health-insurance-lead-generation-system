"""Scrapy middlewares for BLS spider."""

import time
import logging
from datetime import datetime
from typing import Optional, Union

import scrapy
from scrapy import signals
from scrapy.http import Request, Response
from scrapy.spiders import Spider
from scrapy.exceptions import NotConfigured

from models import ScrapingLog, get_db_session
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitMiddleware:
    """Middleware to enforce rate limiting between requests."""
    
    def __init__(self, delay: float = 2.0, randomize_delay: float = 0.5):
        """
        Initialize rate limiting middleware.
        
        Args:
            delay: Base delay in seconds between requests
            randomize_delay: Range for randomizing delays (0.5 = ±50%)
        """
        self.delay = delay
        self.randomize_delay = randomize_delay
        self.last_request_time = 0
        
    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware from crawler settings."""
        delay = crawler.settings.getfloat('BLS_DOWNLOAD_DELAY', 2.0)
        randomize = crawler.settings.getfloat('BLS_RANDOMIZE_DOWNLOAD_DELAY', 0.5)
        
        middleware = cls(delay=delay, randomize_delay=randomize)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware
    
    def spider_opened(self, spider):
        """Log when spider opens."""
        spider.logger.info(f'Rate limiting enabled: {self.delay}s delay')
    
    def process_request(self, request: Request, spider: Spider) -> Optional[Request]:
        """Apply rate limiting before processing request."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.delay:
            sleep_time = self.delay - time_since_last
            spider.logger.debug(f'Rate limiting: sleeping {sleep_time:.2f}s')
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        return None


class ComplianceLoggingMiddleware:
    """Middleware to log all requests for compliance tracking."""
    
    def __init__(self):
        """Initialize compliance logging middleware."""
        self.request_count = 0
        self.response_count = 0
        self.error_count = 0
        self.start_time = None
        self.scraping_log_id = None
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware from crawler settings."""
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def spider_opened(self, spider: Spider):
        """Log when spider starts."""
        self.start_time = datetime.utcnow()
        
        # Create scraping log entry
        try:
            with get_db_session() as db:
                scraping_log = ScrapingLog(
                    source="BLS_SCRAPY",
                    operation_type="scrapy_spider",
                    status="running",
                    started_at=self.start_time,
                    worker_id=f"scrapy_{spider.name}",
                    extra_data={
                        "spider_name": spider.name,
                        "spider_settings": {
                            "delay": spider.settings.getfloat('BLS_DOWNLOAD_DELAY', 2.0),
                            "concurrent_requests": spider.settings.getint('CONCURRENT_REQUESTS', 16),
                        }
                    }
                )
                db.add(scraping_log)
                db.commit()
                db.refresh(scraping_log)
                self.scraping_log_id = scraping_log.id
                
        except Exception as e:
            spider.logger.error(f"Failed to create scraping log: {e}")
        
        spider.logger.info(f"Compliance logging enabled for spider: {spider.name}")
    
    def spider_closed(self, spider: Spider, reason: str):
        """Log when spider closes."""
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds() if self.start_time else 0
        
        # Update scraping log
        if self.scraping_log_id:
            try:
                with get_db_session() as db:
                    log = db.query(ScrapingLog).filter_by(id=self.scraping_log_id).first()
                    if log:
                        log.status = "success" if reason == "finished" else "failed"
                        log.completed_at = end_time
                        log.duration_seconds = int(duration)
                        log.api_calls_made = self.request_count
                        log.records_processed = self.response_count
                        log.error_count = self.error_count
                        
                        if reason != "finished":
                            log.error_message = f"Spider closed with reason: {reason}"
                        
                        db.commit()
                        
            except Exception as e:
                spider.logger.error(f"Failed to update scraping log: {e}")
        
        spider.logger.info(
            f"Spider closed: {reason}. "
            f"Requests: {self.request_count}, "
            f"Responses: {self.response_count}, "
            f"Errors: {self.error_count}, "
            f"Duration: {duration:.2f}s"
        )
    
    def process_request(self, request: Request, spider: Spider) -> Optional[Request]:
        """Log outgoing requests."""
        self.request_count += 1
        
        spider.logger.debug(
            f"Request #{self.request_count}: {request.method} {request.url}"
        )
        
        # Add compliance headers
        request.headers.setdefault('User-Agent', 
            'Lead Generation System/1.0 (Compliance-Enabled; +https://yourcompany.com/contact)')
        
        return None
    
    def process_response(self, request: Request, response: Response, spider: Spider) -> Response:
        """Log incoming responses."""
        self.response_count += 1
        
        spider.logger.debug(
            f"Response #{self.response_count}: {response.status} {response.url} "
            f"({len(response.body)} bytes)"
        )
        
        return response
    
    def process_exception(self, request: Request, exception: Exception, spider: Spider):
        """Log request exceptions."""
        self.error_count += 1
        
        spider.logger.error(
            f"Request exception #{self.error_count}: {request.url} - {exception}"
        )


class APIKeyMiddleware:
    """Middleware to add BLS API key to requests."""
    
    def __init__(self, api_key: str):
        """Initialize API key middleware."""
        if not api_key:
            raise NotConfigured("BLS API key not configured")
        self.api_key = api_key
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware from crawler settings."""
        api_key = crawler.settings.get('BLS_API_KEY') or settings.bls_api_key
        return cls(api_key=api_key)
    
    def process_request(self, request: Request, spider: Spider) -> Optional[Request]:
        """Add API key to request."""
        if 'bls.gov' in request.url:
            # Add API key as query parameter
            if '?' in request.url:
                request._set_url(f"{request.url}&registrationkey={self.api_key}")
            else:
                request._set_url(f"{request.url}?registrationkey={self.api_key}")
        
        return None


class RetryMiddleware:
    """Enhanced retry middleware for API requests."""
    
    def __init__(self, max_retry_times: int = 3, retry_http_codes: list = None):
        """Initialize retry middleware."""
        self.max_retry_times = max_retry_times
        self.retry_http_codes = retry_http_codes or [500, 502, 503, 504, 408, 429]
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware from crawler settings."""
        max_retries = crawler.settings.getint('BLS_RETRY_TIMES', 3)
        retry_codes = crawler.settings.getlist('BLS_RETRY_HTTP_CODES', [500, 502, 503, 504, 408, 429])
        return cls(max_retry_times=max_retries, retry_http_codes=retry_codes)
    
    def process_response(self, request: Request, response: Response, spider: Spider) -> Union[Request, Response]:
        """Retry failed responses."""
        if response.status in self.retry_http_codes:
            retry_times = request.meta.get('retry_times', 0) + 1
            
            if retry_times <= self.max_retry_times:
                spider.logger.warning(
                    f"Retrying {request.url} (attempt {retry_times}/{self.max_retry_times}) "
                    f"due to status {response.status}"
                )
                
                # Exponential backoff
                delay = 2 ** retry_times
                time.sleep(delay)
                
                retryreq = request.copy()
                retryreq.meta['retry_times'] = retry_times
                retryreq.dont_filter = True
                return retryreq
            else:
                spider.logger.error(
                    f"Gave up retrying {request.url} after {retry_times} attempts"
                )
        
        return response 