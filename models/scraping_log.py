"""Scraping log model for tracking data collection operations."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class ScrapingLog(Base):
    """Model for logging scraping operations and their results."""
    
    __tablename__ = "scraping_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Operation details
    source = Column(String(50), nullable=False, index=True)  # BLS, SAM_GOV, etc.
    operation_type = Column(String(50))  # initial_scrape, update, retry
    target_url = Column(Text)
    target_state = Column(String(2))  # For state-specific scraping
    target_naics = Column(String(6))  # For NAICS-specific scraping
    
    # Results
    status = Column(String(20), nullable=False, index=True)  # running, success, failed, timeout
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Performance metrics
    duration_seconds = Column(Integer)
    api_calls_made = Column(Integer, default=0)
    bytes_downloaded = Column(Integer)
    
    # Error tracking
    error_count = Column(Integer, default=0)
    error_message = Column(Text)
    error_details = Column(JSON)
    
    # Timing
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Additional metadata
    worker_id = Column(String(50))  # ID of the worker/agent that performed the scraping
    batch_id = Column(String(50))  # For grouping related scraping operations
    extra_data = Column(JSON, default=dict)
    
    def __repr__(self) -> str:
        return f"<ScrapingLog(id={self.id}, source='{self.source}', status='{self.status}', records={self.records_processed})>"
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of processed records."""
        if self.records_processed == 0:
            return 0.0
        return (self.records_created + self.records_updated) / self.records_processed * 100
    
    @property
    def is_successful(self) -> bool:
        """Check if the scraping operation was successful."""
        return self.status == "success"
    
    def to_dict(self) -> dict:
        """Convert scraping log to dictionary representation."""
        return {
            "id": str(self.id),
            "source": self.source,
            "status": self.status,
            "records_processed": self.records_processed,
            "records_created": self.records_created,
            "records_updated": self.records_updated,
            "error_count": self.error_count,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success_rate": self.success_rate,
        } 