"""Base scraper class with common functionality."""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from tenacity import retry, stop_after_attempt, wait_exponential
import httpx

from config import get_settings
from models import ScrapingLog, get_db_session

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""
    
    def __init__(self, worker_id: Optional[str] = None):
        """Initialize the base scraper."""
        self.worker_id = worker_id or f"worker_{uuid4().hex[:8]}"
        self.settings = settings
        self.session = None
        self.scraping_log = None
        self.stats = {
            "records_processed": 0,
            "records_created": 0,
            "records_updated": 0,
            "records_failed": 0,
            "errors": []
        }
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the data source."""
        pass
    
    @property
    @abstractmethod
    def rate_limit_seconds(self) -> int:
        """Return the rate limit in seconds for this source."""
        pass
    
    def start_scraping_session(self, operation_type: str = "scrape", **kwargs) -> ScrapingLog:
        """Start a new scraping session and create a log entry."""
        with get_db_session() as db:
            self.scraping_log = ScrapingLog(
                source=self.source_name,
                operation_type=operation_type,
                status="running",
                started_at=datetime.utcnow(),
                worker_id=self.worker_id,
                extra_data=kwargs
            )
            db.add(self.scraping_log)
            db.commit()
            db.refresh(self.scraping_log)
        
        logger.info(f"Started {self.source_name} scraping session: {self.scraping_log.id}")
        return self.scraping_log
    
    def update_scraping_log(self, status: str = "running", error_message: Optional[str] = None):
        """Update the current scraping log."""
        if not self.scraping_log:
            return
        
        with get_db_session() as db:
            log = db.query(ScrapingLog).filter_by(id=self.scraping_log.id).first()
            if log:
                log.status = status
                log.records_processed = self.stats["records_processed"]
                log.records_created = self.stats["records_created"]
                log.records_updated = self.stats["records_updated"]
                log.records_failed = self.stats["records_failed"]
                log.error_count = len(self.stats["errors"])
                
                if error_message:
                    log.error_message = error_message
                
                if status in ["success", "failed"]:
                    log.completed_at = datetime.utcnow()
                    if log.started_at:
                        duration = (log.completed_at - log.started_at).total_seconds()
                        log.duration_seconds = int(duration)
                
                db.commit()
    
    def rate_limit(self):
        """Apply rate limiting between requests."""
        time.sleep(self.rate_limit_seconds)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def make_request(self, url: str, method: str = "GET", **kwargs) -> httpx.Response:
        """Make an HTTP request with retry logic."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate scraped data before processing."""
        # Override in subclasses for specific validation
        return bool(data)
    
    def clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize scraped data."""
        # Remove None values and strip strings
        cleaned = {}
        for key, value in data.items():
            if value is not None:
                if isinstance(value, str):
                    value = value.strip()
                    if value:  # Only include non-empty strings
                        cleaned[key] = value
                else:
                    cleaned[key] = value
        return cleaned
    
    @abstractmethod
    async def scrape(self, **kwargs) -> List[Dict[str, Any]]:
        """Main scraping method to be implemented by subclasses."""
        pass
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Run the scraper with error handling and logging."""
        try:
            # Start scraping session
            self.start_scraping_session(**kwargs)
            
            # Run the actual scraping
            results = await self.scrape(**kwargs)
            
            # Update final stats
            self.update_scraping_log(status="success")
            
            logger.info(
                f"{self.source_name} scraping completed: "
                f"{self.stats['records_processed']} processed, "
                f"{self.stats['records_created']} created, "
                f"{self.stats['records_updated']} updated"
            )
            
            return {
                "success": True,
                "stats": self.stats,
                "scraping_log_id": str(self.scraping_log.id) if self.scraping_log else None
            }
            
        except Exception as e:
            logger.error(f"{self.source_name} scraping failed: {str(e)}")
            self.stats["errors"].append(str(e))
            self.update_scraping_log(status="failed", error_message=str(e))
            
            return {
                "success": False,
                "error": str(e),
                "stats": self.stats,
                "scraping_log_id": str(self.scraping_log.id) if self.scraping_log else None
            } 